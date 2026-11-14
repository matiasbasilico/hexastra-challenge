"""Ledoit-Wolf shrinkage covariance for the topographic vector T.

T = (relative_relief_m, slope_deg, roughness_m). Absolute elevation is not used.
The estimator follows Ledoit & Wolf (2004): shrink the sample covariance towards
mu * I, with shrinkage intensity clipped to [0, 1].
"""
from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

import numpy as np

LABELS = ("relative_relief_m", "slope_deg", "roughness_m")


def ledoit_wolf(X: np.ndarray) -> Tuple[np.ndarray, float]:
    """Return (shrunk covariance, shrinkage). X is n x p, one sample per row."""
    X = np.asarray(X, dtype=float)
    if X.ndim != 2 or X.shape[0] < 2:
        raise ValueError("Need at least two samples to estimate covariance")
    n, p = X.shape
    Xc = X - X.mean(axis=0, keepdims=True)
    # Maximum-likelihood covariance (divide by n), as in the LW 2004 derivation.
    S = (Xc.T @ Xc) / n
    mu = float(np.trace(S) / p)
    F = mu * np.eye(p)
    # Estimated variance of the covariance elements (Ledoit-Wolf 2004, eq. commonly implemented).
    Xc2 = Xc ** 2
    phi_mat = (Xc2.T @ Xc2) / n - S ** 2
    phi = float(np.sum(phi_mat))
    gamma = float(np.sum((S - F) ** 2))
    if gamma <= 0:
        shrinkage = 1.0
    else:
        shrinkage = max(0.0, min(1.0, phi / (n * gamma)))
    sigma = shrinkage * F + (1.0 - shrinkage) * S
    # Numerical safety for inversion later.
    ev = np.linalg.eigvalsh(sigma)
    if ev.min() <= 1e-12:
        sigma = sigma + (1e-8 - ev.min()) * np.eye(p)
    return sigma, shrinkage


def fit_from_samples(samples: Sequence[Dict[str, float]], labels: Sequence[str] = LABELS) -> Dict:
    rows = []
    for s in samples:
        row = [s.get(k) for k in labels]
        if all(v is not None and np.isfinite(v) for v in row):
            rows.append(row)
    if len(rows) < 2:
        raise ValueError("Not enough complete T samples to estimate Sigma")
    X = np.array(rows, dtype=float)
    sigma, shrinkage = ledoit_wolf(X)
    mean = X.mean(axis=0)
    try:
        sigma_inv = np.linalg.inv(sigma)
    except np.linalg.LinAlgError:
        sigma_inv = np.linalg.pinv(sigma)
    return {
        "labels": list(labels),
        "n_samples": int(X.shape[0]),
        "mean": mean.tolist(),
        "sigma": sigma.tolist(),
        "sigma_inv": sigma_inv.tolist(),
        "shrinkage": shrinkage,
        "method": "Ledoit-Wolf 2004 shrinkage towards mu * I, estimated on Earth terrain-cell T vectors (relative relief, slope, roughness). Absolute elevation excluded.",
    }


def submatrix(cov: Dict, used_labels: List[str]) -> Tuple[np.ndarray, np.ndarray, List[str]]:
    labels = list(cov["labels"])
    idx = [labels.index(k) for k in used_labels if k in labels]
    used = [labels[i] for i in idx]
    sigma = np.array(cov["sigma"], dtype=float)
    sub = sigma[np.ix_(idx, idx)]
    try:
        inv = np.linalg.inv(sub)
    except np.linalg.LinAlgError:
        inv = np.linalg.pinv(sub)
    return sub, inv, used
