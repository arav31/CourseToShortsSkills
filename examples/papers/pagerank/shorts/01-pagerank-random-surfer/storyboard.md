# PageRank: the random surfer
claim:      A page's PageRank is the long-run share of time a random surfer spends on it, so one link from a busy page can beat many links from quiet ones.
example:    Pages A, B, C, D; links A->B, A->C, B->C, C->A, D->C; d = 0.85, N = 4 (3.75% per page from random jumps).
            Start 25% each. Tick 1: A 25%, B 14.4%, C 56.9% (= 0.85 x (12.5 + 25 + 25) + 3.75), D 3.75%.
            Settles (about tick 12) at A 37.3%, B 19.6%, C 39.4%, D 3.75% -> shown as 37 / 20 / 39 / 4.
            Verified in runs/paper-pagerank/checks/examples.py (power iteration, exact fractions, 1M-step simulated surfer).
objects:    4 page boxes at the stage corners (A top-left, B top-right, C bottom-right, D bottom-left) that FILL with
            their share of the crowd (box full = 60%), percent label outside each box; 5 straight link arrows (A<->C as two
            parallel diagonals); the surfer dot; flow blobs (area ~ amount); a tick counter.
            (v1 used a small circle graph over a separate bar chart; both came out too small, so v2 merged them.)
layout:     graph spans the whole STAGE. Paper credit plate in the centre during the hook, before the arrows exist.
            Tick counter and "15% / 4 = 3.75%" plate in the free gap between A and D (no A-D link).
            Final formula (with 0.15/4 and 0.85 written in) on a plate in the centre band after the arrows fade.
invariant:  the bars always add to 100% (the crowd is never created or destroyed); the graph never changes.
reveal:     PR(p) = 0.15/4 + 0.85 * sum over q->p of PR(q)/(links out of q), stated last (the paper's d = 0.85; the paper writes (1-d) without /N).

| beat | narration (spoken) | picture (what moves) |
|------|--------------------|----------------------|
| hook | In 1998, Sergey Brin and Larry Page asked how to rank every page on the web. Their answer: an imaginary surfer who clicks links forever. | Title + graph appear at once; paper credit plate (authors, year, paper title) fades in below. |
| links | Take four pages and five links. C has three links coming in. A has only one. | Credit fades; C's three incoming arrows light up, then A's single incoming arrow. |
| surfer | On each page the surfer clicks one of its links at random. But fifteen percent of the time, they get bored and jump to any page at all. | Yellow dot hops A->B->C->A along arrows; then vanishes and reappears on D (teleport), hops D->C. |
| crowd | Now swap the one surfer for a crowd, with a quarter of it on each page. | Bars grow to 25% each with labels; tick counter "tick 0". |
| tick | Each tick, eighty-five percent of every crowd follows the links, split evenly. The other fifteen percent scatter evenly over all four pages. | Blobs (area ~ amount) leave each node and travel along its out-arrows; "15% -> 3.75% each" plate; tiny drops land on all 4 nodes. |
| step | After one tick, C holds fifty-seven percent: half of A's crowd, plus everyone from B and D. | Bars move to 25 / 14 / 57 / 4; C's bar and its three incoming arrows highlighted. |
| settle | Keep ticking. The shares swing, then settle: A thirty-seven, B twenty, C thirty-nine, D four percent. Those shares are PageRank. | Ticks 2..12, bars swing and settle; counter runs; final values land on the spoken numbers. |
| insight | Look at A. It has one link in, yet almost ties C, because that link comes from C, the busiest page, and C sends A everyone. | A's incoming arrow C->A turns green and thick; bars A and C outlined side by side. |
| lonely | D has no links in, so it only ever gets the random jumpers. | D node and its 4% bar outlined in red. |
| takeaway | So a link is a vote, worth the voter's own rank, split among all its links. | Graph dims; PageRank formula plate fades in over it; bars stay. |

risks: graph + bars could feel like two small pictures -> make the graph wide (nodes at the stage edges) and bars tall.
       Curved A<->C arrows may cross labels -> no labels on arrows. Flow blobs could look decorative -> blob area proportional to amount.
       Paper-title text is long -> SMALL size, wrapped, shown only during the hook.
