from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from polar import (  # noqa: E402
    MOON_RADIUS_M, destination, local_grid_points, lower_bound, parse_pcp_line, pcp_bin_value,
    pcp_summary, polar_xy_south,
)

R = MOON_RADIUS_M
STEP = 240.0 / R


def test_polar_xy_matches_a_published_pcp_row():
    # First record of pcp_avg_tbol_pols_sum_ltim01_240: x=-0.174908, y=-0.000829 at lon -90.27, lat -80.00383
    x, y = polar_xy_south(-80.00383, -90.271559)
    assert x / R == pytest.approx(-0.174908, abs=2e-6)
    assert y / R == pytest.approx(-0.000829, abs=2e-6)


def test_polar_xy_pole_is_origin_and_orientation():
    assert polar_xy_south(-90.0, 123.0) == pytest.approx((0.0, 0.0), abs=1e-6)
    x, y = polar_xy_south(-85.0, 0.0)
    assert x == pytest.approx(0.0, abs=1e-6) and y > 0
    x, y = polar_xy_south(-85.0, 90.0)
    assert x > 0 and y == pytest.approx(0.0, abs=1e-6)


def test_destination_moves_the_requested_distance():
    lat, lon = destination(-89.655, 129.174, 120.0, 0.0)
    # great-circle distance back to the start
    p1, p2 = math.radians(-89.655), math.radians(lat)
    dlon = math.radians(lon - 129.174)
    cos_d = math.sin(p1) * math.sin(p2) + math.cos(p1) * math.cos(p2) * math.cos(dlon)
    assert math.acos(cos_d) * R == pytest.approx(120.0, rel=1e-6)


def test_destination_with_zero_offset_is_identity():
    assert destination(-88.0, 10.0, 0.0, 0.0) == (-88.0, 10.0)


def test_local_grid_is_7x7_centred_and_120_m_apart_near_the_pole():
    pts = local_grid_points(-89.655, 129.174)
    assert len(pts) == 49
    assert pts[24] == pytest.approx((-89.655, 129.174))
    x0, y0 = polar_xy_south(*pts[24])
    x1, y1 = polar_xy_south(*pts[25])
    x2, y2 = polar_xy_south(*pts[31])
    # on the projection the spacing equals 120 m times the local scale factor (~1 within 1e-5 of the pole)
    assert math.hypot(x1 - x0, y1 - y0) == pytest.approx(120.0, rel=1e-3)
    assert math.hypot(x2 - x0, y2 - y0) == pytest.approx(120.0, rel=1e-3)


def test_lower_bound_finds_first_not_less():
    keys = [1, 2, 2, 5, 9]
    assert lower_bound(len(keys), lambda i: keys[i], 2) == 1
    assert lower_bound(len(keys), lambda i: keys[i], 3) == 3
    assert lower_bound(len(keys), lambda i: keys[i], 10) == 5
    assert lower_bound(len(keys), lambda i: keys[i], 0) == 0


def test_parse_pcp_line():
    line = "-0.174908, -0.000829,  -90.271559, -80.003830,  75.385880"
    assert parse_pcp_line(line) == (-0.174908, -0.000829, 75.38588)
    assert parse_pcp_line("        x,         y,        clon,       clat,       tbol") is None


def _table():
    rows = []
    for ix in range(-3, 4):
        for iy in range(-3, 4):
            if (ix, iy) == (1, 1):
                continue  # empty bin is omitted in the product
            rows.append((ix * STEP, iy * STEP, 100.0 + 10 * ix + iy))
    return rows


def _reader(rows):
    return lambda first, count: rows[first:first + count]


def test_pcp_bin_value_picks_the_containing_bin():
    rows = _table()
    t = pcp_bin_value(2 * STEP + STEP * 0.3, -1 * STEP - STEP * 0.2, len(rows), _reader(rows))
    assert t == pytest.approx(100.0 + 20 - 1)


def test_pcp_bin_value_is_none_for_an_omitted_bin_or_outside():
    rows = _table()
    assert pcp_bin_value(1 * STEP, 1 * STEP, len(rows), _reader(rows)) is None
    assert pcp_bin_value(9 * STEP, 0.0, len(rows), _reader(rows)) is None
    assert pcp_bin_value(-9 * STEP, 0.0, len(rows), _reader(rows)) is None


def test_pcp_summary_averages_both_seasons():
    summer = [100.0 + (i % 2) * 20 for i in range(96)]
    winter = [80.0 + (i % 2) * 40 for i in range(96)]
    s = pcp_summary({"sum": summer, "win": winter})
    assert s["mean_K"] == pytest.approx((110.0 + 100.0) / 2)
    assert s["diurnal_range_K"] == pytest.approx((20.0 + 40.0) / 2)
    assert s["max_K"] == 120.0
