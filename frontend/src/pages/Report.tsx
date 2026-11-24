import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, goldenApi, MODE_LABEL, type DimensionScore, type Session, type SessionEvent } from "../api";
import { fmtClock, fmtScore, Highlighted, TopBar } from "../components/bits";

const NAMES: Record<string, string> = {
  correctness: "Correctness",
  complexity: "Complexity",
  edge_cases: "Edge cases",
  code_quality: "Code quality",
  independence_pace: "Independence and pace",
  framing: "Problem framing",
  decomposition: "Decomposition",
  ownership: "Reasoning ownership",
  verification: "Verification",
  efficiency: "Efficiency",
};

const tone = (s: number) => (s >= 3 ? "strong" : s >= 2 ? "mid" : "weak");

export default function Report() {
  const { id = "" } = useParams();
  const [session, setSession] = useState<Session | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [retrying, setRetrying] = useState(false);

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>;
    let stop = false;
    const load = async () => {
      try {
        const s = await api.session(id);
        if (stop) return;
        setSession(s);
        if (s.status === "scoring" || s.status === "active") timer = setTimeout(load, 2000);
      } catch (e) {
        setError((e as Error).message);
      }
    };
    load();
    return () => {
      stop = true;
      clearTimeout(timer);
    };
  }, [id, retrying]);

  const ev = session?.evaluation ?? null;

  // open on the weakest judged dimension: that's where the most useful feedback is
  useEffect(() => {
    if (!ev || selected) return;
    const judged = ev.dimensions.filter((d) => d.scored_by === "judge");
    const weakest = [...judged].sort((a, b) => a.score - b.score)[0];
    setSelected(weakest?.dimension ?? ev.dimensions[0]?.dimension ?? null);
  }, [ev, selected]);

  const retry = async () => {
    setError(null);
    try {
      await api.rescore(id);
      setRetrying((r) => !r);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  if (error && !session)
    return (
      <>
        <TopBar />
        <main className="center-msg">
          <p className="banner banner-error" role="alert">
            {error}
          </p>
          <Link to="/">Back to problems</Link>
        </main>
      </>
    );
  if (!session)
    return (
      <>
        <TopBar />
        <main className="center-msg muted">Loading report…</main>
      </>
    );

  const sub = session.submit_summary;

  return (
    <>
      <TopBar>
        <Link to="/" className="btn btn-primary">
          Practice another problem
        </Link>
      </TopBar>
      <main className="report">
        <header className="report-head">
          <p className="muted">
            {session.problem_title}, {MODE_LABEL[session.mode]} session
          </p>
          {session.status === "scored" && ev ? (
            <div className="verdict">
              <div className="verdict-score">
                <span className="verdict-num">{fmtScore(ev.combined)}</span>
                <span className="verdict-of">/ 4</span>
              </div>
              <div>
                <h1>{ev.label}</h1>
                <p className="verdict-parts">
                  Code readiness {fmtScore(ev.readiness)}
                  {ev.prompting != null && <>, working with AI {fmtScore(ev.prompting)}</>}
                  {sub && (
                    <>
                      . {sub.hidden_passed} of {sub.hidden_total} hidden tests passed
                      {sub.failed_hidden.length > 0 && <> (failed: {sub.failed_hidden.join(", ")})</>}
                    </>
                  )}
                  .
                </p>
              </div>
            </div>
          ) : session.status === "error" ? (
            <div className="status-box">
              <h1>Scoring didn't finish</h1>
              <p className="bad">{session.error}</p>
              <button type="button" className="btn btn-primary" onClick={retry}>
                Retry scoring
              </button>
              {error && <p className="bad">{error}</p>}
            </div>
          ) : (
            <div className="status-box" role="status">
              <h1>Scoring your session</h1>
              <p className="muted">
                {sub && (
                  <>
                    {sub.hidden_passed} of {sub.hidden_total} hidden tests passed.{" "}
                  </>
                )}
                The judge is reading your code and conversation. This takes about 30 seconds.
              </p>
              <div className="progress" aria-hidden="true">
                <span />
              </div>
            </div>
          )}
        </header>

        {session.status === "scored" && ev && (
          <div className="report-grid">
            <section aria-label="Scorecard" className="scorecard">
              <Track
                title="Code readiness"
                score={ev.readiness}
                dims={ev.dimensions.filter((d) => d.track === "readiness")}
                selected={selected}
                onSelect={setSelected}
              />
              {ev.prompting != null && (
                <Track
                  title="Working with AI"
                  score={ev.prompting}
                  dims={ev.dimensions.filter((d) => d.track === "prompting")}
                  selected={selected}
                  onSelect={setSelected}
                />
              )}
              {ev.rewrite && (
                <section className="rewrite" aria-labelledby="rewrite-h">
                  <h2 id="rewrite-h" className="section-h">
                    The prompt to rewrite first
                  </h2>
                  <div className="rewrite-pair">
                    <div>
                      <p className="rewrite-label">You wrote</p>
                      <blockquote className="quote-old">{ev.rewrite.original}</blockquote>
                    </div>
                    <div>
                      <p className="rewrite-label">A stronger version</p>
                      <blockquote className="quote-new">{ev.rewrite.rewritten}</blockquote>
                    </div>
                  </div>
                  <p className="muted">{ev.rewrite.why}</p>
                </section>
              )}
              <p className="fineprint">
                Scored with rubric {ev.rubric_version} by {ev.judge_model}. Each judged dimension is scored twice;
                differing runs are shown.
              </p>
              <AddToGolden sessionId={session.id} />
            </section>

            <Evidence
              session={session}
              dim={ev.dimensions.find((d) => d.dimension === selected) ?? null}
            />
          </div>
        )}
      </main>
    </>
  );
}

function Track({
  title,
  score,
  dims,
  selected,
  onSelect,
}: {
  title: string;
  score: number;
  dims: DimensionScore[];
  selected: string | null;
  onSelect: (d: string) => void;
}) {
  return (
    <section className="track" aria-label={title}>
      <div className="track-head">
        <h2 className="section-h">{title}</h2>
        <span className={`track-score tone-${tone(score)}`}>{fmtScore(score)}</span>
      </div>
      <ul className="dims">
        {dims.map((d) => {
          const on = selected === d.dimension;
          return (
            <li key={d.dimension}>
              <button
                type="button"
                className={`dim${on ? " is-on" : ""}`}
                aria-pressed={on}
                onClick={() => onSelect(d.dimension)}
              >
                <span className="dim-top">
                  <span className="dim-name">{NAMES[d.dimension] ?? d.dimension}</span>
                  <span className="dim-weight">{Math.round(d.weight * 100)}%</span>
                  <span className={`dim-score tone-${tone(d.score)}`}>{fmtScore(d.score)}</span>
                </span>
                <span className="scale" aria-hidden="true">
                  <span className={`scale-fill tone-bg-${tone(d.score)}`} style={{ width: `${(d.score / 4) * 100}%` }} />
                  {[1, 2, 3].map((t) => (
                    <span key={t} className="scale-tick" style={{ left: `${t * 25}%` }} />
                  ))}
                </span>
                <span className="dim-why">{d.rationale}</span>
                {d.judge_runs.length > 1 && new Set(d.judge_runs).size > 1 && (
                  <span className="dim-runs">Judge runs disagreed: {d.judge_runs.join(", ")}</span>
                )}
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

function Evidence({ session, dim }: { session: Session; dim: DimensionScore | null }) {
  const byEvent = useMemo(() => {
    const m = new Map<string, string[]>();
    for (const e of dim?.evidence ?? []) m.set(e.event_id, [...(m.get(e.event_id) ?? []), e.quote]);
    return m;
  }, [dim]);
  const firstMarked = useRef<HTMLDivElement>(null);

  useEffect(() => {
    firstMarked.current?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [dim]);

  const convo = session.events.filter((e) => e.type === "prompt" || e.type === "ai_reply");
  const codeQuotes = byEvent.get("final_code") ?? [];
  let attached = false;
  const refFor = (marked: boolean) => {
    if (marked && !attached) {
      attached = true;
      return firstMarked;
    }
    return undefined;
  };

  return (
    <section className="evidence" aria-labelledby="evidence-h">
      <h2 id="evidence-h" className="section-h">
        {dim ? `Evidence for ${NAMES[dim.dimension] ?? dim.dimension}` : "Evidence"}
      </h2>
      {dim?.scored_by === "code" && (
        <p className="evidence-note">Measured from your tests and timing, not by the judge: {dim.rationale}</p>
      )}
      {dim?.scored_by === "judge" && byEvent.size > 0 && (
        <p className="evidence-note">Highlighted below are the exact words the judge based this score on.</p>
      )}

      {convo.length > 0 && (
        <div className="transcript">
          <h3 className="evidence-sub">Conversation</h3>
          {convo.map((e) => (
            <Turn key={e.id} event={e} quotes={byEvent.get(e.id) ?? []} markRef={refFor(byEvent.has(e.id))} />
          ))}
        </div>
      )}

      <div className="final-code" ref={refFor(codeQuotes.length > 0)}>
        <h3 className="evidence-sub">Submitted code</h3>
        <pre className={codeQuotes.length ? "is-marked" : ""}>
          <code>
            <Highlighted text={session.last_code} quotes={codeQuotes} />
          </code>
        </pre>
      </div>
    </section>
  );
}

function Turn({
  event,
  quotes,
  markRef,
}: {
  event: SessionEvent;
  quotes: string[];
  markRef?: React.Ref<HTMLDivElement>;
}) {
  const [open, setOpen] = useState(false);
  const you = event.type === "prompt";
  const long = !you && event.text.length > 280 && quotes.length === 0;
  const text = long && !open ? event.text.slice(0, 280).trimEnd() + "…" : event.text;
  return (
    <div ref={markRef} className={`turn ${you ? "turn-you" : "turn-ai"}${quotes.length ? " is-marked" : ""}`}>
      <div className="turn-who">
        {you ? "You" : "Assistant"} <span className="muted">{fmtClock(event.ts)}</span>
      </div>
      <div className="turn-text">
        <Highlighted text={text} quotes={quotes} />
      </div>
      {long && (
        <button type="button" className="link-btn" onClick={() => setOpen(!open)}>
          {open ? "Show less" : "Show full reply"}
        </button>
      )}
    </div>
  );
}

function AddToGolden({ sessionId }: { sessionId: string }) {
  const [state, setState] = useState<"idle" | "busy" | "done" | "error">("idle");
  const [msg, setMsg] = useState("");
  const add = async () => {
    setState("busy");
    try {
      const { golden_id } = await goldenApi.addFromApp(sessionId);
      setState("done");
      setMsg(`Added as ${golden_id}.`);
    } catch (e) {
      setState("error");
      setMsg((e as Error).message);
    }
  };
  return (
    <div className="golden-add">
      <p className="muted">
        Real sessions make the judge's accuracy number more credible. Labels are best done blind, so leave it a few
        days or ask someone who hasn't seen this report.
      </p>
      {state === "done" ? (
        <p className="ok" role="status">
          {msg} <Link to="/label">Open the labeling page</Link>
        </p>
      ) : (
        <button type="button" className="btn btn-quiet btn-small" onClick={add} disabled={state === "busy"}>
          {state === "busy" ? "Adding…" : "Add this session to the golden set"}
        </button>
      )}
      {state === "error" && <p className="bad">{msg}</p>}
    </div>
  );
}
