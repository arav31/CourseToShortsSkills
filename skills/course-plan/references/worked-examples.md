# Worked examples and short selection

The worked example is the spine of every short: the picture animates it, the narration
walks it, the notes reuse it. Get it right in the plan and everything downstream is easier.

## What a good worked example is

- **Concrete.** Real numbers, a specific small object (a 3-element group, a 4-node graph,
  a 2x2 matrix, a payoff table, a 1 kg block on a 30° incline), or a tiny symbolic case.
- **Mechanism-true.** It exercises the named idea and nothing else. Dijkstra's example
  relaxes edges with a priority queue; topological sort uses indegrees, not distances.
  A tax example shows the wedge between buyer and seller prices, not an elasticity formula.
- **Visualizable.** Small enough to draw legibly on a phone: ≤ 6 nodes, ≤ 3x3 matrices,
  integers or simple fractions, numbers that land on grid points.
- **Self-checking.** Contains a second route to the same answer or a sanity check
  (row rule vs column picture; area formula vs counting squares; conservation of mass).
- **Fresh.** No two shorts in a series share the same setup or the same numbers unless
  the short is explicitly a comparison. Changing the title around the same numbers is a repeat.
- **Correct.** Compute every value (in your head and, for anything non-trivial, with a
  quick Python snippet). Wrong arithmetic in a published video is the most damaging error.

For theoretical topics, the example is a small instance that makes the statement checkable:
cosets of {0, 3} in Z6 (three blocks of two), a counterexample showing why a hypothesis is
needed, a 3x3 grid DP filled in cell by cell, a 2-state Markov chain iterated three steps.

## Bad examples (all seen in earlier versions of this pipeline)

| bad | why |
|---|---|
| "Choose a small example and work through the definition." | placeholder, no content |
| The same matrix `[[2,0],[0,3]]` for invertibility, determinants and eigenvectors | reuse makes the series feel templated |
| Dijkstra's relaxation formula attached to topological sort | cross-mechanism copy |
| "Oligopoly" illustrated by a generic firm-revenue example | example does not exercise the concept |
| Numbers that need 4 decimal places on screen | unreadable; pick values that come out clean |

## Choosing the shorts

- One idea per short. If the claim needs "and", it is probably two shorts.
- Order by prerequisites: representations before operations, operations before
  theorems, intuition before abstraction.
- Cover the course: aim for at least one short per outline unit. Units that are
  pure review, logistics or exams go to `skipped_units` with a reason; proof-heavy units
  can still get a short built around one checkable instance of the theorem.
- Prefer ideas with a strong visual mechanism. When a unit has none, a well-chosen
  counterexample or a "two ways to compute the same thing" picture usually works.
- Typical sizes: a 30–40 lecture course gives 15–30 shorts. Ask the user if they want
  a subset; for a quick demo pick 3–5 shorts that show the course's arc.
- Hooks are questions or tensions in plain words ("Why does every rotation have a
  fixed axis?"), not titles ("Euler's rotation theorem").
