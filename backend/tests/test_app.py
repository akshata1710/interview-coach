import json
import asyncio
import time

import pytest
from fastapi.testclient import TestClient

from app import problems, runner
from app.main import app

SOLUTIONS = {
    "two-sum": "def two_sum(nums, target):\n    seen = {}\n    for i, x in enumerate(nums):\n"
               "        if target - x in seen:\n            return [seen[target - x], i]\n        seen[x] = i\n",
    "longest-substring": "def length_of_longest_substring(s):\n    last, left, best = {}, 0, 0\n"
                         "    for r, ch in enumerate(s):\n        if ch in last and last[ch] >= left:\n"
                         "            left = last[ch] + 1\n        last[ch] = r\n"
                         "        best = max(best, r - left + 1)\n    return best\n",
    "valid-parentheses": "def is_valid(s):\n    pairs = {')': '(', ']': '[', '}': '{'}\n    st = []\n"
                         "    for c in s:\n        if c in pairs:\n            if not st or st.pop() != pairs[c]:\n"
                         "                return False\n        else:\n            st.append(c)\n    return not st\n",
    "merge-intervals": "def merge(intervals):\n    out = []\n    for a, b in sorted(intervals):\n"
                       "        if out and a <= out[-1][1]:\n            out[-1][1] = max(out[-1][1], b)\n"
                       "        else:\n            out.append([a, b])\n    return out\n",
}


def run(code, slug, hidden=True):
    p = problems.get(slug)
    tests = p["tests"] if hidden else [t for t in p["tests"] if not t["hidden"]]
    return asyncio.run(runner.run_tests(code, p, tests))


# ------------------------------------------------------------------ runner

@pytest.mark.parametrize("slug", list(SOLUTIONS))
def test_reference_solutions_pass_every_test(slug):
    res = run(SOLUTIONS[slug], slug)
    assert res["compile_error"] is None
    assert all(r["passed"] for r in res["results"]), [r for r in res["results"] if not r["passed"]]


def test_two_sum_accepts_any_valid_pair_order():
    code = SOLUTIONS["two-sum"].replace("[seen[target - x], i]", "[i, seen[target - x]]")
    assert all(r["passed"] for r in run(code, "two-sum")["results"])


def test_wrong_answer_fails_and_hides_hidden_details():
    res = run("def length_of_longest_substring(s):\n    return len(set(s))\n", "longest-substring")
    failed = [r for r in res["results"] if not r["passed"]]
    assert failed
    hidden = [r for r in res["results"] if r["hidden"]]
    assert all("input" not in r and "expected" not in r for r in hidden)
    visible = [r for r in res["results"] if not r["hidden"]]
    assert all("input" in r and "expected" in r for r in visible)


def test_syntax_error_and_missing_function():
    assert "SyntaxError" in run("def oops(:\n", "two-sum", hidden=False)["compile_error"]
    assert "No function named two_sum" in run("def other():\n    pass\n", "two-sum", hidden=False)["compile_error"]


def test_runtime_error_is_reported_per_test():
    res = run("def is_valid(s):\n    return 1 / 0\n", "valid-parentheses", hidden=False)
    assert all(not r["passed"] and "ZeroDivisionError" in r["error"] for r in res["results"])


def test_infinite_loop_is_stopped():
    t = time.time()
    res = run("def is_valid(s):\n    while True:\n        pass\n", "valid-parentheses", hidden=False)
    assert time.time() - t < 15
    assert all(not r["passed"] for r in res["results"])


def test_user_prints_do_not_break_results():
    code = "print('debug')\n" + SOLUTIONS["valid-parentheses"]
    assert all(r["passed"] for r in run(code, "valid-parentheses", hidden=False)["results"])


# ------------------------------------------------------------------ API

def test_problem_endpoints_never_leak_hidden_tests():
    with TestClient(app) as c:
        items = c.get("/api/problems").json()
        assert [p["difficulty"] for p in items] == sorted([p["difficulty"] for p in items],
                                                          key=lambda d: {"Easy": 0, "Medium": 1, "Hard": 2}[d])
        detail = c.get("/api/problems/longest-substring").json()
        assert "tests" not in detail and len(detail["visible_tests"]) == 3
        assert detail["hidden_test_count"] == 10


def _wait_scored(c, sid):
    for _ in range(100):
        s = c.get(f"/api/sessions/{sid}").json()
        if s["status"] in ("scored", "error"):
            return s
        time.sleep(0.05)
    raise AssertionError("scoring never finished")


def test_full_ai_assisted_session():
    with TestClient(app) as c:
        sid = c.post("/api/sessions", json={"problem_slug": "longest-substring", "mode": "ai_assisted"}).json()["id"]

        r = c.post(f"/api/sessions/{sid}/chat", json={"message": "is a sliding window right here?",
                                                      "code": "def f(): pass"})
        assert r.status_code == 200 and r.json()["prompt"]["id"] == "p1"

        res = c.post(f"/api/sessions/{sid}/run", json={"code": SOLUTIONS["longest-substring"]}).json()
        assert all(r["passed"] for r in res["results"])

        sub = c.post(f"/api/sessions/{sid}/submit",
                     json={"code": SOLUTIONS["longest-substring"], "ai_pasted_chars": 0}).json()
        assert sub["status"] == "scoring" and sub["submit_summary"]["hidden_passed"] == 10

        s = _wait_scored(c, sid)
        assert s["status"] == "scored", s["error"]
        ev = s["evaluation"]
        assert ev["readiness"] > 0 and ev["prompting"] is not None and ev["rewrite"]["event_id"] == "p1"
        by = {d["dimension"]: d for d in ev["dimensions"]}
        assert by["correctness"]["score"] == 4.0 and by["framing"]["evidence"][0]["event_id"] == "p1"

        assert c.post(f"/api/sessions/{sid}/submit", json={"code": "x"}).status_code == 409
        assert any(x["id"] == sid and x["combined"] is not None for x in c.get("/api/sessions").json())


def test_solo_session_has_no_assistant_and_no_prompting_score():
    with TestClient(app) as c:
        sid = c.post("/api/sessions", json={"problem_slug": "two-sum", "mode": "solo"}).json()["id"]
        assert c.post(f"/api/sessions/{sid}/chat", json={"message": "hi"}).status_code == 400
        c.post(f"/api/sessions/{sid}/submit", json={"code": SOLUTIONS["two-sum"]})
        s = _wait_scored(c, sid)
        assert s["status"] == "scored" and s["evaluation"]["prompting"] is None


def test_unknown_problem_and_session():
    with TestClient(app) as c:
        assert c.post("/api/sessions", json={"problem_slug": "nope", "mode": "solo"}).status_code == 404
        assert c.get("/api/sessions/doesnotexist").status_code == 404


def test_golden_labeling_flow(tmp_path, monkeypatch):
    monkeypatch.setenv("COACH_GOLDEN_DIR", str(tmp_path))
    with TestClient(app) as c:
        sid = c.post("/api/sessions", json={"problem_slug": "two-sum", "mode": "ai_assisted"}).json()["id"]
        assert c.post(f"/api/sessions/{sid}/golden").status_code == 409  # not submitted yet
        c.post(f"/api/sessions/{sid}/chat", json={"message": "hash map idea, O(n)?", "code": ""})
        c.post(f"/api/sessions/{sid}/submit", json={"code": SOLUTIONS["two-sum"]})
        _wait_scored(c, sid)
        gid = c.post(f"/api/sessions/{sid}/golden").json()["golden_id"]

        summary = c.get("/api/golden/summary", params={"labeler": "me"}).json()
        assert summary["total"] == 1 and summary["labeled_by_you"] == 0

        g = c.get(f"/api/golden/sessions/{gid}").json()
        assert "source" not in g and "evaluation" not in g and "judge_runs" not in json.dumps(g)
        assert len(g["dimensions"]) == 7 and g["facts"]["Hidden tests"].endswith("passed.")

        scores = {d["id"]: 3 for d in g["dimensions"]}
        assert c.post(f"/api/golden/sessions/{gid}/labels",
                      json={"labeler": "me", "scores": {"framing": 3}}).status_code == 400
        assert c.post(f"/api/golden/sessions/{gid}/labels", json={"labeler": "me", "scores": scores}).status_code == 200
        assert c.get("/api/golden/summary", params={"labeler": "me"}).json()["labeled_by_you"] == 1
        assert c.get(f"/api/golden/sessions/{gid}", params={"labeler": "me"}).json()["your_label"]["scores"] == scores
        assert c.get("/api/golden/sessions/..%2Fx").status_code in (400, 404)
