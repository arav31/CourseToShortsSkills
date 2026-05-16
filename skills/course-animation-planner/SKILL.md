---
name: course-animation-planner
description: Use when planning silent, 3Blue1Brown-level mathematical animations before generating Manim scenes. It turns a concept into visual claims, objects, transformations, and quality checks.
---

# Course Animation Planner

## Purpose

Plan the animation before code generation. The output should make the mathematical idea visible without relying on narration: objects move, deform, match, split, recombine, and reveal the result.

## Visual Story Standard

- Start from the central visual claim, not from a title card.
- Name the mathematical objects that must appear on screen.
- Choose one transformation that carries the proof or intuition: unwrap, project, rotate, shear, stretch, partition, match, collapse, or compare.
- Keep explanatory text sparse and label-like. The visual motion should do the explaining.
- Use color as semantic bookkeeping: input/object, operation/transformation, invariant/result.
- Use at least three meaningful transformations per short before any long hold.
- No voiceover is required. Captions/SRT may exist as metadata, but the MP4 must stand alone visually.
- Prefer proof-style visuals over generic input-rule-output diagrams when the topic is geometric, algebraic, physical, economic, or computational.

## Planning Checklist

For each short, define:

1. **Claim:** the one sentence the animation should make obvious.
2. **Objects:** concrete shapes, graphs, tables, vectors, states, or diagrams.
3. **Motion Beats:** 4-7 timed transformations that advance the idea.
4. **Invariant:** what stays the same through the motion.
5. **Reveal:** the final formula, theorem, or decision rule.
6. **Failure Check:** what would make the scene feel static, text-only, or generic.

## Examples

- Sphere area: draw sphere/cylinder cross-section, slice latitude bands, project them to cylinder strips, stack strips, reveal `4 pi R^2`.
- Linear map: transform a grid and track basis arrows instead of writing only `Ax`.
- Group quotient: partition elements into cosets, collapse an ideal/normal subgroup block, then show operation on blocks.
- Economics tax: shift supply, show buyer/seller price wedge, quantity drop, and deadweight-loss triangle.
