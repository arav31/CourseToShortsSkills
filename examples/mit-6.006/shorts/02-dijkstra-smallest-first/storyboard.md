# Dijkstra trusts the smallest  (s02, MIT 6.006 Lecture 13)

claim:      With non-negative weights, the unfinished place with the smallest estimate can never be
            improved, so Dijkstra finalizes it (delete_min) and relaxes its roads (decrease_key).
example:    Undirected roads in minutes: Home-Cafe 2, Home-Park 5, Home-Work 10, Cafe-Park 1,
            Cafe-Shop 6, Park-Shop 2, Park-Work 6, Shop-Work 1. Source Home.
            Pop Home 0: Cafe inf->2, Park inf->5, Work inf->10.
            Pop Cafe 2: Park 5->3, Shop inf->8.
            Pop Park 3: back road to Cafe gives 4 (not < 2, no change); Shop 8->5, Work 10->9.
            Pop Shop 5: Work 9->6.   Pop Work 6.
            Parents: Home <- Cafe <- Park <- Shop <- Work, 2+1+2+1 = 6 < 10 (direct road).
            scene.py recomputes all of it (6.006-style loop over every adjacency, ties by place order),
            brute-forces every simple Home-Work route (6 is the unique minimum) and asserts each
            spoken number against the computed values.
objects:    one road map: 5 circles (estimate inside, name label beside), 8 grey roads with weight
            plates beside them (Home-Work drawn as a long arc along the bottom); a priority-queue row
            under the map: a muted "priority queue" row header and 5 rounded cells (place name over
            estimate), kept sorted; later a dashed green boundary around the finished set; at the end
            the green route, the sum and the rule.
layout:     title (44 pt: the default 48 wraps this title) in TITLE_ZONE; map fills the stage width,
            y from about -0.8 to 4.7 (Home/Work low at the sides, Cafe/Shop on top, Park in the middle);
            queue row at y = -2.2 (cells 1.25 tall) spanning the width. Every name stands alone: "Park"
            under its circle with 5 and 6 above their roads, 1 and 2 at different heights in the upper
            face, and the direct road's 10 below the arc. Comparison plates ("4 > 2", "8+2 > 3") go in the
            empty queue slots; the sum and the rule take the queue row once it is empty.
colours:    Home = blue (source); untouched = muted (circle + infinity); touched = white; final =
            green circle, number and queue cell; road being relaxed, its weight and d(u) = yellow, with
            a yellow dot running along the road; the old value struck in red; rejected candidates and
            the direct road at the end red; the boundary and the route green.
invariant:  the same map, the same five circles and the same queue cells persist from the first
            frame to the end; only numbers, colours and cell positions change.
reveal:     d(v) <- min(d(v), d(u) + w(u, v)) and w(u, v) >= 0, after the run has shown both.

| beat | narration (spoken) | picture (what moves) |
|------|--------------------|----------------------|
| hook | The direct road from home to work takes ten minutes. Is there a faster way, and how would you know? | title + whole map fade in together (empty circles, names, weights); on "ten" the Home-Work arc and its 10 turn yellow; on "faster" a yellow flash runs along each of the other seven roads; the arc settles back. |
| guesses | Dijkstra keeps a guess for each place: zero for home, infinity for the rest, in a queue sorted smallest first. | on "guess" a muted ? appears in each circle; on "zero" Home's ? leaves and a blue 0 appears (Home ringed blue); on "infinity" the other four become infinity; on "queue" the row header and five cells appear, each estimate copied down from its circle. |
| home | Take the smallest, home, and lock it in. Then relax its roads: cafe gets two, park five, work ten. | pop: the leftmost cell (Home 0) turns green and leaves as Home turns green, then the queue slides left. On each name: the road, its weight and Home's 0 turn yellow while a yellow dot runs to the neighbour; the old infinity turns red and is struck; old value (circle and cell) leaves, then the new one appears; Work 10 hops left over Shop (Shop dips under it). |
| cafe | Next is cafe, at two. Through cafe, park drops from five to three, and shop gets eight. | pop Cafe; Cafe-Park: 5 struck -> 3; Cafe-Shop: infinity struck -> 8, Shop hops left over Work. |
| why | Why trust park's three? Any other route has to leave the finished places somewhere, and every exit already costs three or more. Roads only add minutes. | yellow ring on Park and outline on its queue cell (both fade in); dashed green boundary drawn around Home and Cafe; on "leave" the four exit roads turn yellow; on "every exit" red rings on Shop (8) and Work (10); on "three" Park's 3 pulses; on "Roads" the exits go grey, a red detour is drawn out through Shop and back along Shop-Park, and "8+2 > 3" appears in the empty queue slots. |
| park | So park is locked in. Its road back to cafe gives four, worse than two, but shop drops to five, and work to nine. | why-marks fade; pop Park. Park-Cafe: yellow dot runs to Cafe and turns red, "4 > 2" appears in the empty queue slots, Cafe's 2 pulses green; then Park-Shop 8 -> 5 and Park-Work 10 -> 9. |
| shop | Shop is next, at five, and work drops to six. Then work comes out last. | pop Shop; Shop-Work 9 -> 6; pop Work; the queue is empty and its header fades. |
| route | Now walk back from work to whoever set each guess: shop, park, cafe, home. Six minutes, not ten. | Work's 6 pulses; on each name the road from the previous place back to that parent is drawn thick green and its weight turns green; on "six" "2+1+2+1 = 6 < 10" appears in the queue row; on "ten" the direct arc and its 10 turn red. |
| rule | That's Dijkstra: lock in the smallest guess, relax its roads, repeat. It only works because no road takes negative minutes. | the sum swaps for d(v) <- min(d(v), d(u) + w(u, v)) (relax part yellow; an outline fades in on "relax"); on "no" w(u, v) >= 0 appears below it; the green route stays above. |

risks:
- crowding: 5 circles + 8 weight plates + names + queue. Weights sit beside their roads (offset so the
  line never crosses the digits); comparison plates only in empty regions; the why beat adds no
  numbers on the map, only rings, highlighted roads, one red detour and one plate.
- superimposed digits: an old value always leaves before its replacement appears; d(u) + w is shown
  by colour and a dot travelling the road, not by flying copies of digits.
- queue swaps colliding: a cell moving left rises 0.62 while the cell it passes dips 0.55
  (cells are 1.15 tall), so they never touch; the pop finishes before the queue slides.
- pace: 8 relaxations + 1 non-improving check in ~25 s; each relaxation is ~1.25 s and cued on the
  spoken place name.
- static tail: the final beat adds the second formula on "no"; the last hold is ~2.5 s.
