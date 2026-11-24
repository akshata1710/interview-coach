import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, MODE_LABEL, type Mode, type ProblemSummary, type RecentSession } from "../api";
import { Difficulty, fmtScore, KeyBanner, TopBar } from "../components/bits";

const MODES: { id: Mode; blurb: string }[] = [
  { id: "ai_assisted", blurb: "An AI assistant sits beside the editor. You're scored on your code and on how you use it." },
  { id: "solo", blurb: "No assistant. A pure check of your problem-solving and code." },
  { id: "interviewer", blurb: "The AI acts as the interviewer: it asks follow-ups and won't write the solution." },
];

export default function Home() {
  const [mode, setMode] = useState<Mode>("ai_assisted");
  const [list, setList] = useState<ProblemSummary[] | null>(null);
  const [recent, setRecent] = useState<RecentSession[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [starting, setStarting] = useState<string | null>(null);
  const [level, setLevel] = useState<"All" | ProblemSummary["difficulty"]>("All");
  const [topic, setTopic] = useState("All topics");
  const [query, setQuery] = useState("");
  const navigate = useNavigate();

  const topics = useMemo(
    () => ["All topics", ...Array.from(new Set((list ?? []).flatMap((p) => p.topics))).sort()],
    [list],
  );
  const shown = useMemo(() => {
    const q = query.trim().toLowerCase();
    return (list ?? []).filter(
      (p) =>
        (level === "All" || p.difficulty === level) &&
        (topic === "All topics" || p.topics.includes(topic)) &&
        (!q || p.title.toLowerCase().includes(q)),
    );
  }, [list, level, topic, query]);

  useEffect(() => {
    api.problems().then(setList).catch((e) => setError(e.message));
    api.recent().then(setRecent).catch(() => {});
  }, []);

  const start = async (slug: string) => {
    setStarting(slug);
    setError(null);
    try {
      const s = await api.startSession(slug, mode);
      navigate(`/session/${s.id}`);
    } catch (e) {
      setError((e as Error).message);
      setStarting(null);
    }
  };

  return (
    <>
      <TopBar />
      <KeyBanner />
      <main className="home">
        <section className="home-intro">
          <h1>Practice the interview where you're allowed to use AI.</h1>
          <p>
            Solve a timed problem with an assistant beside you. When you submit, you get two scores: how ready your
            code is, and how well you worked with the AI, with the exact prompts that cost you points.
          </p>
        </section>

        <fieldset className="mode-picker">
          <legend>Session mode</legend>
          {MODES.map((m) => (
            <label key={m.id} className={`mode-option${mode === m.id ? " is-on" : ""}`}>
              <input
                type="radio"
                name="mode"
                value={m.id}
                checked={mode === m.id}
                onChange={() => setMode(m.id)}
              />
              <span className="mode-name">{MODE_LABEL[m.id]}</span>
              <span className="mode-blurb">{m.blurb}</span>
            </label>
          ))}
        </fieldset>

        {error && (
          <p className="banner banner-error" role="alert">
            {error}
          </p>
        )}

        <section aria-labelledby="problems-h">
          <div className="problems-bar">
            <h2 id="problems-h" className="section-h">
              Problems{list && <span className="muted"> ({shown.length} of {list.length})</span>}
            </h2>
            <div className="filters">
              <div className="seg" role="group" aria-label="Difficulty">
                {(["All", "Easy", "Medium", "Hard"] as const).map((d) => (
                  <button
                    key={d}
                    type="button"
                    className={`seg-btn${level === d ? " is-on" : ""}`}
                    aria-pressed={level === d}
                    onClick={() => setLevel(d)}
                  >
                    {d}
                  </button>
                ))}
              </div>
              <label className="sr-only" htmlFor="topic-filter">
                Topic
              </label>
              <select id="topic-filter" className="field" value={topic} onChange={(e) => setTopic(e.target.value)}>
                {topics.map((t) => (
                  <option key={t}>{t}</option>
                ))}
              </select>
              <label className="sr-only" htmlFor="problem-search">
                Search problems
              </label>
              <input
                id="problem-search"
                className="field"
                type="search"
                placeholder="Search by name"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </div>
          </div>
          <div className="table-wrap">
            <table className="problems">
              <thead>
                <tr>
                  <th scope="col">Problem</th>
                  <th scope="col">Difficulty</th>
                  <th scope="col">Topics</th>
                  <th scope="col">
                    <span className="sr-only">Start</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {!list && (
                  <tr>
                    <td colSpan={4} className="muted">
                      Loading problems…
                    </td>
                  </tr>
                )}
                {list && shown.length === 0 && (
                  <tr>
                    <td colSpan={4} className="muted">
                      No problems match these filters.{" "}
                      <button
                        type="button"
                        className="link-btn"
                        onClick={() => {
                          setLevel("All");
                          setTopic("All topics");
                          setQuery("");
                        }}
                      >
                        Clear filters
                      </button>
                    </td>
                  </tr>
                )}
                {shown.map((p) => (
                  <tr key={p.slug}>
                    <th scope="row">{p.title}</th>
                    <td>
                      <Difficulty level={p.difficulty} />
                    </td>
                    <td className="muted">{p.topics.join(", ")}</td>
                    <td className="cell-action">
                      <button
                        type="button"
                        className="btn btn-primary btn-small"
                        disabled={starting !== null}
                        onClick={() => start(p.slug)}
                      >
                        {starting === p.slug ? "Starting…" : `Start ${MODE_LABEL[mode]}`}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section aria-labelledby="recent-h">
          <h2 id="recent-h" className="section-h">
            Your sessions
          </h2>
          {recent.length === 0 ? (
            <p className="muted">Sessions you start will appear here with their scores.</p>
          ) : (
            <ul className="recent">
              {recent.map((s) => (
                <li key={s.id}>
                  <Link to={s.status === "active" ? `/session/${s.id}` : `/report/${s.id}`}>
                    <span className="recent-title">{s.problem_title}</span>
                    <span className="muted">{MODE_LABEL[s.mode]}</span>
                    <span className="muted">{new Date(s.created_at * 1000).toLocaleString()}</span>
                    <span className="recent-score">
                      {s.status === "scored"
                        ? `${fmtScore(s.combined)} / 4, ${s.label}`
                        : s.status === "active"
                          ? "In progress"
                          : s.status === "scoring"
                            ? "Scoring"
                            : "Scoring failed"}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>
      </main>
    </>
  );
}
