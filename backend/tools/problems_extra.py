"""The second batch of problems. build_problems.py imports EXTRA from here.

To add a problem: write a reference solution, then a dict like the ones below.
Expected outputs are computed by calling the reference solution, never typed by hand.
`compare` decides how an answer is checked:
  exact      answer must equal the expected value
  sorted     a list whose order doesn't matter
  groups     a list of lists where neither the outer nor inner order matters
  min_window any valid minimum window (problem-specific checker in app/runner.py)
"""
from __future__ import annotations

import json
import random
from collections import Counter, defaultdict, deque
import heapq

rng = random.Random(11)


def case(name, category, hidden, fn, *args):
    copy = json.loads(json.dumps(list(args)))  # reference must not see mutations of the stored args
    return {"name": name, "category": category, "hidden": hidden, "args": list(args), "expected": fn(*copy)}


# ------------------------------------------------------------------ reference solutions

def climb_stairs(n):
    a, b = 1, 1
    for _ in range(n):
        a, b = b, a + b
    return a


def max_profit(prices):
    best, low = 0, float("inf")
    for p in prices:
        low = min(low, p)
        best = max(best, p - low)
    return best


def is_anagram(s, t):
    return Counter(s) == Counter(t)


def contains_duplicate(nums):
    return len(set(nums)) != len(nums)


def search(nums, target):
    lo, hi = 0, len(nums) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if nums[mid] == target:
            return mid
        if nums[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1


def max_sub_array(nums):
    best = cur = nums[0]
    for x in nums[1:]:
        cur = max(x, cur + x)
        best = max(best, cur)
    return best


def group_anagrams(strs):
    groups = defaultdict(list)
    for s in strs:
        groups["".join(sorted(s))].append(s)
    return list(groups.values())


def top_k_frequent(nums, k):
    return [x for x, _ in Counter(nums).most_common(k)]


def product_except_self(nums):
    n = len(nums)
    out = [1] * n
    left = 1
    for i in range(n):
        out[i] = left
        left *= nums[i]
    right = 1
    for i in range(n - 1, -1, -1):
        out[i] *= right
        right *= nums[i]
    return out


def three_sum(nums):
    nums = sorted(nums)
    out = []
    for i, a in enumerate(nums):
        if i and a == nums[i - 1]:
            continue
        lo, hi = i + 1, len(nums) - 1
        while lo < hi:
            s = a + nums[lo] + nums[hi]
            if s < 0:
                lo += 1
            elif s > 0:
                hi -= 1
            else:
                out.append([a, nums[lo], nums[hi]])
                lo += 1
                while lo < hi and nums[lo] == nums[lo - 1]:
                    lo += 1
    return out


def max_area(height):
    lo, hi, best = 0, len(height) - 1, 0
    while lo < hi:
        best = max(best, (hi - lo) * min(height[lo], height[hi]))
        if height[lo] < height[hi]:
            lo += 1
        else:
            hi -= 1
    return best


def search_rotated(nums, target):
    lo, hi = 0, len(nums) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if nums[mid] == target:
            return mid
        if nums[lo] <= nums[mid]:
            if nums[lo] <= target < nums[mid]:
                hi = mid - 1
            else:
                lo = mid + 1
        else:
            if nums[mid] < target <= nums[hi]:
                lo = mid + 1
            else:
                hi = mid - 1
    return -1


def num_islands(grid):
    rows, cols = len(grid), len(grid[0])
    seen = set()
    count = 0
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == "1" and (r, c) not in seen:
                count += 1
                q = deque([(r, c)])
                seen.add((r, c))
                while q:
                    y, x = q.popleft()
                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < rows and 0 <= nx < cols and grid[ny][nx] == "1" and (ny, nx) not in seen:
                            seen.add((ny, nx))
                            q.append((ny, nx))
    return count


def coin_change(coins, amount):
    inf = amount + 1
    dp = [0] + [inf] * amount
    for a in range(1, amount + 1):
        for c in coins:
            if c <= a and dp[a - c] + 1 < dp[a]:
                dp[a] = dp[a - c] + 1
    return dp[amount] if dp[amount] <= amount else -1


def daily_temperatures(temperatures):
    out = [0] * len(temperatures)
    stack = []
    for i, t in enumerate(temperatures):
        while stack and temperatures[stack[-1]] < t:
            j = stack.pop()
            out[j] = i - j
        stack.append(i)
    return out


def can_finish(num_courses, prerequisites):
    graph = defaultdict(list)
    indeg = [0] * num_courses
    for a, b in prerequisites:
        graph[b].append(a)
        indeg[a] += 1
    q = deque(i for i in range(num_courses) if indeg[i] == 0)
    done = 0
    while q:
        x = q.popleft()
        done += 1
        for y in graph[x]:
            indeg[y] -= 1
            if indeg[y] == 0:
                q.append(y)
    return done == num_courses


def min_window(s, t):
    need = Counter(t)
    missing = len(t)
    left = start = 0
    end = None
    for right, ch in enumerate(s, 1):
        if need[ch] > 0:
            missing -= 1
        need[ch] -= 1
        if missing == 0:
            while need[s[left]] < 0:
                need[s[left]] += 1
                left += 1
            if end is None or right - left < end - start:
                start, end = left, right
            need[s[left]] += 1
            missing += 1
            left += 1
    return "" if end is None else s[start:end]


def trap(height):
    lo, hi = 0, len(height) - 1
    lmax = rmax = water = 0
    while lo < hi:
        if height[lo] < height[hi]:
            lmax = max(lmax, height[lo])
            water += lmax - height[lo]
            lo += 1
        else:
            rmax = max(rmax, height[hi])
            water += rmax - height[hi]
            hi -= 1
    return water


# ------------------------------------------------------------------ large inputs

def rand_ints(n, lo, hi):
    return [rng.randint(lo, hi) for _ in range(n)]


def rotated(n):
    base = sorted(rng.sample(range(-10**4 * 5, 10**4 * 5), n))
    k = rng.randrange(n)
    return base[k:] + base[:k]


def top_k_input():
    # distinct frequencies for the leading values so the top k is unambiguous
    nums = []
    for v, freq in zip(range(1, 11), range(3000, 0, -290)):
        nums += [v] * freq
    nums += rng.sample(range(100, 10**6), 60_000)
    rng.shuffle(nums)
    return nums


def islands_grid(rows, cols, p):
    return [["1" if rng.random() < p else "0" for _ in range(cols)] for _ in range(rows)]


def dag(n, edges):
    order = list(range(n))
    rng.shuffle(order)
    pos = {c: i for i, c in enumerate(order)}
    pairs = set()
    while len(pairs) < edges:
        a, b = rng.sample(range(n), 2)
        if pos[a] > pos[b]:  # course a needs b, and b comes earlier
            pairs.add((a, b))
    return [list(p) for p in pairs]


def random_word():
    return "".join(rng.choice("abcde") for _ in range(rng.randint(1, 6)))


big_dag = dag(2000, 6000)
cyclic = dag(2000, 6000)
cyclic.append([cyclic[0][1], cyclic[0][0]])  # reversing one edge closes a cycle
min_window_s = "".join(rng.choice("ABCDEFGHIJ") for _ in range(100_000))
three_sum_big = rand_ints(1500, -10**5, 10**5)
rotated_big = rotated(5000)
# the product of everything must fit in 32 bits, so: +-1 everywhere and a handful of 2s and 3s
product_big = [rng.choice([1, 1, 1, -1]) for _ in range(100_000)]
for i in rng.sample(range(100_000), 12):
    product_big[i] = rng.choice([2, 3])
rotated_target = rng.randrange(len(rotated_big))


EXTRA = [
    {
        "slug": "climbing-stairs", "title": "Climbing Stairs", "difficulty": "Easy",
        "topics": ["Dynamic programming"],
        "statement": "You are climbing a staircase with n steps. Each time you can climb 1 or 2 steps. In how many distinct ways can you reach the top?",
        "constraints": "1 <= n <= 45",
        "examples": [{"input": "n = 2", "output": "2", "explanation": "1+1 or 2"},
                     {"input": "n = 3", "output": "3", "explanation": "1+1+1, 1+2 or 2+1"}],
        "optimal_time": "O(n)", "optimal_space": "O(1)",
        "function_name": "climb_stairs", "starter_code": "def climb_stairs(n: int) -> int:\n    pass\n", "compare": "exact",
        "tests": [case("n = 2", "typical", False, climb_stairs, 2), case("n = 3", "typical", False, climb_stairs, 3),
                  case("n = 1", "edge", True, climb_stairs, 1), case("n = 5", "typical", True, climb_stairs, 5),
                  case("n = 10", "typical", True, climb_stairs, 10),
                  case("n = 45 (naive recursion times out)", "large", True, climb_stairs, 45)],
    },
    {
        "slug": "best-time-to-buy-and-sell-stock", "title": "Best Time to Buy and Sell Stock", "difficulty": "Easy",
        "topics": ["Array", "Greedy"],
        "statement": "prices[i] is the price of a stock on day i. Choose one day to buy and a later day to sell. Return the maximum profit, or 0 if no profit is possible.",
        "constraints": "1 <= prices.length <= 10^5; 0 <= prices[i] <= 10^4",
        "examples": [{"input": "prices = [7,1,5,3,6,4]", "output": "5", "explanation": "Buy at 1, sell at 6."},
                     {"input": "prices = [7,6,4,3,1]", "output": "0"}],
        "optimal_time": "O(n)", "optimal_space": "O(1)",
        "function_name": "max_profit", "starter_code": "def max_profit(prices: list[int]) -> int:\n    pass\n", "compare": "exact",
        "tests": [case("[7,1,5,3,6,4]", "typical", False, max_profit, [7, 1, 5, 3, 6, 4]),
                  case("[7,6,4,3,1]", "typical", False, max_profit, [7, 6, 4, 3, 1]),
                  case("single day", "edge", True, max_profit, [5]),
                  case("flat prices", "edge", True, max_profit, [3, 3, 3]),
                  case("minimum after maximum", "edge", True, max_profit, [2, 9, 1, 4]),
                  case("rising", "typical", True, max_profit, [1, 2, 3, 4, 5]),
                  case("100k random", "large", True, max_profit, rand_ints(100_000, 0, 10**4))],
    },
    {
        "slug": "valid-anagram", "title": "Valid Anagram", "difficulty": "Easy",
        "topics": ["Hash map", "String"],
        "statement": "Given two strings s and t, return true if t is an anagram of s: the same letters with the same counts, in any order.",
        "constraints": "1 <= s.length, t.length <= 5 * 10^4; lowercase English letters",
        "examples": [{"input": 's = "anagram", t = "nagaram"', "output": "true"},
                     {"input": 's = "rat", t = "car"', "output": "false"}],
        "optimal_time": "O(n)", "optimal_space": "O(1) (fixed alphabet)",
        "function_name": "is_anagram", "starter_code": "def is_anagram(s: str, t: str) -> bool:\n    pass\n", "compare": "exact",
        "tests": [case('"anagram", "nagaram"', "typical", False, is_anagram, "anagram", "nagaram"),
                  case('"rat", "car"', "typical", False, is_anagram, "rat", "car"),
                  case("different lengths", "edge", True, is_anagram, "ab", "abb"),
                  case("same letters, different counts", "edge", True, is_anagram, "aab", "abb"),
                  case("single char", "edge", True, is_anagram, "a", "a"),
                  case("50k shuffled", "large", True, is_anagram,
                       *(lambda s: (s, "".join(rng.sample(s, len(s)))))("".join(rng.choice("abcxyz") for _ in range(50_000))))],
    },
    {
        "slug": "contains-duplicate", "title": "Contains Duplicate", "difficulty": "Easy",
        "topics": ["Hash map", "Array"],
        "statement": "Return true if any value appears at least twice in nums, and false if every element is distinct.",
        "constraints": "1 <= nums.length <= 10^5; -10^9 <= nums[i] <= 10^9",
        "examples": [{"input": "nums = [1,2,3,1]", "output": "true"}, {"input": "nums = [1,2,3,4]", "output": "false"}],
        "optimal_time": "O(n)", "optimal_space": "O(n)",
        "function_name": "contains_duplicate", "starter_code": "def contains_duplicate(nums: list[int]) -> bool:\n    pass\n",
        "compare": "exact",
        "tests": [case("[1,2,3,1]", "typical", False, contains_duplicate, [1, 2, 3, 1]),
                  case("[1,2,3,4]", "typical", False, contains_duplicate, [1, 2, 3, 4]),
                  case("single element", "edge", True, contains_duplicate, [7]),
                  case("negatives", "edge", True, contains_duplicate, [-1, 0, -1]),
                  case("100k distinct", "large", True, contains_duplicate, rng.sample(range(-10**9, 10**9), 100_000)),
                  case("100k, duplicate at the end", "large", True, contains_duplicate,
                       (lambda a: a + [a[0]])(rng.sample(range(-10**9, 10**9), 99_999)))],
    },
    {
        "slug": "binary-search", "title": "Binary Search", "difficulty": "Easy",
        "topics": ["Binary search", "Array"],
        "statement": "Given a sorted array of distinct integers nums and a target, return the index of target, or -1 if it is not present. Aim for O(log n).",
        "constraints": "1 <= nums.length <= 10^4; values are distinct and sorted ascending",
        "examples": [{"input": "nums = [-1,0,3,5,9,12], target = 9", "output": "4"},
                     {"input": "nums = [-1,0,3,5,9,12], target = 2", "output": "-1"}],
        "optimal_time": "O(log n)", "optimal_space": "O(1)",
        "function_name": "search", "starter_code": "def search(nums: list[int], target: int) -> int:\n    pass\n", "compare": "exact",
        "tests": [case("found", "typical", False, search, [-1, 0, 3, 5, 9, 12], 9),
                  case("missing", "typical", False, search, [-1, 0, 3, 5, 9, 12], 2),
                  case("single element, found", "edge", True, search, [5], 5),
                  case("single element, missing", "edge", True, search, [5], -5),
                  case("first index", "edge", True, search, [1, 3, 5, 7], 1),
                  case("last index", "edge", True, search, [1, 3, 5, 7], 7),
                  case("below range", "edge", True, search, [1, 3, 5, 7], 0),
                  case("10k", "large", True, search, list(range(0, 20_000, 2)), 13_336)],
    },
    {
        "slug": "maximum-subarray", "title": "Maximum Subarray", "difficulty": "Medium",
        "topics": ["Dynamic programming", "Array"],
        "statement": "Find the contiguous non-empty subarray with the largest sum and return that sum.",
        "constraints": "1 <= nums.length <= 10^5; -10^4 <= nums[i] <= 10^4",
        "examples": [{"input": "nums = [-2,1,-3,4,-1,2,1,-5,4]", "output": "6", "explanation": "[4,-1,2,1]"},
                     {"input": "nums = [5,4,-1,7,8]", "output": "23"}],
        "optimal_time": "O(n)", "optimal_space": "O(1)",
        "function_name": "max_sub_array", "starter_code": "def max_sub_array(nums: list[int]) -> int:\n    pass\n", "compare": "exact",
        "tests": [case("example 1", "typical", False, max_sub_array, [-2, 1, -3, 4, -1, 2, 1, -5, 4]),
                  case("[5,4,-1,7,8]", "typical", False, max_sub_array, [5, 4, -1, 7, 8]),
                  case("single negative", "edge", True, max_sub_array, [-3]),
                  case("all negative", "edge", True, max_sub_array, [-8, -3, -6, -2, -5]),
                  case("zeros", "edge", True, max_sub_array, [0, 0, 0]),
                  case("100k random", "large", True, max_sub_array, rand_ints(100_000, -10**4, 10**4))],
    },
    {
        "slug": "group-anagrams", "title": "Group Anagrams", "difficulty": "Medium",
        "topics": ["Hash map", "String", "Sorting"],
        "statement": "Group the strings that are anagrams of each other. Return the groups in any order; the strings inside a group can be in any order too.",
        "constraints": "1 <= strs.length <= 10^4; 0 <= strs[i].length <= 100; lowercase English letters",
        "examples": [{"input": 'strs = ["eat","tea","tan","ate","nat","bat"]',
                      "output": '[["bat"],["nat","tan"],["ate","eat","tea"]]'}],
        "optimal_time": "O(n * k log k) for word length k", "optimal_space": "O(n * k)",
        "function_name": "group_anagrams", "starter_code": "def group_anagrams(strs: list[str]) -> list[list[str]]:\n    pass\n",
        "compare": "groups",
        "tests": [case("example", "typical", False, group_anagrams, ["eat", "tea", "tan", "ate", "nat", "bat"]),
                  case("empty string", "edge", False, group_anagrams, [""]),
                  case("single", "edge", True, group_anagrams, ["a"]),
                  case("duplicates", "edge", True, group_anagrams, ["ab", "ba", "ab"]),
                  case("no anagrams", "typical", True, group_anagrams, ["abc", "def", "ghi"]),
                  case("10k words", "large", True, group_anagrams, [random_word() for _ in range(10_000)])],
    },
    {
        "slug": "top-k-frequent-elements", "title": "Top K Frequent Elements", "difficulty": "Medium",
        "topics": ["Hash map", "Heap", "Bucket sort"],
        "statement": "Return the k most frequent elements of nums, in any order. The answer is guaranteed to be unique.",
        "constraints": "1 <= nums.length <= 10^5; 1 <= k <= number of distinct values",
        "examples": [{"input": "nums = [1,1,1,2,2,3], k = 2", "output": "[1,2]"}, {"input": "nums = [1], k = 1", "output": "[1]"}],
        "optimal_time": "O(n)", "optimal_space": "O(n)",
        "function_name": "top_k_frequent", "starter_code": "def top_k_frequent(nums: list[int], k: int) -> list[int]:\n    pass\n",
        "compare": "sorted",
        "tests": [case("example", "typical", False, top_k_frequent, [1, 1, 1, 2, 2, 3], 2),
                  case("single", "edge", False, top_k_frequent, [1], 1),
                  case("negatives", "edge", True, top_k_frequent, [-1, -1, -2, -2, -2, 3], 2),
                  case("k equals distinct count", "edge", True, top_k_frequent, [4, 4, 5, 5, 5, 6], 3),
                  case("~90k values", "large", True, top_k_frequent, top_k_input(), 10)],
    },
    {
        "slug": "product-of-array-except-self", "title": "Product of Array Except Self", "difficulty": "Medium",
        "topics": ["Array", "Prefix sums"],
        "statement": "Return an array answer where answer[i] is the product of every element of nums except nums[i]. Do it in O(n) without using division.",
        "constraints": "2 <= nums.length <= 10^5; -30 <= nums[i] <= 30",
        "examples": [{"input": "nums = [1,2,3,4]", "output": "[24,12,8,6]"}, {"input": "nums = [-1,1,0,-3,3]", "output": "[0,0,9,0,0]"}],
        "optimal_time": "O(n)", "optimal_space": "O(1) extra (output excluded)",
        "function_name": "product_except_self",
        "starter_code": "def product_except_self(nums: list[int]) -> list[int]:\n    pass\n", "compare": "exact",
        "tests": [case("[1,2,3,4]", "typical", False, product_except_self, [1, 2, 3, 4]),
                  case("with a zero", "edge", False, product_except_self, [-1, 1, 0, -3, 3]),
                  case("two zeros", "edge", True, product_except_self, [0, 4, 0]),
                  case("two elements", "edge", True, product_except_self, [3, -2]),
                  case("negatives", "typical", True, product_except_self, [-1, -2, -3, -4]),
                  case("100k mostly ones", "large", True, product_except_self, product_big)],
    },
    {
        "slug": "3sum", "title": "3Sum", "difficulty": "Medium",
        "topics": ["Two pointers", "Sorting"],
        "statement": "Return every unique triplet [a, b, c] of values from nums at distinct indices with a + b + c == 0. The output must not contain duplicate triplets; order doesn't matter.",
        "constraints": "3 <= nums.length <= 3000; -10^5 <= nums[i] <= 10^5",
        "examples": [{"input": "nums = [-1,0,1,2,-1,-4]", "output": "[[-1,-1,2],[-1,0,1]]"},
                     {"input": "nums = [0,1,1]", "output": "[]"}],
        "optimal_time": "O(n^2)", "optimal_space": "O(1) extra (output excluded)",
        "function_name": "three_sum", "starter_code": "def three_sum(nums: list[int]) -> list[list[int]]:\n    pass\n",
        "compare": "groups",
        "tests": [case("example", "typical", False, three_sum, [-1, 0, 1, 2, -1, -4]),
                  case("no triplet", "typical", False, three_sum, [0, 1, 1]),
                  case("all zeros", "edge", True, three_sum, [0, 0, 0, 0]),
                  case("many duplicates", "edge", True, three_sum, [-2, 0, 0, 2, 2, -2, 1, -1]),
                  case("three elements", "edge", True, three_sum, [1, -1, 0]),
                  case("1500 random (cubic times out)", "large", True, three_sum, three_sum_big)],
    },
    {
        "slug": "container-with-most-water", "title": "Container With Most Water", "difficulty": "Medium",
        "topics": ["Two pointers", "Greedy"],
        "statement": "height[i] is the height of a vertical line at x = i. Pick two lines that, with the x-axis, hold the most water. Return that maximum amount of water.",
        "constraints": "2 <= height.length <= 10^5; 0 <= height[i] <= 10^4",
        "examples": [{"input": "height = [1,8,6,2,5,4,8,3,7]", "output": "49"}, {"input": "height = [1,1]", "output": "1"}],
        "optimal_time": "O(n)", "optimal_space": "O(1)",
        "function_name": "max_area", "starter_code": "def max_area(height: list[int]) -> int:\n    pass\n", "compare": "exact",
        "tests": [case("example", "typical", False, max_area, [1, 8, 6, 2, 5, 4, 8, 3, 7]),
                  case("[1,1]", "edge", False, max_area, [1, 1]),
                  case("zeros", "edge", True, max_area, [0, 0, 0]),
                  case("increasing", "typical", True, max_area, [1, 2, 3, 4, 5, 6]),
                  case("tall ends", "typical", True, max_area, [9, 1, 1, 1, 9]),
                  case("100k random (quadratic times out)", "large", True, max_area, rand_ints(100_000, 0, 10**4))],
    },
    {
        "slug": "search-in-rotated-sorted-array", "title": "Search in Rotated Sorted Array", "difficulty": "Medium",
        "topics": ["Binary search", "Array"],
        "statement": "A sorted array of distinct integers was rotated at an unknown pivot (for example [0,1,2,4,5,6,7] became [4,5,6,7,0,1,2]). Return the index of target, or -1. Aim for O(log n).",
        "constraints": "1 <= nums.length <= 5000; values are distinct",
        "examples": [{"input": "nums = [4,5,6,7,0,1,2], target = 0", "output": "4"},
                     {"input": "nums = [4,5,6,7,0,1,2], target = 3", "output": "-1"}],
        "optimal_time": "O(log n)", "optimal_space": "O(1)",
        "function_name": "search_rotated",
        "starter_code": "def search_rotated(nums: list[int], target: int) -> int:\n    pass\n", "compare": "exact",
        "tests": [case("found", "typical", False, search_rotated, [4, 5, 6, 7, 0, 1, 2], 0),
                  case("missing", "typical", False, search_rotated, [4, 5, 6, 7, 0, 1, 2], 3),
                  case("single element", "edge", True, search_rotated, [1], 1),
                  case("not rotated", "edge", True, search_rotated, [1, 2, 3, 4, 5], 4),
                  case("two elements, rotated", "edge", True, search_rotated, [3, 1], 1),
                  case("target at pivot", "edge", True, search_rotated, [6, 7, 1, 2, 3, 4, 5], 1),
                  case("5000 rotated", "large", True, search_rotated, rotated_big, rotated_big[rotated_target])],
    },
    {
        "slug": "number-of-islands", "title": "Number of Islands", "difficulty": "Medium",
        "topics": ["Graph", "BFS", "DFS"],
        "statement": 'grid is a map of "1" (land) and "0" (water). An island is land connected horizontally or vertically. Return the number of islands.',
        "constraints": "1 <= rows, cols <= 300",
        "examples": [{"input": 'grid = [["1","1","0"],["1","0","0"],["0","0","1"]]', "output": "2"}],
        "optimal_time": "O(rows * cols)", "optimal_space": "O(rows * cols)",
        "function_name": "num_islands", "starter_code": "def num_islands(grid: list[list[str]]) -> int:\n    pass\n",
        "compare": "exact",
        "tests": [case("example", "typical", False, num_islands, [["1", "1", "0"], ["1", "0", "0"], ["0", "0", "1"]]),
                  case("one big island", "typical", False, num_islands, [["1", "1"], ["1", "1"]]),
                  case("all water", "edge", True, num_islands, [["0", "0"], ["0", "0"]]),
                  case("single cell land", "edge", True, num_islands, [["1"]]),
                  case("diagonals don't connect", "edge", True, num_islands, [["1", "0"], ["0", "1"]]),
                  case("snake", "typical", True, num_islands,
                       [list("11111"), list("00001"), list("11111"), list("10000"), list("11111")]),
                  case("300x300 random", "large", True, num_islands, islands_grid(300, 300, 0.45))],
    },
    {
        "slug": "coin-change", "title": "Coin Change", "difficulty": "Medium",
        "topics": ["Dynamic programming"],
        "statement": "Given coin denominations (unlimited supply of each) and an amount, return the fewest coins that add up to amount, or -1 if it can't be made.",
        "constraints": "1 <= coins.length <= 12; 1 <= coins[i] <= 2^31 - 1; 0 <= amount <= 10^4",
        "examples": [{"input": "coins = [1,2,5], amount = 11", "output": "3", "explanation": "5 + 5 + 1"},
                     {"input": "coins = [2], amount = 3", "output": "-1"}],
        "optimal_time": "O(amount * coins)", "optimal_space": "O(amount)",
        "function_name": "coin_change", "starter_code": "def coin_change(coins: list[int], amount: int) -> int:\n    pass\n",
        "compare": "exact",
        "tests": [case("[1,2,5], 11", "typical", False, coin_change, [1, 2, 5], 11),
                  case("[2], 3", "edge", False, coin_change, [2], 3),
                  case("amount 0", "edge", True, coin_change, [1], 0),
                  case("greedy fails", "edge", True, coin_change, [1, 3, 4], 6),
                  case("huge coin", "edge", True, coin_change, [2**31 - 1], 7),
                  case("amount 10^4 (exponential recursion times out)", "large", True, coin_change, [3, 7, 11, 19, 23], 10_000)],
    },
    {
        "slug": "daily-temperatures", "title": "Daily Temperatures", "difficulty": "Medium",
        "topics": ["Stack", "Monotonic stack"],
        "statement": "For each day, return how many days you have to wait for a warmer temperature. Use 0 if no warmer day follows.",
        "constraints": "1 <= temperatures.length <= 10^5; 30 <= temperatures[i] <= 100",
        "examples": [{"input": "temperatures = [73,74,75,71,69,72,76,73]", "output": "[1,1,4,2,1,1,0,0]"}],
        "optimal_time": "O(n)", "optimal_space": "O(n)",
        "function_name": "daily_temperatures",
        "starter_code": "def daily_temperatures(temperatures: list[int]) -> list[int]:\n    pass\n", "compare": "exact",
        "tests": [case("example", "typical", False, daily_temperatures, [73, 74, 75, 71, 69, 72, 76, 73]),
                  case("increasing", "typical", False, daily_temperatures, [30, 40, 50, 60]),
                  case("single day", "edge", True, daily_temperatures, [50]),
                  case("decreasing", "edge", True, daily_temperatures, [90, 80, 70]),
                  case("equal temperatures", "edge", True, daily_temperatures, [70, 70, 71]),
                  case("100k descending (quadratic times out)", "large", True, daily_temperatures,
                       [100 - (i * 70 // 100_000) for i in range(100_000)])],
    },
    {
        "slug": "course-schedule", "title": "Course Schedule", "difficulty": "Medium",
        "topics": ["Graph", "Topological sort"],
        "statement": "There are num_courses courses labelled 0 to num_courses - 1. prerequisites[i] = [a, b] means you must take b before a. Return true if you can finish every course.",
        "constraints": "1 <= num_courses <= 2000; 0 <= prerequisites.length <= 6000; pairs are unique",
        "examples": [{"input": "num_courses = 2, prerequisites = [[1,0]]", "output": "true"},
                     {"input": "num_courses = 2, prerequisites = [[1,0],[0,1]]", "output": "false"}],
        "optimal_time": "O(V + E)", "optimal_space": "O(V + E)",
        "function_name": "can_finish",
        "starter_code": "def can_finish(num_courses: int, prerequisites: list[list[int]]) -> bool:\n    pass\n", "compare": "exact",
        "tests": [case("possible", "typical", False, can_finish, 2, [[1, 0]]),
                  case("cycle", "typical", False, can_finish, 2, [[1, 0], [0, 1]]),
                  case("no prerequisites", "edge", True, can_finish, 3, []),
                  case("self loop", "edge", True, can_finish, 1, [[0, 0]]),
                  case("long chain", "typical", True, can_finish, 5, [[1, 0], [2, 1], [3, 2], [4, 3]]),
                  case("2000 courses, acyclic", "large", True, can_finish, 2000, big_dag),
                  case("2000 courses, one cycle", "large", True, can_finish, 2000, cyclic)],
    },
    {
        "slug": "minimum-window-substring", "title": "Minimum Window Substring", "difficulty": "Hard",
        "topics": ["Sliding window", "Hash map", "String"],
        "statement": 'Return the shortest substring of s that contains every character of t, including duplicates. Return "" if there is none. Any shortest window is accepted.',
        "constraints": "1 <= s.length, t.length <= 10^5; uppercase and lowercase English letters",
        "examples": [{"input": 's = "ADOBECODEBANC", t = "ABC"', "output": '"BANC"'},
                     {"input": 's = "a", t = "aa"', "output": '""'}],
        "optimal_time": "O(len(s) + len(t))", "optimal_space": "O(alphabet)",
        "function_name": "min_window", "starter_code": "def min_window(s: str, t: str) -> str:\n    pass\n",
        "compare": "min_window",
        "tests": [case("example", "typical", False, min_window, "ADOBECODEBANC", "ABC"),
                  case("not enough letters", "edge", False, min_window, "a", "aa"),
                  case("whole string", "edge", True, min_window, "a", "a"),
                  case("case sensitive", "edge", True, min_window, "aA", "A"),
                  case("duplicates in t", "edge", True, min_window, "AAABBC", "AAB"),
                  case("100k (quadratic times out)", "large", True, min_window, min_window_s, "AABBCCDDEEFFGGHHIIJJ")],
    },
    {
        "slug": "trapping-rain-water", "title": "Trapping Rain Water", "difficulty": "Hard",
        "topics": ["Two pointers", "Stack"],
        "statement": "height[i] is the height of a bar of width 1. Return how much rain water is trapped between the bars after it rains.",
        "constraints": "1 <= height.length <= 2 * 10^4; 0 <= height[i] <= 10^5",
        "examples": [{"input": "height = [0,1,0,2,1,0,1,3,2,1,2,1]", "output": "6"},
                     {"input": "height = [4,2,0,3,2,5]", "output": "9"}],
        "optimal_time": "O(n)", "optimal_space": "O(1)",
        "function_name": "trap", "starter_code": "def trap(height: list[int]) -> int:\n    pass\n", "compare": "exact",
        "tests": [case("example 1", "typical", False, trap, [0, 1, 0, 2, 1, 0, 1, 3, 2, 1, 2, 1]),
                  case("example 2", "typical", False, trap, [4, 2, 0, 3, 2, 5]),
                  case("single bar", "edge", True, trap, [5]),
                  case("no basin", "edge", True, trap, [1, 2, 3, 4]),
                  case("valley", "edge", True, trap, [5, 0, 5]),
                  case("20k random", "large", True, trap, rand_ints(20_000, 0, 10**5))],
    },
]
