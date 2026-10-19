# Storyboarding a short

Write `storyboard.md` in the short's folder before any code. Ten minutes here saves
several render cycles. Template:

```markdown
# <title>
claim:      <the one sentence the video makes obvious>
example:    <the worked example from the plan, with the numbers>
objects:    <the persistent things on screen: a plane with two arrows, a 6-node graph + queue strip, ...>
layout:     <where each lives: diagram fills STAGE; equation column top-left; live values on the right>
invariant:  <what stays fixed while everything moves: the column arrows, total probability, atom counts>
reveal:     <the formula/theorem that closes the video, stated after the picture showed it>

| beat | narration (spoken) | picture (what moves) |
|------|--------------------|----------------------|
| hook | ... | ... |
| ...  | ... | ... |

risks: <what could make this static, crowded or misleading, and how you avoid it>
```

## From claim to motion

Ask: *what transformation, applied to which object, makes the claim obvious?* Then pick
from this vocabulary. Every beat should apply at least one verb to an existing object.

| verb | Manim tools |
|---|---|
| grow / draw | `GrowArrow`, `Create`, `Write`, `DrawBorderThenFill` |
| move / slide / chain | `.animate.move_to/shift`, `MoveAlongPath` (on a `Line`/`VMobject`, never a `DashedLine`) |
| stretch / scale / shear / rotate | `.animate.scale/stretch/rotate`, `ApplyMatrix`, `plane.animate.apply_matrix(M)` |
| morph one form into another | `Transform`, `ReplacementTransform`, `TransformMatchingShapes` (equations) |
| split / partition / tile | `VGroup.animate.arrange(...)`, colouring blocks, `LaggedStart` of shifts |
| accumulate | `ValueTracker` + `always_redraw` area/curve, `DecimalNumber` with updater |
| compare | place two versions side by side, or `ghost = obj.copy().set_opacity(0.25)` |
| trace / scan | `MoveAlongPath` of a dot, `Create` of a path, a cursor `Triangle` moving along cells |
| point at | `highlight(obj)` outline, `Indicate` (once), `Circumscribe` (once); never a filled sweep |

## Beats and narration

- 5–9 beats is typical. Each beat = one line of narration (1–2 sentences) + the motion
  that shows it. Beat ids are short (`hook`, `columns`, `scale`, `sum`, `check`, `takeaway`).
- The hook beat shows the real object immediately and asks the question.
- Put the motion *inside* the beat whose words describe it. The beat waits for the
  narration to finish; keep the animations a little shorter than the line so the
  picture finishes as the sentence does.
- A typical beat: 1–3 animations of 0.8–1.6 s each, then a short hold while the voice ends.
- End with the reveal beat: the general statement, now earned.

## Visual vocabulary by field (starting points, not templates)

- **Linear algebra:** number plane with basis arrows; `plane.apply_matrix` to show a map;
  unit square → parallelogram for determinants; eigen-directions staying on their own line;
  projection as dropping a perpendicular; column arrows chaining tip-to-tail.
- **Calculus:** secant sliding into a tangent; Riemann rectangles thinning into area with a
  `ValueTracker`; a dot moving along a curve with its velocity arrow; Taylor polynomials
  hugging a curve one term at a time.
- **Probability/statistics:** probability mass as blocks that flow along a tree; a 2x2 area
  diagram for Bayes when the probabilities are moderate, and a population of dots (natural
  frequencies: "of 1000 people, 10 are sick...") when one probability is tiny; histograms built by dropping samples; a Markov chain whose state
  distribution bars update step by step.
- **Algorithms/data structures:** arrays as rows of labelled cells; pointers as small triangles;
  a queue strip beside the graph for BFS; distances written into nodes and updated on
  relaxation; recursion trees that collapse into a memo table; splits and merges for merge sort.
- **Discrete maths / abstract algebra:** Cayley tables that fill in; cosets as coloured blocks
  tiling the group; a square that actually rotates for D4; homomorphisms as arrows between
  two clouds of elements; orbits as cycles of moving points.
- **Physics:** free-body diagrams whose arrows add tip-to-tail; trajectories traced in time with
  synchronized x(t)/v(t) plots sampled from the same model; energy bars that trade height.
- **Economics:** supply/demand curves that shift; equilibrium projected to both axes; tax wedges
  and deadweight-loss triangles filling in; payoff matrices with best responses marked one at a time.
- **Chemistry:** atoms that keep their identity as they move from reactants to products; counts per
  element staying fixed.

## Layout planning

The frame is 9 x 16 units. Zones (from shortkit):

```
y =  6.0 ┌──────────────────┐  TITLE_ZONE: compact title (one line)
y =  5.05└──────────────────┘
y =  4.8 ┌──────────────────┐
         │      STAGE       │  the diagram; equations in a corner or a band
         │  (8.2 x 7.5)     │  STAGE.rows(...) / STAGE.cols(...) to split
y = -2.7 └──────────────────┘
y = -2.9 ┌───────────────┐     CAPTION_ZONE: burned-in narration captions.
y = -4.9 └───────────────┘     Keep it empty.
        x=-4.1          x=4.1   (the bottom ~370 px and right edge are platform UI)
```

Decide where equations live before coding: a corner of the diagram that stays empty, a
band from `STAGE.rows(1, 3)`, or a side column from `STAGE.cols(2, 1)`.
