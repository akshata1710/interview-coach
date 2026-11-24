"""Run a candidate's Python solution against test cases in a child process.

Each test gets its own time limit, and results are written one line at a time,
so a slow brute force on the large test fails that test alone instead of wiping
out the results of the tests before it.

This is a local-development runner: a separate process with CPU and time limits,
an empty environment and a throwaway working directory. It is NOT a security
sandbox. Before anyone else's code runs on your machine, swap this for the
Docker runner described in the design doc.
"""
from __future__ import annotations

import asyncio
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

from .config import MEMORY_LIMIT_MB, PER_TEST_TIMEOUT_S

HARNESS = r'''
import json, signal, sys, time
sys.setrecursionlimit(20000)
src_path, cases_path, fn_name, out_path, per_test = sys.argv[1:6]
per_test = float(per_test)
out = open(out_path, "w")

def emit(obj):
    out.write(json.dumps(obj, default=repr) + "\n")
    out.flush()

class TimeLimit(BaseException):  # BaseException, so a candidate's `except Exception` can't swallow it
    pass

def on_alarm(signum, frame):
    raise TimeLimit()

signal.signal(signal.SIGALRM, on_alarm)
ns = {"__name__": "solution"}
try:
    exec(compile(open(src_path).read(), "solution.py", "exec"), ns)
    fn = ns[fn_name]
except KeyError:
    emit({"compile_error": f"No function named {fn_name}() was found."}); sys.exit(0)
except Exception as e:
    emit({"compile_error": f"{type(e).__name__}: {e}"}); sys.exit(0)
emit({"compiled": True})

for args in json.load(open(cases_path)):
    t = time.perf_counter()
    signal.setitimer(signal.ITIMER_REAL, per_test)
    try:
        r, err = fn(*args), None
    except TimeLimit:
        r, err = None, f"Time limit exceeded ({per_test:g} s). Look for a faster approach."
    except RecursionError:
        r, err = None, "RecursionError: maximum recursion depth exceeded"
    except Exception as e:
        r, err = None, f"{type(e).__name__}: {e}"
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
    emit({"result": r, "error": err, "ms": round((time.perf_counter() - t) * 1000, 2)})
'''


def _limits(cpu_seconds: int):
    def apply() -> None:  # runs in the child before exec
        import resource
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
        try:
            mem = MEMORY_LIMIT_MB * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (mem, mem))
        except (ValueError, OSError):
            pass  # macOS does not support RLIMIT_AS
    return apply


def _canonical_groups(value: Any) -> list:
    return sorted(sorted(group) for group in value)


def _matches(compare: str, got: Any, expected: Any, args: list[Any]) -> bool:
    try:
        if compare == "two_sum":
            nums, target = args
            return (isinstance(got, (list, tuple)) and len(got) == 2
                    and all(isinstance(i, int) and 0 <= i < len(nums) for i in got)
                    and got[0] != got[1] and nums[got[0]] + nums[got[1]] == target)
        if compare == "sorted":
            return sorted(got) == sorted(expected)
        if compare == "groups":
            return _canonical_groups(got) == _canonical_groups(expected)
        if compare == "min_window":
            s, t = args
            if expected == "":
                return got == ""
            return (isinstance(got, str) and len(got) == len(expected) and got in s
                    and not (Counter(t) - Counter(got)))
        return got == expected
    except (TypeError, ValueError):
        return False  # an answer of the wrong shape simply fails


def _preview(value: Any, limit: int = 120) -> str:
    text = json.dumps(value, default=repr)
    return text if len(text) <= limit else text[:limit] + "…"


async def run_tests(code: str, problem: dict[str, Any], tests: list[dict[str, Any]]) -> dict[str, Any]:
    """Returns {"compile_error": str|None, "timed_out": bool, "results": [...] }."""
    budget = PER_TEST_TIMEOUT_S * len(tests) + 5  # backstop if the per-test alarm can't fire
    with tempfile.TemporaryDirectory(prefix="coach-run-") as tmp:
        d = Path(tmp)
        (d / "solution.py").write_text(code)
        (d / "harness.py").write_text(HARNESS)
        (d / "cases.json").write_text(json.dumps([t["args"] for t in tests]))
        out = d / "out.jsonl"

        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-I", str(d / "harness.py"),
            str(d / "solution.py"), str(d / "cases.json"), problem["function_name"], str(out),
            str(PER_TEST_TIMEOUT_S),
            cwd=tmp, env={"PATH": "/usr/bin:/bin"},
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE,
            preexec_fn=_limits(int(budget) + 1),
        )
        killed = False
        try:
            _, stderr = await asyncio.wait_for(proc.communicate(), timeout=budget)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            killed, stderr = True, b""

        lines = [json.loads(x) for x in out.read_text().splitlines() if x.strip()] if out.exists() else []

    if lines and "compile_error" in lines[0]:
        err = lines[0]["compile_error"]
        return {"compile_error": err, "timed_out": False, "results": [_row(t, False, error=err) for t in tests]}

    done = lines[1:]  # the first line only confirms the code compiled
    if not lines:
        reason = "Your code was stopped before any test ran (CPU or memory limit)."
        tail = stderr.decode(errors="replace").strip().splitlines()[-1:] if stderr else []
        return {"compile_error": None, "timed_out": killed,
                "results": [_row(t, False, error=" ".join([reason, *tail])) for t in tests]}

    rows = []
    for i, t in enumerate(tests):
        if i < len(done):
            r = done[i]
            ok = r["error"] is None and _matches(problem["compare"], r["result"], t["expected"], t["args"])
            rows.append(_row(t, ok, got=r["result"], error=r["error"], ms=r["ms"]))
        elif i == len(done):
            rows.append(_row(t, False, error="Stopped here: CPU, memory or time limit."))
        else:
            rows.append(_row(t, False, error="Not run: an earlier test hit a limit."))
    return {"compile_error": None, "timed_out": killed or len(done) < len(tests), "results": rows}


def _row(t: dict[str, Any], passed: bool, got: Any = None, error: str | None = None,
         ms: float | None = None) -> dict[str, Any]:
    row = {"name": t["name"], "category": t["category"], "hidden": t["hidden"],
           "passed": passed, "error": error, "ms": ms}
    if not t["hidden"]:  # never reveal hidden inputs or answers
        row.update(input=_preview(t["args"]), expected=_preview(t["expected"]), got=_preview(got))
    return row
