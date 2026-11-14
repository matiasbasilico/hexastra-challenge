import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for name in ("catalog", "main", "vector", "geocode", "covariance", "tasi"):
    sys.modules.pop(name, None)
sys.path.insert(0, str(ROOT))
