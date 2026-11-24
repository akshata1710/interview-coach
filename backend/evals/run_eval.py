"""Score the golden set with the judge and measure agreement with the human labels.

    python -m evals.run_eval                  # score, report, compare with the baseline
    python -m evals.run_eval --gate           # also exit 1 if agreement is below the thresholds (CI)
    python -m evals.run_eval --write-baseline # accept the current numbers as the new baseline
    python -m evals.run_eval --fake           # offline: placeholder judge, checks the plumbing

Judge results are cached by a hash of everything that can change them: the
session, the rubric, the judge's code and prompts, and the model. Re-running
after editing only a label costs nothing; editing a prompt re-scores everything.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any

import app.config  # noqa: F401  (loads backend/.env so ANTHROPIC_API_KEY is available)
import judge
from judge import models as jm

from . import golden
from .metrics import Pair, agreement, human_agreement

JUDGE_DIR = Path(judge.__file__).resolve().parent


def judge_fingerprint() -> str:
    """Hash of the judge's code, prompts and rubric: any change here invalidates the cache."""
    h = hashlib.sha256()
    for path in sorted(JUDGE_DIR.glob("*.py")) + [JUDGE_DIR / "rubric.yaml"]:
        h.update(path.name.encode())
        h.update(path.read_bytes())
    return h.hexdigest()


def cache_key(session: dict[str, Any], model: str, fingerprint: str) -> str:
    body = json.dumps({"session": session, "model": model, "judge": fingerprint}, sort_keys=True)
    return hashlib.sha256(body.encode()).hexdigest()[:24]


async def score_all(sessions: list[dict], client: judge.LLMClient, use_cache: bool,
                    concurrency: int) -> tuple[dict[str, dict], dict[str, str], int]:
    """Returns ({session_id: evaluation}, {session_id: error}, fresh_calls)."""
    cache_dir = golden.golden_dir() / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    fingerprint = judge_fingerprint()
    sem = asyncio.Semaphore(concurrency)
    results: dict[str, dict] = {}
    errors: dict[str, str] = {}
    fresh = 0

    async def one(session: dict) -> None:
        nonlocal fresh
        path = cache_dir / f"{cache_key(session, client.model, fingerprint)}.json"
        if use_cache and path.exists():
            results[session["id"]] = json.loads(path.read_text())
            return
        async with sem:
            try:
                ev = await judge.evaluate(jm.Session.model_validate(session), client)
            except Exception as exc:  # one bad session is reported, not fatal
                errors[session["id"]] = f"{type(exc).__name__}: {exc}"
                return
        data = ev.model_dump(mode="json")
        results[session["id"]] = data
        fresh += 1
        if use_cache:
            path.write_text(json.dumps(data))
        print(f"  scored {session['id']}", file=sys.stderr)

    await asyncio.gather(*(one(s) for s in sessions))
    return results, errors, fresh


def build_pairs(sessions: list[dict], evaluations: dict[str, dict],
                labels: dict[str, dict[str, dict]]) -> list[Pair]:
    pairs = []
    for s in sessions:
        ev = evaluations.get(s["id"])
        if not ev:
            continue
        by_dim = {d["dimension"]: d for d in ev["dimensions"]}
        for dim in {k for lab in labels[s["id"]].values() for k in lab["scores"]}:
            humans = [lab["scores"][dim] for lab in labels[s["id"]].values() if dim in lab["scores"]]
            j = by_dim.get(dim)
            if j is None or j["scored_by"] != "judge":
                continue
            pairs.append(Pair(s["id"], dim, j["score"], sum(humans) / len(humans),
                              rationale=j["rationale"], judge_runs=j.get("judge_runs", [])))
    return pairs


def check_gate(result: dict[str, Any], limits: dict[str, float], base: dict[str, Any] | None,
               errors: dict[str, str]) -> list[str]:
    failures = []
    o = result["overall"]
    if errors:
        failures.append(f"{len(errors)} session(s) could not be scored")
    if o["within_half"] < limits["min_within_half"]:
        failures.append(f"within ±0.5 is {o['within_half']:.0%}, below the floor of {limits['min_within_half']:.0%}")
    if o["mae"] > limits["max_mae"]:
        failures.append(f"mean absolute error is {o['mae']:.2f}, above the limit of {limits['max_mae']:.2f}")
    for dim, m in result["per_dimension"].items():
        if m["n"] >= 5 and m["within_half"] < limits["min_within_half_per_dimension"]:
            failures.append(f"{dim}: within ±0.5 is {m['within_half']:.0%}, below "
                            f"{limits['min_within_half_per_dimension']:.0%}")
    if base:
        drop = base["within_half"] - o["within_half"]
        if drop > limits["max_drop_from_baseline"]:
            failures.append(f"within ±0.5 fell {drop:.0%} from the baseline of {base['within_half']:.0%} "
                            f"(allowed: {limits['max_drop_from_baseline']:.0%})")
    return failures


def pct(x: float | None) -> str:
    return "–" if x is None else f"{x:.0%}"


def write_report(result: dict, pairs: list[Pair], humans: dict | None, base: dict | None,
                 meta: dict, failures: list[str], errors: dict[str, str]) -> str:
    o = result["overall"]
    lines = ["# Judge agreement report", ""]
    kappa = "–" if o["kappa"] is None else f"{o['kappa']:.2f}"
    lines.append(
        f"On **{result['sessions']} human-labeled sessions** ({o['n']} scores), the judge's score is within "
        f"±0.5 of the human score **{pct(o['within_half'])}** of the time, and within ±1 **{pct(o['within_one'])}**. "
        f"Mean absolute error {o['mae']:.2f} on a 0–4 scale; quadratic-weighted kappa {kappa}."
    )
    lines.append("")
    if humans:
        lines.append(f"For reference, two humans scoring the same {humans['sessions']} sessions agreed within ±0.5 "
                     f"{pct(humans['within_half'])} of the time (MAE {humans['mae']:.2f}). That is the realistic ceiling.")
        lines.append("")
    if base:
        delta = o["within_half"] - base["within_half"]
        lines.append(f"Baseline: {pct(base['within_half'])} on {base['n']} scores "
                     f"(rubric {base['rubric_version']}, {base['model']}, {base['date']}). Change: {delta:+.0%}.")
        lines.append("")
    lines.append("**Gate:** " + ("passed." if not failures else "failed: " + "; ".join(failures) + "."))
    lines += ["", "## By dimension", "",
              "| Dimension | Scores | Within ±0.5 | Within ±1 | MAE | Bias (judge − human) | Kappa |",
              "| --- | --- | --- | --- | --- | --- | --- |"]
    for dim, m in result["per_dimension"].items():
        kappa = "–" if m["kappa"] is None else f"{m['kappa']:.2f}"
        lines.append(f"| {dim} | {m['n']} | {pct(m['within_half'])} | {pct(m['within_one'])} | "
                     f"{m['mae']:.2f} | {m['bias']:+.2f} | {kappa} |")
    worst = sorted(pairs, key=lambda p: -abs(p.diff))[:10]
    if worst and abs(worst[0].diff) > 0.5:
        lines += ["", "## Largest disagreements", "",
                  "Read these first: each is either a judge error or a label worth revisiting.", "",
                  "| Session | Dimension | Judge | Human | Judge's reason |", "| --- | --- | --- | --- | --- |"]
        for p in worst:
            if abs(p.diff) <= 0.5:
                break
            reason = p.rationale.replace("|", "/").replace("\n", " ")
            reason = reason if len(reason) <= 160 else reason[:157] + "…"
            lines.append(f"| {p.session_id} | {p.dimension} | {p.judge:g} | {p.human:g} | {reason} |")
    if errors:
        lines += ["", "## Sessions that could not be scored", ""]
        lines += [f"- {sid}: {err}" for sid, err in errors.items()]
    lines += ["", "## Run", "",
              f"- Model: {meta['model']}", f"- Rubric: {meta['rubric_version']}",
              f"- Judge fingerprint: `{meta['fingerprint'][:12]}`", f"- Date: {meta['date']}",
              f"- Fresh scoring runs this time: {meta['fresh']} (the rest came from the cache)", ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default=app.config.JUDGE_MODEL)
    ap.add_argument("--fake", action="store_true", help="offline placeholder judge (no API calls)")
    ap.add_argument("--no-cache", action="store_true")
    ap.add_argument("--gate", action="store_true", help="exit 1 if agreement is below the thresholds")
    ap.add_argument("--strict", action="store_true", help="with --gate, also fail when there are too few labels")
    ap.add_argument("--write-baseline", action="store_true")
    ap.add_argument("--concurrency", type=int, default=4)
    args = ap.parse_args(argv)

    rubric = jm.Rubric.load()
    labels = golden.load_labels()
    sessions = [s for s in golden.list_sessions() if s["id"] in labels]
    limits = golden.thresholds()
    out_dir = golden.golden_dir()

    if len(sessions) < limits["min_sessions"]:
        msg = (f"Only {len(sessions)} session(s) have human labels; the gate needs {limits['min_sessions']:g}. "
               f"Label more on the app's Label page (/label).")
        print(msg)
        if not sessions:
            return 1 if args.strict else 0
        if args.gate and args.strict:
            return 1

    if args.fake:
        from app.fake_judge import FakeJudge
        client: judge.LLMClient = FakeJudge()
    else:
        client = judge.AnthropicClient(model=args.model)

    started = time.time()
    evaluations, errors, fresh = asyncio.run(
        score_all(sessions, client, use_cache=not args.no_cache, concurrency=args.concurrency))
    pairs = build_pairs(sessions, evaluations, labels)
    if not pairs:
        print("No judge scores to compare: every session failed to score.", *errors.values(), sep="\n")
        return 1

    result = agreement(pairs)
    humans = human_agreement({s["id"]: labels[s["id"]] for s in sessions})
    base = golden.baseline()
    enough = len(sessions) >= limits["min_sessions"]
    failures = check_gate(result, limits, base, errors) if enough else []
    meta = {"model": client.model, "rubric_version": rubric.version, "fingerprint": judge_fingerprint(),
            "date": time.strftime("%Y-%m-%d"), "fresh": fresh, "seconds": round(time.time() - started, 1)}

    report = write_report(result, pairs, humans, base, meta, failures, errors)
    (out_dir / "REPORT.md").write_text(report)
    (out_dir / "report.json").write_text(json.dumps(
        {"meta": meta, "result": result, "human_agreement": humans, "gate_failures": failures,
         "errors": errors, "pairs": [p.__dict__ for p in pairs]}, indent=1))
    print(report)

    if args.write_baseline:
        if args.fake:
            print("Not writing a baseline from the placeholder judge.")
        else:
            golden.write_baseline({"within_half": result["overall"]["within_half"], "n": result["overall"]["n"],
                                   "per_dimension": {d: m["within_half"] for d, m in result["per_dimension"].items()},
                                   "rubric_version": rubric.version, "model": client.model, "date": meta["date"]})
            print("Baseline updated.")

    if args.gate and failures:
        print("\nGate failed.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
