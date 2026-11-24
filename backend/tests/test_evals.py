"""The eval harness, run offline with the placeholder judge (which scores 2 on every judged dimension)."""
import json
import shutil
from pathlib import Path

import pytest

from evals import golden, run_eval
from evals.metrics import Pair, agreement, human_agreement, weighted_kappa
from judge.models import Rubric

SEEDS = Path(__file__).resolve().parents[1] / "golden" / "sessions"


@pytest.fixture
def gdir(tmp_path, monkeypatch):
    monkeypatch.setenv("COACH_GOLDEN_DIR", str(tmp_path))
    (tmp_path / "sessions").mkdir()
    picked = {"ai": None, "solo": None}
    for path in sorted(SEEDS.glob("*.json")):
        s = json.loads(path.read_text())
        key = "solo" if s["mode"] == "solo" else "ai" if s["mode"] == "ai_assisted" else None
        if key and picked[key] is None:
            picked[key] = s["id"]
            shutil.copy(path, tmp_path / "sessions" / path.name)
    (tmp_path / "thresholds.yaml").write_text("min_sessions: 2\nmin_within_half: 0.8\n")
    return tmp_path, picked


def label_all(picked, labeler, value_for):
    rubric = Rubric.load()
    for sid in picked.values():
        s = golden.get_session(sid)
        scores = {d.id: value_for(d.id) for _, d in golden.judged_dimensions(s, rubric)}
        golden.save_label(sid, labeler, scores, "", rubric)


# ------------------------------------------------------------------ metrics

def test_kappa_and_summary():
    assert weighted_kappa([0, 1, 2, 3, 4], [0, 1, 2, 3, 4]) == pytest.approx(1.0)
    assert weighted_kappa([0, 1, 2, 3, 4], [4, 3, 2, 1, 0]) < 0
    pairs = [Pair("s", "d", 2, 2), Pair("s", "d", 2.5, 2), Pair("s", "d", 3, 1)]
    o = agreement(pairs)["overall"]
    assert o["within_half"] == pytest.approx(2 / 3)
    assert o["within_one"] == pytest.approx(2 / 3)
    assert o["mae"] == pytest.approx((0 + 0.5 + 2) / 3)
    assert o["bias"] == pytest.approx((0 + 0.5 + 2) / 3)


def test_human_agreement_needs_two_labelers():
    one = {"s1": {"a": {"scores": {"x": 2}}}}
    assert human_agreement(one) is None
    two = {"s1": {"a": {"scores": {"x": 2, "y": 4}}, "b": {"scores": {"x": 3, "y": 4}}}}
    h = human_agreement(two)
    assert h["sessions"] == 1 and h["within_half"] == 0.5 and h["within_one"] == 1.0


# ------------------------------------------------------------------ labels

def test_labels_are_validated(gdir):
    _, picked = gdir
    rubric = Rubric.load()
    sid = picked["solo"]
    with pytest.raises(ValueError, match="cover exactly"):
        golden.save_label(sid, "me", {"complexity": 2}, "", rubric)
    with pytest.raises(ValueError, match="whole number"):
        golden.save_label(sid, "me", {"complexity": 5, "code_quality": 2}, "", rubric)
    with pytest.raises(ValueError, match="labeler"):
        golden.save_label(sid, "Bad Name", {"complexity": 2, "code_quality": 2}, "", rubric)
    with pytest.raises(ValueError):
        golden.get_session("../etc/passwd")
    golden.save_label(sid, "me", {"complexity": 2, "code_quality": 3}, "ok", rubric)
    assert golden.load_labels()[sid]["me"]["scores"] == {"complexity": 2, "code_quality": 3}


def test_solo_sessions_only_label_readiness(gdir):
    _, picked = gdir
    rubric = Rubric.load()
    solo = [d.id for _, d in golden.judged_dimensions(golden.get_session(picked["solo"]), rubric)]
    ai = [d.id for _, d in golden.judged_dimensions(golden.get_session(picked["ai"]), rubric)]
    assert solo == ["complexity", "code_quality"]
    assert len(ai) == 7 and "framing" in ai


# ------------------------------------------------------------------ full run

def test_gate_passes_when_humans_agree(gdir):
    root, picked = gdir
    label_all(picked, "me", lambda dim: 2)  # placeholder judge also says 2
    assert run_eval.main(["--fake", "--gate"]) == 0
    report = (root / "REPORT.md").read_text()
    assert "**100%**" in report and "Gate:** passed" in report


def test_gate_fails_and_lists_disagreements(gdir):
    root, picked = gdir
    label_all(picked, "me", lambda dim: 4)
    assert run_eval.main(["--fake", "--gate"]) == 1
    report = (root / "REPORT.md").read_text()
    assert "Gate:** failed" in report and "Largest disagreements" in report


def test_cache_skips_rescoring(gdir):
    root, picked = gdir
    label_all(picked, "me", lambda dim: 2)
    run_eval.main(["--fake"])
    run_eval.main(["--fake"])
    assert json.loads((root / "report.json").read_text())["meta"]["fresh"] == 0


def test_baseline_drop_fails_gate(gdir):
    root, picked = gdir
    label_all(picked, "me", lambda dim: 3)  # judge (2) is within 1 but not 0.5
    golden.write_baseline({"within_half": 1.0, "n": 9, "per_dimension": {}, "rubric_version": "x",
                           "model": "m", "date": "d"})
    (root / "thresholds.yaml").write_text("min_sessions: 2\nmin_within_half: 0.0\nmax_mae: 4\n"
                                          "min_within_half_per_dimension: 0\n")
    assert run_eval.main(["--fake", "--gate"]) == 1
    assert "fell" in (root / "REPORT.md").read_text()


def test_too_few_labels_reports_without_failing(gdir):
    root, picked = gdir
    (root / "thresholds.yaml").write_text("min_sessions: 25\n")
    label_all(picked, "me", lambda dim: 0)
    assert run_eval.main(["--fake", "--gate"]) == 0
    assert run_eval.main(["--fake", "--gate", "--strict"]) == 1


def test_seed_set_is_well_formed():
    from judge import models as jm
    sessions = [json.loads(p.read_text()) for p in SEEDS.glob("*.json")]
    assert len(sessions) >= 30
    modes = {s["mode"] for s in sessions}
    assert modes == {"ai_assisted", "solo", "interviewer"}
    for s in sessions:
        jm.Session.model_validate(s)
        assert s["id"].startswith("g-"), "seed ids must not reveal what the seed is"
        assert "seed" not in json.dumps(s["events"]).lower()
