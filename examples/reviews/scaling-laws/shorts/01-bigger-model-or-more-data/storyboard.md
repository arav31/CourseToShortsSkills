# Bigger model, or more data?
claim:      With training cost C ≈ 6ND, Kaplan et al. (2020) put extra compute mostly into model size (N ∝ C^0.73); Hoffmann et al. (2022) grow parameters and tokens together (N ∝ C^0.5). Run from the same budget to Gopher's 5.76e23 FLOPs, the rules land at ≈480B params / 200B tokens versus ≈70B / 1.4T, which is Chinchilla, and Chinchilla beat Gopher. Pearce & Song (2024) explain most of the gap.
example:    Start at 1e21 FLOPs (Hoffmann D.4 head-to-head: Kaplan's fit 4.68B params, Approach 1 2.86B; tokens by 6ND: 36B, 58B). Scale the budget 576x. Kaplan: 485B params, 198B tokens. Hoffmann: 69B, 1.40T. Real: Gopher 280B/300B, Chinchilla 70B/1.4T (20 tokens per parameter). Pearce & Song: 0.78 (non-embedding, small scale) vs 0.73; 0.51 (total) vs 0.50. All in checks/examples.py.
objects:    one log-log plane (parameters across 1B..1T, tokens up 10B..10T); a yellow budget line (slope -1, isoFLOP); an orange dot (Kaplan) and a blue dot (Hoffmann) that ride the line and leave trails; Gopher and Chinchilla points; a dashed 20-tokens-per-parameter diagonal.
layout:     top band of the stage (STAGE.rows) holds plates: C ≈ 6ND, then the two rules side by side (orange left, blue right) with their (Author, year), later Pearce & Song's exponent panel. The plane fills the rest of the stage, ticks on the left/bottom; point labels on plates in empty regions.
invariant:  the plane and the budget line; the two dots always sit on the current budget line (both rules spend the same compute).
reveal:     N ∝ C^0.5, D ∝ C^0.5 (about 20 tokens per parameter), stated after the sweep and the Chinchilla result.

| beat | narration (spoken) | picture (what moves) |
|------|--------------------|----------------------|
| hook | Fixed compute budget: bigger model or more data? The answer flipped. | title + plane draw in; empty axes with tick labels |
| budget | Cost ≈ 6 × params × tokens, so one budget is a line: double the model, halve the data. | C ≈ 6ND plate; yellow line drawn at 1e21; a marker slides along it (N up, D down) |
| kaplan | Kaplan 2020: per 10x compute, model ~5x, data ~2x. | orange dot on the line at 4.7B; plate "Kaplan et al., 2020  N ∝ C^0.73"; ghost arrow of one 10x step (×5.4 right, ×1.9 up) |
| hoffmann | Hoffmann 2022, 400+ models: grow both equally, ~3x each. | blue dot at 2.9B; plate "Hoffmann et al., 2022  N ∝ C^0.5"; ghost arrow of a 10x step (×3.2, ×3.2) |
| duel | Same budget: 4.7B vs 2.9B; trained side by side, the smaller won. | labels 4.7B / 2.9B; highlight on blue |
| sweep | Scale budget ~600x to Gopher's. | budget line slides outward (live "budget ×N"); dots ride it leaving orange/blue trails |
| land | Kaplan: ~480B params on 200B tokens; Hoffmann: ~70B on 1.4T. | endpoint labels appear as the narration says them |
| real | Gopher 280B/300B went big; Chinchilla 70B/1.4T, same compute, beat it; 20 tokens per parameter. | Gopher point near Kaplan's side, Chinchilla on the blue dot; dashed 20:1 diagonal |
| pearce | Pearce & Song 2024: non-embedding params at small scale gives 0.78 ≈ Kaplan's 0.73. | top band swaps to the exponent panel |
| takeaway | Grow model and data together. | final plate N ∝ C^0.5, D ∝ C^0.5 |

risks: the plane is crowded at the end (two trails, two real models, a diagonal, five labels): keep labels on plates in the empty lower-right and upper-left; drop the 1e21 labels before the sweep. Start dots are close together (0.3 decades apart): label them on opposite sides. Kaplan's extrapolation uses his own fit with C = 2 Cmin, which reproduces Hoffmann's 4.68B at 1e21 FLOPs; it extrapolates, as Hoffmann's Figure 1 does.
