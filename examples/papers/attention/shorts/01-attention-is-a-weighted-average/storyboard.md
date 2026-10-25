# Attention is a weighted average
source:     "Attention Is All You Need", Vaswani, Shazeer, Parmar, Uszkoreit, Jones, Gomez, Kaiser, Polosukhin (2017), section 3.2.1
claim:      Scaled dot-product attention scores each key against the query, softmaxes the scaled scores into weights that sum to one, and outputs the weighted average of the values.
example:    "the cat sat", d_k = 2. q(sat) = (1, 2). keys the (1,0), cat (1,1), sat (0,1).
            scores 1, 3, 2 -> / sqrt 2 -> 0.71, 2.12, 1.41 -> softmax 0.14, 0.58, 0.28 (sum 1).
            values the (4,0), cat (4,4), sat (0,4) -> output ≈ (2.9, 3.4), nearest cat. (checks/examples.py)
objects:    three token cards (word + key; sat also shows its query); three bars, one under each card;
            a value plane with three value points and a green output point built tip to tail.
layout:     cards across the top of STAGE; bars in the middle band, each under its card; bottom band:
            working equation on a plate (beats 4-6), then the value plane (left) + readout (right).
invariant:  the same three cards and the same three bars persist; bar heights change meaning
            (score -> scaled score -> weight) but each bar stays under its word.
reveal:     softmax(Q K^T / sqrt(d_k)) V, stated last, with each part coloured as it was used.

| beat | narration (spoken) | picture (what moves) |
|------|--------------------|----------------------|
| hook | When a Transformer reads the word sat, how does it decide which other words matter? | three cards fade in with empty bar baseline; sat card outlined |
| paper | This is the core idea of the 2017 paper Attention Is All You Need, by Ashish Vaswani and seven colleagues. | citation plate in the bottom band |
| keys | Sat sends out a query, the vector one, two. Every word, sat included, holds up a key. | q tag grows on sat card; key vectors write under each word |
| scores | Multiply query and key entry by entry and add. That dot product scores each word: one, three and two. | worked q·k for cat on a plate; bars grow to 1, 3, 2 with labels |
| scale | Then divide every score by the square root of two, the key length, so the numbers stay tame. | bars shrink to 0.71, 2.12, 1.41; plate shows ÷ √2 |
| softmax | A softmax turns the scores into weights that are positive and add up to one: point one four, point five eight, point two eight. | bars morph to weight bars (green), labels 0.14 0.58 0.28, "sum = 1" |
| values | Each word also carries a value. Here, three points: four zero, four four, and zero four. | plate clears; value plane with three labelled points |
| blend | The output is the weighted average of the values: a little the, mostly cat, some sat. It lands near two point nine, three point four. | three scaled value arrows chain tip to tail from the origin, each lit as its bar is; output dot at the end |
| takeaway | That is attention: compare the query with every key, scale, softmax, and average the values. | formula softmax(QKᵀ/√d_k)V on a plate in the readout |

risks: three rows on a 7.5-unit stage may crowd: keep cards short (word + key only, q on sat);
the bottom band is empty in beats 1-3 (stage_fill): draw bar baseline and slots from the hook.
Too many decimals on screen: two decimals for weights, one for the output.
