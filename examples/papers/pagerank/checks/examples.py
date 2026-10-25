"""Verify the worked example for s01 (PageRank as a random surfer).

4 pages A, B, C, D. Links: A->B, A->C, B->C, C->A, D->C. Damping d = 0.85.
Normalized form: PR(p) = (1-d)/N + d * sum_{q -> p} PR(q)/C(q), ranks sum to 1.
(The paper writes (1-d) without /N; that version gives ranks that sum to N, i.e. N times these.)
"""
import random
from fractions import Fraction as F

PAGES = "ABCD"
LINKS = {"A": "BC", "B": "C", "C": "A", "D": "C"}
d = F(85, 100)
N = len(PAGES)


def step(pr):
    new = {p: (1 - d) / N for p in PAGES}
    for q, outs in LINKS.items():
        for p in outs:
            new[p] += d * pr[q] / len(outs)
    return new


pr = {p: F(1, N) for p in PAGES}
history = [pr]
for _ in range(60):
    pr = step(pr)
    history.append(pr)

for k in (0, 1, 2, 3, 60):
    print(k, {p: round(float(history[k][p]), 4) for p in PAGES}, "sum", float(sum(history[k].values())))

# exact solution by linear algebra (fractions): solve x = (1-d)/N + d M x
import sympy as sp  # noqa: E402
x = sp.symbols("a b c dd")
idx = dict(zip(PAGES, x))
eqs = []
for p in PAGES:
    rhs = sp.Rational(15, 400)
    for q, outs in LINKS.items():
        if p in outs:
            rhs += sp.Rational(85, 100) * idx[q] / len(outs)
    eqs.append(sp.Eq(idx[p], rhs))
sol = sp.solve(eqs, x)
exact = {p: sol[idx[p]] for p in PAGES}
print("exact", exact, {p: float(v) for p, v in exact.items()})
assert abs(sum(exact.values()) - 1) == 0
for p in PAGES:
    assert abs(float(history[60][p]) - float(exact[p])) < 1e-9

# Monte Carlo random surfer agrees
random.seed(1)
visits = {p: 0 for p in PAGES}
cur = "A"
STEPS = 1_000_000
for _ in range(STEPS):
    if random.random() < 0.15:
        cur = random.choice(PAGES)
    else:
        cur = random.choice(LINKS[cur])
    visits[cur] += 1
print("surfer", {p: round(visits[p] / STEPS, 4) for p in PAGES})
for p in PAGES:
    assert abs(visits[p] / STEPS - float(exact[p])) < 0.003
print("percent", {p: round(100 * float(exact[p]), 1) for p in PAGES})
