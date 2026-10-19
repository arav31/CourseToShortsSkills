# Positive test, only 9%?

claim:      With a rare disease, a positive result is mostly false alarms: of everyone who tests
            positive, only about 9% are actually sick, because 9% of the many healthy people
            outnumber 90% of the few sick ones.
example:    Prevalence 1%, sensitivity 90%, false-positive rate 9%. In 1000 people: 10 sick,
            990 healthy; 9 true positives, 0.09 x 990 = 89.1 (about 89) false positives;
            98 positives, 9/98 = 9.18%. Exact: P(D|+) = 0.009 / 0.0981 = 10/109 = 9.17% (both 9.2%).
objects:    a 40 x 25 grid of 1000 dots (people; red = sick, blue = healthy); a yellow-outlined
            "tested positive" tray that collects the positives (red 3x3 block + blue block);
            count labels; three equation rows (counts, probabilities, theorem).
layout:     counters band at the top of STAGE (y ~ 4.5); grid fills the stage width (y 4.1 .. -0.9);
            tray sits below the grid at the left (y -1.15 .. -2.6) with its labels to its right.
            After conditioning, the negatives leave, the tray moves up and grows (y ~ 4 .. 2),
            and the equation rows stack underneath it.
invariant:  every dot is one person and keeps its colour (true health) the whole time; positives
            move, they never change colour. The 9 red + 89 blue in the tray are the same dots that
            left the grid.
reveal:     P(D | +) = P(+ | D) P(D) / P(+), shown after the counting and the probabilities.

| beat | narration (spoken) | picture (what moves) |
|------|--------------------|----------------------|
| hook | You test positive for a rare disease, with a test that catches ninety percent of cases. So why is your chance of being sick only about nine percent? | title; grid of 1000 dots sweeps in; "1000 people" counter |
| prevalence | Picture a thousand people. The disease affects one percent of them, so just ten are sick. | 10 dots in the top-left corner turn red; counter splits into "10 sick" / "990 healthy" |
| truepos | The test catches ninety percent of the sick, so nine of those ten test positive. | tray + "tested positive" appear; 9 red dots get a yellow ring and fly into the tray (1 stays) |
| falsepos | But it also flags nine percent of healthy people. Nine percent of nine hundred ninety is about eighty-nine more. | 89 scattered blue dots get rings and fly into the tray, swamping the red block; "89 healthy" label |
| condition | Your test was positive, so you are one of these ninety-eight people. Only nine of them are sick: about nine percent. | the negatives fade out; tray moves up and grows; 9/(9+89) ≈ 9.2% appears under it |
| probs | In probabilities, the nine is ninety percent of one percent. The eighty-nine is nine percent of the other ninety-nine percent. | probability fraction appears under the count fraction, same colours, same 9.2% |
| bayes | That is Bayes' theorem: the chance of disease given a positive is the true positives over all the positives. | general formula P(D|+) = P(+|D)P(D)/P(+) appears last; outline on numerator / denominator |
| takeaway | When a disease is rare, false alarms from the many healthy people can outnumber the few real cases. | outlines on the blue block and the blue term of the denominator |

risks:
- 1000 dots could look like noise: the sick ones are a tight 2x5 block in a corner so "ten" is countable,
  and the positives physically leave the grid so the comparison is a comparison of two blocks.
- 89 is a rounded 89.1: narration says "about eighty-nine"; exact Bayes on screen gives the same 9.2%.
- Three equation rows plus the tray is a lot of stage: rows are measured (count 3.2 wide, probs 7.0,
  theorem 6.2 at body size) and the tray is scaled to leave ~4.5 units below it.
- Dots flying from the grid to the tray must not hide behind other dots: raise their z-index.
- Narration numbers are a literal (BEATS cannot be f-strings): assert the computed counts match.
