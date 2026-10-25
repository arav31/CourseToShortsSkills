"""Verify every number in the worked example of short_plan.json (s01).

Source: C. E. Shannon, "A Mathematical Theory of Communication", BSTJ 1948,
Section 10 uses this same four-letter source (A, B, C, D with 1/2, 1/4, 1/8, 1/8).
"""
from fractions import Fraction as F
from math import log2

P = {"A": F(1, 2), "B": F(1, 4), "C": F(1, 8), "D": F(1, 8)}
CODE = {"A": "0", "B": "10", "C": "110", "D": "111"}  # one bit per yes/no answer

assert sum(P.values()) == 1

# Questions asked in order: "Is it A?" -> "Is it B?" -> "Is it C?"
questions = {s: len(CODE[s]) for s in P}
assert questions == {"A": 1, "B": 2, "C": 3, "D": 3}

avg = sum(P[s] * questions[s] for s in P)
H = sum(float(p) * log2(1 / float(p)) for p in P.values())
assert avg == F(7, 4)
assert abs(H - 1.75) < 1e-12
# each symbol's question count equals its surprise log2(1/p)
assert all(log2(1 / float(P[s])) == questions[s] for s in P)

# prefix-free: no codeword starts another; Kraft sum is exactly 1
words = list(CODE.values())
assert not any(a != b and b.startswith(a) for a in words for b in words)
assert sum(F(1, 2 ** len(w)) for w in words) == 1

# fixed-length strategy (halve the four letters twice): 2 questions every time
fixed = 2
assert fixed == log2(len(P))
uniform_H = log2(4)
assert uniform_H == 2.0

# a typical message of 8 letters in proportion: A A A A B B C D
msg = "AAAABBCD"
assert all(msg.count(s) == P[s] * len(msg) for s in P)
bits = "".join(CODE[s] for s in msg)
assert len(bits) == 14 and len(bits) / len(msg) == 1.75
assert fixed * len(msg) == 16
# it decodes uniquely
out, cur = [], ""
inv = {v: k for k, v in CODE.items()}
for b in bits:
    cur += b
    if cur in inv:
        out.append(inv[cur]); cur = ""
assert "".join(out) == msg

# practice question: what if all four letters were equally likely? -> 2 bits
print("avg questions =", avg, "=", float(avg), "bits; H =", H)
print("message", msg, "->", bits, len(bits), "bits vs", fixed * len(msg), "fixed")
