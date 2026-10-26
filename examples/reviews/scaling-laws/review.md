---
title: Neural scaling laws, from power laws to compute-optimal training
author: Course to Shorts example
---
# Neural scaling laws, from power laws to compute-optimal training

A short literature review of how the field learned to predict a model's loss from its size, its
data and its training compute, and how its advice on spending a fixed compute budget changed.

## Error falls as a power law

Hestness et al. (2017) trained models of increasing size on growing slices of data in four domains
(machine translation, language modelling, image classification and speech recognition) and found
that generalization error falls as a power law in training-set size, with exponents between about
−0.07 and −0.35 depending on the task. On a log–log plot the learning curve is a straight line, so
small experiments predict large ones. Rosenfeld et al. (2019) extended this to a single functional
form in both model size and data size, fitted on small runs and used to predict error at larger
scales.

## Language models: bigger models, stopped early

Kaplan et al. (2020) measured the test loss of Transformer language models over more than seven
orders of magnitude and found three clean power laws: in the number of non-embedding parameters
N (exponent about 0.076), in the dataset size D (about 0.095) and in training compute C (about
0.050). Their fit for compute-efficient training said that as the budget grows, most of it should
go into model size: the optimal N grows roughly as C^0.73 while the data grows far more slowly.
The practical advice was to train very large models and stop well before convergence.

## Compute-optimal training: scale data with the model

Hoffmann et al. (2022) revisited the question with over 400 models, from 70 million to over 16
billion parameters trained on 5 to 500 billion tokens, and with learning-rate schedules matched to
each run's length. Three separate estimation methods agreed that parameters and training tokens
should grow in equal proportion, N ∝ C^0.5 and D ∝ C^0.5, using the standard estimate C ≈ 6ND
floating-point operations. They tested the prediction directly: Chinchilla, a 70-billion-parameter
model trained on 1.4 trillion tokens, used about the same compute as the 280-billion-parameter
Gopher trained on 300 billion tokens, and outperformed it. The ratio behind Chinchilla, about 20
training tokens per parameter, became a common rule of thumb.

## Checking and reconciling the fits

Besiroglu et al. (2024) re-fitted the third of Hoffmann et al.'s methods from data extracted from the
paper's figures and found the published fit inconsistent with the other two methods and its
confidence intervals implausibly narrow; their corrected fit agrees with the equal-scaling result.
Pearce and Song (2024) traced most of the gap between Kaplan's and Hoffmann's advice to Kaplan
counting only non-embedding parameters and fitting at small scale; correcting for both recovers
coefficients close to Chinchilla's.

## Beyond training compute

Compute-optimal training minimises the cost of training alone. Sardana et al. (2023) added the
cost of serving the model: when a model will answer many requests, it pays to train a smaller
model on more tokens than the Chinchilla ratio suggests, trading extra training compute for cheaper
inference.

## References

- Hestness, J., Narang, S., Ardalani, N., et al. (2017). Deep Learning Scaling is Predictable, Empirically. arXiv:1712.00409
- Rosenfeld, J. S., Rosenfeld, A., Belinkov, Y., and Shavit, N. (2019). A Constructive Prediction of the Generalization Error Across Scales. arXiv:1909.12673
- Kaplan, J., McCandlish, S., Henighan, T., et al. (2020). Scaling Laws for Neural Language Models. arXiv:2001.08361
- Hoffmann, J., Borgeaud, S., Mensch, A., et al. (2022). Training Compute-Optimal Large Language Models. arXiv:2203.15556
- Sardana, N., Portes, J., Doubov, S., and Frankle, J. (2023). Beyond Chinchilla-Optimal: Accounting for Inference in Language Model Scaling Laws. arXiv:2401.00448
- Besiroglu, T., Erdil, E., Barnett, M., and You, J. (2024). Chinchilla Scaling: A replication attempt. arXiv:2404.10102
- Pearce, T., and Song, J. (2024). Reconciling Kaplan and Chinchilla Scaling Laws. arXiv:2406.12907
