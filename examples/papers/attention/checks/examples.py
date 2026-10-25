"""Verify every number in the worked example of short_plan.json (s01, scaled dot-product attention).

Toy setup: the 3-token sentence "the cat sat", 2-dimensional queries/keys/values (d_k = 2).
We compute the attention output for the query of the token "sat".
Run:  python checks/examples.py   (exits non-zero if any assertion fails)
"""

import math

TOKENS = ["the", "cat", "sat"]
Q_SAT = (1, 2)                                  # query of "sat"
KEYS = {"the": (1, 0), "cat": (1, 1), "sat": (0, 1)}
VALUES = {"the": (4, 0), "cat": (4, 4), "sat": (0, 4)}
D_K = 2


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def softmax(xs):
    m = max(xs)
    e = [math.exp(x - m) for x in xs]
    s = sum(e)
    return [v / s for v in e]


scores = [dot(Q_SAT, KEYS[t]) for t in TOKENS]
assert scores == [1, 3, 2], scores

scaled = [s / math.sqrt(D_K) for s in scores]
assert [round(x, 2) for x in scaled] == [0.71, 2.12, 1.41], scaled

w = softmax(scaled)
assert [round(x, 2) for x in w] == [0.14, 0.58, 0.28], w
assert abs(sum(w) - 1) < 1e-12
assert abs(sum(round(x, 2) for x in w) - 1) < 1e-9  # the rounded weights shown on screen also sum to 1

out = tuple(sum(w[i] * VALUES[t][j] for i, t in enumerate(TOKENS)) for j in range(2))
assert [round(x, 2) for x in out] == [2.86, 3.44], out
assert [round(x, 1) for x in out] == [2.9, 3.4], out  # shown on screen to one decimal
w2 = [round(x, 2) for x in w]  # same answer from the rounded weights on screen
assert [round(sum(w2[i] * VALUES[t][j] for i, t in enumerate(TOKENS)), 1) for j in range(2)] == [2.9, 3.4]

# second route: the output lies inside the triangle of the value points, pulled toward "cat"
dist = {t: math.dist(out, VALUES[t]) for t in TOKENS}
assert min(dist, key=dist.get) == "cat", dist

# contrast: without the 1/sqrt(d_k) scaling the weights are sharper
w_raw = softmax(scores)
assert [round(x, 2) for x in w_raw] == [0.09, 0.67, 0.24], w_raw
assert max(w_raw) > max(w)

# practice question: double the query to (2, 4) -> scores 2, 6, 4 -> scaled 1.41, 4.24, 2.83
w_pr = softmax([dot((2, 4), KEYS[t]) / math.sqrt(D_K) for t in TOKENS])
assert [round(x, 2) for x in w_pr] == [0.05, 0.77, 0.19], w_pr

print("scores", scores)
print("scaled", [round(x, 2) for x in scaled])
print("weights", [round(x, 2) for x in w])
print("output", [round(x, 2) for x in out])
print("unscaled weights", [round(x, 2) for x in w_raw])
print("practice weights", [round(x, 2) for x in w_pr])
print("all checks pass")
