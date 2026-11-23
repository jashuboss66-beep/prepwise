"""Small original DSA demo set, organized around Striver A2Z topic areas."""

PROBLEMS = [
    {
        "id": "pair-target-indices",
        "title": "Find a Pair for the Target",
        "topic": "Arrays and Hashing",
        "difficulty": "Easy",
        "description": (
            "Given an integer list and a target, print the zero-based indices of the "
            "lexicographically earliest pair i < j whose values sum to the target "
            "(choose the smallest i, then the smallest j if several pairs exist). "
            "Print -1 -1 if no pair exists."
        ),
        "input_format": "Line 1: n and target. Line 2: n integers.",
        "output_format": "Print i and j separated by one space, or -1 -1.",
        "constraints": "2 <= n <= 100000; -10^9 <= values, target <= 10^9.",
        "sample_input": "5 9\n2 7 11 15 0\n",
        "sample_output": "0 1",
        "starter_code": """def main():
    # Read input from stdin and print the required indices.
    pass

if __name__ == \"__main__\":
    main()
""",
        "hint": "A value-to-index map can find complements in one pass. Preserve the earliest valid pair.",
        "tests": [
            ("5 9\n2 7 11 15 0\n", "0 1"),
            ("4 6\n3 3 2 4\n", "0 1"),
            ("5 0\n-3 1 3 -1 2\n", "0 2"),
            ("3 100\n1 2 3\n", "-1 -1"),
            ("6 10\n1 9 2 8 3 7\n", "0 1"),
        ],
    },
    {
        "id": "maximum-segment-sum",
        "title": "Largest Contiguous Segment Sum",
        "topic": "Arrays / Kadane's Algorithm",
        "difficulty": "Medium",
        "description": (
            "For a non-empty integer list, find the greatest sum obtainable from a "
            "contiguous segment. A segment must contain at least one element."
        ),
        "input_format": "Line 1: n. Line 2: n integers.",
        "output_format": "Print the maximum contiguous segment sum.",
        "constraints": "1 <= n <= 200000; -10^6 <= each value <= 10^6.",
        "sample_input": "8\n-2 -3 4 -1 -2 1 5 -3\n",
        "sample_output": "7",
        "starter_code": """def main():
    # Read input from stdin and print the maximum segment sum.
    pass

if __name__ == \"__main__\":
    main()
""",
        "hint": "Track the best segment ending at each position and the best seen overall.",
        "tests": [
            ("8\n-2 -3 4 -1 -2 1 5 -3\n", "7"),
            ("4\n-8 -3 -6 -2\n", "-2"),
            ("5\n1 2 3 4 5\n", "15"),
            ("6\n5 -10 6 7 -2 4\n", "15"),
            ("1\n-9\n", "-9"),
        ],
    },
    {
        "id": "first-target-position",
        "title": "First Position of a Target",
        "topic": "Binary Search",
        "difficulty": "Medium",
        "description": (
            "Given a sorted non-decreasing integer list and a target, print the index "
            "of its first occurrence. Print -1 when the target is absent."
        ),
        "input_format": "Line 1: n and target. Line 2: n sorted integers.",
        "output_format": "Print one zero-based index, or -1.",
        "constraints": "1 <= n <= 200000; -10^9 <= values, target <= 10^9.",
        "sample_input": "7 4\n1 2 4 4 4 7 9\n",
        "sample_output": "2",
        "starter_code": """def main():
    # Read input from stdin and print the first matching index.
    pass

if __name__ == \"__main__\":
    main()
""",
        "hint": "When a match is found, keep searching the left half for an earlier match.",
        "tests": [
            ("7 4\n1 2 4 4 4 7 9\n", "2"),
            ("5 2\n2 2 2 2 2\n", "0"),
            ("4 8\n1 3 5 7\n", "-1"),
            ("1 -5\n-5\n", "0"),
            ("6 0\n-5 -2 0 0 3 9\n", "2"),
        ],
    },
]

PROBLEM_BY_ID = {problem["id"]: problem for problem in PROBLEMS}

# Compiler versions are resolved from Wandbox's live catalog at runtime.
LANGUAGES = [
    {"id": "python", "label": "Python 3"},
    {"id": "cpp", "label": "C++"},
    {"id": "java", "label": "Java"},
    {"id": "javascript", "label": "JavaScript (Node.js)"},
]
LANGUAGE_BY_ID = {language["id"]: language for language in LANGUAGES}


def starter_code(problem_id, language_id):
    problem = PROBLEM_BY_ID[problem_id]
    if language_id == "python":
        return problem["starter_code"]
    templates = {
        "cpp": {
            "pair-target-indices": """#include <bits/stdc++.h>
using namespace std;
int main() {
    int n; long long target;
    if (!(cin >> n >> target)) return 0;
    vector<long long> values(n);
    for (auto &value : values) cin >> value;
    // Print the lexicographically earliest matching pair, or -1 -1.
    return 0;
}
""",
            "maximum-segment-sum": """#include <bits/stdc++.h>
using namespace std;
int main() {
    int n; if (!(cin >> n)) return 0;
    vector<long long> values(n);
    for (auto &value : values) cin >> value;
    // Print the largest sum of a non-empty contiguous segment.
    return 0;
}
""",
            "first-target-position": """#include <bits/stdc++.h>
using namespace std;
int main() {
    int n; long long target;
    if (!(cin >> n >> target)) return 0;
    vector<long long> values(n);
    for (auto &value : values) cin >> value;
    // Print the first matching index, or -1.
    return 0;
}
""",
        },
        "java": {
            "pair-target-indices": """import java.util.*;
public class Main {
    public static void main(String[] args) {
        Scanner in = new Scanner(System.in);
        int n = in.nextInt(); long target = in.nextLong();
        long[] values = new long[n];
        for (int i = 0; i < n; i++) values[i] = in.nextLong();
        // Print the lexicographically earliest matching pair, or -1 -1.
    }
}
""",
            "maximum-segment-sum": """import java.util.*;
public class Main {
    public static void main(String[] args) {
        Scanner in = new Scanner(System.in);
        int n = in.nextInt(); long[] values = new long[n];
        for (int i = 0; i < n; i++) values[i] = in.nextLong();
        // Print the largest sum of a non-empty contiguous segment.
    }
}
""",
            "first-target-position": """import java.util.*;
public class Main {
    public static void main(String[] args) {
        Scanner in = new Scanner(System.in);
        int n = in.nextInt(); long target = in.nextLong();
        long[] values = new long[n];
        for (int i = 0; i < n; i++) values[i] = in.nextLong();
        // Print the first matching index, or -1.
    }
}
""",
        },
        "javascript": {
            "pair-target-indices": """const fs = require('fs');
const data = fs.readFileSync(0, 'utf8').trim().split(/\\s+/).map(Number);
const n = data[0], target = data[1], values = data.slice(2, 2 + n);
// Print the lexicographically earliest matching pair, or -1 -1.
""",
            "maximum-segment-sum": """const fs = require('fs');
const data = fs.readFileSync(0, 'utf8').trim().split(/\\s+/).map(Number);
const n = data[0], values = data.slice(1, 1 + n);
// Print the largest sum of a non-empty contiguous segment.
""",
            "first-target-position": """const fs = require('fs');
const data = fs.readFileSync(0, 'utf8').trim().split(/\\s+/).map(Number);
const n = data[0], target = data[1], values = data.slice(2, 2 + n);
// Print the first matching index, or -1.
""",
        },
    }
    return templates[language_id][problem_id]

