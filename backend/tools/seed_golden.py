"""Write the seed sessions for the golden set to golden/sessions/.

    python tools/seed_golden.py

Real sessions are better, and you can add them from the app's report page. Seeds
exist so the set covers the whole score range on day one: a judge that only ever
sees middling sessions can look accurate while being unable to tell 0 from 4.

Each AI-assisted seed combines a problem with a prompting archetype:
  handoff      pastes the problem, asks for the code, submits it
  strong       states constraints and an idea, asks for critique, checks edge cases early
  late_verify  reasonable framing, picks an approach, asks about edge cases only at the end
  flailing     vague, repeated prompts; pastes code in pieces
  blind_trust  states an idea, accepts a wrong claim from the assistant, ships the bug
  catches_bug  asks for an approach, spots the assistant's mistake with a counterexample
Code quality varies independently (clean, messy, brute force, buggy), and every
seed's test results come from actually running its code.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import problems, runner  # noqa: E402

OUT = ROOT / "golden" / "sessions"
LIMIT_S = 45 * 60

# ------------------------------------------------------------------ per-problem material

P = {
    "two-sum": {
        "paste": "two sum leetcode, solve in python",
        "own_words": "I need indices of two numbers in an array that add up to a target.",
        "constraints": "Array up to 10^4 ints, values can be negative, exactly one answer, can't reuse an element.",
        "idea": "I'm thinking a hash map from value to index so I can do it in one pass, O(n).",
        "tricky": "If I insert the current number before checking for its complement, can [3,3] with target 6 break?",
        "edge_q": "Before I code it: what edge cases should I handle, like duplicates or negatives?",
        "wrong_claim": "Insert each number into the map first, then look up target - x. Order doesn't matter here.",
        "counter": "That can't be right: with [3,2,4] and target 6, inserting 3 first then finding 3 returns [0,0], the same element twice.",
        "approaches": "Two options: nested loops in O(n^2), or a hash map of seen values in O(n).",
        "clean": "def two_sum(nums: list[int], target: int) -> list[int]:\n    seen = {}\n    for i, x in enumerate(nums):\n        if target - x in seen:\n            return [seen[target - x], i]\n        seen[x] = i\n    return []\n",
        "messy": "def two_sum(nums, target):\n    d = {}\n    res = []\n    for i in range(len(nums)):\n        n = nums[i]\n        t = target - n\n        if t in d.keys():\n            res = [d[t], i]\n            return res\n        else:\n            d[n] = i\n    return res\n",
        "brute": "def two_sum(nums, target):\n    for i in range(len(nums)):\n        for j in range(i + 1, len(nums)):\n            if nums[i] + nums[j] == target:\n                return [i, j]\n    return []\n",
        "buggy": "def two_sum(nums, target):\n    seen = {}\n    for i, x in enumerate(nums):\n        seen[x] = i\n        if target - x in seen:\n            return [seen[target - x], i]\n    return []\n",
    },
    "longest-substring": {
        "paste": "longest substring without repeating characters solve in python",
        "own_words": "I need the length of the longest substring with all distinct characters.",
        "constraints": "String up to 5*10^4 chars, any ASCII including spaces. I want O(n).",
        "idea": "My plan is a sliding window with a map of each char's last index; on a repeat I move left past it.",
        "tricky": "When the repeated char was last seen before the current window starts, should left move at all?",
        "edge_q": "Before I write it, which edge cases matter: empty string, all same char, something like abba?",
        "wrong_claim": "On a repeat, always set left = last_seen[ch] + 1. No other check is needed.",
        "counter": "That breaks on \"abba\": at the last a, last_seen[a] is 0, so left would jump back from 2 to 1.",
        "approaches": "Brute force checks every substring, O(n^3). A sliding window with a last-seen map is O(n).",
        "clean": "def length_of_longest_substring(s: str) -> int:\n    last_seen = {}\n    left = best = 0\n    for right, ch in enumerate(s):\n        if ch in last_seen and last_seen[ch] >= left:\n            left = last_seen[ch] + 1\n        last_seen[ch] = right\n        best = max(best, right - left + 1)\n    return best\n",
        "messy": "def length_of_longest_substring(s):\n    m = {}\n    l = 0\n    ans = 0\n    for r in range(len(s)):\n        c = s[r]\n        if c in m:\n            if m[c] >= l:\n                l = m[c] + 1\n        m[c] = r\n        if r - l + 1 > ans:\n            ans = r - l + 1\n    return ans\n",
        "brute": "def length_of_longest_substring(s):\n    best = 0\n    for i in range(len(s)):\n        for j in range(i, len(s)):\n            if len(set(s[i:j + 1])) == j - i + 1:\n                best = max(best, j - i + 1)\n    return best\n",
        "buggy": "def length_of_longest_substring(s):\n    last_seen = {}\n    left = best = 0\n    for right, ch in enumerate(s):\n        if ch in last_seen:\n            left = last_seen[ch] + 1\n        last_seen[ch] = right\n        best = max(best, right - left + 1)\n    return best\n",
    },
    "valid-parentheses": {
        "paste": "valid parentheses problem, write python",
        "own_words": "I need to check that every bracket in a string is closed by the same type, in the right order.",
        "constraints": "String up to 10^4 chars, only ()[]{}. Target O(n) time.",
        "idea": "I'll push opening brackets on a stack and pop when I see the matching closer.",
        "tricky": "What should happen when a closing bracket arrives and the stack is already empty?",
        "edge_q": "What edge cases should I test first: a lone closer, a leftover opener, interleaving like ([)]?",
        "wrong_claim": "Just pop on each closer and compare. If the loop finishes without a mismatch, return True.",
        "counter": "That returns True for \"((\": nothing mismatches, but two openers are never closed. We need the stack to be empty at the end.",
        "approaches": "You can repeatedly delete matched pairs like \"()\" until nothing changes, or use a stack in one pass.",
        "clean": "def is_valid(s: str) -> bool:\n    pairs = {')': '(', ']': '[', '}': '{'}\n    stack = []\n    for ch in s:\n        if ch in pairs:\n            if not stack or stack.pop() != pairs[ch]:\n                return False\n        else:\n            stack.append(ch)\n    return not stack\n",
        "messy": "def is_valid(s):\n    st = []\n    for c in s:\n        if c == '(' or c == '[' or c == '{':\n            st.append(c)\n        else:\n            if len(st) == 0:\n                return False\n            t = st.pop()\n            if c == ')' and t != '(':\n                return False\n            if c == ']' and t != '[':\n                return False\n            if c == '}' and t != '{':\n                return False\n    if len(st) == 0:\n        return True\n    return False\n",
        "brute": "def is_valid(s):\n    prev = None\n    while prev != s:\n        prev = s\n        s = s.replace('()', '').replace('[]', '').replace('{}', '')\n    return s == ''\n",
        "buggy": "def is_valid(s):\n    pairs = {')': '(', ']': '[', '}': '{'}\n    stack = []\n    for ch in s:\n        if ch in pairs:\n            if not stack or stack.pop() != pairs[ch]:\n                return False\n        else:\n            stack.append(ch)\n    return True\n",
    },
    "merge-intervals": {
        "paste": "merge overlapping intervals, give me python code",
        "own_words": "I need to merge overlapping intervals and return the merged list.",
        "constraints": "Up to 10^4 intervals, unsorted, and touching ones like [1,4],[4,5] count as overlapping.",
        "idea": "I'll sort by start, then extend the last merged interval while the next one starts before it ends.",
        "tricky": "For touching intervals, should my overlap check be start <= last_end or start < last_end?",
        "edge_q": "Which edge cases should I plan for: a single interval, one containing another, touching ends?",
        "wrong_claim": "After sorting, merge when start < last_end. Touching intervals stay separate.",
        "counter": "The problem says touching intervals overlap: [1,4],[4,5] must become [1,5], so it has to be <=.",
        "approaches": "Compare every pair repeatedly until nothing merges, or sort by start and do one pass.",
        "clean": "def merge(intervals: list[list[int]]) -> list[list[int]]:\n    merged = []\n    for start, end in sorted(intervals):\n        if merged and start <= merged[-1][1]:\n            merged[-1][1] = max(merged[-1][1], end)\n        else:\n            merged.append([start, end])\n    return merged\n",
        "messy": "def merge(intervals):\n    intervals.sort(key=lambda x: x[0])\n    res = []\n    for i in intervals:\n        if len(res) == 0:\n            res.append(i)\n        elif i[0] <= res[-1][1]:\n            if i[1] > res[-1][1]:\n                res[-1][1] = i[1]\n        else:\n            res.append(i)\n    return res\n",
        "brute": "def merge(intervals):\n    items = [list(x) for x in intervals]\n    changed = True\n    while changed:\n        changed = False\n        for i in range(len(items)):\n            for j in range(i + 1, len(items)):\n                a, b = items[i], items[j]\n                if a[0] <= b[1] and b[0] <= a[1]:\n                    items[i] = [min(a[0], b[0]), max(a[1], b[1])]\n                    items.pop(j)\n                    changed = True\n                    break\n            if changed:\n                break\n    return items\n",
        "buggy": "def merge(intervals):\n    merged = []\n    for start, end in sorted(intervals):\n        if merged and start < merged[-1][1]:\n            merged[-1][1] = max(merged[-1][1], end)\n        else:\n            merged.append([start, end])\n    return merged\n",
    },
}


def fenced(code: str) -> str:
    return f"```python\n{code.rstrip()}\n```"


# ------------------------------------------------------------------ archetypes
# each returns (turns, code_variant, solve_fraction or None, pasted_fraction)
# turns: list of ("you" | "ai", text); the clock advances between turns

def handoff(m):
    return [("you", m["paste"]),
            ("ai", "Here's an efficient solution:\n\n" + fenced(m["clean"])),
            ("you", "write the code with comments"),
            ("ai", "Same solution with comments:\n\n" + fenced(m["clean"]))], "clean", 0.25, 0.95


def strong(m):
    return [("you", f"{m['constraints']} {m['idea']} Can you check the idea before I code it?"),
            ("ai", "That approach works and meets the target complexity. Watch the order of your updates."),
            ("you", m["tricky"]),
            ("ai", "Good catch to ask. Yes, that case matters; handle it explicitly before updating your state."),
            ("you", m["edge_q"]),
            ("ai", "Those are the right ones to test; your plan covers them if the update order is right.")], "clean", 0.45, 0.0


def late_verify(m):
    return [("you", f"{m['own_words']} What approaches are there?"),
            ("ai", m["approaches"]),
            ("you", "I'll go with the faster one. Any pitfalls in how I update state?"),
            ("ai", "Update the result after adjusting your pointers or map, not before."),
            ("you", "What edge cases should I check now that my code passes the examples?"),
            ("ai", "Try the smallest inputs, duplicates, and the boundaries described in the constraints.")], "messy", 0.7, 0.1


def flailing(m):
    return [("you", m["paste"]),
            ("ai", m["approaches"]),
            ("you", "just give me the code"),
            ("ai", "Here's a straightforward version:\n\n" + fenced(m["brute"])),
            ("you", "it doesn't work"),
            ("ai", "Can you share the failing input and what you got?"),
            ("you", "doesn't work, fix it"),
            ("ai", "Without the error it's hard to tell. Here's the code again; check your function name.\n\n" + fenced(m["brute"])),
            ("you", "try again"),
            ("ai", "The code above is correct for the examples; it may be slow on large inputs.")], "brute", 0.95, 0.85


def blind_trust(m):
    return [("you", f"{m['own_words']} {m['idea']}"),
            ("ai", m["wrong_claim"]),
            ("you", "ok great, so that's all I need?"),
            ("ai", "Yes, that should cover it."),
            ("you", "thanks, writing it now")], "buggy", 0.4, 0.0


def catches_bug(m):
    return [("you", f"{m['constraints']} What's the cleanest approach?"),
            ("ai", m["approaches"] + " " + m["wrong_claim"]),
            ("you", m["counter"]),
            ("ai", "You're right, that was wrong. Thanks for the counterexample; use the corrected condition."),
            ("you", m["edge_q"]),
            ("ai", "Those cover it. Your counterexample is a good test to keep.")], "clean", 0.5, 0.0


ARCHETYPES = {"handoff": handoff, "strong": strong, "late_verify": late_verify,
              "flailing": flailing, "blind_trust": blind_trust, "catches_bug": catches_bug}


def interviewer(m):
    return [("you", f"{m['own_words']} {m['constraints']}"),
            ("ai", "Good. What's your first approach, and its complexity?"),
            ("you", m["idea"]),
            ("ai", "Before you code: what input would break a naive version of that?"),
            ("you", m["tricky"]),
            ("ai", "Think it through and tell me your answer.")]


# ------------------------------------------------------------------ build

def events_from(turns: list[tuple[str, str]], solve_s: int) -> list[dict]:
    events, step = [], max(30, solve_s // (len(turns) + 2))
    counts = {"prompt": 0, "ai_reply": 0}
    for i, (who, text) in enumerate(turns):
        kind = "prompt" if who == "you" else "ai_reply"
        counts[kind] += 1
        events.append({"id": f"{'p' if kind == 'prompt' else 'a'}{counts[kind]}", "type": kind,
                       "ts": float(60 + i * step + (8 if kind == "ai_reply" else 0)), "text": text})
    return events


async def build(sid: str, slug: str, mode: str, turns, variant: str, solve_frac, pasted_frac) -> dict:
    p = problems.get(slug)
    m = P[slug]
    code = m[variant]
    res = await runner.run_tests(code, p, p["tests"])
    rows = res["results"]
    visible_ok = all(r["passed"] for r in rows if not r["hidden"])
    solve_s = int(LIMIT_S * solve_frac) if solve_frac and visible_ok else None
    events = events_from(turns, solve_s or LIMIT_S // 2)
    t_end = float(solve_s or LIMIT_S * 0.9)
    vis = [r for r in rows if not r["hidden"]]
    hid = [r for r in rows if r["hidden"]]
    events.append({"id": "r1", "type": "run", "ts": t_end - 40,
                   "text": f"{sum(r['passed'] for r in vis)} of {len(vis)} visible tests passed"})
    events.append({"id": "s1", "type": "submit", "ts": t_end,
                   "text": f"{sum(r['passed'] for r in hid)} of {len(hid)} hidden tests passed"})
    return {
        "id": sid, "mode": mode, "language": "python",
        "problem": {k: p[k] for k in ("title", "statement", "constraints", "optimal_time", "optimal_space")},
        "time_limit_s": LIMIT_S, "solve_time_s": solve_s, "final_code": code,
        "ai_pasted_chars": int(len(code) * pasted_frac),
        "events": sorted(events, key=lambda e: e["ts"]),
        "tests": [{k: r[k] for k in ("name", "category", "hidden", "passed")} for r in rows],
        "source": "seed",
    }


def opaque_id(name: str) -> str:
    """Labels must be blind, and a name like seed-two-sum-blind_trust gives the answer away."""
    return "g-" + hashlib.sha1(name.encode()).hexdigest()[:8]


async def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    jobs = []
    for slug in P:
        for name, fn in ARCHETYPES.items():
            turns, variant, solve, pasted = fn(P[slug])
            jobs.append((f"seed-{slug}-{name}", slug, "ai_assisted", turns, variant, solve, pasted))
    solo = [("two-sum", "brute", 0.3), ("longest-substring", "messy", 0.55), ("merge-intervals", "clean", 0.35)]
    for slug, variant, solve in solo:
        jobs.append((f"seed-{slug}-solo-{variant}", slug, "solo", [], variant, solve, 0.0))
    for slug, variant in [("valid-parentheses", "clean"), ("two-sum", "messy"), ("merge-intervals", "buggy")]:
        jobs.append((f"seed-{slug}-interviewer-{variant}", slug, "interviewer", interviewer(P[slug]), variant, 0.5, 0.0))

    manifest = {}
    for name, slug, mode, turns, variant, solve, pasted in jobs:
        sid = opaque_id(name)
        session = await build(sid, slug, mode, turns, variant, solve, pasted)
        (OUT / f"{sid}.json").write_text(json.dumps(session, indent=1))
        manifest[sid] = {"seed": name, "problem": slug, "mode": mode, "code": variant}
        hid = [t for t in session["tests"] if t["hidden"]]
        print(f"{sid}  {name:<44} hidden {sum(t['passed'] for t in hid)}/{len(hid)}")
    # what each seed was built to be: for analysis after labeling, never shown while labeling
    (OUT.parent / "seed_manifest.json").write_text(json.dumps(manifest, indent=1))
    print(f"\n{len(jobs)} seed sessions written to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    asyncio.run(main())
