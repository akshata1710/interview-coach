import { useCallback, useEffect, useRef, useState, type KeyboardEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, MODE_LABEL, type Problem, type RunResult, type Session, type SessionEvent } from "../api";
import { Difficulty, fmtClock, KeyBanner, RichText, TopBar } from "../components/bits";
import CodeEditor from "../components/CodeEditor";

const draftKey = (id: string) => `coach-draft-${id}`;
const pasteKey = (id: string) => `coach-pasted-${id}`;

function readLocal(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}
function writeLocal(key: string, value: string) {
  try {
    localStorage.setItem(key, value);
  } catch {
    /* storage unavailable: the server still has the last run's code */
  }
}

export default function SessionPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const [session, setSession] = useState<Session | null>(null);
  const [problem, setProblem] = useState<Problem | null>(null);
  const [code, setCode] = useState("");
  const [result, setResult] = useState<RunResult | null>(null);
  const [running, setRunning] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [messages, setMessages] = useState<SessionEvent[]>([]);
  const [draft, setDraft] = useState("");
  const [thinking, setThinking] = useState(false);
  const [pasted, setPasted] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [now, setNow] = useState(Date.now() / 1000);
  const chatEnd = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const s = await api.session(id);
        if (s.status !== "active") {
          navigate(`/report/${id}`, { replace: true });
          return;
        }
        const p = await api.problem(s.problem_slug);
        if (cancelled) return;
        setSession(s);
        setProblem(p);
        setCode(readLocal(draftKey(id)) ?? s.last_code);
        setPasted(Number(readLocal(pasteKey(id)) ?? 0));
        setMessages(s.events.filter((e) => e.type === "prompt" || e.type === "ai_reply"));
      } catch (e) {
        setError((e as Error).message);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id, navigate]);

  useEffect(() => {
    const t = setInterval(() => setNow(Date.now() / 1000), 1000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    chatEnd.current?.scrollIntoView({ block: "end" });
  }, [messages, thinking]);

  const updateCode = (v: string) => {
    setCode(v);
    writeLocal(draftKey(id), v);
  };

  const onPaste = (text: string) => {
    const t = text.trim();
    if (t.length < 20) return;
    const norm = (s: string) => s.replace(/\s+/g, " ");
    const fromAi = messages.some((m) => m.type === "ai_reply" && norm(m.text).includes(norm(t)));
    if (fromAi) {
      const next = pasted + t.length;
      setPasted(next);
      writeLocal(pasteKey(id), String(next));
    }
  };

  const run = useCallback(async () => {
    if (running) return;
    setRunning(true);
    setError(null);
    try {
      setResult(await api.run(id, code));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setRunning(false);
    }
  }, [id, code, running]);

  const send = async () => {
    const text = draft.trim();
    if (!text || thinking) return;
    setThinking(true);
    setError(null);
    const pending: SessionEvent = { id: "pending", type: "prompt", ts: 0, text };
    setMessages((m) => [...m, pending]);
    setDraft("");
    try {
      const { prompt, reply } = await api.chat(id, text, code);
      setMessages((m) => [...m.filter((x) => x.id !== "pending"), prompt, reply]);
    } catch (e) {
      setMessages((m) => m.filter((x) => x.id !== "pending"));
      setDraft(text);
      setError((e as Error).message);
    } finally {
      setThinking(false);
    }
  };

  const onChatKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  const submit = async () => {
    if (!window.confirm("Submit for scoring? Your code runs against the hidden tests and you can't edit it after.")) return;
    setSubmitting(true);
    setError(null);
    try {
      await api.submit(id, code, Math.min(pasted, code.length));
      navigate(`/report/${id}`);
    } catch (e) {
      setError((e as Error).message);
      setSubmitting(false);
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
  if (!session || !problem)
    return (
      <>
        <TopBar />
        <main className="center-msg muted">Loading session…</main>
      </>
    );

  const remaining = session.time_limit_s - (now - session.created_at);
  const showChat = session.mode !== "solo";
  const passed = result?.results.filter((r) => r.passed).length ?? 0;

  return (
    <div className="session-shell">
      <TopBar>
        <span className="mode-tag">{MODE_LABEL[session.mode]}</span>
        <span className={`timer${remaining < 300 ? " timer-low" : ""}`} aria-label="Time remaining" role="timer">
          {remaining > 0 ? fmtClock(remaining) : "Time's up"}
        </span>
        <button type="button" className="btn btn-quiet" onClick={run} disabled={running}>
          {running ? "Running…" : "Run tests"}
        </button>
        <button type="button" className="btn btn-primary" onClick={submit} disabled={submitting}>
          {submitting ? "Submitting…" : "Submit"}
        </button>
      </TopBar>
      <KeyBanner />
      {error && (
        <p className="banner banner-error" role="alert">
          {error}
        </p>
      )}

      <main className={`session-grid${showChat ? "" : " no-chat"}`}>
        <section className="pane problem-pane" aria-labelledby="problem-title">
          <div className="problem-meta">
            <Difficulty level={problem.difficulty} />
            <span className="muted">{problem.topics.join(", ")}</span>
          </div>
          <h1 id="problem-title">{problem.title}</h1>
          <p>{problem.statement}</p>
          {problem.examples.map((ex, i) => (
            <div className="example" key={i}>
              <div>
                <span className="muted">Input</span> <code>{ex.input}</code>
              </div>
              <div>
                <span className="muted">Output</span> <code>{ex.output}</code>
              </div>
              {ex.explanation && <div className="muted">{ex.explanation}</div>}
            </div>
          ))}
          <h2 className="pane-h">Constraints</h2>
          <p className="muted">{problem.constraints}</p>
          <p className="pane-note">
            Implement <code>{problem.function_name}</code>. Run tests checks the {problem.visible_tests.length}{" "}
            examples; Submit also runs {problem.hidden_test_count} hidden tests. Cmd/Ctrl + Enter runs tests.
          </p>
        </section>

        <section className="work-pane" aria-label="Editor and test results">
          <div className="editor-wrap">
            <CodeEditor value={code} onChange={updateCode} onPaste={onPaste} onRun={run} />
          </div>
          <div className="results" aria-live="polite">
            <div className="results-head">
              <h2 className="pane-h">Test results</h2>
              {result && !result.compile_error && (
                <span className={passed === result.results.length ? "ok" : "bad"}>
                  {passed} of {result.results.length} passed
                </span>
              )}
            </div>
            {!result && <p className="muted">Run tests to check your code against the examples.</p>}
            {result?.compile_error && <pre className="error-pre">{result.compile_error}</pre>}
            {result && !result.compile_error && (
              <ul className="test-list">
                {result.results.map((r) => (
                  <li key={r.name} className={r.passed ? "is-pass" : "is-fail"}>
                    <span className="test-mark" aria-hidden="true">
                      {r.passed ? "✓" : "✗"}
                    </span>
                    <div>
                      <div className="test-name">
                        {r.name}
                        <span className="sr-only">{r.passed ? " passed" : " failed"}</span>
                        {r.ms != null && <span className="muted"> {r.ms} ms</span>}
                      </div>
                      {!r.passed && (
                        <div className="test-detail">
                          {r.error ? (
                            <code className="bad">{r.error}</code>
                          ) : (
                            <>
                              <div>
                                <span className="muted">Expected</span> <code>{r.expected}</code>
                              </div>
                              <div>
                                <span className="muted">Got</span> <code>{r.got}</code>
                              </div>
                            </>
                          )}
                        </div>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>

        {showChat && (
          <section className="pane chat-pane" aria-labelledby="chat-title">
            <div className="chat-head">
              <h2 id="chat-title" className="pane-h">
                {session.mode === "interviewer" ? "Interviewer" : "AI assistant"}
              </h2>
              <p className="muted">
                {session.mode === "interviewer"
                  ? "Talk through your approach. It asks questions and won't write the solution."
                  : "Use it as you would in the real interview. Every message is part of your score."}
              </p>
            </div>
            <div className="chat-log">
              {messages.length === 0 && (
                <p className="muted chat-empty">
                  Strong first messages state the constraints, your idea, and what you want checked.
                </p>
              )}
              {messages.map((m) =>
                m.type === "prompt" ? (
                  <div key={m.id} className="msg msg-you">
                    {m.text}
                  </div>
                ) : (
                  <div key={m.id} className="msg msg-ai">
                    <RichText text={m.text} />
                  </div>
                ),
              )}
              {thinking && <div className="msg msg-ai muted">Thinking…</div>}
              <div ref={chatEnd} />
            </div>
            <form
              className="chat-form"
              onSubmit={(e) => {
                e.preventDefault();
                send();
              }}
            >
              <label htmlFor="chat-input" className="sr-only">
                Message
              </label>
              <textarea
                id="chat-input"
                rows={3}
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={onChatKey}
                placeholder="Message. Enter sends, Shift+Enter for a new line."
              />
              <button type="submit" className="btn btn-primary" disabled={thinking || !draft.trim()}>
                Send
              </button>
            </form>
          </section>
        )}
      </main>
    </div>
  );
}
