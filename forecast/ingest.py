"""IMS ICON forecast download + extraction.

Replaces the external `FORECAST_URL` provider by fetching NetCDF files from the
Israel Meteorological Service directly and writing a JSON cache shaped to match
what the existing services layer already consumes.
"""
from __future__ import annotations

import bz2
import json
import logging
import math
import shutil
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Iterator

import requests
import urllib3
from requests_ntlm import HttpNtlmAuth

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SeriesSpec:
    output_key: str
    field: str
    variable: str
    plev: int | None = None
    transform: Callable | None = None


def _kelvin_to_celsius(da):
    return da - 273.15


SERIES = (
    SeriesSpec("total_cloud_cover", "clct", "clct"),
    SeriesSpec("high_cloud_cover", "clch", "clch"),
    SeriesSpec("medium_cloud_cover", "clcm", "clcm"),
    SeriesSpec("low_cloud_cover", "clcl", "clcl"),
    SeriesSpec("temperature", "temp", "temp", plev=97500, transform=_kelvin_to_celsius),
    SeriesSpec("total_precipitation", "tot_prec", "tot_prec"),
    SeriesSpec("relative_humidity", "rh", "rh", plev=97500),
)


class IMSClient:
    def __init__(self, username, password, base_url, directory, verify_ssl=False):
        if not verify_ssl:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        self._username = username
        self._password = password
        self._base = base_url.rstrip("/")
        self._directory = directory.strip("/")
        self._verify_ssl = verify_ssl

    def _url(self, filename: str) -> str:
        return f"{self._base}/ims/{self._directory}/{filename}"

    def _get(self, filename: str, timeout: float):
        return requests.get(
            self._url(filename),
            auth=HttpNtlmAuth(self._username, self._password),
            verify=self._verify_ssl,
            stream=True,
            timeout=timeout,
        )

    def remote_exists(self, filename: str) -> bool:
        with self._get(filename, timeout=30) as response:
            return response.status_code == 200

    def download(self, filename: str, dest: Path) -> bool:
        with self._get(filename, timeout=120) as response:
            if response.status_code != 200:
                return False
            with open(dest, "wb") as out:
                for chunk in response.iter_content(chunk_size=1 << 20):
                    if chunk:
                        out.write(chunk)
        return True


def _build_filename(date_value: datetime, time_slot: str, field: str) -> str:
    return f"IE_{date_value:%Y%m%d}{time_slot}_{field}.nc.bz2"


def _find_latest_filename(
    client: IMSClient,
    field: str,
    today: datetime,
    max_days_back: int = 3,
    time_slots: tuple[str, ...] = ("12", "00"),
) -> str | None:
    for day_offset in range(max_days_back + 1):
        date_value = today - timedelta(days=day_offset)
        for slot in time_slots:
            filename = _build_filename(date_value, slot, field)
            if client.remote_exists(filename):
                return filename
    return None


def _prune_old_files(directory: Path, retention_days: int, today: datetime) -> int:
    cutoff = today.date() - timedelta(days=retention_days)
    removed = 0
    for path in directory.glob("IE_*.nc.bz2"):
        try:
            file_date = datetime.strptime(path.name[3:11], "%Y%m%d").date()
        except (ValueError, IndexError):
            continue
        if file_date < cutoff:
            path.unlink(missing_ok=True)
            removed += 1
    return removed


def _download_latest(
    client: IMSClient,
    directory: Path,
    fields: tuple[str, ...],
    today: datetime,
    max_days_back: int = 3,
) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for field in fields:
        filename = _find_latest_filename(client, field, today, max_days_back=max_days_back)
        if filename is None:
            logger.warning("No remote IMS file found for field %s", field)
            continue
        target = directory / filename
        if target.exists():
            continue
        if not client.download(filename, target):
            logger.warning("IMS download failed for %s", filename)


def _latest_file_per_field(directory: Path, fields: tuple[str, ...]) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for field in fields:
        candidates = sorted(
            directory.glob(f"IE_*_{field}.nc.bz2"),
            key=lambda p: p.name[3:13],
            reverse=True,
        )
        if candidates:
            result[field] = candidates[0]
    return result


@contextmanager
def _open_bz2_netcdf(path: Path) -> Iterator:
    import xarray as xr

    with tempfile.NamedTemporaryFile(suffix=".nc", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        with bz2.open(path, "rb") as src:
            shutil.copyfileobj(src, tmp)
    try:
        with xr.open_dataset(tmp_path) as ds:
            yield ds
    finally:
        tmp_path.unlink(missing_ok=True)


def _to_epoch_ms(time_array) -> list[int]:
    return time_array.values.astype("datetime64[ms]").astype("int64").tolist()


def _clean(values: list) -> list:
    cleaned = []
    for v in values:
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            cleaned.append(None)
        else:
            cleaned.append(v)
    return cleaned


def _extract_series(
    file_path: Path,
    spec: SeriesSpec,
    lat: float,
    lon: float,
) -> dict[str, list]:
    selectors: dict[str, float | int] = {"lat": lat, "lon": lon}
    if spec.plev is not None:
        selectors["plev"] = spec.plev

    with _open_bz2_netcdf(file_path) as ds:
        point = ds.sel(method="nearest", **selectors)
        var = point[spec.variable]
        if spec.transform is not None:
            var = spec.transform(var)
        times = _to_epoch_ms(point["time"])
        values = _clean(var.values.tolist())

    return {"time": times, "value": values}


def _build_cache_payload(
    directory: Path,
    lat: float,
    lon: float,
) -> dict[str, dict[str, list]]:
    fields = tuple(spec.field for spec in SERIES)
    files_by_field = _latest_file_per_field(directory, fields)

    payload: dict[str, dict[str, list]] = {}
    for spec in SERIES:
        file_path = files_by_field.get(spec.field)
        if file_path is None:
            logger.warning("No local file for field %s; skipping series", spec.field)
            continue
        try:
            payload[spec.output_key] = _extract_series(file_path, spec, lat, lon)
        except Exception:
            logger.exception("Failed to extract %s from %s", spec.output_key, file_path)
    return payload


def _atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w") as f:
        json.dump(payload, f)
    tmp.replace(path)


def run(
    *,
    username: str,
    password: str,
    base_url: str,
    directory: str,
    data_dir: Path,
    cache_path: Path,
    location: tuple[float, float],
    verify_ssl: bool = False,
    retention_days: int = 2,
    today: datetime | None = None,
) -> dict[str, dict[str, list]]:
    """Download latest IMS files, extract series at the observatory point, write the JSON cache."""
    today = today or datetime.now(timezone.utc)
    data_dir = Path(data_dir)
    cache_path = Path(cache_path)

    client = IMSClient(username, password, base_url, directory, verify_ssl=verify_ssl)
    fields = tuple(spec.field for spec in SERIES)

    _prune_old_files(data_dir, retention_days, today)
    _download_latest(client, data_dir, fields, today)

    lat, lon = location
    payload = _build_cache_payload(data_dir, lat, lon)
    _atomic_write_json(cache_path, payload)
    return payload
