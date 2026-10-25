"""Verify the worked example of s01 (lemons unravelling) and the paper's continuous case.

Model (our own discrete instance of Akerlof's Section II):
  four used cars; each seller knows her car's value to her (in $ thousands);
  every buyer values any car at 1.5x its seller value, but cannot tell cars apart,
  so buyers offer 1.5 x the AVERAGE value of the cars still for sale.
  A seller keeps her car if the offer is below her value.
"""
from fractions import Fraction as F

CARS = [1, 7, 10, 14]          # seller values, $ thousands
MARKUP = F(3, 2)               # buyers value a car at 1.5x


def unravel(cars):
    rounds, on_sale = [], sorted(cars)
    while True:
        avg = F(sum(on_sale), len(on_sale))
        offer = MARKUP * avg
        stay = [v for v in on_sale if v <= offer]
        rounds.append({"on_sale": list(on_sale), "avg": avg, "offer": offer, "leave": [v for v in on_sale if v > offer]})
        if stay == on_sale:
            return rounds
        on_sale = stay


R = unravel(CARS)
for r in R:
    print(r["on_sale"], "avg", r["avg"], "offer", r["offer"], "leave", r["leave"])

assert [r["avg"] for r in R] == [8, 6, 4, 1]
assert [r["offer"] for r in R] == [12, 9, 6, F(3, 2)]
assert [r["leave"] for r in R] == [[14], [10], [7], []]
assert R[-1]["on_sale"] == [1]

# full information: every car is worth more to a buyer than to its seller, so all 4 trade
gains_full = sum((MARKUP - 1) * v for v in CARS)
gains_lemons = (MARKUP - 1) * 1
assert gains_full == 16 and gains_lemons == F(1, 2)
print("gains from trade: full info", gains_full, "k; hidden quality", gains_lemons, "k")

# Akerlof's continuous case (Section II.B): quality uniform on [0, 2], sellers value x,
# buyers 3x/2. At price p the cars offered have average p/2, worth 3p/4 < p to buyers:
# each round of offers shrinks by 3/4, so no price sustains trade.
p = F(3, 2)  # buyers' first offer: 1.5 x average quality 1
for _ in range(5):
    p = MARKUP * (p / 2)
print("continuous case after 5 rounds:", float(p))
assert p == F(3, 2) * F(3, 4) ** 5
