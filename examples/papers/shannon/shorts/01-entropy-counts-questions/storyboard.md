# Entropy counts yes/no questions
source:     C. E. Shannon, "A Mathematical Theory of Communication", Bell System Technical Journal, 1948 (Sections 6 and 10; Section 10 uses this exact four-letter source)
claim:      Entropy is the average number of well-chosen yes/no questions needed to pin down the outcome; an outcome of probability p costs log2(1/p) questions, so H = sum p log2(1/p).
example:    A, B, C, D with chances 1/2, 1/4, 1/8, 1/8. Ask "A?", then "B?", then "C?": 1, 2, 3, 3 questions.
            Average 1/2*1 + 1/4*2 + 1/8*3 + 1/8*3 = 7/4 = 1.75. Code A=0, B=10, C=110, D=111 (yes=0, no=1).
            Message AAAABBCD -> 14 bits, vs 16 with two halving questions per letter.
objects:    a probability bar (4 coloured blocks, widths 4:2:1:1) along the bottom of the stage;
            a staircase question tree (nodes "A?", "B?", "C?"; leaves A, B, C, D) filling the left/top;
            a running-sum column on the right (p x questions rows, total 1.75);
            a credit plate (author, title, year) at the top of the stage.
layout:     credit plate across the top of STAGE (y 4.1..4.8); tree in x -4..0.6, y 3.6..-1.0;
            sum column x 1.0..4.0, y 3.4..-0.6; bar y -1.5..-2.6 full width.
            Message beat: tree and bar fade, credit stays; message row + 14-cell and 16-cell strips fill the stage.
invariant:  the four coloured letters keep their colour (A blue, B orange, C purple, D green-ish) on bar, leaves, sum rows, code and message cells.
reveal:     H = sum p log2(1/p) = 1.75 bits, stated after the tree and the sum produced 1.75.

| beat | narration (spoken) | picture (what moves) |
|------|--------------------|----------------------|
| hook | Guess a hidden letter using only yes or no questions. How few questions can you get away with, on average? | probability bar of A B C D appears with the title |
| source | Claude Shannon's 1948 paper, A Mathematical Theory of Communication, uses this source: A comes up half the time, B a quarter, C and D an eighth each. | credit plate fades in; fractions write into the blocks |
| first | So ask about the likeliest letter first. Is it A? Half the time, one question settles it. | root node "A?" grows; yes-edge to leaf A; A's block lights, badge 1 |
| deeper | If not, ask: is it B? And then: is it C? B takes two questions, while C and D take three. | B?, C? nodes and leaves B, C, D grow down the staircase; badges 2, 3, 3 |
| average | Weight each count by its chance: one half times one, a quarter times two, an eighth times three, twice. That adds up to one point seven five. | four product rows fly from blocks/badges into the right column; total counts up to 1.75 |
| surprise | Notice the pattern: a letter with chance one over two to the k needs exactly k questions. That count is its surprise, log base two of one over p. | bar fractions swap to 2^-1, 2^-2, 2^-3; exponents highlighted beside badges |
| formula | Averaging the surprise gives Shannon's entropy: H is the sum of p times log two of one over p. Here, one point seven five bits. | sum column morphs into H = sum p log2(1/p) = 1.75 bits |
| code | Write each answer as a bit, yes as zero and no as one, and the questions become a code: A is zero, B is one zero, C is one one zero, D is one one one. | edge labels yes/no turn into 0/1; codewords slide out next to leaves |
| message | A typical message, four A's, two B's, a C and a D, takes fourteen bits. Two questions for every letter would take sixteen. | tree shrinks to a corner; 8 letters drop into codeword cells (14), a 16-cell muted strip below; counters |
| takeaway | Entropy is the average number of yes or no questions the best strategy needs. Likely letters cost few bits, rare ones cost more. | strips stay; final formula plate with 1.75 bits highlighted |

risks: tree + column crowding on 9:16 (keep the column narrow, fractions large); the sum
column must not overlap the C?/D edge; message strips need the full width, so the tree shrinks
first; bar fractions must stay legible in the 1-unit-wide C and D blocks.
