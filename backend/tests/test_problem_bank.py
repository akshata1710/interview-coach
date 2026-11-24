"""Every problem in the bank must be solvable: its reference solution passes every test,
including the large one, inside the per-test time limit."""
import asyncio
import inspect
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import build_problems  # noqa: E402
import problems_extra  # noqa: E402

from app import problems, runner  # noqa: E402

REFERENCE = {
    "two-sum": build_problems.two_sum,
    "longest-substring": build_problems.longest_substring,
    "valid-parentheses": build_problems.valid_parentheses,
    "merge-intervals": build_problems.merge_intervals,
    **{p["slug"]: getattr(problems_extra, p["function_name"]) for p in problems_extra.EXTRA},
}
HEADER = "from collections import Counter, defaultdict, deque\nimport heapq\n\n"


def source_for(slug):
    fn = REFERENCE[slug]
    name = problems.get(slug)["function_name"]
    return HEADER + inspect.getsource(fn) + f"\n{name} = {fn.__name__}\n"


def test_bank_has_every_problem_and_valid_shape():
    bank = problems.all_problems()
    assert set(bank) == set(REFERENCE), "every problem needs a reference solution in this test"
    for p in bank.values():
        assert p["difficulty"] in ("Easy", "Medium", "Hard")
        assert p["compare"] in ("exact", "sorted", "groups", "min_window", "two_sum")
        visible = [t for t in p["tests"] if not t["hidden"]]
        hidden = [t for t in p["tests"] if t["hidden"]]
        assert visible and hidden, p["slug"]
        assert any(t["category"] == "edge" for t in p["tests"]), p["slug"]
        assert any(t["category"] == "large" for t in p["tests"]), p["slug"]
        assert p["starter_code"].startswith(f"def {p['function_name']}("), p["slug"]


@pytest.mark.parametrize("slug", sorted(REFERENCE))
def test_reference_solution_passes_everything(slug):
    p = problems.get(slug)
    res = asyncio.run(runner.run_tests(source_for(slug), p, p["tests"]))
    failed = [(r["name"], r["error"]) for r in res["results"] if not r["passed"]]
    assert not failed, failed
    slowest = max(r["ms"] for r in res["results"])
    assert slowest < 1000, f"{slug}: reference took {slowest} ms; the 2 s limit would be too tight"


def test_brute_force_fails_only_the_large_test():
    brute = ("def max_area(height):\n    best = 0\n    for i in range(len(height)):\n"
             "        for j in range(i + 1, len(height)):\n"
             "            best = max(best, (j - i) * min(height[i], height[j]))\n    return best\n")
    p = problems.get("container-with-most-water")
    res = asyncio.run(runner.run_tests(brute, p, p["tests"]))
    by_cat = {r["category"]: [] for r in res["results"]}
    for r in res["results"]:
        by_cat[r["category"]].append(r)
    assert all(r["passed"] for r in by_cat["typical"] + by_cat["edge"])
    (large,) = by_cat["large"]
    assert not large["passed"] and "Time limit" in large["error"]


def test_groups_and_min_window_accept_any_valid_answer():
    assert runner._matches("groups", [["tea", "eat"], ["bat"]], [["bat"], ["eat", "tea"]], [])
    assert not runner._matches("groups", [["tea"], ["eat"], ["bat"]], [["bat"], ["eat", "tea"]], [])
    assert runner._matches("min_window", "ABC", "BCA", ["xxABCyyBCA", "ABC"])
    assert not runner._matches("min_window", "ABCy", "BCA", ["xxABCyyBCA", "ABC"])
    assert not runner._matches("groups", None, [["a"]], [])
