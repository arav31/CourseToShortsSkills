# BFS grows level by level
claim:      BFS builds level L_i from the unvisited neighbours of L_(i-1), so a vertex's level is exactly its distance from s.
example:    Lecture 9, Example 3 (undirected): Adj(s)=[a,c], Adj(a)=[s,b], Adj(b)=[a], Adj(c)=[s,d,e],
            Adj(d)=[c,e,f], Adj(e)=[c,d,f], Adj(f)=[d,e], Adj(g)=[]. Levels L0={s}, L1={a,c}, L2={b,d,e},
            L3={f}, L4 empty; g unreachable (infinity). Parents a,c<-s; b<-a; d,e<-c; f<-d.
            8 edges, 16 adjacency checks (running count 2, 4, 7, 8, 11, 14, 16). Only d-e lies inside a level.
objects:    one 8-vertex graph (circles + letters + a distance tag beside each vertex, "?" until found);
            a strip of level rows L0..L3 (label + three rounded cells each) that fills with vertex chips;
            an "edge checks" counter (and "L4 = empty" under it at the stop); at the end four level
            guide lines and a two-line formula panel.
layout:     algorithm phase: graph fills the top 55% of STAGE (y 0.5..4.6, full width) in a map-like,
            non-layered drawing (s centre-left, b bottom-left, f centre-right, g alone bottom-right); every
            distance tag ("?" until found) sits on a side of its vertex that no edge leaves from. Level rows
            L0..L3 bottom-left of STAGE (y -2.65..0.3), drawn once in level0; counter column bottom-right.
            Reveal phase: the strip dissolves and the graph re-lays itself on four level guide lines over
            the whole stage, every distance tag above its vertex (g below-right, below every level, tag
            left); formulas in a band at the bottom of STAGE (y -1.35..-2.65). Caption band empty.
invariant:  the same eight vertex objects, eight edge objects and distance tags are carried through
            every beat; each edge object keeps its colour (muted / green tree edge) as it moves.
reveal:     layered drawing (every edge spans at most one lane), then
            L_i = { v in Adj(L_(i-1)) : v unvisited },  delta(s, v) = i for v in L_i,  cost 2|E| = 16 -> O(|V|+|E|).

colour:     s blue (input); frontier rings + check flashes yellow (operation now); discovered vertices,
            distance tags, chips, tree edges green (final); rejected checks and unreachable g red;
            untouched vertices and edges muted.

| beat | narration (spoken) | picture (what moves) |
|------|--------------------|----------------------|
| hook | How far is every vertex from s? And can some vertex never be reached? | title + graph appear at once; a muted "?" tag fades in beside every vertex; s pulses blue |
| level0 | Level zero is just s, at distance zero. | the four level rows slide in; s's "?" becomes green 0; chip s drops into L0 |
| level1 | Level one is every unvisited neighbour of level zero, at distance one. | yellow ring on s and outline on row L0; counter appears; s->a, s->c flash yellow (counter 2); both turn green with 1, parent edges thicken green, chips drop into L1 |
| level2 | Level two grows only from level one. Edges back to s are rejected; b, d and e are new. | rings move to L1; from each frontier vertex every adjacency is flashed: back to s red (rejected), to b / d / e yellow -> green 2, tree edges thicken, chips into L2 (counter 4, 7) |
| level3 | Level three: only f is new, found from d. Every other edge, even e to f, is rejected. | rings on b, d, e; b->a red; d->c, d->e red, d->f yellow -> f green 3; then e->c, e->d, e->f all red because f is already placed (counter 8, 11, 14) |
| stop | Level four is empty, so we stop. g was never reached: its distance is infinity. | ring on f; f->d, f->e red (counter 16); "L4 = empty set" appears under the counter; rings clear; g turns red, "?" becomes infinity |
| layers | Slide each vertex into its level. No edge skips a level; only d to e stays inside one. | strip and tags dissolve; row labels spread to four guide lines; vertices slide onto their level carrying their edges; tags return above each vertex; g drops below every level; the d-e edge (the one same-level edge) lights yellow |
| proof | So reaching f takes at least three edges, and the green tree path uses exactly three. | the tree path s-c-d-f is traced edge by edge in yellow, each step lighting the next lane label; f's tag 3 is outlined |
| cost | The cost: eight edges, each checked from both ends, so sixteen checks. Linear time, order V plus E. | all 16 checks replayed as flashes along each edge from both ends; counter 16 swaps for 2|E| = 2*8 = 16, then O(|V|+|E|) |
| rule | Each level is the unvisited neighbours of the level before, and a vertex's level is its distance. | formula panel swaps to L_i = Adj(L_(i-1)) minus visited; the tree edges flash level by level (L0->L1, L1->L2, L2->L3); then v in L_i => delta(s,v) = i; final layered picture holds |

risks: crowding (8 tags + 5 rows + counter) -> tags sit in each vertex's free direction, the strip uses
only the left half, the counter the right half; flashes are simultaneous per frontier vertex so the
level beats stay inside their narration; vertices crossing during the slide -> check frames
mid-transition; the word "a" is never spoken (levels are narrated instead); every count in the
narration is asserted against the BFS run in scene.py.
