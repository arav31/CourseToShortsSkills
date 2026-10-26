"""Recompute every number shown in short s01 (how the compute-optimal recipe changed).

Every input below is quoted from the ORIGINAL cited paper in sources/, not from the review:

  kaplan2020   sources/5d8915-...  N = (1.3e9) Cmin^0.73 (Cmin in PF-days, non-embedding; Fig. 14),
               "5x for each 10x increase in compute", data "only by 2x"; C = 2 Cmin at the critical
               batch size (Sec. 6); C ~ 6N FLOPs per training token (Sec. 2.1).
  hoffmann2022 sources/dd3e4f-...  Table 2: a = 0.50, 0.49, 0.46 (N_opt ~ C^a); Kaplan row 0.73 / 0.27;
               D.4: at 1e21 FLOPs Kaplan's fit gives 4.68B params, Approach 1 gives 2.86B, and the
               smaller model wins; Table 1: Gopher 280B params / 300B tokens, Chinchilla 70B / 1.4T;
               Gopher budget 5.76e23 FLOPs (Fig. 2, Table 3); Table 3: 67B params / 1.5T tokens at
               that budget; "4 times smaller ... 4 times more tokens".
  pearce2024   sources/278750-...  simulated Chinchilla study under Kaplan's conditions gives a local
               coefficient 0.78 (close to 0.73); with total parameters 0.51 (close to 0.50).

Run:  python checks/examples.py   (exits non-zero if any assertion fails)
"""

import math

PF_DAY = 1e15 * 86400                  # FLOPs in one petaflop/s-day = 8.64e19
A_KAPLAN, A_HOFF = 0.73, 0.50          # N_opt ~ C^a
C0 = 1e21                              # the head-to-head budget in Hoffmann et al. D.4
C_GOPHER = 5.76e23                     # Gopher's training compute (Hoffmann et al.)


def kaplan_n(c):
    """Kaplan's fit N = 1.3e9 * Cmin^0.73, Cmin in PF-days, with C = 2 Cmin (critical batch)."""
    return 1.3e9 * (c / 2 / PF_DAY) ** A_KAPLAN


def hoff_n(c):
    """Hoffmann Approach 1 through its own D.4 point: 2.86B params at 1e21 FLOPs, N ~ C^0.5."""
    return 2.86e9 * (c / C0) ** A_HOFF


def tokens(c, n):
    return c / (6 * n)                 # C ~ 6 N D


# --- 10x more compute: how each rule splits it (Kaplan: "5x" model, "2x" data) ---------------
k_n10, k_d10 = 10 ** A_KAPLAN, 10 ** (1 - A_KAPLAN)
h_n10, h_d10 = 10 ** A_HOFF, 10 ** (1 - A_HOFF)
assert round(k_n10, 1) == 5.4 and round(k_d10, 1) == 1.9, (k_n10, k_d10)   # Hoffmann quotes "5.5x" and "1.8x"
assert round(h_n10, 1) == 3.2 and round(h_d10, 1) == 3.2
assert abs(k_n10 * k_d10 - 10) < 1e-9 and abs(h_n10 * h_d10 - 10) < 1e-9     # both spend exactly 10x

# --- the same 1e21 FLOP budget: the paper's head-to-head ------------------------------------
assert round(kaplan_n(C0) / 1e9, 2) == 4.68, kaplan_n(C0)    # reproduces Hoffmann's 4.68B for Kaplan
k_d0 = tokens(C0, 4.68e9)
h_d0 = tokens(C0, 2.86e9)
assert round(k_d0 / 1e9) == 36 and round(h_d0 / 1e9) == 58, (k_d0, h_d0)

# --- Gopher's budget, each rule extrapolated -------------------------------------------------
k_ng = kaplan_n(C_GOPHER)
k_dg = tokens(C_GOPHER, k_ng)
h_ng = hoff_n(C_GOPHER)
h_dg = tokens(C_GOPHER, h_ng)
assert round(k_ng / 1e9, -1) == 480 and round(k_dg / 1e9, -1) == 200, (k_ng, k_dg)   # ~480B on ~200B tokens
assert round(h_ng / 1e9) == 69 and round(h_dg / 1e12, 1) == 1.4, (h_ng, h_dg)        # ~70B on ~1.4T tokens
assert abs(h_ng / 67e9 - 1) < 0.05                                                     # Table 3 says 67B / 1.5T

# --- the real models: same compute, different shape -------------------------------------------
GOPHER = (280e9, 300e9)
CHINCHILLA = (70e9, 1.4e12)
c_gopher = 6 * GOPHER[0] * GOPHER[1]
c_chin = 6 * CHINCHILLA[0] * CHINCHILLA[1]
assert round(c_gopher / 1e23, 1) == 5.0 and round(c_chin / 1e23, 1) == 5.9
assert abs(math.log10(c_chin / C_GOPHER)) < 0.01 and abs(math.log10(c_gopher / C_GOPHER)) < 0.06  # ~same budget
assert GOPHER[0] / CHINCHILLA[0] == 4                     # "4x smaller"
assert round(CHINCHILLA[1] / GOPHER[1], 1) == 4.7         # ~4-5x more tokens (paper: "4x more data")
tpp_chin = CHINCHILLA[1] / CHINCHILLA[0]
tpp_gopher = GOPHER[1] / GOPHER[0]
assert tpp_chin == 20 and round(tpp_gopher, 1) == 1.1, (tpp_chin, tpp_gopher)
assert round(k_dg / k_ng, 1) == 0.4                       # Kaplan's extrapolation: under half a token per parameter

# --- Pearce & Song: exponents ----------------------------------------------------------------
PEARCE_KAPLAN_LIKE, PEARCE_TOTAL = 0.78, 0.51
assert abs(PEARCE_KAPLAN_LIKE - A_KAPLAN) < 0.06 and abs(PEARCE_TOTAL - A_HOFF) < 0.02

if __name__ == "__main__":
    print(f"10x compute  Kaplan: model x{k_n10:.2f}, data x{k_d10:.2f} | Hoffmann: x{h_n10:.2f}, x{h_d10:.2f}")
    print(f"1e21 FLOPs   Kaplan: {kaplan_n(C0)/1e9:.2f}B params, {k_d0/1e9:.1f}B tokens | Hoffmann: 2.86B, {h_d0/1e9:.1f}B tokens")
    print(f"Gopher C     Kaplan: {k_ng/1e9:.0f}B params, {k_dg/1e9:.0f}B tokens | Hoffmann: {h_ng/1e9:.1f}B, {h_dg/1e12:.2f}T tokens")
    print(f"6ND          Gopher {c_gopher:.2e}, Chinchilla {c_chin:.2e} (paper: {C_GOPHER:.2e})")
    print(f"tokens/param Chinchilla {tpp_chin:.0f}, Gopher {tpp_gopher:.2f}, Kaplan-extrapolated {k_dg/k_ng:.2f}")
    print("all checks pass")
