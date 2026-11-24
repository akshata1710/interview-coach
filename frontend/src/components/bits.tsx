import { Fragment, useEffect, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { api, type Health } from "../api";

export function TopBar({ children }: { children?: ReactNode }) {
  return (
    <header className="topbar">
      <Link to="/" className="brand" aria-label="Interview Coach home">
        <span className="brand-mark" aria-hidden="true">
          {"{ }"}
        </span>
        Interview Coach
      </Link>
      <div className="topbar-right">
        {children}
        <Link to="/label" className="topbar-link">
          Label golden set
        </Link>
      </div>
    </header>
  );
}

/** Warns once at the top of a page when the backend cannot reach Claude. */
export function KeyBanner() {
  const [health, setHealth] = useState<Health | null>(null);
  const [down, setDown] = useState(false);
  useEffect(() => {
    api.health().then(setHealth).catch(() => setDown(true));
  }, []);
  if (down)
    return (
      <p className="banner banner-error" role="alert">
        The backend isn't running. Start it in a terminal with <code>uvicorn app.main:app --reload</code> from the
        backend folder.
      </p>
    );
  if (!health) return null;
  if (health.offline_mode)
    return (
      <p className="banner">
        Offline mode: the assistant gives canned replies and scores are placeholders. Restart the backend without{" "}
        <code>COACH_FAKE_LLM=1</code> for real feedback.
      </p>
    );
  if (!health.api_key_set)
    return (
      <p className="banner banner-error" role="alert">
        The assistant and scoring need an API key. In the backend terminal, run{" "}
        <code>export ANTHROPIC_API_KEY=…</code> and restart the backend.
      </p>
    );
  return null;
}

export function Difficulty({ level }: { level: string }) {
  return <span className={`difficulty difficulty-${level.toLowerCase()}`}>{level}</span>;
}

/** Renders assistant text: fenced code blocks, inline `code`, and paragraphs. */
export function RichText({ text }: { text: string }) {
  const parts = text.split(/```(\w*)\n?([\s\S]*?)```/g);
  const out: ReactNode[] = [];
  for (let i = 0; i < parts.length; i += 3) {
    const prose = parts[i];
    if (prose?.trim()) out.push(<Prose key={`p${i}`} text={prose.trim()} />);
    if (i + 2 < parts.length) out.push(<CodeBlock key={`c${i}`} code={parts[i + 2].replace(/\n$/, "")} />);
  }
  return <>{out}</>;
}

function Prose({ text }: { text: string }) {
  return (
    <>
      {text.split(/\n{2,}/).map((para, i) => (
        <p key={i} className="rich-p">
          {para.split(/(`[^`]+`)/g).map((bit, j) =>
            bit.startsWith("`") && bit.endsWith("`") && bit.length > 2 ? (
              <code key={j}>{bit.slice(1, -1)}</code>
            ) : (
              <Fragment key={j}>{bit}</Fragment>
            ),
          )}
        </p>
      ))}
    </>
  );
}

function CodeBlock({ code }: { code: string }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard blocked: the user can still select the text */
    }
  };
  return (
    <div className="codeblock">
      <pre>
        <code>{code}</code>
      </pre>
      <button type="button" className="btn btn-quiet btn-small codeblock-copy" onClick={copy}>
        {copied ? "Copied" : "Copy code"}
      </button>
    </div>
  );
}

/** Wraps every case-insensitive occurrence of any quote in <mark>. */
export function Highlighted({ text, quotes }: { text: string; quotes: string[] }) {
  const words = quotes.map((q) => q.trim().split(/\s+/).filter(Boolean)).filter((w) => w.length > 0);
  if (!words.length) return <>{text}</>;
  const spans: [number, number][] = [];
  for (const w of words) {
    // the judge's quotes match ignoring case and runs of whitespace, so search the same way
    const re = new RegExp(w.map((x) => x.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("\\s+"), "gi");
    for (const m of text.matchAll(re)) spans.push([m.index!, m.index! + m[0].length]);
  }
  if (!spans.length) return <>{text}</>;
  spans.sort((a, b) => a[0] - b[0]);
  const merged: [number, number][] = [];
  for (const s of spans) {
    const last = merged[merged.length - 1];
    if (last && s[0] <= last[1]) last[1] = Math.max(last[1], s[1]);
    else merged.push([...s]);
  }
  const out: ReactNode[] = [];
  let pos = 0;
  merged.forEach(([a, b], i) => {
    if (a > pos) out.push(text.slice(pos, a));
    out.push(<mark key={i}>{text.slice(a, b)}</mark>);
    pos = b;
  });
  if (pos < text.length) out.push(text.slice(pos));
  return <>{out}</>;
}

export function fmtClock(totalSeconds: number) {
  const s = Math.max(0, Math.floor(totalSeconds));
  return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
}

export function fmtScore(n: number | null | undefined) {
  return n == null ? "–" : n.toFixed(1);
}
