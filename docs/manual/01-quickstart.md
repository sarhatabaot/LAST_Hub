# Quickstart

This is a quickstart guide for new observers with essential information for your shift.

---

## 1. Weather station monitoring (Grafana)

Monitor weather stations through Grafana via the browser on any computer in the wired WIS network or in the observatory.

**Access URLs:**

* **Primary:** [http://10.23.1.25/grafana](http://10.23.1.25/grafana)
* **Secondary:** [http://10.23.1.25:3000/grafana](http://10.23.1.25:3000/grafana)
* **Fallback:** [http://127.0.0.1:3000/grafana](http://127.0.0.1:3000/grafana)
* **VPN Access:** [http://10.23.1.25/grafana](http://10.23.1.25/grafana) (Does not require NoMachine)
* **New:** [http://10.23.1.25/grafana-new](http://10.23.1.25/grafana-new) (username: ocs, password: physics)

**Troubleshooting:**

* If weather plots are empty, restart the service using:

  ```bash
  sudo systemctl restart last-safety-daemon
  ```
* Additional instructions: [Grafana Troubleshooting Wiki](https://github.com/blumzi/WAO_Safety/wiki/troubleshooting)

---

## 2. Closure conditions

The observatory **must** be closed if any of these conditions are reached:

| Metric                | Threshold | Action                            |
|-----------------------|-----------|-----------------------------------|
| **Internal Humidity** | > 80%     | **Close Observatory**             |
| **Wind Speed**        | > 40 km/h | **Close Observatory**             |
| **Wind Speed**        | > 10 km/h | Close Northern and Southern walls |

---

## 3. External conditions & surveillance

### Cloud coverage & forecasts

* **Satellite Images:** [Sat24 (Israel)](https://www.sat24.com/en-gb/country/il) and [Zoom Earth](https://zoom.earth/)
* **Weather Forecasts:** [Meteoblue Astronomy Seeing](https://www.meteoblue.com/en/weather/outdoors/seeing/ne%E2%80%99ot-semadar_israel_8346527) and [YR.no Details](https://www.yr.no/nb/detaljer/tabell/2-8346527/Israel/S%C3%B8rdistriktet/Ne%E2%80%99ot%20Semadar)

### Visual monitoring

Periodically monitor the situation in the observatory using the webcams:

* **Webcam Stream:** [http://10.23.1.25:8000/webcams.html](http://10.23.1.25:8000/webcams.html)

---

## 4. Telescope & image quality

### MultiPanel monitoring

* **Mount Status:** Ensure status is **‘tracking’** during observations.
* **⚠️ Critical:** If status is **‘idle’** while observing, call your backup expert observer immediately.

### Focus and FWHM

Periodically check the focus of each telescope via the FWHM reported in the MultiPanel. If **FWHM > 4**, follow these steps:

1. **Check Images:** Inspect specific unit images following the detailed guide.
2. **Diagnose Elongation:** If stars are only slightly elongated, it may be wind. If this occurs before 1:00 AM, call your backup expert observer to raise the walls.
3. **Diagnose Focus:** If stars appear out of focus:
   * Call your backup expert observer.
   * **Alternatively:** If you are experienced, stop observations on the specific mount, refocus, and then restart observations.