"""Agreement between the judge and human labels.

The headline is "within ±0.5": how often the judge lands on the human's score or
half a point from it (a median of two judge runs can be x.5). Alongside it:
within ±1, mean absolute error, bias (does the judge score high or low?), and
quadratic-weighted kappa, which credits agreement beyond what chance would give
and penalises big misses more than small ones.

When two or more people labeled the same session, their agreement with each
other is reported too. That's the ceiling: a judge can't be expected to agree
with one human more often than humans agree with each other.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations
from statistics import mean
from typing import Any

SCALE = range(5)  # 0..4


@dataclass
class Pair:
    session_id: str
    dimension: str
    judge: float
    human: float          # mean of the human labels for this session and dimension
    rationale: str = ""
    judge_runs: list[int] = field(default_factory=list)

    @property
    def diff(self) -> float:
        return self.judge - self.human


def _round(x: float) -> int:
    return int(min(4, max(0, round(x + 1e-9))))


def weighted_kappa(a: list[float], b: list[float]) -> float | None:
    """Quadratic-weighted Cohen's kappa on the 0-4 scale. None when undefined."""
    if len(a) < 2:
        return None
    a_i, b_i = [_round(x) for x in a], [_round(x) for x in b]
    k = len(SCALE)
    observed = [[0] * k for _ in range(k)]
    for x, y in zip(a_i, b_i):
        observed[x][y] += 1
    n = len(a_i)
    hist_a = [sum(row) for row in observed]
    hist_b = [sum(observed[i][j] for i in range(k)) for j in range(k)]
    num = den = 0.0
    for i in range(k):
        for j in range(k):
            w = (i - j) ** 2 / (k - 1) ** 2
            num += w * observed[i][j]
            den += w * hist_a[i] * hist_b[j] / n
    return None if den == 0 else 1 - num / den


def summarize(pairs: list[Pair]) -> dict[str, Any]:
    if not pairs:
        return {"n": 0}
    diffs = [p.diff for p in pairs]
    kappa = weighted_kappa([p.judge for p in pairs], [p.human for p in pairs])
    return {
        "n": len(pairs),
        "within_half": sum(abs(d) <= 0.5 for d in diffs) / len(diffs),
        "within_one": sum(abs(d) <= 1.0 for d in diffs) / len(diffs),
        "mae": mean(abs(d) for d in diffs),
        "bias": mean(diffs),
        "kappa": kappa,
    }


def agreement(pairs: list[Pair]) -> dict[str, Any]:
    dims = sorted({p.dimension for p in pairs})
    return {
        "overall": summarize(pairs),
        "per_dimension": {d: summarize([p for p in pairs if p.dimension == d]) for d in dims},
        "sessions": len({p.session_id for p in pairs}),
    }


def human_agreement(labels: dict[str, dict[str, dict[str, Any]]]) -> dict[str, Any] | None:
    """Pairwise agreement between labelers on sessions that two or more people scored."""
    diffs: list[float] = []
    sessions = 0
    for by_labeler in labels.values():
        if len(by_labeler) < 2:
            continue
        sessions += 1
        for x, y in combinations(by_labeler.values(), 2):
            for dim in set(x["scores"]) & set(y["scores"]):
                diffs.append(x["scores"][dim] - y["scores"][dim])
    if not diffs:
        return None
    return {"sessions": sessions, "n": len(diffs),
            "within_half": sum(abs(d) <= 0.5 for d in diffs) / len(diffs),
            "within_one": sum(abs(d) <= 1 for d in diffs) / len(diffs),
            "mae": mean(abs(d) for d in diffs)}
