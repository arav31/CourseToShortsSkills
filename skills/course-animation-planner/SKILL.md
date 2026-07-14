---
name: course-animation-planner
description: Use when planning silent, vertical mathematical or technical animations before generating Manim scenes. It converts a concept and worked example into a continuous visual proof with persistent objects, beat-level state changes, phone-safe composition, and renderable QA evidence.
---

# Course Animation Planner

## Purpose

Plan one continuous visual argument before writing code. The finished MP4 must make the claim and worked example understandable with no voiceover: the learner should be able to follow the same objects as they move, deform, split, combine, or change value.

Set `COURSE_SHORTS_ROOT` to the absolute plugin root before running a wrapper. Wrappers resolve their own location; set `COURSE_SHORTS_PYTHON` when the required packages live outside `python3`.

A sequence of title, definition, formula, and worked-example cards is not a visual explanation. Neither is a large labeled box whose contents appear only as prose.

## Required Workflow Stage

Run the planner for every short after `short_plan.json` is created, not only when adding a new renderer:

```bash
"$COURSE_SHORTS_ROOT/scripts/course-shorts" storyboard --run runs/<course>
```

`animation-plan` is an alias for `storyboard`. The command writes one fingerprinted artifact per short under `animation_plans/short_XX.json` and a run-level `animation_plan_index.json`. It also links each short to its artifact in `short_plan.json`.

Do not call `manim` or `render` before this stage. Both commands fail when a plan is missing, stale, edited without updating its index hash, or invalid. After any change to a short's hook, intuition, formula, visual type, or worked example, rerun `storyboard` before regenerating scenes.

## Required Plan

Each per-short JSON artifact must contain these items:

1. **Visual claim:** one sentence describing what the viewer will see become true.
2. **Concrete example:** the actual numbers, symbols, shapes, graph, state, or dataset used on screen.
3. **Object roster:** stable IDs, initial appearance, semantic color, and role for every important object.
4. **Continuity spine:** the one anchor object or object group visible through at least three consecutive beats and transformed into, or directly connected to, the result.
5. **Beat table:** 5-8 beats with the fields below.
6. **Invariant:** what remains fixed while other state changes.
7. **Reveal:** the final relation, theorem, mechanism, or decision made visible by the preceding motion.
8. **QA evidence plan:** the rendered timestamps or frame pairs that will prove each required change occurred.

The six-beat sequence must form one **build -> transform -> resolve** arc. The opening constructs the proof surface, the middle beats perform causally linked operations on it, and the ending resolves that same surface into the result. A sequence of individually valid but interchangeable demonstrations is not an arc.

The artifact must use a supported semantic visual route. Shared renderer registries such as `CS_VISUAL_KINDS` and `PHYSICS_VISUAL_KINDS` define the available families, while the worked example selects the concrete route and renderer state. A BFS frontier, heap sift, hash collision, DP dependency, force sum, wave measurement, market intersection, and elasticity movement require different object roles, actions, invariants, and intermediate states; broad family boilerplate is invalid. `numeric_rule` is only a diagnostic fallback. `state_machine` is supported only for a concrete automaton with named states and explicit transitions. Stop before Manim for either unsupported case.

Each beat-table row must specify:

- `time`: target start/end, long enough to inspect but not a substitute for motion
- `arc_phase`: exactly one of `build`, `transform`, `hold`, or `resolve`; construction and resolution never count toward the four required transformations
- `claim`: the one idea this beat makes visible
- `start_state`: object IDs and relevant values/positions at entry
- `action`: a mathematical or diagrammatic transformation, not merely a fade or camera move
- `end_state`: the changed values, positions, shape, grouping, or correspondence
- `state_delta`: complete `before` and `after` snapshots plus the exact `changed_object_ids`; a transform with an empty or fabricated delta is invalid
- `carry`: object IDs that persist into the next beat
- `text` and `cue_lines`: only the label, cue, or short equation needed to read the action, represented as one or two complete visible lines
- `evidence`: a timestamp before and after the state change

For every carried object, one beat's end state must equal the next beat's start state. A mismatch is allowed only when the next beat declares an animated handoff with the same object ID, exact source and destination states, and the transformation that connects them. The resolve phase must begin from the last transform's changed state.

## Continuous Visual Story Contract

- Put a meaningful object on screen in the opening beat. A title may accompany it, but a title is never the first scene by itself.
- At least four beats must visibly change mathematical or diagram state. Creating, fading, highlighting, or moving text alone does not count.
- At least 70% of beats must act on the objects that carry the explanation. No more than one beat may be a pure reading hold.
- Preserve at least one semantic anchor across every adjacent pair of explanatory beats. When an object must be replaced, specify an explicit visual handoff such as shape matching, morphing, tracing, or a copy moving into the successor.
- Do not clear the canvas between the concept and worked example. Instantiate the example by relabeling, specializing, measuring, or adding values to the existing representation.
- The worked example must show setup, operation, intermediate state, and result as visible object states. A heading, border, placeholder, or final answer pasted into a box does not satisfy this.
- For mutable graph and table values, enumerate persistent label/cell object IDs and exact before/after snapshots. A caption that states a relaxation, reweighting, or recurrence is not evidence unless the corresponding on-diagram value changes and remains visible in the next state.
- Introduce formulas from the picture: align terms with objects, transform labels into terms, or reveal terms as their visual counterparts change. Do not cut from a diagram to an unrelated equation card.
- End by resolving or annotating the continuity spine. The final result must be traceable back to the opening object without narration.
- Preserve the identity of the proof surface for the whole arc. Prefer changing parameters, highlights, boundaries, partitions, paths, values, or attached copies over replacing the central representation. If a replacement is mathematically necessary, the predecessor must visibly deform, project, unwrap, or move into the successor.
- Choreograph causal updates in the order **orient -> expose evidence -> animate effect -> commit -> inspect**. Dependency paths, source values, forces, constraints, or competing choices must become readable before the result changes. Do not draw a route for the first time while a carrier is already traversing it, and do not write the destination value before the carrier arrives.
- When alternatives compete, keep them in a stable spatial comparison rail or shared frame long enough to compare. Move the selected alternative into the result and leave rejected alternatives visible until the choice is legible; do not flash the whole table, graph, or canvas as a substitute for showing why one candidate wins.
- Give every proof-carrying motion enough visual footprint to read at phone size. A tiny dot crossing an otherwise frozen diagram is a pointer, not a state transformation. Move or progressively construct the relevant object, boundary, path, vector, region, or correspondence as well.
- When an object travels between labeled regions, plan a visible route through an empty lane. Draw the route as the object moves, then retire both coherently; an invisible motion path or a token crossing text does not communicate the handoff.

Treat the continuity spine as the proof surface, not as a decorative thumbnail. It should normally occupy at least half of the safe width while it is carrying the argument. Do not shrink it into a corner to make room for prose. A reference-quality sequence should contain at least three causally linked operations on that same representation, such as refine -> project -> unwrap -> accumulate; three unrelated entrances, pulses, or camera moves do not count.

Derive duration from the complete beat sequence. Budget time for the learner to inspect each start state, see the operation, and inspect the changed state. Do not target a fixed minimum, 38-second, or 60-second runtime, and never pad every beat to manufacture a clip length. Preserve content-derived reading and action floors, but assign action time only when the renderer has an exact executable callback and observable before/after state for that transition. If the full visual proof needs more time, keep it; if it contains two independent claims, split it into two shorts.

Allocate discrete semantic transitions by the motion time available in each beat, not by equal transition counts. Preserve at least one transition in every active beat, then give longer beats proportionally more updates. Each update still needs its own orient/evidence/effect/commit/inspect cycle; if that cannot fit, lengthen the beat or split the short.

Annotate each planned action with its visible motion class and object IDs. Opening construction belongs to an explicit build action even when it does not mutate domain state. A long beat cannot rely on opacity, color, hidden-object movement, a same-position transform, or a tiny cursor as its only motion carrier; interleave bounded, mechanism-specific sustain actions while preserving exact semantic transition order and duration.

Allocate state paths and callbacks globally across the whole beat sequence, including resolve. Reserve the terminal state and endpoint action before distributing intermediate states, and give every long or resolve beat either a qualifying causal-motion interval or an explicitly bounded reading hold. Record intended sub-play frame ranges so motion intervals plus holds conserve the exact renderer-frame budget.

Plan portrait composition by semantic role, not one aggregate bounding box. Reserve separate title, cue/formula, core-proof, and evidence lanes; size the core mechanism against the core lane alone. When its aspect ratio cannot meet both width and height occupancy, specify a wide/tall/dense/sparse reflow or staged continuation while keeping one persistent proof carrier.

Useful proof-carrying actions include unwrap, project, rotate, shear, stretch, partition, pair, substitute, accumulate, cancel, sort, traverse, collapse, compare, and vary a parameter. Choose actions because they expose the topic's mechanism, not because they are available effects.

## Text And Color Contract

- Use three levels only: a short concept label, beat-level cues/equations, and local object labels. The visual object remains larger and more prominent than explanatory prose.
- Keep the concept label to one line. Keep a beat cue to at most two short lines and one idea. Split a derivation across beats rather than shrinking it.
- Rewrite boilerplate such as `This teaches TOPIC by...` as a concise result or mechanism claim before storyboarding. Stage longer essential copy across successive cues; never compress it into a tiny footer.
- Use labels as semantic pointers, not paragraph subtitles. Silent does not mean text-heavy: the object changes plus sparse labels must carry the logic.
- Assign colors by role and keep them stable across all beats, for example input/object, operation/change, and invariant/result. Never recolor an object merely for decoration.
- Plan text removal or replacement when its beat ends so labels do not accumulate into a slide.

## Phone-Safe Composition

- Plan for a 9:16 frame viewed at approximately 270 x 480 pixels.
- Reserve outer safe margins of at least 8% of frame width and 6% of frame height. Keep titles, equations, labels, and critical marks inside them.
- Give the continuity spine the central visual field. Do not divide the frame into a small diagram plus a dominant text panel.
- At every beat, identify the occupied regions and collision risks. Labels must sit beside their referents with leader lines or backplates when needed; axes, arrows, curves, and borders may not run through text.
- Never plan a large decorative or explanatory panel. A region larger than about 35% of the safe frame must represent the mathematical object itself and must be visibly populated when introduced. There is no empty `Worked example` box.
- If content does not fit at phone size, reduce the number of simultaneous objects, stage the construction, or split the beat. Do not solve it with tiny type.
- Enforce the role's minimum type size after all width and height fitting, not only at object construction. A fit that pushes a title, cue/equation, or essential label below its floor is a planning failure.

## Evidence-Based QA Plan

The plan is incomplete until it defines how the render will be judged.

- Capture opening, pre-action, post-action, and final-reveal frames, plus both sides of every major transformation.
- For each required transformation, name the persistent object visible in both frames and the state difference the pair must show.
- Review frames at phone size, not only full-resolution. All essential labels, values, and correspondences must remain legible.
- Reject the plan if the evidence could be satisfied by reordered still cards, if two consecutive beats have no visible state change, or if the worked-example region is blank or mostly unused.
- Reject the plan if the destination state appears before its visual cause, if comparison choices never coexist, or if the same central construction is needlessly torn down and rebuilt.
- Treat automated density, blank-frame, and static-frame metrics as triage evidence only. The acceptance decision must also cite rendered frame pairs showing object continuity and meaningful change.
- Planned timestamps are not proof that an action executed. Production rendering must emit a hash-bound runtime trace from the renderer, with actual start/end times, beat and transition IDs, object IDs, changed attribute, and structured observed before/after states for every required transform.

After rendering, initialize the separate temporal-review manifest:

```bash
"$COURSE_SHORTS_ROOT/scripts/course-shorts" visual-review --run runs/<course>
```

This copies the plan's evidence windows and hashes the final MP4. It intentionally leaves observations and verdicts pending. A human or agent must watch the opening, both sides of planned actions, an intermediate state, and the final reveal, then sweep the whole video at intervals no larger than 0.25 seconds. Record persistent object IDs, observed changes, overlap/legibility results, text-bearing-object collision and persistent-text-integrity results, reviewer identity, and a verdict in `visual_review.json`.

## Failure Test

Before implementation, answer all of these with concrete beat IDs and object IDs:

- What object survives from the opening into the explanation?
- Which four state changes advance the proof?
- How does the worked example inherit the concept representation?
- Which visible intermediate state prevents the result from looking asserted?
- What can be removed without breaking the visual proof? Remove decorative items.
- Which rendered frame pairs will demonstrate that this is animation rather than a slide deck?

If any answer is missing, revise the plan before generating Manim.

## Topic-Independent Examples

- A quantity becomes bars, the operation changes their lengths, and the same bars recombine into the result.
- Elements remain visible while boundaries form around equivalence classes; each class then collapses to one representative state.
- A graph retains its nodes while an algorithm changes frontier, visited, and predecessor state step by step.
- A curve remains fixed while a point, secant, and measured ratio transform into a tangent and derivative value.
- A payoff table remains fixed while row-wise comparisons mark the same action and converge on the decision rule.
