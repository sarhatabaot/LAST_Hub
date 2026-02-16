(function () {
  const formatUtc = (date) => {
    const days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
    const months = [
      "Jan",
      "Feb",
      "Mar",
      "Apr",
      "May",
      "Jun",
      "Jul",
      "Aug",
      "Sep",
      "Oct",
      "Nov",
      "Dec",
    ];
    const dayName = days[date.getUTCDay()];
    const day = String(date.getUTCDate()).padStart(2, "0");
    const month = months[date.getUTCMonth()];
    const year = date.getUTCFullYear();
    const time = date.toISOString().slice(11, 19);
    return `${dayName}, ${day} ${month} ${year} ${time} GMT`;
  };

  const toDegrees = (rad) => (rad * 180) / Math.PI;
  const toRadians = (deg) => (deg * Math.PI) / 180;

  const julianDate = (date) => date.getTime() / 86400000 + 2440587.5;

  const normalizeAngle = (deg) => {
    let value = deg % 360;
    if (value < 0) value += 360;
    return value;
  };

  const greenwichSiderealTime = (jd) => {
    const t = (jd - 2451545.0) / 36525.0;
    const gst =
      280.46061837 +
      360.98564736629 * (jd - 2451545.0) +
      0.000387933 * t * t -
      (t * t * t) / 38710000;
    return normalizeAngle(gst);
  };

  const lstFromLongitude = (jd, lonDeg) => {
    const gst = greenwichSiderealTime(jd);
    return normalizeAngle(gst + lonDeg);
  };

  const angleToTime = (deg) => {
    const totalSeconds = (deg / 360) * 24 * 3600;
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = Math.floor(totalSeconds % 60);
    return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(
      seconds
    ).padStart(2, "0")}`;
  };

  const sunPosition = (jd) => {
    const n = jd - 2451545.0;
    const l = normalizeAngle(280.460 + 0.9856474 * n);
    const g = normalizeAngle(357.528 + 0.9856003 * n);
    const gRad = toRadians(g);
    const lambda = l + 1.915 * Math.sin(gRad) + 0.02 * Math.sin(2 * gRad);
    const lambdaRad = toRadians(lambda);
    const epsilon = toRadians(23.439 - 0.0000004 * n);
    const alpha = Math.atan2(Math.cos(epsilon) * Math.sin(lambdaRad), Math.cos(lambdaRad));
    const delta = Math.asin(Math.sin(epsilon) * Math.sin(lambdaRad));
    return { ra: normalizeAngle(toDegrees(alpha)), dec: toDegrees(delta) };
  };

  const moonPosition = (jd) => {
    const n = jd - 2451545.0;
    const l = normalizeAngle(218.316 + 13.176396 * n);
    const m = normalizeAngle(134.963 + 13.064993 * n);
    const f = normalizeAngle(93.272 + 13.229350 * n);

    const lRad = toRadians(l);
    const mRad = toRadians(m);
    const fRad = toRadians(f);

    const lambda = l + 6.289 * Math.sin(mRad);
    const beta = 5.128 * Math.sin(fRad);

    const lambdaRad = toRadians(lambda);
    const betaRad = toRadians(beta);
    const epsilon = toRadians(23.439 - 0.0000004 * n);

    const alpha = Math.atan2(
      Math.sin(lambdaRad) * Math.cos(epsilon) -
        Math.tan(betaRad) * Math.sin(epsilon),
      Math.cos(lambdaRad)
    );
    const delta = Math.asin(
      Math.sin(betaRad) * Math.cos(epsilon) +
        Math.cos(betaRad) * Math.sin(epsilon) * Math.sin(lambdaRad)
    );

    return { ra: normalizeAngle(toDegrees(alpha)), dec: toDegrees(delta) };
  };

  const altitudeFromRaDec = (lstDeg, latDeg, raDeg, decDeg) => {
    const ha = normalizeAngle(lstDeg - raDeg);
    const haRad = toRadians(ha);
    const latRad = toRadians(latDeg);
    const decRad = toRadians(decDeg);
    const sinAlt =
      Math.sin(decRad) * Math.sin(latRad) +
      Math.cos(decRad) * Math.cos(latRad) * Math.cos(haRad);
    return toDegrees(Math.asin(sinAlt));
  };

  const buildSkyText = (date, latDeg, lonDeg) => {
    const jd = julianDate(date);
    const lstDeg = lstFromLongitude(jd, lonDeg);
    const sun = sunPosition(jd);
    const moon = moonPosition(jd);
    const sunAlt = altitudeFromRaDec(lstDeg, latDeg, sun.ra, sun.dec);
    const moonAlt = altitudeFromRaDec(lstDeg, latDeg, moon.ra, moon.dec);
    const lstTime = angleToTime(lstDeg);
    const utcLabel = formatUtc(date);

    const deg = "\u00b0";
    return `${utcLabel} - LST: ${lstTime} (${lstDeg.toFixed(3)}${deg}) - Local Sun Altitude: ${sunAlt.toFixed(
      2
    )}${deg} Moon Altitude: ${moonAlt.toFixed(2)}${deg}`;
  };

  const initSkybox = (node) => {
    const lat = Number(node.dataset.lat);
    const lon = Number(node.dataset.lon);

    if (!Number.isFinite(lat) || !Number.isFinite(lon)) {
      node.textContent = "Sky data unavailable";
      return;
    }

    const update = () => {
      const now = new Date();
      node.textContent = buildSkyText(now, lat, lon);
    };

    update();
    setInterval(update, 1000);
  };

  document.addEventListener("DOMContentLoaded", () => {
    const node = document.querySelector("[data-skybox]");
    if (node) {
      initSkybox(node);
    }
  });
})();
