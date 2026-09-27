"""Measures, Wilson intervals and a cluster bootstrap. Standard library only."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass


@dataclass(frozen=True)
class Unit:
    """One episode (D1) or task (D2)."""
    cluster: str
    resolved: bool
    consulted: bool


def counts(units: list[Unit]) -> dict:
    """The 2x2 table (resolved x consulted) that every measure is built from."""
    c = {"n": 0, "resolved": 0, "no_consult": 0, "resolved_no_consult": 0}
    for u in units:
        c["n"] += 1
        c["resolved"] += u.resolved
        c["no_consult"] += not u.consulted
        c["resolved_no_consult"] += u.resolved and not u.consulted
    return c


def measures_from_counts(c: dict) -> dict:
    n, res, free, res_free = c["n"], c["resolved"], c["no_consult"], c["resolved_no_consult"]
    nan = float("nan")
    r0 = free / n if n else nan
    r1 = res_free / res if res else nan
    r0p = res_free / n if n else nan
    return {
        "R0": r0,
        "R1": r1,
        "R0_prime": r0p,
        # R0 - R0' == (unresolved AND no consultation) / all
        "numerator_effect": r0 - r0p,
        "denominator_effect": r0 - r1,
    }


def wilson(k: int, n: int, z: float = 1.959963984540054) -> list[float]:
    """Wilson score interval. Ignores clustering, so it is narrower than it should be."""
    if n == 0:
        return [float("nan"), float("nan")]
    p = k / n
    d = 1 + z * z / n
    centre = p + z * z / (2 * n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return [(centre - half) / d, (centre + half) / d]


def percentile(sorted_vals: list[float], q: float) -> float:
    """Linear interpolation between order statistics (type 7)."""
    if not sorted_vals:
        return float("nan")
    h = (len(sorted_vals) - 1) * q
    lo = math.floor(h)
    hi = min(lo + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (h - lo) * (sorted_vals[hi] - sorted_vals[lo])


def cluster_bootstrap(units: list[Unit], replicates: int, seed_label: str,
                      level: float = 0.95) -> dict:
    """Resample clusters (developers) with replacement; recompute every measure.

    `seed_label` is a string; `random.Random(str)` is deterministic across runs and
    does not depend on PYTHONHASHSEED.
    """
    per_cluster: dict[str, dict] = {}
    for u in units:
        per_cluster.setdefault(u.cluster, []).append(u)
    clusters = sorted(per_cluster)
    tables = [counts(per_cluster[k]) for k in clusters]

    rng = random.Random(seed_label)
    draws: dict[str, list[float]] = {k: [] for k in
                                     ("R0", "R1", "R0_prime", "numerator_effect", "denominator_effect")}
    undefined = 0
    for _ in range(replicates):
        agg = {"n": 0, "resolved": 0, "no_consult": 0, "resolved_no_consult": 0}
        for _ in clusters:
            t = tables[rng.randrange(len(tables))]
            for key in agg:
                agg[key] += t[key]
        m = measures_from_counts(agg)
        if any(math.isnan(v) for v in m.values()):
            undefined += 1
            continue
        for key, v in m.items():
            draws[key].append(v)

    alpha = (1 - level) / 2
    out = {}
    for key, vals in draws.items():
        vals.sort()
        out[key] = [percentile(vals, alpha), percentile(vals, 1 - alpha)]
    return {"intervals": out, "clusters": len(clusters), "replicates": replicates,
            "undefined_replicates": undefined}


def summarise(units: list[Unit], replicates: int, seed_label: str, level: float) -> dict:
    c = counts(units)
    m = measures_from_counts(c)
    unresolved_free = c["no_consult"] - c["resolved_no_consult"]
    return {
        "counts": c,
        "unresolved_no_consult": unresolved_free,
        "point": m,
        "wilson95": {
            "R0": wilson(c["no_consult"], c["n"]),
            "R1": wilson(c["resolved_no_consult"], c["resolved"]),
            "R0_prime": wilson(c["resolved_no_consult"], c["n"]),
            "numerator_effect": wilson(unresolved_free, c["n"]),
        },
        "cluster_bootstrap": cluster_bootstrap(units, replicates, seed_label, level),
    }
