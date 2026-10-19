# Circle in, ellipse out  (s05, svd-circle-to-ellipse)

claim:      Every matrix sends some perpendicular pair of unit arrows v1, v2 to a perpendicular
            pair sigma1 u1, sigma2 u2; that pair is why the circle's image is an ellipse, and it is
            the SVD A = U Sigma V^T.
example:    A = [[6, 8], [-4, 3]]. Axes: A(1,0) = (6,-4), A(0,1) = (8,3), dot 48 - 12 = 36 (skewed).
            v1 = (0.6, 0.8), v2 = (-0.8, 0.6): A v1 = (10, 0), A v2 = (0, 5) (perpendicular).
            sigma1 = 10, sigma2 = 5;  Sigma V^T = A, U = I.  (A^T A eigenvalues 100, 25; |det A| = 50.)
objects:    top-left: input plane (grid step 0.5) with the unit circle (blue) and a perpendicular
            pair of unit arrows (blue) carrying a right-angle marker;
            bottom: output plane (grid step 1) with the image ellipse (green) and the image pair
            (red while skewed, green once perpendicular) with a live angle arc / right-angle marker;
            top-right: equation column (A in yellow, live dot-product readout, then values).
layout:     STAGE split: input panel x in [-4.1, -0.45], y in [1.5, 4.8]; equation column
            x in [-0.25, 4.1], same rows; output panel full width, y in [-2.7, 1.3].
            Unit circle radius ~1.1 units on screen; ellipse ~7.1 x 3.6 units.
invariant:  the input pair always stays perpendicular (marker rotates with it); the circle and
            ellipse stay put; the image pair is always A applied to the input pair.
reveal:     A v_i = sigma_i u_i, i.e. A = U Sigma V^T, with the numbers
            [[6,8],[-4,3]] = I * diag(10,5) * [[0.6,0.8],[-0.8,0.6]].

| beat | narration (spoken) | picture (what moves) |
|------|--------------------|----------------------|
| hook | Feed a matrix every arrow on a circle. However messy the matrix, out comes a clean ellipse. Why? | Title plays with the input panel: circle + 16 spokes grow, A appears (yellow); at "messy" a copy of circle and spokes travels down and morphs, point by point, into the ellipse and the image spokes (green). |
| axes | Take A with rows six, eight and minus four, three. The two axis arrows land on its columns. | Spokes fade; yellow outline steps over row 1 then row 2 of A as they are read; v1=(1,0), v2=(0,1) grow with a right-angle marker; copies travel down to A v1=(6,-4), A v2=(8,3) in red; red outlines on A's two columns + red coordinate labels. |
| skew | Those images are no longer perpendicular: their dot product is forty eight minus twelve, thirty six. | Red angle arc between the images; readout A v1 . A v2 = 48 - 12 = 36 writes in the equation column. |
| turn | Now turn the pair. A quarter turn swaps their roles, so the dot product flips to minus thirty six. | Readout collapses to a live number; ValueTracker turns the input pair 0 -> 90 deg (marker turns with it); images sweep round the ellipse, arc widens, number runs 36 -> 37 -> -36; faint red ghosts keep the skewed pair. |
| zero | So somewhere in between it is zero, for any matrix at all. Here that happens at v one equals point six, point eight. | Pair turns back to 53.13 deg; number lands on 0; images and number turn green, arc becomes a green right-angle marker; at "happens" the readout gives way to v1 = (0.6, 0.8), v2 = (-0.8, 0.6). |
| land | Their images, ten, zero and zero, five, are perpendicular too: the long and short axes of the ellipse. | A applied again one arrow at a time: copy of v1 travels down onto (10, 0), copy of v2 onto (0, 5), green labels appear; ghosts fade at "perpendicular"; dashed green completes the long and short axes at "long". |
| why | Any arrow on the circle is a mix of v one and v two, so its image is the same mix of the two axes. That traces an ellipse. | x = c v1 + s v2 then A x = c A v1 + s A v2 in the column; a point runs once round the circle with dashed components along v1, v2; its image runs round the ellipse with components along the axes, tracing a bright green path. |
| reveal | Ten and five are the singular values, and in matrix form this is the singular value decomposition: A equals U Sigma V transpose. | sigma1 = 10, sigma2 = 5 label the semi-axes; at "matrix" the input panel and column fade and [[6,8],[-4,3]] = I diag(10,5) [[0.6,0.8],[-0.8,0.6]] appears; at "A equals" A = U Sigma V^T is written beneath it. |

risks: two panels at different scales (circle radius 1 vs ellipse 10 x 5) could hide that the
ellipse is the circle's image -> the hook morphs the actual circle point by point into it and every
image arrow travels from top to bottom; the live dot-product readout needs many LaTeX numbers ->
pre-compile -38..38 in one batch; moving labels could hit the ellipse or each other -> labels only
on the input pair (radially outside the circle) during the turn, image labels appear only once
arrows rest; the reveal's 4-matrix product is wide -> give it the whole top band after clearing.
