from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from climate import (  # noqa: E402
    diurnal_stats, gcp_file_and_offset, ls_time_weight, mcd_annual_stats, parse_gcp_rows, parse_mcd_table,
)
from terrain import bilinear, grid_points, sample_grid, terrain_metrics  # noqa: E402


def test_grid_spacing_is_120_m_on_the_body_sphere():
    radius = 3396190.0
    pts = grid_points(10.0, 20.0, radius)
    assert len(pts) == 49
    (lat0, lon0), (lat1, lon1) = pts[24], pts[25]
    assert (lat0, lon0) == pytest.approx((10.0, 20.0))
    east_m = math.radians(lon1 - lon0) * radius * math.cos(math.radians(lat0))
    north_m = math.radians(pts[31][0] - lat0) * radius
    assert east_m == pytest.approx(120.0, rel=1e-6)
    assert north_m == pytest.approx(120.0, rel=1e-6)


def test_terrain_metrics_on_a_tilted_plane_matches_its_slope():
    spacing = 120.0
    # z rises 12 m per 120 m eastwards: slope atan(0.1)
    z = [12.0 * ix for iy in range(7) for ix in range(7)]
    m = terrain_metrics(z)
    assert m["slope_deg"] == pytest.approx(math.degrees(math.atan(12.0 / spacing)))
    assert m["relative_relief_m"] == pytest.approx(72.0)
    assert m["elevation_m"] == pytest.approx(36.0)


def test_terrain_metrics_refuses_to_guess_with_too_few_values():
    m = terrain_metrics([None] * 45 + [1.0, 2.0, 3.0, 4.0])
    assert m["slope_deg"] is None and m["relative_relief_m"] is None


def test_bilinear_and_sample_grid_use_cell_values_only():
    window = [[0.0, 10.0], [20.0, 30.0]]
    assert bilinear(window, 0.5, 0.5) == pytest.approx(15.0)
    assert bilinear([[0.0, None], [1.0, 1.0]], 0.5, 0.5) is None
    calls = []

    def read_window(col, row, w, h):
        calls.append((col, row, w, h))
        return [[float(c + r) for c in range(col, col + w)] for r in range(row, row + h)]

    z = sample_grid([(0.0, 0.0), (1.0, 1.0)], lambda lat, lon: (10.0 + lon, 5.0 + lat), read_window)
    assert len(calls) == 1
    assert z == pytest.approx([15.0, 17.0])


MCD_SAMPLE = """###
### Columns 2+ are Temperature (K)
---- ||    0.0 1.0
-----------------------------------
"""


def _mcd_text(rows):
    lines = [MCD_SAMPLE]
    for ls, vals in rows:
        lines.append("%+04d || " % ls + " ".join("%.5e" % v for v in vals))
    return "\n".join(lines)


def test_mcd_annual_stats_weights_seasons_by_time():
    flat = [(ls, [200.0] * 24 + [200.0]) for ls in range(0, 361, 15)]
    s = mcd_annual_stats(parse_mcd_table(_mcd_text(flat)))
    assert s["mean_K"] == pytest.approx(200.0)
    assert s["diurnal_range_K"] == pytest.approx(0.0)
    assert s["n_ls"] == 24  # Ls = 360 duplicates Ls = 0 and is dropped
    # Mars moves slowest near aphelion (Ls ~ 71°), so that season weighs more.
    assert ls_time_weight(71.0) > ls_time_weight(251.0)


def test_mcd_stats_need_a_full_diurnal_cycle():
    with pytest.raises(ValueError):
        mcd_annual_stats([(0.0, [200.0] * 10)])


def test_gcp_offset_for_marius_hills_bin():
    name, offset, centre = gcp_file_and_offset(14.0917, -56.7701)
    assert name == "global_cumul_avg_cyl_10n20n_002.tab"
    assert centre == pytest.approx((14.25, -56.75))
    # lon index 246, lat index 8, 96 local-time rows each, one header record
    assert offset == 113 * (1 + (246 * 20 + 8) * 96)
    with pytest.raises(ValueError):
        gcp_file_and_offset(-5.0, 10.0)


def test_gcp_parsing_and_gap_filling():
    rows = parse_gcp_rows(
        " -56.75,  14.25,   0.12, 1, 1, 1, 1, 1, 1, 1,  100.0\n"
        " -56.75,  14.25,   0.38, 1, 1, 1, 1, 1, 1, 1,  -9999\n"
        " -56.75,  14.25,   0.62, 1, 1, 1, 1, 1, 1, 1,  300.0\n"
        " -56.75,  14.25,   0.88, 1, 1, 1, 1, 1, 1, 1,  -9999\n"
    )
    temps = [t for *_, t in rows]
    assert temps == [100.0, None, 300.0, None]
    s = diurnal_stats(temps)
    # gaps are filled linearly: 100, 200, 300, 200
    assert s["mean_K"] == pytest.approx(200.0)
    assert s["diurnal_range_K"] == pytest.approx(200.0)
    assert s["n_valid"] == 2 and s["max_gap_bins"] == 1
