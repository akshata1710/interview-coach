"""The golden set on disk: sessions, human labels, thresholds and the recorded baseline.

golden/
  sessions/<id>.json          sessions in the judge's input format
  labels/<labeler>/<id>.json  one human's blind scores for one session
  seed_manifest.json          what each seed was built to be (never shown while labeling)
  thresholds.yaml             the CI gate
  baseline.json               the last accepted agreement numbers
  REPORT.md / report.json     the latest eval results
  cache/                      judge outputs keyed by everything that could change them (git-ignored)
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any

import yaml

from judge.models import Dimension, Rubric

BACKEND_DIR = Path(__file__).resolve().parents[1]
LABELER_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}$")
SESSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")


def golden_dir() -> Path:
    return Path(os.getenv("COACH_GOLDEN_DIR", BACKEND_DIR / "golden"))


def _check_id(value: str, pattern: re.Pattern, what: str) -> str:
    if not pattern.match(value or ""):
        raise ValueError(f"invalid {what}: {value!r}")
    return value


# ------------------------------------------------------------------ sessions

def list_sessions() -> list[dict[str, Any]]:
    d = golden_dir() / "sessions"
    return [json.loads(p.read_text()) for p in sorted(d.glob("*.json"))] if d.exists() else []


def get_session(session_id: str) -> dict[str, Any] | None:
    path = golden_dir() / "sessions" / f"{_check_id(session_id, SESSION_RE, 'session id')}.json"
    return json.loads(path.read_text()) if path.exists() else None


def save_session(session: dict[str, Any]) -> None:
    sid = _check_id(session["id"], SESSION_RE, "session id")
    d = golden_dir() / "sessions"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{sid}.json").write_text(json.dumps(session, indent=1))


# ------------------------------------------------------------------ dimensions

def judged_dimensions(session: dict[str, Any], rubric: Rubric) -> list[tuple[str, Dimension]]:
    """The dimensions a human labels: the ones the LLM judge scores for this session's mode."""
    tracks = ["readiness"] if session["mode"] == "solo" else ["readiness", "prompting"]
    return [(t, d) for t in tracks for d in rubric.tracks[t] if d.scored_by == "judge"]


# ------------------------------------------------------------------ labels

def save_label(session_id: str, labeler: str, scores: dict[str, int], notes: str, rubric: Rubric) -> dict[str, Any]:
    session = get_session(session_id)
    if session is None:
        raise KeyError(session_id)
    _check_id(labeler, LABELER_RE, "labeler name (use lowercase letters, digits, - or _)")
    expected = {d.id for _, d in judged_dimensions(session, rubric)}
    if set(scores) != expected:
        missing, extra = expected - set(scores), set(scores) - expected
        raise ValueError(f"scores must cover exactly {sorted(expected)}; missing {sorted(missing)}, extra {sorted(extra)}")
    for dim, value in scores.items():
        if not isinstance(value, int) or not 0 <= value <= 4:
            raise ValueError(f"{dim}: score must be a whole number from 0 to 4")
    label = {"session_id": session_id, "labeler": labeler, "rubric_version": rubric.version,
             "scores": scores, "notes": notes.strip(), "labeled_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    d = golden_dir() / "labels" / labeler
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{session_id}.json").write_text(json.dumps(label, indent=1))
    return label


def load_labels() -> dict[str, dict[str, dict[str, Any]]]:
    """{session_id: {labeler: label}}"""
    out: dict[str, dict[str, dict[str, Any]]] = {}
    root = golden_dir() / "labels"
    if not root.exists():
        return out
    for path in sorted(root.glob("*/*.json")):
        label = json.loads(path.read_text())
        out.setdefault(label["session_id"], {})[label["labeler"]] = label
    return out


# ------------------------------------------------------------------ gate config

DEFAULT_THRESHOLDS = {
    "min_sessions": 20,
    "min_within_half": 0.80,
    "min_within_half_per_dimension": 0.60,
    "max_mae": 0.75,
    "max_drop_from_baseline": 0.05,
}


def thresholds() -> dict[str, float]:
    path = golden_dir() / "thresholds.yaml"
    loaded = yaml.safe_load(path.read_text()) if path.exists() else {}
    return {**DEFAULT_THRESHOLDS, **(loaded or {})}


def baseline() -> dict[str, Any] | None:
    path = golden_dir() / "baseline.json"
    return json.loads(path.read_text()) if path.exists() else None


def write_baseline(data: dict[str, Any]) -> None:
    (golden_dir() / "baseline.json").write_text(json.dumps(data, indent=1))
