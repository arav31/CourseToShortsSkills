# How lemons empty a car market
claim:      When buyers cannot see quality they pay for the average car, so the best cars withdraw, the average falls, and the market unravels until only the lemon trades.
example:    Owners value four cars at $1k, $7k, $10k, $14k; buyers value any car at 1.5x its owner's value but cannot tell them apart, so they offer 1.5 x the average of the cars still for sale. Rounds: avg 8 -> offer 12 ($14k leaves); avg 6 -> 9 ($10k leaves); avg 4 -> 6 ($7k leaves); only the $1k lemon is left, offer 1.5, it sells. Full information: all four trade, gains 0.5 x 32 = $16k; hidden quality: $0.5k. (checks/examples.py)
objects:    a bar chart on a $-thousand axis: four blue bars (owner values) with car icons and value labels underneath; green "gain" caps from v to 1.5v; a blue dashed average line and a yellow offer line with plated labels on the right; a two-line readout band at the top of the stage.
layout:     readout band = top ~1.1 units of STAGE; chart fills the rest (baseline y=-1.55, 22k at y~3.6); bars at x=-2.5..1.1; line labels in the right margin x~2.7; in the loss beat the right margin holds two gain stacks ("seen" vs "hidden").
invariant:  the four bars never change height (owners' values are fixed); only the average line, the offer line and which bars are still for sale move.
reveal:     "price follows the average, so the bad drive out the good" - offer = 1.5 x average of cars still for sale, after three rounds of unravelling.

| beat | narration (spoken) | picture (what moves) |
|------|--------------------|----------------------|
| hook | Four owners sell used cars; every buyer values each car more than its owner. Why do the good cars never sell? | bars grow with icons and $ labels; green gain caps grow on top of each bar |
| source | Akerlof's 1970 paper The Market for Lemons: owners know their car, buyers can't tell them apart. | citation plate in the readout band; grey "buyer's view" ghosts of all four bars squash to one height (the average) with "?" on each |
| average | Buyers pay for the average car: average 8, times one and a half = 12. | ghosts collapse into the blue avg line at 8; a copy rises to the yellow offer line at 12; readout shows the arithmetic |
| round1 | The $14k car is worth more than 12 to its owner: she keeps it. | 14 bar flashes red above the offer line, then greys out |
| round2 | Average of the rest 6, offer 9, the $10k car leaves. | avg line slides 8->6, offer 12->9, readout swaps, 10 bar greys |
| round3 | Average 4, offer 6, the $7k car goes. | same motion, 7 bar greys |
| lemon | Only the $1k lemon is left; buyers offer 1,500; it's the only car that sells. | avg->1, offer->1.5; 1 bar turns red, "sold" tag |
| loss | With quality visible all four would sell: $16k of gains. Hidden quality: $500. | lines fade; green caps of all four bars fly into a "seen" stack (16 tall on the same axis); only the lemon's cap forms the "hidden" stack (0.5) |
| takeaway | Adverse selection: price can only follow the average, so the bad cars drive out the good. | readout band shows offer = 1.5 x average of cars for sale; small citation |

risks: the 1k bar is tiny (0.24 units) - its label sits below the baseline like all others; lines crossing value labels - labels live below the baseline, line labels in the right margin; on-screen prose - only the citation and two stack captions.
