---
name: course-manim-3b1b
description: Use when generating or repairing silent, vertical Manim explainers for math, CS, physics, economics, or other technical topics. Enforces a continuous 3Blue1Brown-inspired visual proof, persistent object state, beat-level transformations, concrete worked examples, phone-safe text/layout, and rendered motion evidence.
---

# Course Manim 3B1B

## Purpose

Generate concept-specific Manim scenes that teach through changing visual state. The render must work as an intentional silent video: no claim, calculation step, or transition may depend on speech or audio timing to be understood.

Set `COURSE_SHORTS_ROOT` to the absolute plugin root before running a wrapper. The wrappers resolve bundled tools from their own location, not the current directory; set `COURSE_SHORTS_PYTHON` if necessary.

Dark canvas, color, and smooth fades are styling, not proof. A valid scene follows recognizable objects through setup, operation, intermediate states, and result.

## Workflow

1. Confirm `short_plan.json` contains a concrete, non-placeholder worked example.
2. Run `course-animation-planner` for the entire run and inspect its artifacts:

```bash
"$COURSE_SHORTS_ROOT/scripts/course-shorts" storyboard --run runs/<course>
```

Require `animation_plan_index.json` and one valid `animation_plans/short_XX.json` per short. Never reconstruct or bypass the storyboard inside Manim. Plans must carry the exact renderer state and route-specific actions, not one script reused across a broad family. A `numeric_rule` fallback is unsupported; `state_machine` is valid only for a concrete automaton with named states and explicit transitions.
3. Generate scene code, scripts, and captions from those artifacts:

```bash
"$COURSE_SHORTS_ROOT/scripts/course-shorts" manim --run runs/<course>
```

4. Inspect representative files under `runs/<course>/scenes/`, `scripts/`, and `captions/`. Confirm each scene embeds the matching animation-plan fingerprint and planned beat/object/continuity metadata. Compare the generated scene against every planned beat; generated text is not evidence that a beat exists visually.
5. Run the draft validator:

```bash
"$COURSE_SHORTS_ROOT/scripts/course-shorts-validate" runs/<course> --draft
```

6. Render silently and create a denser visual audit:

```bash
"$COURSE_SHORTS_ROOT/scripts/course-shorts" render --run runs/<course> --voice-engine none --quality preview
"$COURSE_SHORTS_ROOT/scripts/course-shorts-audit" runs/<course> --interval 0.25 --allow-missing-ocr
```

7. Inspect the rendered evidence using the QA contract below. Patch the visual family, regenerate, rerender, and reaudit until it passes. Treat fixes to one generated output as provisional when the same failure can recur in that visual family.
8. Once previews pass, rerender the full run at production quality and audit those exact files. Then initialize the hash-bound temporal-review manifest, actually watch the evidence windows, and complete it before strict validation:

```bash
"$COURSE_SHORTS_ROOT/scripts/course-shorts" render --run runs/<course> --voice-engine none --quality production
"$COURSE_SHORTS_ROOT/scripts/course-shorts-audit" runs/<course> --interval 0.25
"$COURSE_SHORTS_ROOT/scripts/course-shorts" visual-review --run runs/<course>
"$COURSE_SHORTS_ROOT/scripts/course-shorts-validate" runs/<course>
```

The initialized manifest is deliberately pending and cannot pass strict validation until a named human or agent records concrete observations, completes the full quarter-second transition sweep, and records a `pass` verdict.

Production rendering must also write `render_runtime_trace.json`. Each row is bound to the current animation-plan index and final MP4 hash and contains renderer-captured execution markers for every transform. A plan-derived estimate, a copied evidence timestamp, or a trace missing an executed callback is a production failure.

## Scene Structure Contract

- Show the first meaningful mathematical or diagram object within the opening two seconds. A title may appear with it, then shrink, move aside, or disappear; never hold a title card as a beat.
- Implement 5-8 semantic beats. At least four must visibly transform mathematical or diagram state. `FadeIn`, `FadeOut`, `Write`, `Indicate`, camera motion, and text replacement do not count by themselves.
- Make object changes legible with `Transform`, `ReplacementTransform`, `TransformMatchingShapes`, `TransformMatchingTex`, updaters, parameter animation, or an equally explicit domain-specific construction.
- Keep the planned continuity spine on screen through at least three consecutive beats. Reuse the same mobject when practical. If replacement is necessary, animate an unambiguous handoff from predecessor to successor.
- Do not use `fade_all_except`, a full-canvas fade, or a blank reset between concept and example. The worked example must specialize the existing representation by adding values, selecting a case, moving a copy, or continuing the same construction.
- At least 70% of semantic beats must animate the explanatory objects. No more than one beat may consist only of text entry or a reading hold.
- A long wait cannot compensate for missing choreography. Holds follow a visible state change and preserve the state the learner is meant to inspect.
- Do not infer an action-duration floor from text, operator counts, or estimated steps when the beat has no exact executable transition callback. A beat labeled `transform` must execute a registered semantic callback with an observable state delta; otherwise classify and time it as reading/inspection.
- Never reverse and replay a finite motion sequence merely because later holds remain. Stop on the terminal semantic state. Keep post-action and terminal frozen tails near 1.5 seconds or less; stage additional copy instead of extending a still frame.
- Schedule finite semantic actions by the durations of the remaining canonical holds. Preserve action order and execute every action exactly once. For near-full schedules, preserve opening and final actions and put unavoidable action-free slots in the shortest interior holds instead of creating a long frozen gap.
- Partition discrete semantic updates by the active beats' actual motion budgets. Give every active beat at least one update, then assign additional updates proportionally to available time. Equal-count chunks are invalid when beat durations differ materially.
- Use a read-act-read rhythm inside active holds: meaningful object displacement or progressive construction should normally occupy about 60-76% of the available hold, with short inspection time on both sides. Fades, text replacement, and perpetual decorative motion do not satisfy this budget.
- Keep the proof surface large while it is active. Do not reduce the persistent mechanism to a corner thumbnail so prose or a formula card can take over the frame. A strong route performs at least three causally linked operations on the same representation and lets each result become the next operation's input.
- Structure those operations as one build-transform-resolve arc. Keep the central representation stable enough that a viewer can track object identity from the opening construction through the final relation; do not make the scene a playlist of interchangeable visual cards.
- Finish on the transformed continuity spine plus the concise result. The final formula or conclusion must correspond by position, color, or animated mapping to objects already seen.
- Bind every plan object ID to one live semantic mobject and every planned transform/transition ID to one executed callback. Duplicate, missing, extra, or out-of-order bindings are render failures; embedded metadata does not count as executing the plan.
- Schedule callbacks and every nested `play` in integer renderer frames. Weighted child segments must use a conserved frame partition whose children sum exactly to the parent callback budget; floating-point subdivisions and route-specific timing cushions are invalid. Fill an underrun with a frame-counted frozen wait and fail immediately on any overrun.
- Record actual sub-play frame spans, persistent carrier IDs, motion class, and semantic before/after state in the runtime trace. A callback returning successfully is not motion evidence by itself. Consume every planned state exactly once, reserve terminal motion for resolve, and reject a long beat whose only activity is opacity, instantaneous reveal, localized flash, or an empty callback.
- Classify every scheduled callback as `displacement`, `progressive_draw`, or `opacity_only`, and name the visible object IDs it acts on. A hidden object, a same-position transform, a tiny pointer over a frozen surface, or an opacity/color-only callback cannot carry a build/transform/resolve beat lasting five seconds or more. Keep every local motion-free interval below 4.5 seconds and finish meaningful terminal motion within about one second of the end.
- Treat transition-free opening construction as an executed `build_action`, not an immediate fade followed by a hold. Progressively construct the persistent surface and move a visible probe, key, vector, boundary, or comparable carrier into its first meaningful state within the opening two seconds.

## Worked Example Contract

- Render the exact numbers, symbols, states, or shapes from `worked_example`; do not substitute a generic example merely because a renderer already supports it.
- Show four distinct example states: setup, operation, at least one intermediate, and checked result. Reveal them sequentially on the same representation.
- Animate values or symbols into their operative locations. Highlighting a prose calculation or placing the answer below a diagram is not a worked calculation.
- Keep the causal step visible: row contribution before matrix output, partition before quotient representative, traversal frontier before visited result, force change before motion change, or the topic's analogous intermediate state.
- Never draw a large container labeled `Worked example`, `Example`, or `Calculation` and leave its interior empty. A small section label is optional; the example objects must already be present or enter in the same animation.
- The example must occupy meaningful visual space. At phone scale, its core object group should normally use roughly 45-85% of the safe width and 30-65% of the central safe height, adjusted for the topic.
- A computed state must exist as a persistent visible object, not only in a cue or metadata. Graph relaxations replace the target's visible distance label; Johnson reweighting replaces the visible label on that exact edge; DP updates reveal and retain the solved cell. The final frame must visibly contain the final graph/table state.
- Give every mutable value a stable object ID and an exact before/after snapshot. Renderers must consume those snapshots and preserve object identity through replacement. Never expose implementation sentinels such as `None`, `nan`, `inf`, or `Infinity`; display mathematical `∞` for an unreachable value.

## Text Hierarchy

- Use at most three typographic roles: concept label, beat cue/equation, and local object label. Keep each role visually consistent across the scene.
- Keep the concept label to one line and subordinate it after the opening. It must not compete with the proof object.
- Keep each cue to one idea and at most two short lines. Prefer equations aligned to their visual terms over prose explaining the equation.
- Do not keep hook, title, formula, intuition, section heading, setup, calculation, and takeaway on screen together. Retire text when its referent or beat ends.
- Preserve spaces and mathematical structure. Render matrices/vectors as stacked math objects and animate long formulas in meaningful parts.
- Do not reduce essential text below a phone-readable floor to fix overflow. With the repository's 1080 x 1920 configuration, use approximately 36-48 for titles, 28-36 for equations/cues, and 24 or larger for essential labels; restructure content if it still does not fit.
- Apply those floors after every `fit_in`, width fit, and height fit. If the fitted role is too small, split the copy into successive states and rerun layout; silent shrinking is a render failure.
- Normalize generic takeaway boilerplate in the plan data to a short result claim. Long conclusions must advance through readable stages rather than remaining as one scaled footer.
- Add subtle local backplates only where strokes cross text. A full-width or full-height text panel is not a readability solution.

## Immutable Math And Transit

- Treat titles, theorem statements, equations, node labels, and labeled cards as immutable render layers. Never interpolate a text-bearing VGroup while geometry is moving; animate unlabeled proxy geometry, let it settle, then replace the stationary text atomically.
- Route moving proxies through an explicit empty lane whose segments are checked against occupied object bounds. A source or destination may be highlighted before or after transit, but a duplicate token may not begin on top of its source label, end on top of its destination label, or pass through another labeled row.
- Make a proof-carrying transit visible with a strict causal sequence: orient the viewer, expose or draw the complete checked route, move the proxy, commit the destination state only after arrival, then hold the changed state for inspection. Never reveal the route and move the proxy in the same first instant.
- When two or more candidate values, paths, forces, strategies, or decompositions compete, place them in persistent comparison lanes or a shared spatial frame. Keep every candidate visible through selection, move the winner into the destination, and retire rejected candidates only after the decision is readable.
- Avoid full-table, full-graph, or full-canvas passing flashes for a local result. Focus the exact winning cell, path, region, or relation instead; global emphasis destroys causal locality and can mask overlap or timing defects.
- Retire transit proxies with a brief coherent fade in the empty lane; abrupt removal reads as a one-frame tear in dense review.
- Render symbolic relations with MathTex. If the TeX backend is unavailable, use an explicit Unicode formatter for Greek letters, composition, congruence, set/quotient notation, subscripts, and superscripts. Stripping backslashes is forbidden.
- Block the render if any visible math fallback contains a backslash command, raw underscore syntax, command braces, or residues such as text, mathrm, circ, cong, operatorname, mathbb, or pmod.
- Keep proof/title safe zones immutable for the complete scene. A title losing glyphs, width, or submobjects during another animation is a render failure.
- Stop a repeated-operation proof at the first mathematically decisive return. Do not run a second cycle after g^n=e, an additive return to zero, or an order result has already been established.

## Phone-Safe Layout

- Use vertical `config.pixel_width = 1080`, `config.pixel_height = 1920`, `frame_width = 9`, and `frame_height = 16`.
- Keep critical content within approximately `x = [-4.0, 4.0]` and `y = [-7.2, 7.2]`. Treat captions or platform overlays as additional reserved space when they will be burned in.
- Use `safe_place` and `avoid_layout_collisions` for all text and major visual groups. Register labels, formulas, section markers, and diagrams; boundary checks alone are insufficient.
- Give the proof object the central field. Avoid a stack of horizontal text bands that leaves a small illustration in the middle.
- Labels must remain visually attached to their referents throughout motion. Use updaters, braces, leader lines, or repositioning; never leave a label behind after its object moves.
- Clear prior text before reusing its region. No arrows, axes, curves, grids, or panel borders may cross essential glyphs.
- A decorative panel may not dominate the safe frame. Any rectangle covering more than about 35% of the safe area must itself encode the mathematical domain or state, be populated when introduced, and change with the beat. Giant empty panels are a blocking defect.
- Measure the central explanatory lane separately from title, formula, and cue bands. A sparse title and cue cannot compensate for a shallow diagram. Enlarge the complete persistent diagram uniformly within its reserved lane, applying the same transform to every state and path, and reject sustained central content below the lane occupancy contract.
- Use the shared portrait roles: title `y=6.45..7.55`, cue/formula `y=4.75..6.25`, core proof `y=-4.20..4.50`, and evidence/result `y=-6.35..-4.45`, with about 8.1 units of safe width. Measure the core without detached labels or evidence: target width occupancy `0.78..0.97`, height `0.68..0.95`, area at least `0.48`, occupied rows at least `0.55`, and occupied columns at least `0.60`.
- If uniform scaling cannot satisfy both core dimensions, request semantic reflow or staging. Never count title, cue, formula, or evidence islands toward core occupancy, and rerun collision/path checks after every reflow.
- Every route must register exactly one proof surface with separately identified core geometry, attachments, and evidence, plus a `uniform`, `plot`, or `stacked` reflow strategy. Finalization must measure only currently visible core geometry, perform any required rebuild, remeasure, and raise if occupancy, lane, or collision postconditions remain unresolved. Opacity-zero future objects never count toward construction bounds.
- Treat cue replacement as an atomic lane transaction. Never crossfade two text objects in the same cue/evidence lane; remove the outgoing page before introducing the incoming page, or move the pages through spatially disjoint lanes. Check role collisions throughout the handoff and again after portrait reflow.

## Domain Specificity

Choose a representation that exposes the topic's operation:

- Linear algebra: planes, vectors, bases, projections, transformed grids, eigendirections, areas, and row/column contributions.
- Calculus: moving points and secants, accumulated regions, slope fields, changing approximations, and limits.
- Physics: persistent bodies, force/field vectors, trajectories, energy transfers, and wave state.
- CS: arrays with changing indices, graphs with frontier/visited state, trees, automata, stacks, queues, and complexity curves.
- Algebra/group theory: operation cycles, coset partitions, homomorphism mappings, symmetry actions, roots, and quotient collapse.
- Economics: persistent axes/curves, shifting constraints, price wedges, quantity changes, payoff comparisons, and surplus regions.

Do not route a concept to a numeric input-rule-output diagram when a domain representation can show the mechanism. Group theory and economics must use domain-specific renderers. A theoretical concept still requires a small concrete proof object or counterexample.

## Silent Video Contract

- `--voice-engine none` is a complete final mode, not a draft fallback. Missing audio is expected for this mode.
- The MP4 must stand alone without narration. Sparse labels, equations, object correspondence, timing, and motion must expose every essential reasoning step.
- Do not include phrases that refer to speech, such as “as explained” or “listen for.” Do not rely on SRT captions to supply a missing visual step.
- Scripts and SRT files remain required metadata and timing aids, but the scene is authored as silent-first. Optional later narration must not be necessary for comprehension.
- Do not force a one-minute cap. Use the time needed for state changes and readable holds, without filler emphasis loops.
- Preserve the semantic plan as an independent timing contract. A specialized renderer may not overwrite the planned duration with its shorter raw runtime. Production rendering must fail on a material plan/render mismatch so the route is repaired with meaningful choreography rather than a cloned still-frame tail.

## Evidence-Based Visual QA

Automated metrics can flag blank, static, crowded, or edge-heavy frames, but clean metrics do not prove visual storytelling. A scene passes only with rendered temporal evidence.

For every scene:

1. Inspect the contact sheet at its 270-pixel thumbnail width and the full rendered frames.
2. Record opening, pre-action, post-action, example-intermediate, and final timestamps. Add both sides of every major planned transformation, then inspect the complete video at intervals no larger than 0.25 seconds so mid-transition label collisions and partial glyph loss cannot hide between checkpoints.
3. For each of the four required state changes, identify one persistent object visible in both frames and state exactly what changed: position, shape, value, grouping, correspondence, measure, or parameter.
4. Confirm the concept-to-example transition retains or visibly hands off the continuity spine. A blank frame, full reset, or unrelated replacement fails.
5. Confirm the worked example has visible content in setup, intermediate, and result frames; no large region is an empty labeled shell.
6. Confirm at phone size that essential text is readable, hierarchy is obvious, labels track objects, and nothing overlaps or crosses glyphs.
7. Scrub the video around each transformation. Contact sheets alone may miss a brief glitch or a fake motion sequence made only of fades.
8. For every computed or selected result, verify five ordered frames: readable source state, visible evidence or route, effect in transit, committed destination, and stable result. A commit that precedes its cause fails even if all five ingredients appear somewhere in the scene.

Reject and rerender when any of these are true:

- the same meaning would survive if the frames were rearranged as static cards
- two consecutive semantic beats change only text or emphasis
- setup objects disappear and unrelated result objects appear without a handoff
- the example jumps from setup to answer with no visible intermediate
- the title, prose, or an empty panel is more prominent than the proof object
- frame metrics pass but rendered frame pairs do not show the planned object-state changes
- a title or persistent equation is partially erased, shredded, or ghosted in any transition frame
- labeled cards, node copies, or formula boxes travel through occupied labels or stack on their source/destination
- visible text contains raw TeX residue such as S_n, text, mathrm, circ, cong, command braces, or a backslash command
- a repeated-operation route continues through a redundant second cycle after the first return already proves the result

## Output

- Fingerprinted plans in `runs/<course>/animation_plans/` and `animation_plan_index.json`
- Manim Python files in `runs/<course>/scenes/`
- Markdown scripts in `runs/<course>/scripts/`
- SRT captions in `runs/<course>/captions/`
- Rendered contact sheets and `visual_frame_audit.json` as QA evidence
- Hash-bound temporal observations and reviewer verdicts in `visual_review.json`
