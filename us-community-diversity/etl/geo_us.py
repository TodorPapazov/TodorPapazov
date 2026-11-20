"""Project US county shapes into one page layout.

Lower 48, Alaska, and Hawaii each use an Albers equal-area cone, then each
group is fitted into a fixed box. Alaska and Hawaii sit below the lower 48.
"""

from __future__ import annotations

import math

WIDTH = 960
HEIGHT = 600
LOWER_BOX = (24, 12, 936, 458)
ALASKA_BOX = (28, 468, 250, 588)
HAWAII_BOX = (268, 492, 430, 588)


def project_counties(counties):
    """Return page coordinates for county polygons.

    ``counties`` items need ``fips`` and ``rings`` of ``(longitude, latitude)``
    points. The result items add ``state``, projected ``rings``, and ``box``.
    """

    grouped = {"lower": [], "alaska": [], "hawaii": []}
    for county in counties:
        state = county["fips"][:2]
        if state == "02":
            grouped["alaska"].append(county)
        elif state == "15":
            grouped["hawaii"].append(county)
        else:
            grouped["lower"].append(county)
    projected = []
    projected.extend(_place(grouped["lower"], _lower, LOWER_BOX))
    projected.extend(_place(grouped["alaska"], _alaska, ALASKA_BOX))
    projected.extend(_place(grouped["hawaii"], _hawaii, HAWAII_BOX))
    projected.sort(key=lambda county: county["fips"])
    return projected


def _place(counties, project, box):
    raw = []
    for county in counties:
        rings = []
        for ring in county["rings"]:
            points = []
            for lon, lat in ring:
                if not math.isfinite(lon) or not math.isfinite(lat):
                    continue
                try:
                    points.append(project(lon, lat))
                except ValueError:
                    continue
            if len(points) >= 3:
                rings.append(points)
        if rings:
            raw.append({"fips": county["fips"], "state": county["fips"][:2], "rings": rings})
    return _fit(raw, box)


def _fit(counties, box):
    xs = [point[0] for county in counties for ring in county["rings"] for point in ring]
    ys = [point[1] for county in counties for ring in county["rings"] for point in ring]
    if not xs:
        return []
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    left, top, right, bottom = box
    span_x = max(max_x - min_x, 1e-9)
    span_y = max(max_y - min_y, 1e-9)
    pad = 0.04
    scale = min((right - left) * (1 - 2 * pad) / span_x, (bottom - top) * (1 - 2 * pad) / span_y)
    offset_x = left + ((right - left) - span_x * scale) / 2
    offset_y = top + ((bottom - top) - span_y * scale) / 2
    placed = []
    for county in counties:
        rings = []
        for ring in county["rings"]:
            screen = []
            for x_value, y_value in ring:
                screen_x = round(offset_x + (x_value - min_x) * scale, 1)
                screen_y = round(offset_y + (max_y - y_value) * scale, 1)
                if screen and abs(screen[-1][0] - screen_x) < 0.4 and abs(screen[-1][1] - screen_y) < 0.4:
                    continue
                screen.append([screen_x, screen_y])
            if len(screen) >= 3:
                rings.append(screen)
        if not rings:
            continue
        xs = [point[0] for ring in rings for point in ring]
        ys = [point[1] for ring in rings for point in ring]
        placed.append(
            {
                "fips": county["fips"],
                "state": county["state"],
                "rings": rings,
                "box": [min(xs), min(ys), max(xs), max(ys)],
            }
        )
    return placed


def _lower(lon, lat):
    return _albers(lon, lat, -96.0, 23.0, 29.5, 45.5)


def _alaska(lon, lat):
    if lon > 0:
        lon -= 360.0
    return _albers(lon, lat, -154.0, 50.0, 55.0, 65.0)


def _hawaii(lon, lat):
    return _albers(lon, lat, -157.0, 13.0, 8.0, 18.0)


def _albers(lon, lat, lon0, lat0, lat1, lat2):
    phi = math.radians(lat)
    phi0 = math.radians(lat0)
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    lam = math.radians(lon - lon0)
    n_value = (math.sin(phi1) + math.sin(phi2)) / 2.0
    if n_value == 0:
        raise ValueError("Albers parallels are symmetrical.")
    c_value = math.cos(phi1) ** 2 + 2 * n_value * math.sin(phi1)
    rho0 = math.sqrt(c_value - 2 * n_value * math.sin(phi0)) / n_value
    rho = math.sqrt(c_value - 2 * n_value * math.sin(phi)) / n_value
    theta = n_value * lam
    return rho * math.sin(theta), rho0 - rho * math.cos(theta)
