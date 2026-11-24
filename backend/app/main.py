"""Interview Coach API.

    uvicorn app.main:app --reload --reload-dir app --reload-dir judge --port 8000
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import judge
from judge import models as jm

from . import assistant, problems, runner
from .config import DB_PATH, FAKE_LLM, JUDGE_MODEL, TIME_LIMIT_S
from .fake_judge import FakeJudge
from .store import Store

log = logging.getLogger("coach")
store = Store(DB_PATH)
_tasks: set[asyncio.Task] = set()

Mode = Literal["solo", "ai_assisted", "interviewer"]


@asynccontextmanager
async def lifespan(_: FastAPI):
    # a restart mid-scoring leaves sessions stuck; mark them so the UI offers a retry
    for doc in store.recent(limit=200):
        if doc["status"] == "scoring":
            doc.update(status="error", error="Scoring was interrupted by a server restart.")
            store.put(doc)
    yield


app = FastAPI(title="Interview Coach", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"], allow_headers=["*"],
)


# ------------------------------------------------------------------ helpers

def _has_key() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY"))


def _require_llm() -> None:
    if not FAKE_LLM and not _has_key():
        raise HTTPException(503, "ANTHROPIC_API_KEY is not set in the backend terminal. "
                                 "Set it and restart, or start with COACH_FAKE_LLM=1 for offline mode.")


def _chat_model() -> assistant.ChatModel:
    return assistant.FakeChat() if FAKE_LLM else assistant.AnthropicChat()


def _judge_client() -> judge.LLMClient:
    return FakeJudge() if FAKE_LLM else judge.AnthropicClient(model=JUDGE_MODEL)


def _load(session_id: str) -> dict[str, Any]:
    doc = store.get(session_id)
    if not doc:
        raise HTTPException(404, "Session not found")
    return doc


def _problem(slug: str) -> dict[str, Any]:
    p = problems.get(slug)
    if not p:
        raise HTTPException(404, "Problem not found")
    return p


def _elapsed(doc: dict[str, Any]) -> float:
    return round(time.time() - doc["created_at"], 1)


def _add_event(doc: dict[str, Any], kind: str, text: str) -> dict[str, Any]:
    prefix = {"prompt": "p", "ai_reply": "a", "run": "r", "submit": "s"}[kind]
    n = sum(e["type"] == kind for e in doc["events"]) + 1
    event = {"id": f"{prefix}{n}", "type": kind, "ts": _elapsed(doc), "text": text}
    doc["events"].append(event)
    return event


def _public(doc: dict[str, Any]) -> dict[str, Any]:
    p = problems.get(doc["problem_slug"])
    return {
        "id": doc["id"], "problem_slug": doc["problem_slug"], "problem_title": p["title"] if p else "",
        "mode": doc["mode"], "status": doc["status"], "created_at": doc["created_at"],
        "time_limit_s": TIME_LIMIT_S, "events": doc["events"], "last_code": doc["last_code"],
        "submit_summary": doc.get("submit_summary"), "evaluation": doc.get("evaluation"),
        "error": doc.get("error"),
    }


# ------------------------------------------------------------------ problems

@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"ok": True, "offline_mode": FAKE_LLM, "api_key_set": _has_key()}


@app.get("/api/problems")
def list_problems() -> list[dict[str, Any]]:
    items = [problems.summary(p) for p in problems.all_problems().values()]
    return sorted(items, key=lambda p: (problems.DIFFICULTY_ORDER.get(p["difficulty"], 9), p["title"]))


@app.get("/api/problems/{slug}")
def get_problem(slug: str) -> dict[str, Any]:
    return problems.public(_problem(slug))


# ------------------------------------------------------------------ sessions

class NewSession(BaseModel):
    problem_slug: str
    mode: Mode


@app.post("/api/sessions", status_code=201)
def create_session(body: NewSession) -> dict[str, Any]:
    p = _problem(body.problem_slug)
    doc = {
        "id": uuid.uuid4().hex[:12], "problem_slug": p["slug"], "mode": body.mode,
        "created_at": time.time(), "status": "active", "events": [],
        "last_code": p["starter_code"], "solve_time_s": None,
    }
    store.put(doc)
    return _public(doc)


@app.get("/api/sessions")
def recent_sessions() -> list[dict[str, Any]]:
    out = []
    for d in store.recent():
        ev = d.get("evaluation") or {}
        p = problems.get(d["problem_slug"])
        out.append({"id": d["id"], "problem_title": p["title"] if p else d["problem_slug"],
                    "mode": d["mode"], "status": d["status"], "created_at": d["created_at"],
                    "combined": ev.get("combined"), "label": ev.get("label")})
    return out


@app.get("/api/sessions/{session_id}")
def get_session(session_id: str) -> dict[str, Any]:
    return _public(_load(session_id))


class CodeBody(BaseModel):
    code: str = Field(max_length=50_000)


@app.post("/api/sessions/{session_id}/run")
async def run_visible(session_id: str, body: CodeBody) -> dict[str, Any]:
    doc = _load(session_id)
    if doc["status"] != "active":
        raise HTTPException(409, "This session has already been submitted.")
    p = _problem(doc["problem_slug"])
    visible = [t for t in p["tests"] if not t["hidden"]]
    result = await runner.run_tests(body.code, p, visible)

    passed = sum(r["passed"] for r in result["results"])
    doc = _load(session_id)  # re-read: a chat may have landed while the code ran
    _add_event(doc, "run", f"{passed} of {len(visible)} visible tests passed")
    if passed == len(visible) and doc["solve_time_s"] is None:
        doc["solve_time_s"] = int(_elapsed(doc))
    doc["last_code"] = body.code
    store.put(doc)
    return result


class ChatBody(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    code: str = Field("", max_length=50_000)


@app.post("/api/sessions/{session_id}/chat")
async def chat(session_id: str, body: ChatBody) -> dict[str, Any]:
    doc = _load(session_id)
    if doc["mode"] == "solo":
        raise HTTPException(400, "The assistant is off in Solo mode.")
    if doc["status"] != "active":
        raise HTTPException(409, "This session has already been submitted.")
    _require_llm()
    p = _problem(doc["problem_slug"])

    system = (assistant.INTERVIEWER_SYSTEM if doc["mode"] == "interviewer"
              else assistant.ASSISTANT_SYSTEM).format(problem=assistant.problem_text(p))
    messages = assistant.build_messages(doc["events"], body.message.strip(), body.code)
    try:
        reply = await _chat_model().reply(system, messages)
    except Exception as exc:  # surface API problems (bad key, rate limit) to the UI
        log.exception("assistant call failed")
        raise HTTPException(502, f"The assistant could not reply: {exc}") from exc

    doc = _load(session_id)
    prompt = _add_event(doc, "prompt", body.message.strip())
    answer = _add_event(doc, "ai_reply", reply)
    doc["last_code"] = body.code or doc["last_code"]
    store.put(doc)
    return {"prompt": prompt, "reply": answer}


class SubmitBody(CodeBody):
    ai_pasted_chars: int = Field(0, ge=0)


@app.post("/api/sessions/{session_id}/submit")
async def submit(session_id: str, body: SubmitBody) -> dict[str, Any]:
    doc = _load(session_id)
    if doc["status"] != "active":
        raise HTTPException(409, "This session has already been submitted.")
    _require_llm()
    p = _problem(doc["problem_slug"])
    result = await runner.run_tests(body.code, p, p["tests"])

    hidden = [r for r in result["results"] if r["hidden"]]
    hidden_passed = sum(r["passed"] for r in hidden)
    doc = _load(session_id)
    _add_event(doc, "submit", f"{hidden_passed} of {len(hidden)} hidden tests passed")
    if doc["solve_time_s"] is None and all(r["passed"] for r in result["results"]):
        doc["solve_time_s"] = int(_elapsed(doc))
    doc.update(
        status="scoring", final_code=body.code, last_code=body.code,
        ai_pasted_chars=min(body.ai_pasted_chars, len(body.code)),
        test_results=[{k: r[k] for k in ("name", "category", "hidden", "passed")} for r in result["results"]],
        submit_summary={
            "hidden_passed": hidden_passed, "hidden_total": len(hidden),
            "visible": [r for r in result["results"] if not r["hidden"]],
            "failed_hidden": [r["name"] for r in hidden if not r["passed"]],
            "compile_error": result["compile_error"],
        },
    )
    store.put(doc)
    _start_scoring(session_id)
    return _public(doc)


@app.post("/api/sessions/{session_id}/rescore")
def rescore(session_id: str) -> dict[str, Any]:
    doc = _load(session_id)
    if doc["status"] != "error":
        raise HTTPException(409, "Only a session whose scoring failed can be rescored.")
    _require_llm()
    doc.update(status="scoring", error=None)
    store.put(doc)
    _start_scoring(session_id)
    return _public(doc)


# ------------------------------------------------------------------ scoring

def _start_scoring(session_id: str) -> None:
    task = asyncio.create_task(_score(session_id))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


def _judge_session(doc: dict[str, Any]) -> jm.Session:
    p = problems.get(doc["problem_slug"])
    return jm.Session(
        id=doc["id"], mode=doc["mode"], language="python",
        problem=jm.Problem(title=p["title"], statement=p["statement"], constraints=p["constraints"],
                           optimal_time=p["optimal_time"], optimal_space=p["optimal_space"]),
        time_limit_s=TIME_LIMIT_S, solve_time_s=doc["solve_time_s"],
        final_code=doc["final_code"], ai_pasted_chars=doc.get("ai_pasted_chars", 0),
        events=[jm.Event(**e) for e in doc["events"]],
        tests=[jm.TestResult(**t) for t in doc["test_results"]],
    )


async def _score(session_id: str) -> None:
    doc = store.get(session_id)
    try:
        evaluation = await judge.evaluate(_judge_session(doc), _judge_client())
        doc = store.get(session_id)
        doc.update(status="scored", evaluation=evaluation.model_dump(mode="json"), error=None)
    except Exception as exc:
        log.exception("scoring failed for %s", session_id)
        doc = store.get(session_id)
        doc.update(status="error", error=f"{type(exc).__name__}: {exc}")
    store.put(doc)


# ------------------------------------------------------------------ golden set (blind labeling)

from evals import golden  # noqa: E402
from judge import scorers as judge_scorers  # noqa: E402


def _rubric() -> jm.Rubric:
    return jm.Rubric.load()


@app.get("/api/golden/summary")
def golden_summary(labeler: str = "") -> dict[str, Any]:
    labels = golden.load_labels()
    sessions = golden.list_sessions()
    mine = {sid for sid, by in labels.items() if labeler in by}
    return {
        "total": len(sessions),
        "labeled_by_you": len(mine & {s["id"] for s in sessions}),
        "labelers": sorted({name for by in labels.values() for name in by}),
        "sessions": [{"id": s["id"], "mode": s["mode"], "problem_title": s["problem"]["title"],
                      "labeled": s["id"] in mine} for s in sessions],
    }


@app.get("/api/golden/sessions/{session_id}")
def golden_session(session_id: str, labeler: str = "") -> dict[str, Any]:
    try:
        s = golden.get_session(session_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if s is None:
        raise HTTPException(404, "Golden session not found")
    rubric = _rubric()
    js = jm.Session.model_validate(s)
    mine = golden.load_labels().get(session_id, {}).get(labeler)
    # the labeler sees exactly what the judge sees, and nothing about how it was built or scored
    return {
        "id": s["id"], "mode": s["mode"], "problem": s["problem"], "final_code": s["final_code"],
        "events": [e for e in s["events"] if e["type"] in ("prompt", "ai_reply", "run", "submit")],
        "facts": judge_scorers.facts_for_judge(js),
        "dimensions": [{"id": d.id, "name": d.name, "track": t, "definition": d.definition.strip(),
                        "anchors": {str(k): v for k, v in sorted(d.anchors.items())}}
                       for t, d in golden.judged_dimensions(s, rubric)],
        "your_label": mine,
        "rubric_version": rubric.version,
    }


class LabelBody(BaseModel):
    labeler: str
    scores: dict[str, int]
    notes: str = Field("", max_length=2000)


@app.post("/api/golden/sessions/{session_id}/labels")
def save_golden_label(session_id: str, body: LabelBody) -> dict[str, Any]:
    try:
        return golden.save_label(session_id, body.labeler, body.scores, body.notes, _rubric())
    except KeyError as exc:
        raise HTTPException(404, "Golden session not found") from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/sessions/{session_id}/golden")
def add_to_golden(session_id: str) -> dict[str, Any]:
    doc = _load(session_id)
    if "final_code" not in doc:
        raise HTTPException(409, "Submit the session before adding it to the golden set.")
    gid = f"app-{doc['id']}"
    golden.save_session({**_judge_session(doc).model_dump(mode="json"), "id": gid, "source": "app"})
    return {"golden_id": gid}
