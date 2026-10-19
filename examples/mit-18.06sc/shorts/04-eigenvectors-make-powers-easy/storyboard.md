# Follow the eigenvectors (s04: why A to the 100th is easy)

claim:      Each multiplication by A rescales each eigenvector part by its eigenvalue, so the
            lambda = 1 part (600, 400) survives and the lambda = 1/2 part halves away every year.
example:    Markov matrix A = [[0.8, 0.3], [0.2, 0.7]], start u0 = (1000, 0).
            A(600, 400) = (480 + 120, 120 + 280) = (600, 400)  -> lambda1 = 1
            A(1, -1) = (0.5, -0.5)                             -> lambda2 = 1/2
            (1000, 0) = (600, 400) + 400 (1, -1)
            u_k = (600, 400) + 400 (1/2)^k (1, -1): (800, 200), (700, 300), (650, 350), (625, 375)
            direct check: A(1000, 0) = (800, 200) (the slow way agrees with year one).
            gap 400, 200, 100, 50, 25.  A^100 u0 = (600, 400) + 400 (1/2)^100 (1, -1) ~ (600, 400).
            (all verified with fractions in Python; scene.py recomputes them, nothing retyped)
objects:    one population plane (x = people in city 1, y = people in city 2, range -50..1050);
            the state dot u_k (blue) with two thick blue "city bars" lying on the axes (its
            coordinates) and live head-counts; green eigenline through the origin and (600, 400)
            with a fixed green arrow x1; red eigen-direction line (1, -1) through (600, 400) with a
            red arrow from the green tip to the dot; the A matrix plate; one equation slot.
layout:     title on top; plane fills the top ~5.7 units of STAGE (centred); A plate in the empty
            top-right corner above both lines (spills into the right margin); lambda tags in the
            right margin at the ends of the two lines; "city 2" + y-count in the left margin,
            "city 1" + x-count under the x-axis; equation slot = band at the bottom of STAGE.
invariant:  the green arrow (600, 400) never moves; every state keeps 1000 people, so the dot only
            ever slides along the red line.
reveal:     A^100 (1000, 0) = 1^100 (600, 400) + 400 (1/2)^100 (1, -1): powers of A just power the eigenvalues.

| beat | narration (spoken) | picture (what moves) |
|------|--------------------|----------------------|
| hook | A thousand people move between two cities by the same rule every year. Where are they after a hundred years? | plane draws with the title; the city-1 bar fills to 1000 (dot slides out along the x-axis); counts appear; slot asks A^100 (1000, 0) = ? |
| rule | Each year, city one keeps eighty percent and sends twenty across; city two keeps seventy and sends thirty back. That's the matrix A. | A plate fades in top-right; yellow outline on column 1 at "eighty", moves to column 2 at "city two"; A pulses at "matrix" |
| turn | A turns most vectors: one thousand, zero becomes eight hundred, two hundred. | blue arrow (1000, 0) turns to (800, 200) at "becomes", leaves a hollow marker; slot: A(1000, 0) = (800, 200) |
| stay | But six hundred, four hundred comes back unchanged: an eigenvector with eigenvalue one. | green line through origin draws; green arrow to (600, 400) grows; slot: A(600, 400) = (480+120, 120+280) = (600, 400); tag lambda = 1 |
| half | And anything along one, minus one, A just halves: eigenvalue one half. | red (1, -1) line through (600, 400) draws; a red demo arrow on it halves at "halves"; slot: A(1, -1) = (0.5, -0.5) = 1/2 (1, -1); tag lambda = 1/2 |
| split | Split the start along the two lines: one thousand, zero is six hundred, four hundred, plus four hundred times one, minus one. | slot builds term by term; green arrow pulses at "six"; red arrow grows from the green tip to the dot at "plus" |
| year1 | Each year the green part stays and the red part halves: eight hundred, two hundred, right where A sent us. | green arrow pulses; red arrow halves, dot hops onto the hollow marker, counts roll 1000 -> 800, 0 -> 200; slot numbers morph |
| years | Again it halves: one hundred, fifty, twenty-five, closing in on six hundred, four hundred. | three hops on the spoken numbers, trail dots show the halving spacing; slot numbers morph |
| every | The start doesn't matter: every split of the thousand lies on the red line, and the whole line halves each year. | readout fades; thick red segment (0, 1000)-(1000, 0) with five blue starts; three halvings about (600, 400) |
| takeaway | A to the hundredth just powers the eigenvalues: one stays one, one half to the hundredth is practically zero. Everyone ends at six hundred, four hundred. | slot: A^100 (1000, 0) = 1^100 (600, 400) + 400 (1/2)^100 (1, -1); green box on the 1^100 term, red box on the (1/2)^100 term as the segment collapses; bars return in green: 600 / 400 |

risks:
- Crowding: two lines, arrows, bars, A plate and a slot. Keep the A plate in the corner above both
  lines; one equation at a time in the bottom slot; tags in the margins; head-counts are plain text.
- The red line is drawn through (600, 400) (parallel to the eigenvector (1, -1)); the red arrow is
  measured from the green tip. Narration says "along one, minus one" and the demo arrow halving makes
  "eigenvalue one half" a motion, not just a formula.
- Static stretches: every beat moves something (turn, grow, halve, hop, collapse).
- Text crossing lines: all equations on plates; city labels and counts live off the lines.
