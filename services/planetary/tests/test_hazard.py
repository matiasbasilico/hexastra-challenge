from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hazard import (  # noqa: E402
    MIN_VALID_CELLS, SLOPE_THRESHOLDS_DEG, cell_slopes, feature_id, is_sea_fill, slope_fractions,
)
from terrain import terrain_metrics  # noqa: E402


def plane(slope_deg: float, n: int = 7, spacing: float = 120.0):
    """Tilted plane rising to the east with a given slope."""
    g = math.tan(math.radians(slope_deg))
    return [ix * spacing * g for iy in range(n) for ix in range(n)]


def test_feature_ids_match_thresholds():
    assert [feature_id(t) for t in SLOPE_THRESHOLDS_DEG] == [
        "slope_frac_gt_8deg", "slope_frac_gt_15deg", "slope_frac_gt_30deg"]


def test_plane_has_uniform_slope_on_the_25_interior_cells():
    s = cell_slopes(plane(10.0))
    assert len(s) == 25
    assert all(v == pytest.approx(10.0) for v in s)


def test_centre_cell_equals_T_slope():
    z = [((i * 37) % 11) * 3.0 + (i // 7) * 5.0 for i in range(49)]
    centre = cell_slopes(z)[12]
    assert centre == pytest.approx(terrain_metrics(z)["slope_deg"])


def test_fractions_on_planes():
    fr = slope_fractions(plane(10.0))
    assert fr["slope_frac_gt_8deg"] == 1.0
    assert fr["slope_frac_gt_15deg"] == 0.0
    assert fr["slope_frac_gt_30deg"] == 0.0
    flat = slope_fractions([100.0] * 49)
    assert all(flat[feature_id(t)] == 0.0 for t in SLOPE_THRESHOLDS_DEG)


def test_half_steep_half_flat():
    # west half flat, east half a 20 deg ramp: cells whose stencil touches the ramp are steep
    g = math.tan(math.radians(20.0)) * 120.0
    z = [max(0, ix - 3) * g for iy in range(7) for ix in range(7)]
    fr = slope_fractions(z)
    # interior columns ix = 1..5: ix 1,2 flat (stencil 0..3), ix 3 half ramp, ix 4,5 full ramp
    assert fr["slope_frac_gt_8deg"] == pytest.approx(15 / 25)
    assert fr["slope_frac_gt_15deg"] == pytest.approx(10 / 25)


def test_missing_cells_give_null_not_zero():
    z = plane(5.0)
    for i in range(0, 49, 2):
        z[i] = None
    fr = slope_fractions(z)
    assert fr["n_valid"] < MIN_VALID_CELLS
    assert fr["slope_frac_gt_8deg"] is None


def test_sea_fill():
    assert is_sea_fill([0.0] * 49)
    assert not is_sea_fill([0.0] * 48 + [1.0])
    assert not is_sea_fill([None] * 49)


def test_wrong_size_raises():
    with pytest.raises(ValueError):
        cell_slopes([0.0] * 10)
