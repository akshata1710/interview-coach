import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { goldenApi, MODE_LABEL, type GoldenSession, type GoldenSummary } from "../api";
import { fmtClock, RichText, TopBar } from "../components/bits";

const NAME_KEY = "coach-labeler";
const NAME_RE = /^[a-z0-9][a-z0-9_-]{0,31}$/;

function storedName(): string {
  try {
    return localStorage.getItem(NAME_KEY) ?? "";
  } catch {
    return "";
  }
}

export default function Label() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [name, setName] = useState(storedName);
  const [nameDraft, setNameDraft] = useState(storedName);
  const [summary, setSummary] = useState<GoldenSummary | null>(null);
  const [session, setSession] = useState<GoldenSession | null>(null);
  const [scores, setScores] = useState<Record<string, number>>({});
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!name) return;
    try {
      setSummary(await goldenApi.summary(name));
    } catch (e) {
      setError((e as Error).message);
    }
  }, [name]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  // with no session in the URL, open the first one this labeler hasn't scored
  useEffect(() => {
    if (!summary || id) return;
    const next = summary.sessions.find((s) => !s.labeled) ?? summary.sessions[0];
    if (next) navigate(`/label/${next.id}`, { replace: true });
  }, [summary, id, navigate]);

  useEffect(() => {
    if (!id || !name) return;
    setSession(null);
    setError(null);
    goldenApi
      .session(id, name)
      .then((s) => {
        setSession(s);
        setScores(s.your_label?.scores ?? {});
        setNotes(s.your_label?.notes ?? "");
        window.scrollTo(0, 0);
      })
      .catch((e) => setError((e as Error).message));
  }, [id, name]);

  const saveName = () => {
    const n = nameDraft.trim().toLowerCase();
    if (!NAME_RE.test(n)) {
      setError("Use lowercase letters, digits, - or _ for your labeler name.");
      return;
    }
    try {
      localStorage.setItem(NAME_KEY, n);
    } catch {
      /* fine: the name just won't be remembered */
    }
    setError(null);
    setName(n);
  };

  const complete = session ? session.dimensions.every((d) => scores[d.id] !== undefined) : false;

  const save = async () => {
    if (!session || !complete) return;
    setSaving(true);
    setError(null);
    try {
      await goldenApi.label(session.id, name, scores, notes);
      const fresh = await goldenApi.summary(name);
      setSummary(fresh);
      const order = fresh.sessions;
      const at = order.findIndex((s) => s.id === session.id);
      const next = [...order.slice(at + 1), ...order.slice(0, at)].find((s) => !s.labeled);
      if (next) navigate(`/label/${next.id}`);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  if (!name)
    return (
      <>
        <TopBar />
        <main className="label-intro">
          <h1>Label the golden set</h1>
          <p>
            You'll score practice sessions on the same rubric the judge uses, without seeing the judge's scores. Your
            labels are what the judge's accuracy is measured against, so score what the session shows, using the
            anchors.
          </p>
          <form
            className="name-form"
            onSubmit={(e) => {
              e.preventDefault();
              saveName();
            }}
          >
            <label htmlFor="labeler">Your labeler name</label>
            <div className="name-row">
              <input
                id="labeler"
                className="field"
                value={nameDraft}
                onChange={(e) => setNameDraft(e.target.value)}
                placeholder="e.g. akshata"
                autoComplete="off"
              />
              <button type="submit" className="btn btn-primary">
                Start labeling
              </button>
            </div>
            {error && <p className="bad">{error}</p>}
          </form>
        </main>
      </>
    );

  const done = summary?.labeled_by_you ?? 0;
  const total = summary?.total ?? 0;

  return (
    <>
      <TopBar>
        <span className="muted label-progress">
          {done} of {total} labeled by <strong>{name}</strong>
        </span>
        <button
          type="button"
          className="btn btn-quiet btn-small"
          onClick={() => {
            setName("");
            setSummary(null);
          }}
        >
          Switch labeler
        </button>
      </TopBar>
      {error && (
        <p className="banner banner-error" role="alert">
          {error}
        </p>
      )}
      {summary && done === total && total > 0 && (
        <p className="banner">
          You've labeled every session. Run <code>python -m evals.run_eval</code> in the backend to measure the
          judge against your labels.
        </p>
      )}
      <nav className="label-strip" aria-label="Golden sessions">
        {summary?.sessions.map((s, i) => (
          <button
            key={s.id}
            type="button"
            className={`strip-cell${s.id === id ? " is-current" : ""}${s.labeled ? " is-done" : ""}`}
            onClick={() => navigate(`/label/${s.id}`)}
            aria-label={`Session ${i + 1}${s.labeled ? ", labeled" : ""}`}
            aria-current={s.id === id ? "page" : undefined}
          >
            {i + 1}
          </button>
        ))}
      </nav>

      {!session ? (
        <main className="center-msg muted">Loading session…</main>
      ) : (
        <main className="label-grid">
          <section className="label-evidence" aria-label="Session">
            <header>
              <p className="muted">
                {MODE_LABEL[session.mode]} session, {session.id}
              </p>
              <h1>{session.problem.title}</h1>
              <p>{session.problem.statement}</p>
              <p className="muted">Constraints: {session.problem.constraints}</p>
            </header>
            <dl className="facts">
              {Object.entries(session.facts).map(([k, v]) => (
                <div key={k}>
                  <dt>{k}</dt>
                  <dd>{v}</dd>
                </div>
              ))}
            </dl>
            {session.events.some((e) => e.type === "prompt") && (
              <div className="transcript">
                <h2 className="evidence-sub">Conversation</h2>
                {session.events.map((e) =>
                  e.type === "prompt" || e.type === "ai_reply" ? (
                    <div key={e.id} className={`turn ${e.type === "prompt" ? "turn-you" : "turn-ai"}`}>
                      <div className="turn-who">
                        {e.type === "prompt" ? "Candidate" : "Assistant"}{" "}
                        <span className="muted">
                          {e.id}, {fmtClock(e.ts)}
                        </span>
                      </div>
                      <div className="turn-text">
                        {e.type === "prompt" ? e.text : <RichText text={e.text} />}
                      </div>
                    </div>
                  ) : (
                    <p key={e.id} className="turn-event muted">
                      {fmtClock(e.ts)} {e.type === "run" ? "Ran tests" : "Submitted"}: {e.text}
                    </p>
                  ),
                )}
              </div>
            )}
            <div className="final-code">
              <h2 className="evidence-sub">Submitted code</h2>
              <pre>
                <code>{session.final_code}</code>
              </pre>
            </div>
          </section>

          <section className="label-form" aria-label="Your scores">
            <h2 className="section-h">Your scores</h2>
            <p className="muted label-hint">
              Whole numbers. 0, 2 and 4 are defined below; 1 and 3 sit between them. Score what this session shows,
              not what you'd expect from someone who wrote it.
            </p>
            {session.dimensions.map((d) => (
              <fieldset key={d.id} className="dim-label">
                <legend>
                  {d.name}
                  <span className="muted"> ({d.track === "readiness" ? "code" : "working with AI"})</span>
                </legend>
                <p className="dim-def">{d.definition}</p>
                <ul className="anchors">
                  {Object.entries(d.anchors).map(([k, v]) => (
                    <li key={k}>
                      <span className="anchor-k">{k}</span> {v}
                    </li>
                  ))}
                </ul>
                <div className="score-row" role="radiogroup" aria-label={`${d.name} score`}>
                  {[0, 1, 2, 3, 4].map((n) => (
                    <label key={n} className={`score-pick${scores[d.id] === n ? " is-on" : ""}`}>
                      <input
                        type="radio"
                        name={d.id}
                        value={n}
                        checked={scores[d.id] === n}
                        onChange={() => setScores((s) => ({ ...s, [d.id]: n }))}
                      />
                      {n}
                    </label>
                  ))}
                </div>
              </fieldset>
            ))}
            <label htmlFor="label-notes" className="notes-label">
              Notes (optional)
            </label>
            <textarea
              id="label-notes"
              rows={3}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Anything that made a score hard to call"
            />
            <button type="button" className="btn btn-primary label-save" disabled={!complete || saving} onClick={save}>
              {saving ? "Saving…" : session.your_label ? "Update and go to next" : "Save and go to next"}
            </button>
            {!complete && <p className="muted label-hint">Score every dimension to save.</p>}
          </section>
        </main>
      )}
    </>
  );
}
