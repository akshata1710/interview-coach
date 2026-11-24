"""Generate problems/*.json. Expected outputs come from reference solutions, so they are never hand-typed.

    python tools/build_problems.py
"""
from __future__ import annotations

import json
import random
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "problems"
rng = random.Random(7)


# ------------------------------------------------------------------ reference solutions

def two_sum(nums, target):
    seen = {}
    for i, x in enumerate(nums):
        if target - x in seen:
            return [seen[target - x], i]
        seen[x] = i
    return []


def longest_substring(s):
    last, left, best = {}, 0, 0
    for right, ch in enumerate(s):
        if ch in last and last[ch] >= left:
            left = last[ch] + 1
        last[ch] = right
        best = max(best, right - left + 1)
    return best


def valid_parentheses(s):
    pairs, stack = {")": "(", "]": "[", "}": "{"}, []
    for ch in s:
        if ch in pairs:
            if not stack or stack.pop() != pairs[ch]:
                return False
        else:
            stack.append(ch)
    return not stack


def merge_intervals(intervals):
    out = []
    for start, end in sorted(intervals):
        if out and start <= out[-1][1]:
            out[-1][1] = max(out[-1][1], end)
        else:
            out.append([start, end])
    return out


# ------------------------------------------------------------------ helpers

def case(name, category, hidden, fn, *args):
    return {"name": name, "category": category, "hidden": hidden,
            "args": list(args), "expected": fn(*json.loads(json.dumps(list(args))))}


def two_sum_large(n):
    nums = rng.sample(range(-10**9, 10**9), n)
    i, j = rng.sample(range(n), 2)
    return nums, nums[i] + nums[j]


PROBLEMS = []

# ------------------------------------------------------------------ Two Sum
ts = two_sum
big_nums, big_target = two_sum_large(10_000)
PROBLEMS.append({
    "slug": "two-sum",
    "title": "Two Sum",
    "difficulty": "Easy",
    "topics": ["Hash map", "Array"],
    "statement": "Given an array of integers nums and an integer target, return the indices of the two numbers that add up to target. Each input has exactly one solution, and you may not use the same element twice. Return the indices in any order.",
    "constraints": "2 <= nums.length <= 10^4; -10^9 <= nums[i], target <= 10^9; exactly one valid answer exists.",
    "examples": [
        {"input": "nums = [2, 7, 11, 15], target = 9", "output": "[0, 1]", "explanation": "nums[0] + nums[1] == 9"},
        {"input": "nums = [3, 2, 4], target = 6", "output": "[1, 2]"},
    ],
    "optimal_time": "O(n)",
    "optimal_space": "O(n)",
    "function_name": "two_sum",
    "starter_code": "def two_sum(nums: list[int], target: int) -> list[int]:\n    pass\n",
    "compare": "two_sum",  # any valid pair of indices passes
    "tests": [
        case("[2,7,11,15], 9", "typical", False, ts, [2, 7, 11, 15], 9),
        case("[3,2,4], 6", "typical", False, ts, [3, 2, 4], 6),
        case("[3,3], 6", "edge", False, ts, [3, 3], 6),
        case("negatives", "typical", True, ts, [-3, 4, 3, 90], 0),
        case("duplicates", "edge", True, ts, [1, 5, 1, 6, 7], 13),
        case("zeros", "edge", True, ts, [0, 4, 3, 0], 0),
        case("two elements", "edge", True, ts, [-1, -2], -3),
        case("answer at the end", "typical", True, ts, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 19),
        case("large values", "edge", True, ts, [10**9, -10**9, 5, 10**9 - 5], 10**9),
        case("10k elements", "large", True, ts, big_nums, big_target),
    ],
})

# ------------------------------------------------------------------ Longest Substring
ls = longest_substring
alphabet = "abcdefghijklmnopqrstuvwxyz0123456789 !?"
PROBLEMS.append({
    "slug": "longest-substring",
    "title": "Longest Substring Without Repeating Characters",
    "difficulty": "Medium",
    "topics": ["Sliding window", "Hash map", "String"],
    "statement": "Given a string s, return the length of the longest substring that contains no repeated characters.",
    "constraints": "0 <= s.length <= 5 * 10^4; s may contain letters, digits, symbols and spaces.",
    "examples": [
        {"input": 's = "abcabcbb"', "output": "3", "explanation": 'The answer is "abc".'},
        {"input": 's = "bbbbb"', "output": "1"},
        {"input": 's = "pwwkew"', "output": "3", "explanation": '"wke"; "pwke" is a subsequence, not a substring.'},
    ],
    "optimal_time": "O(n)",
    "optimal_space": "O(min(n, k)) for alphabet size k",
    "function_name": "length_of_longest_substring",
    "starter_code": "def length_of_longest_substring(s: str) -> int:\n    pass\n",
    "compare": "exact",
    "tests": [
        case('"abcabcbb"', "typical", False, ls, "abcabcbb"),
        case('"bbbbb"', "typical", False, ls, "bbbbb"),
        case('"pwwkew"', "typical", False, ls, "pwwkew"),
        case("empty string", "edge", True, ls, ""),
        case("single char", "edge", True, ls, "a"),
        case('"abba" (repeat left of window)', "edge", True, ls, "abba"),
        case("only spaces", "edge", True, ls, "     "),
        case("symbols and spaces", "edge", True, ls, "a b!c a?"),
        case('"dvdf"', "typical", True, ls, "dvdf"),
        case('"tmmzuxt"', "typical", True, ls, "tmmzuxt"),
        case("all distinct", "typical", True, ls, "abcdefghijklmnopqrstuvwxyz"),
        case("50k random", "large", True, ls, "".join(rng.choice(alphabet) for _ in range(50_000))),
        case("50k one char", "large", True, ls, "x" * 50_000),
    ],
})

# ------------------------------------------------------------------ Valid Parentheses
vp = valid_parentheses
PROBLEMS.append({
    "slug": "valid-parentheses",
    "title": "Valid Parentheses",
    "difficulty": "Easy",
    "topics": ["Stack", "String"],
    "statement": "Given a string s containing only the characters ( ) [ ] { }, return true if every opening bracket is closed by the same type of bracket in the correct order, and every closing bracket has a matching opening bracket.",
    "constraints": "1 <= s.length <= 10^4; s contains only ()[]{}.",
    "examples": [
        {"input": 's = "()[]{}"', "output": "true"},
        {"input": 's = "(]"', "output": "false"},
        {"input": 's = "([])"', "output": "true"},
    ],
    "optimal_time": "O(n)",
    "optimal_space": "O(n)",
    "function_name": "is_valid",
    "starter_code": "def is_valid(s: str) -> bool:\n    pass\n",
    "compare": "exact",
    "tests": [
        case('"()[]{}"', "typical", False, vp, "()[]{}"),
        case('"(]"', "typical", False, vp, "(]"),
        case('"([])"', "typical", False, vp, "([])"),
        case("single open", "edge", True, vp, "("),
        case("single close", "edge", True, vp, ")"),
        case("close first", "edge", True, vp, "){}("),
        case("interleaved wrong", "typical", True, vp, "([)]"),
        case("deep nesting", "typical", True, vp, "{[()()]}"),
        case("unclosed at end", "edge", True, vp, "(()"),
        case("10k balanced", "large", True, vp, "([{" * 1666 + "}])" * 1666),
        case("10k off by one", "large", True, vp, "(" * 5000 + ")" * 4999),
    ],
})

# ------------------------------------------------------------------ Merge Intervals
mi = merge_intervals
big_iv = [[s, s + rng.randint(0, 50)] for s in (rng.randint(0, 10**6) for _ in range(10_000))]
PROBLEMS.append({
    "slug": "merge-intervals",
    "title": "Merge Intervals",
    "difficulty": "Medium",
    "topics": ["Sorting", "Array"],
    "statement": "Given an array of intervals where intervals[i] = [start, end], merge all overlapping intervals and return the non-overlapping intervals that cover all of the input. Intervals that touch (one ends where the next starts) overlap. Return them in any order.",
    "constraints": "1 <= intervals.length <= 10^4; 0 <= start <= end <= 10^6.",
    "examples": [
        {"input": "intervals = [[1,3],[2,6],[8,10],[15,18]]", "output": "[[1,6],[8,10],[15,18]]"},
        {"input": "intervals = [[1,4],[4,5]]", "output": "[[1,5]]", "explanation": "Touching intervals merge."},
    ],
    "optimal_time": "O(n log n)",
    "optimal_space": "O(n)",
    "function_name": "merge",
    "starter_code": "def merge(intervals: list[list[int]]) -> list[list[int]]:\n    pass\n",
    "compare": "sorted",
    "tests": [
        case("example 1", "typical", False, mi, [[1, 3], [2, 6], [8, 10], [15, 18]]),
        case("touching", "edge", False, mi, [[1, 4], [4, 5]]),
        case("single interval", "edge", True, mi, [[5, 7]]),
        case("unsorted input", "typical", True, mi, [[8, 10], [1, 3], [2, 6]]),
        case("one contains another", "edge", True, mi, [[1, 10], [2, 3], [4, 5]]),
        case("all merge", "typical", True, mi, [[1, 2], [2, 3], [3, 4], [4, 5]]),
        case("zero-length", "edge", True, mi, [[0, 0], [0, 0], [1, 1]]),
        case("no overlaps", "typical", True, mi, [[1, 2], [4, 5], [7, 8]]),
        case("10k random", "large", True, mi, big_iv),
    ],
})


def main() -> None:
    from problems_extra import EXTRA  # second batch, kept in its own file

    OUT.mkdir(exist_ok=True)
    for p in PROBLEMS + EXTRA:
        (OUT / f"{p['slug']}.json").write_text(json.dumps(p, indent=1))
        hidden = sum(t["hidden"] for t in p["tests"])
        print(f"{p['slug']}: {len(p['tests'])} tests ({hidden} hidden)")


if __name__ == "__main__":
    main()
