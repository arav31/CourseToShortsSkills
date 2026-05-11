#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import math
import os
import re
import shutil
import subprocess
import sys
import textwrap
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAX_FETCH_BYTES = 25_000_000
PDF_TEXT_PAGES = 180
DEFAULT_MAX_PAGES = 160
DEFAULT_MAX_PDFS = 100
DEFAULT_SHORTS = 40
MAX_CRAWL_CANDIDATES = 240
FFMPEG = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
EXTRA_TEX_PATHS = ["/Library/TeX/texbin", "/opt/homebrew/bin", "/usr/local/bin"]
NOTES_GENERATOR_VERSION = "stem-course-notes-v2"



def find_executable(name: str) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    for folder in EXTRA_TEX_PATHS:
        candidate = Path(folder) / name
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


@dataclass(frozen=True)
class Concept:
    name: str
    hook: str
    intuition: str
    formula: str
    prerequisites: list[str]
    misconception: str
    example_setup: str
    example_calc: str
    example_takeaway: str
    application_question: str
    application_answer: str
    visual_type: str


LINEAR_ALGEBRA: list[Concept] = [
    Concept("Vectors and coordinates", "A vector is a quantity with direction, size, and coordinates you can compute with.", "Coordinates tell how much of each basis direction builds the vector.", r"\vec{x}=(x_1,x_2,\ldots,x_n)", ["numbers", "coordinate axes", "arrows"], "A vector is not just an arrow drawing; coordinates depend on the chosen basis.", "Let v = (3, 4), meaning 3 steps east and 4 steps north.", "Length = sqrt(3^2 + 4^2) = sqrt(25) = 5.", "Coordinates tell direction; length tells straight-line size.", "A drone moves 3 meters east and 4 meters north. What is its displacement vector and length?", "Use (3, 4); the length is 5.", "vector_components"),
    Concept("Linear combinations and span", "Span asks what you can build by mixing fixed vectors.", "A linear combination scales vectors and adds them; the span is every reachable mix.", r"c_1\vec{v}_1+c_2\vec{v}_2+\cdots+c_k\vec{v}_k", ["vectors", "scalar multiplication", "addition"], "Span means every possible combination, not just the vectors drawn.", "Use a = (1, 0) and b = (1, 1). Can we reach (5, 2)?", "3a + 2b = 3(1, 0) + 2(1, 1) = (5, 2).", "The target is in the span because weights exist.", "A robot can move by (1,0) and (1,1). Which points can it reach?", "All points in the plane, because the directions are independent.", "linear_combination"),
    Concept("Matrix-vector multiplication", "Matrix-vector multiplication is a weighted recipe using the columns.", "Ax is a linear combination of columns of A, with x entries as weights.", r"A\vec{x}=x_1\vec{a}_1+\cdots+x_n\vec{a}_n", ["linear combinations", "columns", "vectors"], "Do not see Ax as random row arithmetic first; column combinations explain meaning.", "Let A = [[2, 1], [1, 3]] and x = (4, 2).", "Ax = (2*4 + 1*2, 1*4 + 3*2) = (10, 10).", "The output is a weighted mix of matrix columns.", "If A stores ad effects and x is budget, what does Ax mean?", "It predicts response as a weighted combination of ad-effect columns.", "matrix_vector"),
    Concept("Systems of linear equations", "A linear system is a set of constraints asking for one point.", "Solving Ax=b means finding coefficients that combine columns of A to make b.", r"A\vec{x}=\vec{b}", ["equations", "vectors", "matrix notation"], "A system can have no solution, one solution, or infinitely many.", "Solve 2x + y = 7 and x + y = 5.", "Subtract equations: x = 2. Then y = 3.", "The point (2, 3) satisfies both constraints.", "How can Ax=b model bundle counts matching a target order?", "Columns are bundle contents, x gives counts, and b is the target.", "systems"),
    Concept("Gaussian elimination", "Elimination removes one variable at a time until structure is visible.", "Row operations preserve the solution set while simplifying the matrix.", r"U\vec{x}=\vec{c}", ["systems", "row operations", "pivots"], "Elimination changes representation, not the solution set.", "Start with 2x + y = 7 and x + y = 5.", "Replace row1 by row1 - row2 to get x = 2; then y = 3.", "Equivalent equations can be easier to solve.", "How would elimination help solve several current-balance equations?", "It preserves feasible currents while simplifying variables in order.", "elimination"),
    Concept("Pivot columns", "Pivots mark where the system finds new directions.", "Pivot positions identify independent columns and basic variables.", r"\operatorname{rank}(A)=r", ["elimination", "columns", "independence"], "Pivot columns refer back to original columns, not the changed reduced columns.", "Reduce a matrix to [[1, 2, 0], [0, 0, 1]].", "Leading entries are in columns 1 and 3.", "Columns 1 and 3 are pivot columns.", "In a dataset, what does a pivot feature suggest?", "It contributes a new direction not explained by earlier pivot features.", "elimination"),
    Concept("Column space", "The column space is the set of targets your matrix can reach.", "Every Ax is a combination of columns, so Ax=b is solvable when b is in that span.", r"C(A)=\operatorname{span}\{\vec{a}_1,\ldots,\vec{a}_n\}", ["span", "linear combinations", "systems"], "Column space lives in output space, not input space.", "Let a1=(1,0), a2=(1,1), b=(3,2).", "b = 1*a1 + 2*a2 = (3, 2).", "b is reachable because it is a column combination.", "How do you tell whether a machine can produce a requested output?", "Check whether the target lies in the column space.", "subspace"),
    Concept("Nullspace", "The nullspace is everything a matrix sends to zero.", "Nullspace directions disappear under A.", r"A\vec{x}=0", ["matrix-vector multiplication", "homogeneous systems"], "The zero vector is always there; the question is whether anything else is.", "Let A=[1 1] and x=(2,-2).", "Ax = 1*2 + 1*(-2) = 0.", "The nonzero vector disappears under A.", "What does a nullspace image-change vector mean for a filter?", "The filter does not notice that change.", "subspace"),
    Concept("Linear independence", "Independent vectors bring genuinely new directions.", "No vector in an independent set can be built from the others.", r"c_1\vec{v}_1+\cdots+c_k\vec{v}_k=0 \Rightarrow c_i=0", ["linear combinations", "span", "zero vector"], "Independence is about redundancy, not visual distance.", "Compare v1=(1,0), v2=(2,0), w=(0,1).", "v2=2v1, so v1 and v2 are dependent; v1 and w are independent.", "A new direction cannot be a scaled repeat.", "Why are height in inches and centimeters not independent features?", "One is a scalar multiple of the other.", "linear_combination"),
    Concept("Bases and dimension", "A basis is a minimal vocabulary for a vector space.", "A basis spans with no redundancy; dimension counts basis vectors.", r"\dim(V)=k", ["span", "linear independence", "vector spaces"], "A basis is not unique; dimension is.", "In the plane, e1=(1,0), e2=(0,1).", "(4,7)=4e1+7e2, so they span with no redundancy.", "The plane has dimension 2.", "Why can a game position use many coordinate systems but dimension stays 2?", "Every basis for the plane needs exactly two directions.", "basis"),
    Concept("Rank-nullity", "Rank-nullity is the dimension budget of a matrix.", "Pivot directions plus free directions account for all input dimensions.", r"\operatorname{rank}(A)+\operatorname{nullity}(A)=n", ["rank", "nullspace", "dimension"], "It counts input dimensions, not rows.", "A has 3 input variables and rank(A)=2.", "rank + nullity = 3, so nullity = 1.", "One input direction is invisible to the output.", "A 10-variable model has rank 7. How many free directions remain?", "Nullity is 3.", "dimension_bar"),
    Concept("Linear transformations", "A matrix is a machine that moves space.", "A linear transformation preserves linear combinations; basis vectors determine everything.", r"T(cu+dv)=cT(u)+dT(v)", ["vectors", "functions", "basis"], "If grid lines bend or the origin moves, it is not linear in this strict sense.", "Let A=[[2,0],[0,1]] and x=(3,4).", "Ax=(6,4): x doubles and y stays fixed.", "Watch basis directions to know every vector's movement.", "Why do graphics use matrices for rotations and scalings?", "They preserve linear combinations, so basis movement controls the whole scene.", "transform_grid"),
    Concept("Matrix multiplication", "Matrix multiplication is function composition wearing a grid costume.", "AB means do B, then A; the order matters.", r"C=AB", ["linear transformations", "basis vectors"], "Order matters because transformations usually do not commute.", "A scales x by 2; B sends (x,y) to (x+y,y).", "AB(1,2)=A(3,2)=(6,2), but BA(1,2)=B(2,2)=(4,2).", "Changing order changes the result.", "Why does rotate-then-scale differ from scale-then-rotate?", "The second transformation receives a different input.", "transform_grid"),
    Concept("Invertibility", "An invertible matrix is a transformation you can perfectly undo.", "Each output has exactly one input.", r"A^{-1}A=I", ["linear transformations", "systems", "rank"], "A square matrix can still flatten space and fail to be invertible.", "A=[[2,0],[0,3]] sends (x,y) to (2x,3y).", "Undo (8,15) by computing (8/2,15/3)=(4,5).", "No information was lost.", "Why is blur usually not invertible?", "Many original images can produce the same blurred output.", "transform_grid"),
    Concept("Determinants", "The determinant is the signed area or volume scale factor.", "It says how much a linear transformation scales area and whether orientation flips.", r"\det(A)", ["linear transformations", "area", "orientation"], "A zero determinant means space was flattened.", "A=[[2,0],[0,3]].", "det(A)=2*3-0*0=6.", "A unit square becomes area 6.", "What does determinant 3 mean in a 2D transform?", "Every area is scaled by 3, up to orientation sign.", "area"),
    Concept("Change of basis", "Change of basis translates the same vector into a different coordinate language.", "The geometric vector stays fixed while coordinate numbers change.", r"[\vec{x}]_B=P^{-1}\vec{x}", ["bases", "coordinates", "invertible matrices"], "Changing coordinates is not moving the vector itself.", "Use b1=(1,1), b2=(1,-1) for v=(4,2).", "v=3b1+1b2=(4,2).", "The vector stayed fixed; coordinates changed.", "What stays the same when a map changes coordinate axes?", "The physical displacement vector.", "basis"),
    Concept("Dot products", "The dot product measures alignment.", "It combines length and angle to detect component in a direction.", r"\vec{u}\cdot\vec{v}=\|u\|\|v\|\cos\theta", ["vectors", "angles"], "A large dot product can mean long vectors or strong alignment.", "F=(3,4), d=(1,0).", "F dot d = 3*1 + 4*0 = 3.", "Only the component along motion contributes.", "How does dot product decide work from angled force?", "It keeps only the aligned component.", "projection"),
    Concept("Orthogonality", "Orthogonality is independence with a right angle.", "Orthogonal vectors have dot product zero.", r"\vec{u}\cdot\vec{v}=0", ["dot product", "geometry"], "Orthogonal does not mean unit length.", "u=(2,1), v=(1,-2).", "u dot v = 2*1 + 1*(-2)=0.", "The directions are perpendicular.", "How can you check whether two signals are orthogonal?", "Compute their dot product under the chosen inner product.", "projection"),
    Concept("Projection", "Projection is a vector dropping its shadow onto a direction.", "It keeps only the component in a chosen subspace.", r"\operatorname{proj}_u(v)=\frac{v\cdot u}{u\cdot u}u", ["dot product", "vectors"], "Projection is not just shrinking; it chooses information to keep.", "Project v=(3,4) onto u=(1,0).", "proj_u(v) = 3(1,0) = (3,0).", "The perpendicular part is discarded.", "How does projection explain a 3D object's 2D shadow?", "It keeps screen-direction components and discards depth.", "projection"),
    Concept("Least squares", "When no exact answer exists, least squares finds the closest one.", "It minimizes total squared residual error.", r"A^TA\hat{x}=A^Tb", ["projection", "column space"], "It minimizes total squared error, not every single error.", "Fit one constant c to y=2,4,5.", "c=(2+4+5)/3=11/3.", "The best constant is the average.", "What does least squares minimize for noisy points?", "The sum of squared residuals.", "least_squares"),
    Concept("Gram-Schmidt", "Gram-Schmidt turns messy independent vectors into perpendicular ones.", "It repeatedly subtracts projections already explained.", r"q_i=\frac{v_i-\operatorname{proj}(v_i)}{\|v_i-\operatorname{proj}(v_i)\|}", ["projection", "orthogonality", "bases"], "It changes basis vectors but preserves the span.", "Start with v1=(1,0), v2=(1,1).", "v2 - proj_v1(v2) = (1,1)-(1,0)=(0,1).", "The result is perpendicular and spans the same plane.", "Why prefer orthonormal axes in simulation?", "They make projections and lengths stable.", "projection"),
    Concept("QR factorization", "QR separates clean directions from coordinates.", "Q stores orthonormal directions; R stores upper-triangular coordinates.", r"A=QR", ["Gram-Schmidt", "matrix multiplication"], "Q must have orthonormal columns.", "A has columns a1=(1,0), a2=(1,1).", "Gram-Schmidt gives q1=(1,0), q2=(0,1), R=[[1,1],[0,1]].", "Q stores directions; R stores coordinates.", "Why is QR useful for least squares?", "It turns the problem into a stable triangular solve.", "matrix_factor"),
    Concept("Eigenvectors", "Most vectors turn; eigenvectors only stretch.", "An eigenvector's direction survives a transformation.", r"A\vec{v}=\lambda\vec{v}", ["transformations", "scalar multiplication"], "Eigenvectors depend on the transformation.", "A=[[2,0],[0,3]], v=(1,0).", "Av=(2,0)=2v.", "v is an eigenvector with lambda=2.", "In a population model, what can an eigenvector represent?", "A stable direction that only scales after transition.", "eigen"),
    Concept("Eigenvalues", "An eigenvalue is the stretch factor attached to an eigenvector.", "It tells how much the surviving direction scales or flips.", r"A\vec{v}=\lambda\vec{v}", ["eigenvectors", "linear transformations"], "Eigenvalues alone are not the whole transformation.", "A=[[2,0],[0,3]], v=(0,1).", "Av=(0,3)=3v.", "The stretch factor is 3.", "What can eigenvalues tell you in vibrations?", "Natural scaling or frequency behavior of modes.", "eigen"),
    Concept("Diagonalization", "Diagonalization changes coordinates so a matrix becomes scaling.", "In an eigenbasis, repeated matrix powers become powers of eigenvalues.", r"A=S\Lambda S^{-1}", ["eigenvectors", "basis"], "Not every matrix has enough eigenvectors.", "If A=diag(2,3), compute A^5 on x=(1,1).", "A^5x=(2^5,3^5)=(32,243).", "Repeated multiplication becomes repeated scaling.", "Why does diagonalization simplify A^50?", "It reduces powers to eigenvalue powers.", "eigen"),
    Concept("Positive definite matrices", "Positive definite matrices make bowls instead of saddles.", "x^T A x is positive in every nonzero direction.", r"\vec{x}^TA\vec{x}>0", ["quadratic forms", "eigenvalues"], "Positive entries do not guarantee positive definiteness.", "A=[[2,0],[0,1]], x=(3,4).", "x^T A x = 2*3^2 + 1*4^2 = 34 > 0.", "Every nonzero direction gives positive height.", "Why do they matter in optimization?", "They give bowl-shaped problems with a unique minimum.", "quadratic"),
    Concept("Markov matrices", "A Markov matrix moves probability without losing it.", "Multiplying by the transition matrix updates a state distribution.", r"\vec{x}_{k+1}=P\vec{x}_k", ["matrix multiplication", "probability"], "It is about conserved total probability, not arbitrary transitions.", "P=[[0.8,0.3],[0.2,0.7]], x=(100,0).", "Px=(80,20).", "Population moved between states without losing total.", "How can this model users moving between app states?", "Entries are transition probabilities; multiplication updates the distribution.", "markov"),
    Concept("Singular value decomposition", "SVD says every matrix is rotate, stretch, rotate.", "It ranks transformation directions by importance.", r"A=U\Sigma V^T", ["orthogonality", "eigenvectors"], "SVD works for non-square matrices too.", "An image matrix has singular values 10, 2, 0.5.", "Keeping only 10 gives a rank-1 approximation.", "Large singular values preserve strongest structure.", "How does SVD compress an image?", "Keep large singular values and discard small detail.", "svd"),
]

GROUP_THEORY: list[Concept] = [
    Concept("Groups and operations", "A group is a symmetry machine with one legal way to combine moves.", "Closure, identity, inverses, and associativity let transformations behave like algebraic objects.", r"(G,\cdot)", ["sets", "functions", "composition"], "A group is not just any set with a table; every element must have an inverse and the operation must stay inside the set.", "Let G be rotations of a square by 0, 90, 180, and 270 degrees.", "90 degrees composed with 270 degrees gives 360 degrees, the identity rotation.", "The operation keeps every result inside the same four rotations.", "Why do clock-hour rotations modulo 12 form a group under addition?", "Adding hours stays modulo 12, 0 is identity, and each hour has an additive inverse.", "group_structure"),
    Concept("Subgroups", "A subgroup is a smaller world that still obeys all the group rules.", "A subgroup contains the identity and is closed under combining elements and taking inverses.", r"H\leq G", ["groups", "identity", "inverses"], "A subset of a group is not automatically a subgroup.", "In integers under addition, the even integers form a subgroup.", "Even + even is even, 0 is even, and the inverse of 2k is -2k.", "The subgroup test succeeds because the operation never leaves the subset.", "Why are multiples of 5 a subgroup of integers under addition?", "They contain 0, sums stay multiples of 5, and negatives stay multiples of 5.", "group_structure"),
    Concept("Cosets and quotient groups", "Cosets are what a group looks like when you slide a subgroup around.", "A coset gH packages elements that differ by subgroup motion; normal subgroups make those packages multiply consistently.", r"gH=\{gh:h\in H\}", ["subgroups", "equivalence classes"], "Cosets are usually translated copies, not subgroups themselves.", "In integers modulo 6, take H = {0, 3}.", "The cosets are {0,3}, {1,4}, and {2,5}.", "Each coset groups numbers with the same remainder modulo H.", "How do cosets describe parity in integers?", "Even and odd integers are the two cosets of the even subgroup.", "group_cosets"),
    Concept("Homomorphisms", "A homomorphism is a structure-preserving translator between groups.", "It maps one group to another while respecting the operation, so products before mapping match products after mapping.", r"\varphi(ab)=\varphi(a)\varphi(b)", ["groups", "functions"], "A homomorphism does not have to be one-to-one or onto.", "Map integers under addition to parity by phi(n)=n mod 2.", "phi(3+5)=0 and phi(3)+phi(5)=1+1=0 mod 2.", "The map preserves the operation even though it forgets information.", "Why is determinant a homomorphism from invertible matrices to nonzero scalars?", "det(AB)=det(A)det(B), so multiplication is preserved.", "group_homomorphism"),
]

ALGORITHMS: list[Concept] = [
    Concept("Asymptotic complexity", "Big-O lets growth rate speak louder than machine details.", "Asymptotic notation compares how work scales as input size grows, which predicts algorithm behavior across machines.", r"T(n)=O(n\log n)", ["functions", "logs", "counting operations"], "Big-O is an upper bound, not always the exact running time.", "Compare n log n and n squared for n = 1000.", "1000 log2(1000) is about 10000, while 1000^2 is 1000000.", "The slower-growing curve wins at scale.", "Why can a theoretically faster algorithm lose on tiny inputs?", "Constants and setup costs can dominate before asymptotic growth matters.", "cs_array"),
    Concept("Divide and conquer", "Some problems get easier when you keep splitting them in half.", "Divide and conquer solves smaller copies of a problem, then combines their answers.", r"T(n)=2T(n/2)+O(n)", ["recursion", "arrays"], "Splitting alone is not enough; the combine step determines the cost.", "Merge sort splits 8 items into halves until singletons.", "Merging layers costs 8 work per level for about log2(8)=3 levels.", "The structure gives n log n behavior.", "Why does binary search not have a combine step?", "It discards half the input and recurses on only one side.", "cs_array"),
    Concept("Breadth-first search", "BFS explores a graph in expanding rings.", "A queue makes BFS visit all nodes at distance k before distance k+1, giving shortest paths in unweighted graphs.", r"O(V+E)", ["graphs", "queues"], "BFS shortest paths require unweighted or equal-weight edges.", "Start at A with edges A-B, A-C, B-D, C-E.", "BFS visits A, then B and C, then D and E.", "Layer order records shortest edge counts.", "How does BFS find the fewest clicks between webpages?", "Treat pages as nodes, links as edges, and expand layer by layer.", "cs_graph"),
    Concept("Dynamic programming", "Dynamic programming is recursion with a memory.", "DP works when subproblems overlap and a good state captures all information needed for the future.", r"dp[i]=\min_j(dp[j]+\operatorname{cost}(j,i))", ["recursion", "optimization"], "Memoization is not the hard part; choosing the state is.", "For Fibonacci, F(5) asks for F(4) and F(3), and F(4) also asks for F(3).", "Store F(3) once instead of recomputing it.", "The recursion tree collapses into a table.", "How would DP avoid repeated work in text segmentation?", "Store the best answer for each prefix length.", "cs_array"),
]

PHYSICS_MECHANICS: list[Concept] = [
    Concept("Newton's second law", "Forces are how motion gets edited.", "Net force determines acceleration, so changing motion requires an imbalance of forces.", r"\sum F=ma", ["vectors", "free-body diagrams"], "A large velocity does not require a large net force; acceleration does.", "A 2 kg cart feels a 10 N push and 2 N friction.", "Net force is 8 N, so acceleration is 8/2 = 4 m/s^2.", "The unbalanced force sets the acceleration.", "What happens to acceleration if the mass doubles with the same net force?", "It halves, because a=F/m.", "physics_force"),
    Concept("Kinematics", "Kinematics predicts motion before asking what caused it.", "Position, velocity, and acceleration are linked by rates of change and constant-acceleration formulas.", r"x=x_0+v_0t+\frac12at^2", ["algebra", "graphs"], "A position graph's height is position; its slope is velocity.", "A ball starts at 0 m with v0=3 m/s and a=2 m/s^2.", "After 4 s, x = 0 + 12 + 16 = 28 m.", "The formula accumulates initial motion and acceleration.", "How far does a car travel from rest at 3 m/s^2 for 5 s?", "Use x=1/2 at^2 = 37.5 m.", "calculus_tangent"),
    Concept("Work and energy", "Energy is the accounting system for motion.", "Work transfers energy, and conserved energy lets you solve without tracking every instant of force.", r"W=\Delta K", ["forces", "dot products"], "Energy conservation needs the system and nonconservative work to be named.", "A 5 N force pushes 3 m in the same direction.", "Work is Fd = 15 J.", "That work increases kinetic energy if no other losses intervene.", "Why does friction reduce mechanical energy?", "It does negative work and converts organized motion into thermal energy.", "physics_energy"),
    Concept("Momentum", "Momentum tracks motion that interactions must balance.", "In an isolated system, total momentum stays constant even while objects exchange forces.", r"p=mv", ["velocity", "mass"], "Momentum and kinetic energy are not the same conserved quantity.", "A 2 kg cart moving 3 m/s hits a 1 kg cart at rest and they stick.", "Initial momentum is 6 kg m/s; final speed is 6/3 = 2 m/s.", "The stuck pair carries the same total momentum.", "Why do recoil problems use momentum conservation?", "The system starts with zero total momentum, so opposite momenta must balance.", "physics_force"),
]

ECONOMICS: list[Concept] = [
    Concept("Supply and demand equilibrium", "A market price is where two curves stop disagreeing.", "Equilibrium occurs where quantity supplied equals quantity demanded, so there is no pressure from shortage or surplus.", r"Q_s(P)=Q_d(P)", ["graphs", "linear equations"], "Equilibrium is a model prediction, not a guarantee that every real market clears instantly.", "Let demand be Qd=100-2P and supply be Qs=20+2P.", "Set 100-2P = 20+2P, so P=20 and Q=60.", "The crossing price balances plans of buyers and sellers.", "What does a binding price ceiling create?", "A shortage, because quantity demanded exceeds quantity supplied.", "econ_supply_demand"),
    Concept("Elasticity", "Elasticity measures sensitivity in percent language.", "Price elasticity of demand compares percent quantity response to percent price change.", r"E_d=\frac{\%\Delta Q}{\%\Delta P}", ["percent changes", "demand curves"], "A steep-looking curve is not automatically inelastic; units and location matter.", "If price rises 10 percent and quantity falls 20 percent.", "Elasticity is -20 percent / 10 percent = -2.", "Quantity is relatively responsive.", "Why do firms care whether demand is elastic?", "It predicts whether raising price increases or decreases revenue.", "econ_elasticity"),
    Concept("Consumer choice", "A budget line turns preferences into a constrained decision.", "Consumers choose the best affordable bundle where marginal tradeoffs line up with prices.", r"p_x x+p_y y=I", ["algebra", "optimization"], "The favorite bundle may be unaffordable; the constraint matters.", "Income is 40, x costs 4, y costs 2.", "The bundle x=5, y=10 costs 20+20=40.", "It lies exactly on the budget line.", "How does a price increase rotate a budget line?", "The intercept for that good moves inward.", "econ_budget"),
    Concept("Externalities", "An externality is a cost or benefit that escapes the transaction.", "Markets can overproduce or underproduce when private incentives differ from social costs and benefits.", r"MSC=MSB", ["supply and demand", "welfare"], "A market outcome can be efficient privately and inefficient socially.", "A factory's private marginal cost is 5, but pollution adds 3 social cost.", "Marginal social cost is 8.", "The market price misses part of the real cost.", "How can a tax correct a negative externality?", "Set the tax near the external marginal cost so private decisions face social cost.", "econ_curve"),
]


GROUP_THEORY.extend([
    Concept("Cyclic groups", "A cyclic group is generated by repeating one move.", "If every element is a power or multiple of one generator, the whole group has a one-dimensional algebraic clock.", r"G=\langle g\rangle", ["groups", "powers", "orders"], "A group can be generated by one element without looking visually circular.", "In integers modulo 6 under addition, 1 generates every residue.", "0,1,2,3,4,5 appear as repeated additions of 1.", "One generator can encode the whole group.", "How do you test whether 2 generates integers modulo 6?", "List 0,2,4,0; it misses odd residues, so it does not generate.", "group_structure"),
    Concept("Orders of elements", "The order of an element is the first time repetition returns home.", "Element order measures the cycle length created by repeatedly applying that element.", r"g^n=e", ["identity", "cyclic subgroups"], "Order is about the element under the group operation, not its numerical size.", "A rotation by 90 degrees has order 4.", "Four repeats give 360 degrees, the identity.", "The order is the length of the generated cycle.", "What is the order of 3 modulo 8 under addition?", "Repeated addition gives 3,6,1,4,7,2,5,0, so the order is 8.", "group_structure"),
    Concept("Permutation groups", "A permutation group studies rearrangements as algebra.", "Permutations compose, have inverses, and encode symmetries of finite sets.", r"S_n", ["functions", "composition"], "Permutation multiplication is composition, so order matters.", "Let sigma swap 1 and 2, and tau send 2 to 3.", "Composing in opposite orders can move 1 to different places.", "Permutation notation records motion of labels.", "Why is every symmetry of a triangle a permutation of its vertices?", "Each symmetry rearranges the three vertex labels without losing any label.", "group_action"),
    Concept("Lagrange's theorem", "Subgroup size must divide group size.", "Cosets partition a finite group into equal-sized copies of a subgroup.", r"|H|\mid |G|", ["subgroups", "cosets"], "The theorem gives a divisibility condition, not a guarantee that every divisor occurs as a subgroup order.", "If a group has 12 elements and H has 3 elements.", "The left cosets of H form 12/3 = 4 blocks.", "Equal coset blocks force divisibility.", "Why can no subgroup of order 5 exist in a group of order 12?", "5 does not divide 12, so Lagrange rules it out.", "group_cosets"),
    Concept("Normal subgroups", "Normal subgroups are the subgroups whose cosets multiply cleanly.", "Normality means left and right cosets agree, which lets quotient groups inherit a well-defined operation.", r"gH=Hg", ["subgroups", "cosets"], "Normal does not mean common or obvious; it is a conjugation condition.", "In any abelian group, every subgroup is normal.", "Because gh = hg, left and right cosets match.", "Commutativity makes coset order irrelevant.", "How can you test normality using conjugation?", "Check whether ghg^{-1} stays in H for every g in G and h in H.", "group_cosets"),
    Concept("Isomorphisms", "An isomorphism says two groups have the same structure in different names.", "A bijective homomorphism preserves and reflects the operation, so all group facts transfer across the map.", r"G\cong H", ["homomorphisms", "bijections"], "Same size alone does not imply isomorphic.", "Map rotations of a square by multiples of 90 degrees to integers modulo 4.", "Composition of rotations matches addition modulo 4.", "The two groups share the same operation table after relabeling.", "Why are two cyclic groups of order n isomorphic?", "Each is generated by one element with the same cycle length n.", "group_homomorphism"),
    Concept("Kernels and images", "A homomorphism's kernel measures what it forgets.", "The kernel maps to identity; the image records what outputs the homomorphism can reach.", r"\ker\varphi=\{g:\varphi(g)=e\}", ["homomorphisms", "identity"], "A large kernel means information is being collapsed.", "Parity maps integers to Z/2Z.", "All even integers map to 0, so they form the kernel.", "The kernel is the lost distinction.", "What does a trivial kernel tell you?", "The homomorphism is injective.", "group_homomorphism"),
    Concept("First isomorphism theorem", "Quotienting by the kernel leaves exactly the image.", "The theorem formalizes the idea that a homomorphism equals collapse by its kernel followed by relabeling of the image.", r"G/\ker\varphi\cong \operatorname{im}\varphi", ["kernels", "quotients"], "The quotient is by the kernel, not by the image.", "For the parity map from integers to Z/2Z, the kernel is even integers.", "Z/even integers has two cosets, matching the two parity outputs.", "Collapsing the kernel gives the image structure.", "How does this explain determinant as a map?", "Matrices with determinant 1 form the kernel of determinant on invertible matrices.", "group_homomorphism"),
    Concept("Group actions and orbits", "An orbit is everything an action can reach from one starting point.", "A group action partitions a set into reachable motion classes called orbits.", r"Gx=\{g\cdot x:g\in G\}", ["actions", "sets"], "The orbit is a subset of the acted-on set, not usually a subgroup.", "Rotations of a square act on vertices.", "Starting from one vertex, rotations reach all four vertices.", "The orbit records all symmetric positions.", "What is a fixed point of an action?", "A point that every group element leaves unchanged.", "group_action"),
    Concept("Stabilizers", "A stabilizer is the symmetry left after choosing a point.", "The stabilizer of x contains group elements that keep x fixed.", r"G_x=\{g:g\cdot x=x\}", ["actions", "subgroups"], "A stabilizer lives inside the group, while an orbit lives inside the set being acted on.", "A square's full symmetry group acts on one vertex.", "Only symmetries that keep that vertex in place belong to its stabilizer.", "Choosing a point breaks some symmetries.", "Why is the stabilizer always a subgroup?", "Identity fixes x, products of fixers fix x, and inverses of fixers fix x.", "group_action"),
    Concept("Rings", "A ring is algebra with addition, multiplication, and distributivity.", "Rings generalize integer arithmetic while allowing multiplication to behave differently from fields.", r"a(b+c)=ab+ac", ["groups", "operations"], "A ring does not necessarily allow division by every nonzero element.", "Integers form a ring under ordinary addition and multiplication.", "Addition is an abelian group, multiplication is associative, and distributivity holds.", "The integer rules define the ring pattern.", "Why are even integers not a ring with identity 1?", "They do not contain 1, though they are closed under addition and multiplication.", "numeric_rule"),
    Concept("Ideals", "An ideal is the kind of subset you can quotient a ring by.", "Ideals absorb multiplication by arbitrary ring elements, which makes quotient rings well defined.", r"rI\subseteq I", ["rings", "subsets"], "An ideal is stronger than a subring because it must absorb outside multiplication.", "Multiples of 5 form an ideal in the integers.", "Any integer times a multiple of 5 is still a multiple of 5.", "Absorption makes modular arithmetic possible.", "Why are ideals the ring analogue of normal subgroups?", "They are exactly the subsets that make quotient structures well defined.", "numeric_rule"),
    Concept("Fields", "A field is arithmetic where nonzero division always works.", "Fields support addition, subtraction, multiplication, and division by nonzero elements.", r"a^{-1}a=1", ["rings", "inverses"], "A ring with no zero divisors is not automatically a field unless every nonzero element has an inverse.", "Integers modulo 5 form a field.", "2 inverse is 3 because 2 times 3 equals 1 modulo 5.", "Every nonzero residue can divide.", "Why is modulo 6 not a field?", "2 has no inverse modulo 6 because 2x never equals 1 mod 6.", "numeric_rule"),
])

ECONOMICS.extend([
    Concept("Preferences and utility", "Utility represents rankings, not a literal happiness meter.", "A utility function orders bundles so economists can model choices under constraints.", r"U(x,y)", ["bundles", "orderings"], "Utility numbers themselves are less important than the ranking they preserve.", "If U=x+y, bundle (3,2) and (4,1) both give utility 5.", "The consumer is indifferent between those two bundles in this model.", "Utility compresses preference comparisons into a function.", "Why can two different utility functions represent the same preferences?", "Any increasing transformation preserves the ranking of bundles.", "econ_budget"),
    Concept("Budget constraints", "A budget line is the boundary of affordable choices.", "Prices and income define which bundles can be purchased and what tradeoffs are possible.", r"p_x x+p_y y\leq I", ["prices", "income"], "The preferred bundle must still be affordable.", "Income is 60, x costs 5, y costs 3.", "Bundle x=6, y=10 costs 30+30=60.", "The bundle lies exactly on the budget line.", "What happens when income rises?", "The budget line shifts outward in a parallel way if prices stay fixed.", "econ_budget"),
    Concept("Marginal rate of substitution", "MRS is the tradeoff a consumer is willing to make.", "It measures how much of one good compensates for giving up a little of another good while utility stays constant.", r"MRS=-\frac{MU_x}{MU_y}", ["utility", "marginal utility"], "MRS is about preferences, while price ratios are about the market constraint.", "If MUx=6 and MUy=3, MRS is -2.", "The consumer gives up about 2 units of y for 1 more x along an indifference curve.", "The slope captures willingness to substitute.", "At an interior optimum, how does MRS compare to prices?", "It equals the negative price ratio.", "econ_curve"),
    Concept("Demand curves", "A demand curve records optimal quantity at each price.", "Holding other factors fixed, the consumer's choice problem maps prices to quantities demanded.", r"Q_d=D(P)", ["utility", "budget constraints"], "Demand is not just desire; it includes willingness and ability to pay.", "At price 2, quantity demanded is 20; at price 4, it is 12.", "The higher price corresponds to a lower chosen quantity.", "The curve summarizes many optimization problems.", "Why does a demand curve shift when income changes?", "The entire choice problem changes, not just movement along one price axis.", "econ_supply_demand"),
    Concept("Income and substitution effects", "A price change has two stories at once.", "The substitution effect changes relative attractiveness, while the income effect changes purchasing power.", r"\Delta x=SE+IE", ["demand", "budget constraints"], "A price change is not the same as an income change, though it can affect real purchasing power.", "If the price of x falls, x becomes relatively cheaper and the consumer can afford more overall.", "Total demand change decomposes into substitution plus income effects.", "The decomposition explains why responses vary by good type.", "Why can a Giffen good slope upward?", "A strong negative income effect can outweigh the substitution effect.", "econ_curve"),
    Concept("Production functions", "A production function turns inputs into output.", "It describes the maximum output attainable from combinations of inputs such as labor and capital.", r"q=f(L,K)", ["functions", "inputs"], "A production function describes technology, not profit by itself.", "Let q=2L with K fixed, and L=5.", "Output is q=10.", "The function maps input choice to feasible output.", "What does marginal product measure?", "The output gained from one additional unit of an input, holding others fixed.", "econ_curve"),
    Concept("Costs and cost curves", "Cost curves translate production into money.", "Fixed, variable, average, and marginal costs describe different views of the firm's production expense.", r"TC=FC+VC", ["production", "algebra"], "Average cost and marginal cost answer different questions.", "If fixed cost is 10 and variable cost is 3q, then TC=10+3q.", "At q=5, total cost is 25 and average cost is 5.", "Cost curves organize firm decisions.", "When does marginal cost matter most?", "When deciding whether to produce one more unit.", "econ_curve"),
    Concept("Perfect competition", "A competitive firm takes price as given.", "In perfect competition, many small firms choose output where price equals marginal cost.", r"P=MC", ["costs", "markets"], "A price-taking firm chooses quantity, not market price.", "If price is 8 and MC(q)=2q, the firm sets 8=2q.", "The profit-maximizing quantity is q=4.", "The firm expands until the next unit no longer adds profit.", "Why can profit be zero in long-run competition?", "Entry and exit push price toward average cost.", "econ_curve"),
    Concept("Monopoly", "A monopolist chooses quantity knowing price will respond.", "Market power makes marginal revenue fall below price, so monopoly output is lower than competitive output.", r"MR=MC", ["demand", "costs"], "A monopolist cannot independently choose any price and any quantity; demand links them.", "If demand is P=20-Q, then revenue is 20Q-Q^2.", "Marginal revenue is 20-2Q.", "The firm equates MR and MC, not P and MC.", "Why does monopoly create deadweight loss?", "Some mutually beneficial trades do not happen because price exceeds marginal cost.", "econ_supply_demand"),
    Concept("Oligopoly and strategic behavior", "In oligopoly, one firm's best move depends on another firm's move.", "Strategic interaction makes output, pricing, and entry decisions depend on expectations about rivals.", r"\pi_i(q_i,q_{-i})", ["profits", "game theory"], "You cannot analyze one firm in isolation when rivals react.", "Two firms choose quantities; if both expand, market price falls.", "Each firm's payoff depends on total quantity.", "The decision is strategic, not merely individual optimization.", "What is a best response?", "The action that maximizes a player's payoff given rivals' actions.", "state_machine"),
    Concept("Welfare and surplus", "Surplus measures gains from trade.", "Consumer surplus and producer surplus summarize how much buyers and sellers gain relative to their alternatives.", r"TS=CS+PS", ["supply", "demand"], "High revenue is not the same as high total surplus.", "A buyer willing to pay 10 buys at price 7.", "Consumer surplus from that unit is 3.", "Surplus measures value above price.", "Where is total surplus maximized in a competitive market?", "At the efficient quantity where demand equals supply.", "econ_supply_demand"),
    Concept("Taxes and deadweight loss", "A tax creates a wedge between buyers and sellers.", "Taxes can raise revenue but also prevent trades whose value exceeds cost.", r"DWL=\frac12\times base\times height", ["surplus", "elasticity"], "The legal payer of a tax is not necessarily who bears its economic burden.", "If a tax reduces quantity by 4 and creates a wedge of 3.", "DWL is one half times 4 times 3, which is 6.", "The triangle measures lost mutually beneficial trades.", "How does elasticity affect tax burden?", "The less elastic side bears more of the tax burden.", "econ_elasticity"),
    Concept("Public goods", "Public goods are hard to price because people can share them at once.", "Nonrivalry and nonexcludability can create free-rider problems and underprovision.", r"MB_{social}=\sum_i MB_i", ["externalities", "welfare"], "A public good is not simply a good provided by the government.", "A lighthouse can guide many ships without being used up.", "One ship's use does not reduce another ship's benefit.", "Nonrival benefits change the efficient provision rule.", "Why do private markets underprovide public goods?", "Individuals can benefit without paying, so private willingness to pay understates social benefit.", "econ_curve"),
])


GROUP_THEORY.extend([
    Concept("Direct products", "Direct products build a larger group from independent component groups.", "Operations happen coordinate by coordinate, so structure can be decomposed into simpler factors.", r"G\times H", ["groups", "ordered pairs"], "A direct product is not just a union; elements carry both coordinates at once.", "Take Z/2Z x Z/3Z.", "Add each coordinate modulo its own modulus.", "The product keeps two independent clocks running together.", "When is Z/2Z x Z/3Z cyclic?", "It is cyclic when the component orders are relatively prime.", "group_structure"),
    Concept("Abelian groups", "Abelian groups are groups where order of combination does not matter.", "Commutativity makes subgroup, quotient, and generator calculations much cleaner.", r"ab=ba", ["groups", "operations"], "Many familiar groups are abelian, but symmetry groups often are not.", "Integers under addition are abelian.", "a+b=b+a for every pair of integers.", "The operation can be swapped without changing the result.", "Why is every subgroup of an abelian group normal?", "Because gh=hg makes left and right cosets agree.", "group_structure"),
    Concept("Dihedral groups", "Dihedral groups encode rotations and reflections of regular polygons.", "They are the standard finite examples where noncommutativity appears geometrically.", r"D_n=\langle r,s:r^n=e,s^2=e,srs=r^{-1}\rangle", ["symmetry", "generators"], "A reflection and rotation usually do not commute.", "In D4, rotate a square then reflect it.", "Changing the order can send a vertex to a different position.", "The geometry makes multiplication order visible.", "How many elements does D_n have?", "It has n rotations and n reflections, so 2n elements.", "group_action"),
    Concept("Conjugacy classes", "Conjugacy groups elements that are the same up to a change of viewpoint.", "Conjugation measures internal symmetry and partitions a group into structurally similar elements.", r"Cl(g)=\{hgh^{-1}:h\in G\}", ["groups", "conjugation"], "Conjugate elements need not be equal; they share a structural role.", "In S3, transpositions form one conjugacy class.", "Relabeling vertices turns one swap into another.", "The class records a motion type rather than a label.", "Why are conjugacy classes important for normal subgroups?", "Normal subgroups are unions of conjugacy classes.", "group_action"),
    Concept("Center of a group", "The center contains elements that commute with everything.", "It measures the part of a group that behaves abelian from every viewpoint.", r"Z(G)=\{z:zg=gz\}", ["groups", "commutativity"], "The center can be small even when many pairs commute.", "In an abelian group, every element is central.", "So Z(G)=G.", "The center isolates universal commutativity.", "What is the center of a nonabelian group useful for?", "It helps break the group into simpler quotient information.", "group_structure"),
    Concept("Centralizers", "A centralizer is the set of elements that commute with one chosen element.", "It localizes commutativity around a particular element or subset.", r"C_G(g)=\{h:hg=gh\}", ["groups", "commutativity"], "The centralizer of one element can be larger than the center.", "Rotations commute with a fixed rotation in a dihedral group.", "Some reflections may not commute with it.", "Centralizers compare local and global symmetry.", "Why is a centralizer a subgroup?", "Identity commutes, products of commuting elements commute, and inverses commute.", "group_structure"),
    Concept("Cayley's theorem", "Every group can be represented as permutations of itself.", "Left multiplication turns abstract group elements into concrete rearrangements.", r"G\hookrightarrow S_G", ["groups", "permutations"], "The theorem represents structure; it does not say every group is a symmetric group itself.", "Let g act on G by x maps to gx.", "This action is a permutation of the underlying set.", "Group multiplication becomes permutation composition.", "Why is the action faithful?", "Different group elements move the identity to different outputs.", "group_action"),
    Concept("Sylow subgroups", "Sylow theory locates the largest p-power pieces inside finite groups.", "It uses divisibility and congruence to constrain subgroup structure.", r"|P|=p^k", ["Lagrange's theorem", "prime powers"], "Sylow theorems give existence and counts, not a full multiplication table by themselves.", "If |G|=12, a Sylow 3-subgroup has order 3.", "The number of such subgroups divides 4 and is 1 mod 3.", "Arithmetic narrows structural possibilities.", "Why can a unique Sylow subgroup matter?", "A unique Sylow subgroup is normal.", "group_cosets"),
    Concept("Classification of finite abelian groups", "Finite abelian groups split into cyclic prime-power building blocks.", "The classification theorem turns a large group into a product of simpler cyclic factors.", r"G\cong \prod_i \mathbb{Z}/n_i\mathbb{Z}", ["abelian groups", "direct products"], "Same group order does not determine a finite abelian group uniquely.", "Groups of order 4 include Z/4Z and Z/2Z x Z/2Z.", "They have different element orders.", "Element orders distinguish decompositions.", "How does the theorem help classify order 8 groups?", "List products of cyclic prime-power factors whose orders multiply to 8.", "group_structure"),
    Concept("Automorphisms", "Automorphisms are symmetries of an algebraic structure itself.", "They are isomorphisms from an object to itself, preserving all operations while relabeling elements.", r"\operatorname{Aut}(G)", ["isomorphisms", "bijections"], "An automorphism can move elements while preserving the full operation table.", "In a cyclic group, a generator can map to another generator.", "The map extends to every power.", "Generator images determine many automorphisms.", "What is an inner automorphism?", "It is conjugation by a fixed group element.", "group_homomorphism"),
    Concept("Ring homomorphisms", "Ring homomorphisms preserve addition and multiplication together.", "They translate ring arithmetic without breaking either operation.", r"f(a+b)=f(a)+f(b),\quad f(ab)=f(a)f(b)", ["rings", "functions"], "Preserving addition alone is not enough for a ring homomorphism.", "Reduce integers modulo 5.", "Addition and multiplication before reduction match reduction before operations.", "The map carries integer arithmetic into modular arithmetic.", "What is the kernel of a ring homomorphism?", "The set of inputs mapped to zero, usually an ideal.", "group_homomorphism"),
    Concept("Quotient rings", "Quotient rings collapse an ideal to zero.", "They generalize modular arithmetic by identifying elements that differ by an ideal.", r"R/I", ["rings", "ideals"], "The subset must be an ideal, not merely a subring.", "Integers modulo n are Z/nZ.", "Two integers are equivalent when their difference is a multiple of n.", "The ideal defines what counts as zero.", "Why do ideals make quotient multiplication well-defined?", "Absorption keeps products independent of representative choice.", "numeric_rule"),
    Concept("Polynomial rings", "Polynomial rings treat polynomials as algebraic objects with coefficients in a ring or field.", "They let algebraic questions become questions about roots, factors, and ideals.", r"F[x]", ["rings", "polynomials"], "A polynomial ring is not the same object as the field of rational functions.", "Over a field F, add and multiply polynomials coefficientwise.", "Degree tracks how multiplication grows.", "Polynomial arithmetic mirrors integer arithmetic in many ways.", "What does irreducible mean in F[x]?", "The polynomial cannot be factored into lower-degree nonunits over F.", "numeric_rule"),
    Concept("Euclidean domains", "Euclidean domains support division with remainder.", "A Euclidean function makes gcd algorithms and Bezout identities possible.", r"a=bq+r", ["rings", "division"], "Division with remainder depends on a norm-like measure decreasing.", "Integers use absolute value as the Euclidean measure.", "Divide 17 by 5 to get 17=5*3+2.", "The remainder is smaller than the divisor.", "Why does Euclidean imply principal ideal domain?", "The smallest nonzero norm element of an ideal generates it.", "numeric_rule"),
    Concept("Principal ideal domains", "In a PID every ideal has one generator.", "This makes ideal structure and divisibility behave much like integers.", r"I=(a)", ["ideals", "rings"], "Not every integral domain is a PID.", "In Z, the ideal of multiples of 6 is generated by 6.", "Every element of the ideal is 6k.", "One generator describes the whole ideal.", "How does a PID help with gcds?", "The ideal generated by a and b is generated by their gcd.", "numeric_rule"),
    Concept("Unique factorization domains", "UFDs are rings where factorization into irreducibles is essentially unique.", "They preserve the arithmetic intuition of prime factorization beyond integers.", r"a=u p_1\cdots p_k", ["domains", "irreducibles"], "Irreducible and prime can differ outside UFD settings.", "Integers factor uniquely into primes up to signs and order.", "12=2*2*3 is unique after rearrangement.", "Uniqueness turns divisibility into reliable bookkeeping.", "Why does unique factorization matter for polynomials?", "It controls roots, factors, and divisibility arguments.", "numeric_rule"),
    Concept("Field extensions", "Field extensions enlarge a field by adding new elements.", "They let equations have roots in a bigger arithmetic universe.", r"K/F", ["fields", "polynomials"], "An extension is a field containing another field, not just a larger set.", "Adjoin sqrt(2) to Q.", "Numbers a+b sqrt(2) form Q(sqrt(2)).", "The extension contains solutions missing from Q.", "What is the degree of an extension?", "It is the dimension of K as a vector space over F.", "numeric_rule"),
    Concept("Algebraic elements", "An algebraic element satisfies a polynomial equation over the base field.", "This connects field extensions to polynomial roots.", r"p(\alpha)=0", ["fields", "polynomials"], "Not every added element is algebraic over the base field.", "sqrt(2) is algebraic over Q.", "It satisfies x^2-2=0.", "A polynomial relation pins the element to the base field.", "What is a minimal polynomial?", "The monic polynomial of least degree over the base field that has the element as a root.", "numeric_rule"),
    Concept("Finite fields", "Finite fields are fields with finitely many elements.", "Their sizes are prime powers, and their arithmetic is central in algebra and coding.", r"|F|=p^n", ["fields", "prime powers"], "Z/nZ is a field only when n is prime.", "Z/5Z has inverses for every nonzero residue.", "2 inverse is 3 modulo 5.", "Every nonzero element can divide.", "Why are finite field sizes prime powers?", "The field has prime characteristic and is a finite vector space over its prime field.", "numeric_rule"),
    Concept("Galois groups", "A Galois group records symmetries of roots that preserve the base field.", "It converts polynomial-solving questions into group actions on roots.", r"\operatorname{Gal}(K/F)", ["field extensions", "automorphisms"], "The group acts on roots while fixing every base-field element.", "For x^2-2 over Q, send sqrt(2) to -sqrt(2).", "That map preserves rational numbers and the equation.", "Root symmetries become group elements.", "What does the Galois group measure?", "It measures how roots can be permuted without changing base-field arithmetic.", "group_action"),
    Concept("Solvable groups", "Solvable groups can be decomposed through abelian layers.", "They connect group structure to solvability of equations by radicals.", r"G^{(n)}=\{e\}", ["normal subgroups", "commutators"], "Solvable does not mean easy; it means a precise derived-series condition holds.", "Every abelian group is solvable.", "Its commutator subgroup is trivial.", "The noncommutative part disappears immediately.", "Why do solvable groups matter in Galois theory?", "They characterize when certain polynomial equations are solvable by radicals.", "group_structure"),
    Concept("Simple groups", "Simple groups have no nontrivial normal subgroups.", "They are the indivisible building blocks in finite group structure.", r"N\triangleleft G\Rightarrow N=\{e\}\text{ or }G", ["normal subgroups", "quotients"], "Simple does not mean small or abelian.", "A cyclic group of prime order is simple.", "Its only subgroups are identity and itself.", "There is no proper normal subgroup to quotient by.", "Why are simple groups like primes?", "They cannot be decomposed by nontrivial normal quotient steps.", "group_cosets"),
    Concept("Commutator subgroups", "The commutator subgroup measures how far a group is from abelian.", "It is generated by all commutators and controls the largest abelian quotient.", r"[G,G]", ["groups", "normal subgroups"], "A trivial commutator subgroup means the group is abelian.", "Compute aba^{-1}b^{-1} for elements a and b.", "If every commutator is identity, then ab=ba.", "Commutators isolate noncommutativity.", "What quotient does the commutator subgroup produce?", "G/[G,G] is the abelianization of G.", "group_structure"),
    Concept("Exact sequences", "Exact sequences track kernels and images across maps.", "They organize algebraic information by requiring each image to equal the next kernel.", r"\operatorname{im} f=\ker g", ["homomorphisms", "kernels"], "Exactness is a local condition at each object in the sequence.", "For maps A -> B -> C, check image in B equals kernel out of B.", "Elements arriving are exactly those that vanish next.", "Exactness records conservation of algebraic information.", "Why are short exact sequences useful?", "They describe one object as built from a subobject and quotient.", "group_homomorphism"),
])

ECONOMICS.extend([
    Concept("Comparative statics", "Comparative statics asks how an equilibrium changes when one parameter changes.", "It compares before-and-after model outcomes without tracing the whole adjustment path.", r"\Delta y/\Delta x", ["equilibrium", "graphs"], "It is not a time path; it is a comparison of model solutions.", "If income rises, demand may shift right.", "The new intersection has a different price and quantity.", "The shift predicts direction of change.", "What must be held fixed in comparative statics?", "Everything except the named parameter change.", "econ_curve"),
    Concept("Price ceilings", "A price ceiling caps legal price below or above equilibrium.", "A binding ceiling below equilibrium creates excess demand.", r"P\leq \bar P", ["supply", "demand"], "A ceiling above equilibrium is not binding.", "Equilibrium price is 10, ceiling is 7.", "Quantity demanded exceeds quantity supplied at 7.", "The gap is a shortage.", "Why can rent control create queues?", "The controlled price raises quantity demanded and lowers supplied housing.", "econ_supply_demand"),
    Concept("Price floors", "A price floor sets a minimum legal price.", "A binding floor above equilibrium creates excess supply.", r"P\geq \underline P", ["supply", "demand"], "A floor below equilibrium is not binding.", "Equilibrium wage is 12, minimum wage is 15.", "Labor supplied can exceed labor demanded.", "The gap is surplus labor in the model.", "What determines whether a floor binds?", "It binds only when the legal minimum is above equilibrium price.", "econ_supply_demand"),
    Concept("Consumer surplus", "Consumer surplus measures buyer gains from trade.", "It is willingness to pay minus price, aggregated over units bought.", r"CS=WTP-P", ["demand", "welfare"], "Consumer surplus is not the same as total spending.", "A buyer willing to pay 10 buys at price 7.", "Surplus is 3 for that unit.", "The value above price becomes buyer gain.", "Where is consumer surplus on a demand graph?", "It is the area below demand and above price.", "econ_supply_demand"),
    Concept("Producer surplus", "Producer surplus measures seller gains from trade.", "It is price minus willingness to accept or marginal cost, aggregated over units sold.", r"PS=P-MC", ["supply", "welfare"], "Producer surplus is not the same as profit when fixed costs matter.", "A seller's marginal cost is 4 and price is 7.", "Producer surplus on that unit is 3.", "The value above marginal cost becomes seller gain.", "Where is producer surplus on a supply graph?", "It is the area above supply and below price.", "econ_supply_demand"),
    Concept("Tax incidence", "Tax incidence asks who really bears a tax burden.", "The burden falls more on the less elastic side of the market.", r"P_b-P_s=t", ["elasticity", "taxes"], "Legal responsibility for paying the tax is not the same as economic burden.", "A tax creates a wedge of 2 between buyer and seller prices.", "If demand is less elastic, buyers bear more of that wedge.", "Elasticity controls burden sharing.", "Why does the less elastic side bear more tax?", "It adjusts quantity less, so price moves more against it.", "econ_elasticity"),
    Concept("Deadweight loss", "Deadweight loss is surplus destroyed by distorted trades.", "It measures mutually beneficial trades that no longer happen.", r"DWL=\frac12bh", ["surplus", "taxes"], "DWL is not tax revenue; it is lost total surplus.", "A tax reduces quantity by 4 and creates wedge 3.", "DWL is one half times 4 times 3, equal to 6.", "The triangle counts lost gains from trade.", "How does elasticity affect deadweight loss?", "More elastic markets usually create larger quantity distortions and larger DWL.", "econ_elasticity"),
    Concept("Indifference curves", "Indifference curves show bundles a consumer ranks equally.", "Their slope records willingness to trade one good for another while utility stays fixed.", r"U(x,y)=\bar U", ["utility", "graphs"], "Higher curves usually mean better bundles, but numbers depend on representation.", "Bundles (3,4) and (4,3) may give the same utility.", "They lie on the same indifference curve for a symmetric utility.", "The curve gathers equal-ranked choices.", "Why do indifference curves usually slope downward?", "More of one good allows less of another while keeping utility constant.", "econ_budget"),
    Concept("Marginal utility", "Marginal utility is the extra utility from one more unit of a good.", "It turns preferences into local tradeoff calculations.", r"MU_x=\partial U/\partial x", ["utility", "calculus"], "Marginal utility depends on the current bundle.", "If U=sqrt(x), marginal utility falls as x rises.", "Each added unit contributes less utility.", "Diminishing marginal utility bends preferences.", "How does marginal utility connect to MRS?", "MRS is the ratio of marginal utilities, with a sign convention.", "econ_curve"),
    Concept("Income elasticity", "Income elasticity measures how demand responds to income changes.", "It distinguishes normal, inferior, and luxury goods by percentage response.", r"E_I=(\%\Delta Q)/(\%\Delta I)", ["elasticity", "demand"], "A positive income elasticity does not mean demand is price-inelastic.", "Income rises 10 percent and quantity rises 5 percent.", "Income elasticity is 0.5.", "Demand rises less than proportionally.", "What does negative income elasticity mean?", "The good is inferior in the model range.", "econ_elasticity"),
    Concept("Cross-price elasticity", "Cross-price elasticity measures how one good's demand responds to another good's price.", "It helps identify substitutes and complements.", r"E_{xy}=(\%\Delta Q_x)/(\%\Delta P_y)", ["elasticity", "demand"], "A sign must be interpreted with the goods named.", "If coffee price rises and tea demand rises, the cross-price elasticity is positive.", "The goods behave as substitutes.", "One market's price moves another market's demand.", "What does a negative cross-price elasticity suggest?", "The goods are complements.", "econ_elasticity"),
    Concept("Marginal product", "Marginal product is extra output from one more input.", "It describes local productivity in a production function.", r"MP_L=\Delta q/\Delta L", ["production", "inputs"], "Marginal product is not average product.", "Output rises from 20 to 27 when labor rises by 1.", "Marginal product of labor is 7.", "The input's local contribution is measured.", "Why can marginal product diminish?", "Crowding or fixed factors can make each extra input less productive.", "econ_curve"),
    Concept("Returns to scale", "Returns to scale ask what happens when all inputs scale together.", "They classify technologies as increasing, constant, or decreasing returns.", r"f(tL,tK)", ["production functions"], "Returns to scale are not the same as marginal product of one input.", "If doubling all inputs doubles output, returns are constant.", "The whole production plan scales proportionally.", "Scale behavior shapes long-run firm size.", "What does increasing returns to scale mean?", "Doubling all inputs more than doubles output.", "econ_curve"),
    Concept("Average cost", "Average cost spreads total cost over output.", "It helps compare per-unit cost at different production scales.", r"AC=TC/q", ["costs", "division"], "Average cost and marginal cost can move differently.", "Total cost is 100 at q=20.", "Average cost is 5.", "Each unit carries five units of cost on average.", "When does average cost fall?", "When marginal cost is below average cost.", "econ_curve"),
    Concept("Marginal cost", "Marginal cost is the extra cost of one more unit.", "It drives output decisions because firms compare marginal cost to marginal revenue or price.", r"MC=\Delta TC/\Delta q", ["costs", "margins"], "Marginal cost is not total cost divided by quantity.", "Cost rises from 20 to 26 when output rises by 1.", "Marginal cost is 6.", "The next unit's cost is what matters for the decision.", "Why does a competitive firm set P=MC?", "It expands output while price exceeds marginal cost and stops when they match.", "econ_curve"),
    Concept("Shutdown rule", "The shutdown rule compares price to average variable cost in the short run.", "A firm produces only if revenue covers avoidable variable costs.", r"P\geq AVC", ["costs", "firms"], "Fixed costs do not determine short-run shutdown if they are sunk.", "Price is 4 and AVC is 5.", "The firm shuts down in the short run.", "Producing would lose more than fixed cost alone.", "Why can a firm operate at an accounting loss?", "If price covers variable cost, it still contributes toward fixed cost.", "econ_curve"),
    Concept("Marginal revenue", "Marginal revenue is extra revenue from selling one more unit.", "Market power makes marginal revenue differ from price.", r"MR=\Delta TR/\Delta q", ["revenue", "demand"], "For a price taker, MR equals price; for a monopolist, it usually does not.", "Demand is P=20-Q, so TR=20Q-Q^2.", "MR=20-2Q.", "Selling more lowers price on previous units.", "Why is monopoly MR below demand?", "Lowering price to sell another unit reduces revenue on existing units.", "econ_supply_demand"),
    Concept("Price discrimination", "Price discrimination charges different prices for related units or buyers.", "It converts more willingness to pay into producer revenue when resale is limited.", r"P_i\neq P_j", ["monopoly", "demand"], "Different prices alone are not discrimination if costs differ.", "A student discount charges lower price to students.", "The firm separates demand groups by willingness to pay.", "Segmentation changes surplus distribution.", "What condition helps price discrimination work?", "The firm needs market power and limited resale between groups.", "econ_supply_demand"),
    Concept("Nash equilibrium", "A Nash equilibrium is a strategy profile where no player wants to deviate alone.", "It is the basic stability concept for strategic interaction.", r"s_i\in BR_i(s_{-i})", ["game theory", "best responses"], "Nash equilibrium does not always mean socially best.", "Two firms choose high or low output.", "If each is best responding to the other, the profile is Nash.", "Stability comes from mutual best responses.", "How do you check a Nash equilibrium?", "Hold others fixed and see whether each player can improve by changing strategy.", "state_machine"),
    Concept("Dominant strategies", "A dominant strategy is best regardless of what others do.", "It simplifies games because one action wins across all rival actions.", r"u_i(s_i,s_{-i})\geq u_i(s'_i,s_{-i})", ["game theory", "payoffs"], "Dominance is stronger than being part of a Nash equilibrium.", "If confessing gives a prisoner a better payoff no matter what the other does, it is dominant.", "The choice does not depend on beliefs about the other player.", "Dominance removes strategic uncertainty.", "Can both players have dominant strategies?", "Yes, and their combination is a dominant-strategy equilibrium.", "state_machine"),
    Concept("Adverse selection", "Adverse selection arises when hidden type affects market participation.", "Bad types can crowd out good types when prices cannot reflect private information.", r"E[value\mid participate]", ["information", "markets"], "It is about hidden information before trade, not hidden action after trade.", "Used-car buyers cannot observe quality perfectly.", "Low expected quality lowers willingness to pay.", "High-quality sellers may leave the market.", "How can screening reduce adverse selection?", "It lets types separate by observable choices or signals.", "econ_curve"),
    Concept("Moral hazard", "Moral hazard arises when hidden action changes after a contract is signed.", "Insurance or contracts can weaken incentives to avoid costly behavior.", r"action\ hidden\ after\ contract", ["information", "incentives"], "Moral hazard is not the same as adverse selection.", "After getting insurance, a driver may take less care.", "The action is hard for the insurer to observe.", "Hidden behavior changes expected costs.", "How can deductibles reduce moral hazard?", "They keep the insured party exposed to some marginal cost.", "econ_curve"),
    Concept("Coase theorem", "The Coase theorem says bargaining can solve externalities under ideal conditions.", "If property rights are clear and transaction costs are zero, parties can bargain to efficiency.", r"MB=MC", ["externalities", "bargaining"], "The theorem's conditions are strong and often fail in practice.", "A factory and residents bargain over pollution reduction.", "If bargaining is costless, they can choose efficient abatement.", "Assignment of rights affects distribution, not efficiency, under ideal assumptions.", "Why do transaction costs matter?", "They can prevent efficient bargains from happening.", "econ_curve"),
    Concept("Common resources", "Common resources are rival but hard to exclude people from using.", "They can be overused because each user ignores part of the social cost.", r"MSC>Private\ MC", ["externalities", "public goods"], "Common resources are not the same as pure public goods.", "A fishery can be depleted by too much harvesting.", "Each fisher captures private benefit but shares depletion cost.", "Private incentives exceed efficient use.", "How can policy address common-resource overuse?", "Use quotas, property rights, taxes, or regulation to align incentives.", "econ_curve"),
])

DOMAIN_LIBRARY: dict[str, list[Concept]] = {
    "group_theory": GROUP_THEORY,
    "algorithms": ALGORITHMS,
    "physics": PHYSICS_MECHANICS,
    "economics": ECONOMICS,
    "linear_algebra": LINEAR_ALGEBRA,
}

DOMAIN_KEYWORDS: dict[str, dict[str, int]] = {
    "group_theory": {"18-703": 12, "modern algebra": 12, "abstract algebra": 12, "group theory": 12, "groups": 5, " group ": 4, "subgroup": 7, "coset": 7, "homomorphism": 8, "isomorphism": 8, "normal subgroup": 8, "quotient group": 8, "ring": 5, "field": 5},
    "algorithms": {"6-006": 12, "algorithm": 6, "algorithms": 8, "data structure": 7, "complexity": 6, "dynamic programming": 8, "graph traversal": 7, "breadth-first": 7, "depth-first": 7, "hash": 5, "sorting": 5},
    "physics": {"8-01": 12, "classical mechanics": 12, "mechanics": 8, "newton": 7, "force": 5, "acceleration": 5, "momentum": 6, "kinematics": 7, "energy": 5, "oscillation": 6, "torque": 6},
    "economics": {"14.01": 12, "14-01": 12, "microeconomics": 12, "economics": 8, "supply": 4, "demand": 4, "elasticity": 7, "consumer": 5, "market": 5, "marginal": 5, "externality": 7, "game theory": 7},
    "linear_algebra": {"18-06": 12, "linear algebra": 12, "matrix": 5, "matrices": 5, "eigen": 7, "vector space": 6, "vectors": 4, "linear transformation": 7, "least squares": 7, "singular value": 7},
}

SOURCE_TERM_BLOCKLIST = {
    "about", "accessibility", "account", "assignment", "assignments", "browse", "calendar", "citation",
    "creative commons", "download", "download file", "download files", "educator", "exams", "feedback",
    "help", "home", "license", "licensed", "menu", "mit opencourseware", "ocw", "open learning",
    "opencourseware", "privacy", "problem set", "problem sets", "readings", "related resources", "homework", "exam", "final exam",
    "resource", "resources", "search", "share", "site", "skip", "terms", "transcript", "video",
    "video lectures", "view video", "youtube",
    "all rights", "also available", "available online", "back to top", "cookie", "cookies", "course info",
    "course material", "course materials", "course menu", "course number", "course site", "courseware",
    "department", "departments", "description", "download course", "download transcript", "download video",
    "faculty", "file", "files", "instructor", "instructors", "language", "learn", "learning resource",
    "left navigation", "legal notices", "level", "metadata", "navigation", "next lecture", "previous lecture",
    "online publication", "open license", "publication date", "related content", "rights reserved",
    "search ocw", "share this", "social media", "student", "students", "topics", "undergraduate",
    "back", "top", "studies",
}

SOURCE_TERM_BLOCK_PATTERNS = (
    "download", "opencourseware", "creative commons", "license", "youtube", "transcript",
    "course home", "site menu", "privacy", "terms of use", "donate", "learn more", "massachusetts", "institute", "member", "contact", "educator", "learner",
    "all rights", "back to top", "cookie", "course info", "course materials", "course site", "department", "download file",
    "download transcript", "download video", "left navigation", "legal notice", "metadata", "mit open", "ocw", "online publication",
    "previous lecture", "related resource", "rights reserved", "search this", "share this", "skip to",
)

SOURCE_TERM_PREFERRED_MARKERS = {
    "algorithm", "array", "basis", "budget", "consumer", "coset", "cost", "demand", "domain", "elasticity",
    "energy", "equilibrium", "field", "force", "game", "graph", "group", "ideal", "kernel", "market",
    "matrix", "marginal", "momentum", "orbit", "price", "recurrence", "ring", "sequence", "series",
    "subgroup", "supply", "surplus", "tax", "torque", "utility", "vector", "wave",
}

SOURCE_TERM_CONTEXT_MARKERS = {
    "definition", "derive", "equation", "example", "lecture", "lemma", "method", "model", "proof", "problem",
    "section", "session", "solve", "syllabus", "theorem", "unit",
}




class HtmlExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.text: list[str] = []
        self.links: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "svg", "noscript"}:
            self.skip += 1
            return
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append(href)
        if tag in {"title", "h1", "h2", "h3", "p", "li", "td", "th"}:
            self.text.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "svg", "noscript"} and self.skip:
            self.skip -= 1
        elif tag in {"title", "h1", "h2", "h3", "p", "li", "td", "th"}:
            self.text.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.skip:
            cleaned = re.sub(r"\s+", " ", data).strip()
            if cleaned:
                self.text.append(cleaned)

    def clean_text(self) -> str:
        return re.sub(r"\n{3,}", "\n\n", " ".join(self.text)).strip()


def slugify(text: str, fallback: str = "course") -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:72] or fallback


def plain_math(value: str) -> str:
    out = str(value)
    frac_re = re.compile(r"\\frac\s*\{([^{}]+)\}\s*\{([^{}]+)\}")
    out = re.sub(r"\\text\s*\{([^{}]*)\}", r" \1 ", out)
    out = re.sub(r"\^\{\(([^{}]+)\)\}", r" superscript (\1) ", out)
    while frac_re.search(out):
        out = frac_re.sub(lambda m: f"({m.group(1)}) / ({m.group(2)})", out)
    replacements = [
        (r"\operatorname", ""),
        (r"\{", "{"),
        (r"\}", "}"),
        (r"\left", ""),
        (r"\right", ""),
        (r"\cdots", "..."),
        (r"\quad", " "),
        (r"\ldots", "..."),
        (r"\Rightarrow", "=>"),
        (r"\leq", " <= "),
        (r"\geq", " >= "),
        (r"\neq", " != "),
        (r"\cong", " ~= "),
        (r"\triangleleft", " normal in "),
        (r"\mid", " divides "),
        (r"\in", " in "),
        (r"\langle", "<"),
        (r"\rangle", ">"),
        (r"\ker", "ker"),
        (r"\im", "im"),
        (r"\varphi", "phi"),
        (r"\phi", "phi"),
        (r"\pi", "pi"),
        (r"\alpha", "alpha"),
        (r"\Delta", "Delta "),
        (r"\times", " times "),
        (r"\%", " % "),
        (r"\lambda", "lambda"),
        (r"\Lambda", "Lambda"),
        (r"\Sigma", "Sigma"),
        (r"\vec", ""),
        (r"\hat", ""),
        (r"\cdot", " * "),
        (r"\det", "det"),
        (r"\dim", "dim"),
        (r"\sum", "sum "),
        (r"\prod", "prod "),
        (r"\mathbb", ""),
        (r"\mathcal", ""),
        (r"\mathbf", ""),
    ]
    for old, new in replacements:
        out = out.replace(old, new)
    out = re.sub(r"\^\{\s*-\s*1\s*\}", " inverse ", out)
    out = re.sub(r"\^\{\s*T\s*\}", " transpose ", out)
    out = re.sub(r"\^\s*T\b", " transpose ", out)
    out = re.sub(r"\^\s*\{?([A-Za-z0-9]+)\}?", r" to the \1 ", out)
    out = out.replace(r"\|", " norm ")
    out = out.replace(r"\Lambda", "Lambda")
    out = out.replace("{", "").replace("}", "")
    out = re.sub(r"\b(span|rank|det|dim|nullity|proj|ker|im)(?=[A-Za-z])", r"\1 ", out)
    out = re.sub(r"\s*([=+*/<>])\s*", r" \1 ", out)
    out = re.sub(r"_\s*\{([^{}]+)\}", r" sub \1", out)
    out = re.sub(r"_\s*([A-Za-z0-9]+)", r" sub \1", out)
    out = re.sub(r"\b([A-Za-z]) sub ([A-Za-z])([A-Za-z])\b", r"\1 sub \2 \3", out)
    out = re.sub(r"\b(MU|MB|MC|MR|MSB|MSC) sub ([A-Za-z])", r"\1_\2", out)
    out = re.sub(r"<\s+=", "<=", out)
    out = re.sub(r">\s+=", ">=", out)
    out = re.sub(r"!\s+=", "!=", out)
    out = re.sub(r"\)(?=[A-Za-z])", ") ", out)
    return re.sub(r"\s+", " ", out).strip()


def screen_math(value: str) -> str:
    out = plain_math(value)
    out = re.sub(r"\bprod sub ([A-Za-z0-9]+)\b", r"product over \1", out)
    out = re.sub(r"\bsum sub ([A-Za-z0-9]+)\b", r"sum over \1", out)
    out = re.sub(r"\b([A-Za-z]+) sub ([A-Za-z0-9]+)\b", r"\1_\2", out)
    out = re.sub(r"\b([APU])([xvb])\b", r"\1 \2", out)
    out = re.sub(r"\^(?!\s)([A-Za-z0-9]+)", r" to the \1", out)
    out = re.sub(r"\s*([=+*/<>])\s*", r" \1 ", out)
    out = re.sub(r"\s+-\s+", " - ", out)
    out = re.sub(r"<\s+=", "<=", out)
    out = re.sub(r">\s+=", ">=", out)
    out = re.sub(r"!\s+=", "!=", out)
    return re.sub(r"\s+", " ", out).strip()


def fetch_bytes(url: str, accept: str = "*/*") -> tuple[bytes, str, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "course-shorts-skills/0.1", "Accept": accept})
    with urllib.request.urlopen(req, timeout=15) as response:
        return response.read(MAX_FETCH_BYTES), response.headers.get("Content-Type", ""), response.geturl()


def parse_html(raw: bytes, content_type: str, base: str) -> tuple[str, list[str]]:
    encoding = "utf-8"
    match = re.search(r"charset=([\w-]+)", content_type, re.I)
    if match:
        encoding = match.group(1)
    parser = HtmlExtractor()
    parser.feed(raw.decode(encoding, errors="replace"))
    links = []
    for link in parser.links:
        normalized = urllib.parse.urljoin(base, link).split("#", 1)[0]
        if normalized and normalized not in links:
            links.append(normalized)
    return parser.clean_text(), links


def pdf_text(raw: bytes) -> str:
    try:
        import fitz  # type: ignore
    except Exception:
        return ""
    doc = fitz.open(stream=raw, filetype="pdf")
    page_count = min(doc.page_count, PDF_TEXT_PAGES)
    return "\n".join(doc[i].get_text("text") for i in range(page_count))


def title_from_url(url: str) -> str:
    parts = [part for part in urllib.parse.urlparse(url).path.split("/") if part]
    name = parts[-1] if parts else "course"
    name = re.sub(r"-spring-\d{4}|-fall-\d{4}|-january-iap-\d{4}", "", name)
    name = re.sub(r"^\d+[-.]?\d*\w*-?", "", name)
    return name.replace("-", " ").strip().title() or "Course"


def course_prefix(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    parts = [p for p in parsed.path.split("/") if p]
    if "courses" in parts:
        idx = parts.index("courses")
        parts = parts[: idx + 2]
    else:
        parts = parts[:2]
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, "/" + "/".join(parts), "", "", ""))


def link_score(url: str) -> int:
    lower = url.lower()
    score = 0
    for term in ("syllabus", "calendar", "unit", "session", "lecture", "note", "notes", "reading", "readings", "resource", "problem", "assignment", "transcript", "video", "pdf"):
        if term in lower:
            score += 3
    if lower.endswith(".pdf"):
        score += 5
    return score


def sample_pack() -> dict[str, object]:
    return {
        "title": "Linear Algebra",
        "source_url": "sample:linear_algebra",
        "materials": [
            {"kind": "sample", "title": "Linear Algebra core sample", "url": "sample:linear_algebra", "text": "Vectors, linear combinations, matrix-vector multiplication, systems, elimination, column space, nullspace, projections, least squares, eigenvectors, eigenvalues, SVD."}
        ],
        "warnings": [],
    }


def cmd_extract(args: argparse.Namespace) -> None:
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if args.sample:
        pack = sample_pack()
        write_json(out / "source_pack.json", pack)
        print(out / "source_pack.json")
        return

    root = args.url
    prefix = course_prefix(root)
    parsed_root = urllib.parse.urlparse(root)
    materials: list[dict[str, str]] = []
    warnings: list[str] = []
    seen: set[str] = set()
    try:
        raw, ctype, final = fetch_bytes(root, "text/html,text/plain,application/xhtml+xml")
        text, links = parse_html(raw, ctype, final)
    except Exception as exc:
        raise SystemExit(f"extract failed: {exc}")
    materials.append({"kind": "page", "title": "Course landing page", "url": final, "text": text[:120_000]})
    seen.add(final)

    def allowed(link: str) -> bool:
        parsed = urllib.parse.urlparse(link)
        return parsed.scheme in {"http", "https"} and parsed.netloc == parsed_root.netloc and link.startswith(prefix)

    raw_candidates = [link for link in links if allowed(link)]
    scored_candidates = sorted(((link_score(link), link) for link in raw_candidates), key=lambda item: item[0], reverse=True)
    candidates = [link for score, link in scored_candidates if score > 0]
    if not candidates:
        candidates = [link for _score, link in scored_candidates]
    candidates = candidates[:MAX_CRAWL_CANDIDATES]
    pages = 0
    pdfs = 0
    cursor = 0
    while cursor < len(candidates) and (pages < args.max_pages or pdfs < args.max_pdfs):
        url = candidates[cursor]
        cursor += 1
        if url in seen:
            continue
        try:
            raw, ctype, final = fetch_bytes(url)
        except Exception:
            continue
        seen.add(url)
        lower = final.lower()
        if "pdf" in ctype.lower() or lower.endswith(".pdf"):
            if pdfs >= args.max_pdfs:
                continue
            text = pdf_text(raw)
            if text.strip():
                pdfs += 1
                materials.append({"kind": "pdf", "title": Path(urllib.parse.urlparse(final).path).name or "PDF", "url": final, "text": text[:120_000]})
            else:
                warnings.append(f"Could not extract PDF text: {final}")
        elif "html" in ctype.lower() or raw[:200].lower().lstrip().startswith((b"<!doctype", b"<html")):
            if pages >= args.max_pages:
                continue
            text, nested = parse_html(raw, ctype, final)
            if text.strip():
                pages += 1
                materials.append({"kind": "page", "title": title_from_url(final), "url": final, "text": text[:120_000]})
            for link in nested:
                if allowed(link) and link not in seen and link not in candidates and link_score(link) > 0 and len(candidates) < MAX_CRAWL_CANDIDATES:
                    candidates.append(link)
    pack = {"title": title_from_url(root), "source_url": root, "materials": materials, "warnings": warnings}
    write_json(out / "source_pack.json", pack)
    print(out / "source_pack.json")


def domain_score(text: str, keywords: dict[str, int]) -> int:
    padded = f" {text.lower()} "
    score = 0
    for term, weight in keywords.items():
        score += padded.count(term.lower()) * weight
    return score


def choose_concepts(pack: dict[str, object], max_shorts: int) -> list[Concept]:
    text = json.dumps(pack).lower()
    ranked = sorted(
        ((domain, domain_score(text, keywords)) for domain, keywords in DOMAIN_KEYWORDS.items()),
        key=lambda item: item[1],
        reverse=True,
    )
    best_domain, best_score = ranked[0]
    second_score = ranked[1][1] if len(ranked) > 1 else 0
    if best_score >= 8 and best_score >= second_score:
        concepts = list(DOMAIN_LIBRARY[best_domain])
        return fill_concepts_from_source(pack, concepts, max_shorts, best_domain)
    return fill_concepts_from_source(pack, [], max_shorts, None)


def fill_concepts_from_source(pack: dict[str, object], concepts: list[Concept], max_shorts: int, domain: str | None) -> list[Concept]:
    out = list(concepts[:max_shorts])
    existing = {concept.name.lower() for concept in out}
    for term in frequent_terms(source_text(pack)):
        if len(out) >= max_shorts:
            break
        if not is_course_vocabulary_term(term):
            continue
        normalized = term.lower()
        if any(normalized in name or name in normalized for name in existing):
            continue
        concept = source_term_concept(term, domain)
        out.append(concept)
        existing.add(concept.name.lower())
    return out[:max_shorts]


def source_term_concept(term: str, domain: str | None) -> Concept:
    title = re.sub(r"\s+", " ", term).strip().title()
    lower = title.lower()
    if domain == "group_theory":
        visual = "group_structure"
        formula = r"(G,*)"
        prereqs = ["groups", "sets", "maps"]
        if any(word in lower for word in ("coset", "quotient", "normal", "lagrange")):
            visual, formula, prereqs = "group_cosets", r"gH", ["subgroups", "equivalence classes"]
        elif any(word in lower for word in ("homomorphism", "isomorphism", "kernel", "image")):
            visual, formula, prereqs = "group_homomorphism", r"\phi(ab)=\phi(a)\phi(b)", ["groups", "functions"]
        elif any(word in lower for word in ("action", "orbit", "stabilizer", "permutation", "symmetry")):
            visual, formula, prereqs = "group_action", r"Gx", ["groups", "sets"]
        elif any(word in lower for word in ("ring", "field", "ideal")):
            formula, prereqs = r"a(b+c)=ab+ac", ["groups", "operations"]
        return Concept(
            title,
            f"{title} is a structural idea that organizes how algebraic objects behave.",
            f"Study {title} by naming the objects, the operation, and the property being preserved or tested.",
            formula,
            prereqs,
            "Do not use the term as a label only; check the hypotheses in a small example.",
            f"Choose a small group or algebraic structure involving {title}.",
            "Name the identity, operation, relevant subset or map, then verify one defining condition.",
            "The example shows which structure is preserved and which assumptions matter.",
            f"How would {title} change the way you classify a finite example?",
            "Identify the objects, check the required property, and compare with a near-miss example.",
            visual,
        )
    if domain == "economics":
        visual = "econ_curve"
        formula = r"Y=f(X)"
        prereqs = ["graphs", "marginal reasoning"]
        if any(word in lower for word in ("tax", "incidence", "deadweight", "wedge")):
            visual, formula, prereqs = "econ_tax_wedge", r"P_b-P_s=t", ["graphs", "markets", "elasticity"]
        elif any(word in lower for word in ("demand", "supply", "market", "equilibrium", "surplus")):
            visual, formula, prereqs = "econ_supply_demand", r"Q_s(P)=Q_d(P)", ["graphs", "markets"]
        elif any(word in lower for word in ("elasticity", "percent", "response")):
            visual, formula, prereqs = "econ_elasticity", r"E=(\%\Delta Q)/(\%\Delta P)", ["percent changes", "demand"]
        elif any(word in lower for word in ("budget", "consumer", "utility", "preference", "income", "mrs")):
            visual, formula, prereqs = "econ_budget", r"p_x x+p_y y\leq I", ["prices", "choice"]
        return Concept(
            title,
            f"{title} is a modeling idea for comparing incentives, constraints, and marginal choices.",
            f"Study {title} by identifying the decision maker, the constraint, the margin, and the predicted change.",
            formula,
            prereqs,
            "Do not read a curve or equation without naming what is held fixed and what is changing.",
            f"Set up a small numerical market or choice example involving {title}.",
            "Write the relevant curve, constraint, or marginal condition and solve one comparison.",
            "The example connects the economic story to a visible curve or decision rule.",
            f"What does {title} predict when one price, income, or marginal cost changes?",
            "State the changed input, trace the curve or constraint, and explain the new choice or equilibrium.",
            visual,
        )
    return Concept(
        title,
        f"{title} is a core idea in this course.",
        f"Understand {title} by connecting definition, formula, and example.",
        title,
        ["course definitions", "worked examples"],
        "Do not memorize the term without testing it on a concrete example.",
        f"Pick a small numerical or symbolic example involving {title}.",
        "Work through one substitution or transformation step.",
        "The example should make the definition testable.",
        f"Where does {title} appear in an application from the course?",
        "Name the inputs, rule, and output.",
        "numeric_rule",
    )


def source_term_quality(term: str, count: int = 1) -> int:
    normalized = re.sub(r"\s+", " ", term.lower()).strip()
    words = normalized.split()
    score = count * 3 + min(len(words), 3)
    if any(word in SOURCE_TERM_PREFERRED_MARKERS for word in words):
        score += 18
    if any(marker in normalized for marker in SOURCE_TERM_CONTEXT_MARKERS):
        score += 6
    if len(words) == 1 and normalized not in SOURCE_TERM_PREFERRED_MARKERS:
        score -= 4
    if any(word in {"course", "lecture", "notes", "problem", "resource", "section"} for word in words):
        score -= 5
    if any(pattern in normalized for pattern in SOURCE_TERM_BLOCK_PATTERNS):
        score -= 60
    return score


def frequent_terms(text: str) -> list[str]:
    stop = {
        "course", "lecture", "lectures", "chapter", "section", "the", "and", "for", "with", "this", "that",
        "from", "have", "notes", "page", "problem", "problems", "example", "examples", "using", "where",
        "there", "which", "then", "than", "into", "will", "shall", "their", "about", "between", "through",
        "also", "available", "content", "copyright", "download", "file", "files", "instructor", "learn", "learning",
        "material", "materials", "metadata", "navigation", "online", "open", "publication", "related", "reserved", "rights",
        "share", "site", "student", "students", "study", "studies", "topic", "topics", "undergraduate", "back", "top",
    }
    words = re.findall(r"\b[a-zA-Z][a-zA-Z-]{3,}\b", text.lower())
    counts: dict[str, int] = {}
    for word in words:
        if word not in stop and is_course_vocabulary_term(word):
            counts[word] = counts.get(word, 0) + 1
    phrase_counts: dict[str, int] = {}
    usable = [w for w in words if w not in stop]
    for size in (2, 3):
        for i in range(max(0, len(usable) - size + 1)):
            phrase = " ".join(usable[i : i + size])
            if len(set(phrase.split())) > 1 and is_course_vocabulary_term(phrase):
                phrase_counts[phrase] = phrase_counts.get(phrase, 0) + 1
    ranked_phrases = [
        p for p, n in sorted(
            phrase_counts.items(),
            key=lambda item: (source_term_quality(item[0], item[1]), item[1], len(item[0])),
            reverse=True,
        ) if n >= 2
    ]
    ranked_words = [
        w for w, n in sorted(
            counts.items(),
            key=lambda item: (source_term_quality(item[0], item[1]), item[1]),
            reverse=True,
        )
    ]
    out: list[str] = []
    for term in ranked_phrases + ranked_words:
        normalized = term.strip()
        if normalized and all(normalized not in existing and existing not in normalized for existing in out):
            out.append(normalized)
    return out

def source_text(pack: dict[str, object]) -> str:
    return "\n".join(str(m.get("text", "")) for m in pack.get("materials", []) if isinstance(m, dict))


def is_course_vocabulary_term(term: str) -> bool:
    normalized = re.sub(r"\s+", " ", term.lower()).strip(" -_:;,.()[]")
    if len(normalized) < 4 or len(normalized) > 60:
        return False
    if normalized in SOURCE_TERM_BLOCKLIST:
        return False
    if any(pattern in normalized for pattern in SOURCE_TERM_BLOCK_PATTERNS):
        return False
    words = normalized.split()
    if len(words) > 4:
        return False
    if any(word in SOURCE_TERM_BLOCKLIST for word in words):
        return False
    if not any(re.search(r"[a-z]", word) for word in words):
        return False
    if re.fullmatch(r"(?:lecture|session|unit|chapter|section)\s+\d+[a-z]?", normalized):
        return False
    if re.fullmatch(r"(?:pdf|html|www|http|https|email|copyright|reserved)s?", normalized):
        return False
    generic_words = {"activity", "available", "content", "description", "information", "material", "materials", "overview", "resource", "resources", "topic", "topics"}
    if all(word in generic_words for word in words):
        return False
    return True


def source_coverage_terms(pack: dict[str, object], shorts: list[dict[str, object]], limit: int = 80) -> list[str]:
    existing = {str(short.get("concept", "")).lower() for short in shorts}
    terms: list[str] = []
    for term in frequent_terms(source_text(pack)):
        if not is_course_vocabulary_term(term):
            continue
        if any(term in concept or concept in term for concept in existing):
            continue
        if term not in terms:
            terms.append(term)
        if len(terms) >= limit:
            break
    return terms


def source_snippets(pack: dict[str, object], term: str, limit: int = 2) -> list[str]:
    snippets: list[str] = []
    term_lower = term.lower().strip()
    if len(term_lower) < 3:
        return snippets
    for material in pack.get("materials", []):
        if not isinstance(material, dict):
            continue
        text = re.sub(r"\s+", " ", str(material.get("text", ""))).strip()
        if not text:
            continue
        lower = text.lower()
        pos = 0
        attempts = 0
        while len(snippets) < limit and attempts < 24:
            idx = lower.find(term_lower, pos)
            if idx < 0:
                break
            start = max(0, idx - 180)
            end = min(len(text), idx + len(term_lower) + 220)
            while start > 0 and text[start] not in ".?!":
                start -= 1
            if start > 0:
                start += 1
            while end < len(text) and text[end] not in ".?!":
                end += 1
            cleaned = re.sub(r"\s+", " ", text[start:end].strip(" .?!"))
            if any(pattern in cleaned.lower() for pattern in SOURCE_TERM_BLOCK_PATTERNS):
                pos = idx + len(term_lower)
                attempts += 1
                continue
            if 40 <= len(cleaned) <= 360 and cleaned not in snippets:
                snippets.append(cleaned)
            pos = idx + len(term_lower)
            attempts += 1
        if len(snippets) >= limit:
            return snippets
    return snippets


def cmd_plan(args: argparse.Namespace) -> None:
    run = Path(args.run)
    pack = read_json(run / "source_pack.json")
    concepts = choose_concepts(pack, args.max_shorts)
    shorts = [
        {
            "index": i,
            "concept": c.name,
            "hook": c.hook,
            "intuition": c.intuition,
            "formula": c.formula,
            "plain_formula": plain_math(c.formula),
            "prerequisites": c.prerequisites,
            "misconception": c.misconception,
            "worked_example": {"setup": c.example_setup, "calculation": c.example_calc, "takeaway": c.example_takeaway},
            "question_prompt": {"question": c.application_question, "answer": c.application_answer},
            "visual_type": c.visual_type,
        }
        for i, c in enumerate(concepts, start=1)
    ]
    for i, short in enumerate(shorts):
        next_concepts = [s["concept"] for s in shorts[i + 1 : i + 4]]
        short["key_concept"] = f"{short['concept']}: {short['hook']}"
        short["concept_explanation"] = (
            f"{short['intuition']} The worked example makes the idea testable: "
            f"{short['worked_example']['takeaway']}"
        )
        short["recognition_cue"] = (
            f"Use this concept when a problem asks you to identify the rule, structure, or quantity behind "
            f"{short['concept'].lower()} and then check it with a concrete example."
        )
        short["concept_connections"] = {
            "builds_on": short["prerequisites"],
            "prepares_for": next_concepts,
        }
    plan = {
        "course_title": pack.get("title", "Course"),
        "source_url": pack.get("source_url"),
        "shorts": shorts,
    }
    write_json(run / "short_plan.json", plan)
    print(run / "short_plan.json")


def latex_escape(s: str) -> str:
    return (s.replace("\\", r"\textbackslash{}").replace("&", r"\&").replace("%", r"\%").replace("$", r"\$")
             .replace("#", r"\#").replace("_", r"\_").replace("^", r"\^{}").replace("~", r"\textasciitilde{}")
             .replace("{", r"\{").replace("}", r"\}"))


FORMULA_MACROS = {
    "alpha", "beta", "cdot", "cdots", "cong", "cos", "det", "dim", "Delta", "epsilon", "exp",
    "frac", "ge", "geq", "hat", "im", "in", "ker", "lambda", "Lambda", "langle", "ldots",
    "le", "leq", "left", "ln", "log", "mathbb", "mathcal", "mathbf", "mid", "mu", "neq",
    "notin", "operatorname", "phi", "pi", "prod", "rangle", "right", "Rightarrow", "sigma",
    "Sigma", "sin", "sqrt", "subset", "subseteq", "sum", "tan", "text", "theta", "times",
    "triangleleft", "varphi", "vec",
}


def formula_text_value(formula: str) -> str:
    text_value = str(formula).replace(r"\ ", " ").replace("\\", " ")
    return re.sub(r"\s+", " ", plain_math(text_value)).strip()


def formula_has_unknown_macros(formula: str) -> bool:
    return any(match.group(1) not in FORMULA_MACROS for match in re.finditer(r"\\([A-Za-z]+)", str(formula)))


def formula_like_string(formula: str) -> bool:
    raw = str(formula).strip()
    if not raw:
        return False
    if MATRIX_LITERAL_RE.search(raw) or ROW_MATRIX_RE.fullmatch(raw):
        return True
    has_relation = bool(re.search(r"(?:=|<=|>=|<|>|\\leq|\\geq|\\neq|\\subseteq|\\subset|\\in|\\notin|\\Rightarrow)", raw))
    has_math_structure = bool(re.search(r"[0-9_^{}()+*/]|\\(?:" + "|".join(sorted(FORMULA_MACROS)) + r")\b", raw))
    if has_relation or has_math_structure:
        words = re.findall(r"[A-Za-z]{3,}", re.sub(r"\\[A-Za-z]+", " ", raw))
        prose_markers = {"after", "before", "because", "contract", "hidden", "private", "public", "where", "when"}
        return len([word for word in words if word.lower() in prose_markers]) <= 2 or has_relation
    return False


def sanitize_formula_latex(formula: str) -> str:
    raw = str(formula).strip()
    if not raw:
        return r"\text{formula cue not recorded}"
    if not formula_like_string(raw):
        return r"\text{" + latex_escape(formula_text_value(raw) or raw).replace("\\textbackslash{}", "") + "}"
    work = raw.replace(r"\ ", " ")

    def macro_repl(match: re.Match[str]) -> str:
        name = match.group(1)
        return "\\" + name if name in FORMULA_MACROS else name

    work = re.sub(r"\\([A-Za-z]+)", macro_repl, work)

    def relation_side_repl(side_text: str) -> str:
        side = side_text.strip()
        if re.fullmatch(r"[A-Za-z][A-Za-z ]{1,32}", side) and " " in side:
            return r"\mathrm{" + latex_escape(side).replace(" ", r"\ ") + "}"
        if re.fullmatch(r"[A-Z]{2,8}", side):
            return r"\mathrm{" + side + "}"
        return side

    relation_tokens = {
        "<=": r"\leq",
        ">=": r"\geq",
        "!=": r"\neq",
        "<": "<",
        ">": ">",
        "=": "=",
        r"\leq": r"\leq",
        r"\geq": r"\geq",
        r"\neq": r"\neq",
        r"\Rightarrow": r"\Rightarrow",
    }
    parts = re.split(r"(<=|>=|!=|=|<|>|\\leq|\\geq|\\neq|\\Rightarrow)", work)
    if len(parts) > 1:
        formatted_parts = []
        for i, part in enumerate(parts):
            if i % 2 == 0:
                formatted_parts.append(relation_side_repl(part))
            else:
                formatted_parts.append(" " + relation_tokens.get(part, part) + " ")
        work = "".join(formatted_parts)
    work = re.sub(r"\b([A-Z]{2,})(?=_|\()", r"\\operatorname{\1}", work)
    return re.sub(r"\s+", " ", work).strip()


def latex_formula_display(short: dict[str, object]) -> str:
    return sanitize_formula_latex(str(short.get("formula", "")))


MATRIX_LITERAL_RE = re.compile(r"\[\[[^\]]+\](?:\s*,\s*\[[^\]]+\])*\]")
ROW_MATRIX_RE = re.compile(r"\[[^\[\],]+(?:\s+[^\[\],]+)+\]")
TUPLE_LITERAL_RE = re.compile(r"\([^()]*,[^()]*\)")
ASSIGNMENT_RE = re.compile(
    r"(?<![A-Za-z0-9_])([A-Za-z](?:_?[A-Za-z0-9]+)?)\s*=\s*"
    r"(\[\[[^\]]+\](?:\s*,\s*\[[^\]]+\])*\]|\[[^\[\]]+\]|\([^()]*,[^()]*\)|diag\([^()]+\))"
)
MATH_FUNCTIONS = {
    "sin", "cos", "tan", "log", "ln", "exp", "sqrt", "rank", "det", "dim", "diag", "span", "nullity",
    "proj", "lim", "min", "max", "argmin", "argmax", "mean", "var", "cov", "prob",
}
GREEK_LATEX = {
    "alpha": r"\alpha",
    "beta": r"\beta",
    "gamma": r"\gamma",
    "delta": r"\delta",
    "epsilon": r"\epsilon",
    "theta": r"\theta",
    "lambda": r"\lambda",
    "mu": r"\mu",
    "sigma": r"\sigma",
    "omega": r"\omega",
}
SYMBOL_MACROS = {
    "lambda": r"\lambda",
    "theta": r"\theta",
    "mu": r"\mu",
    "sigma": r"\sigma",
    "Sigma": r"\Sigma",
}


def split_top_level_commas(text: str) -> list[str]:
    parts: list[str] = []
    start = 0
    depth = 0
    for i, char in enumerate(text):
        if char in "([{":
            depth += 1
        elif char in ")]}":
            depth = max(0, depth - 1)
        elif char == "," and depth == 0:
            parts.append(text[start:i].strip())
            start = i + 1
    parts.append(text[start:].strip())
    return [part for part in parts if part]


def matrix_rows(value: str) -> list[list[str]] | None:
    source = value.strip()
    if source.startswith("[[") and source.endswith("]]"):
        row_texts = re.split(r"\]\s*,\s*\[", source[2:-2].strip())
    elif ROW_MATRIX_RE.fullmatch(source):
        row_texts = [source[1:-1].strip()]
    else:
        return None
    rows: list[list[str]] = []
    for row_text in row_texts:
        cleaned = row_text.strip().strip("[]")
        cells = split_top_level_commas(cleaned) if "," in cleaned else cleaned.split()
        if not cells:
            return None
        rows.append(cells)
    return rows or None


def vector_items(value: str) -> list[str] | None:
    source = value.strip()
    if source.startswith("(") and source.endswith(")") and "," in source:
        return split_top_level_commas(source[1:-1])
    if source.startswith("[") and source.endswith("]") and "," in source and not source.startswith("[["):
        return split_top_level_commas(source[1:-1])
    return None


def stash_latex(placeholders: dict[str, str], latex: str) -> str:
    key = f"@@@{len(placeholders)}@@@"
    placeholders[key] = latex
    return key


def latex_bmatrix(rows: list[list[str]]) -> str:
    rendered_rows = [" & ".join(latex_math_expr(cell, tuple_style="tuple") for cell in row) for row in rows]
    return r"\begin{bmatrix}" + r" \\ ".join(rendered_rows) + r"\end{bmatrix}"


def latex_tuple(items: list[str]) -> str:
    return r"\left(" + ", ".join(latex_math_expr(item, tuple_style="tuple") for item in items) + r"\right)"


def latex_column_vector(items: list[str]) -> str:
    return r"\begin{bmatrix}" + r" \\ ".join(latex_math_expr(item, tuple_style="tuple") for item in items) + r"\end{bmatrix}"


def latex_value(value: str, *, vector: bool = False) -> str:
    rows = matrix_rows(value)
    if rows:
        return latex_bmatrix(rows)
    items = vector_items(value)
    if items:
        return latex_column_vector(items) if vector else latex_tuple(items)
    if value.strip().lower().startswith("diag(") and value.strip().endswith(")"):
        inner = value.strip()[5:-1]
        return r"\operatorname{diag}\left(" + ", ".join(latex_math_expr(part, tuple_style="tuple") for part in split_top_level_commas(inner)) + r"\right)"
    return latex_math_expr(value, tuple_style="tuple")


def latex_variable(name: str, value: str | None = None) -> str:
    vector = value is not None and vector_items(value) is not None
    match = re.fullmatch(r"([A-Za-z])(?:_?([A-Za-z0-9]+))?", name.strip())
    if vector and match:
        base = rf"\vec{{{match.group(1)}}}"
        if match.group(2):
            base += rf"_{{{match.group(2)}}}"
        return base
    return latex_math_expr(name, tuple_style="tuple")


def latex_math_expr(expr: str, *, tuple_style: str = "tuple") -> str:
    work = str(expr).strip().strip(".;")
    work = work.replace("−", "-").replace("×", "*").replace("·", r"\cdot")
    placeholders: dict[str, str] = {}

    def matrix_repl(match: re.Match[str]) -> str:
        rows = matrix_rows(match.group(0))
        return stash_latex(placeholders, latex_bmatrix(rows)) if rows else match.group(0)

    def row_matrix_repl(match: re.Match[str]) -> str:
        rows = matrix_rows(match.group(0))
        return stash_latex(placeholders, latex_bmatrix(rows)) if rows else match.group(0)

    def diag_repl(match: re.Match[str]) -> str:
        parts = split_top_level_commas(match.group(1))
        rendered = r"\operatorname{diag}\left(" + ", ".join(latex_math_expr(part, tuple_style="tuple") for part in parts) + r"\right)"
        return stash_latex(placeholders, rendered)

    def proj_repl(match: re.Match[str]) -> str:
        sub = latex_math_expr(match.group(1), tuple_style="tuple")
        arg = latex_math_expr(match.group(2), tuple_style="tuple")
        return stash_latex(placeholders, rf"\operatorname{{proj}}_{{{sub}}}\left({arg}\right)")

    def sqrt_repl(match: re.Match[str]) -> str:
        return stash_latex(placeholders, r"\sqrt{" + latex_math_expr(match.group(1), tuple_style="tuple") + "}")

    def tuple_repl(match: re.Match[str]) -> str:
        items = vector_items(match.group(0))
        if not items:
            return match.group(0)
        rendered = latex_column_vector(items) if tuple_style == "vector" else latex_tuple(items)
        return stash_latex(placeholders, rendered)

    work = MATRIX_LITERAL_RE.sub(matrix_repl, work)
    work = ROW_MATRIX_RE.sub(row_matrix_repl, work)
    work = re.sub(r"\bdiag\(([^()]*)\)", diag_repl, work)
    work = re.sub(r"\bproj_([A-Za-z0-9]+)\(([^()]*)\)", proj_repl, work)
    while re.search(r"\bsqrt\(([^()]*)\)", work):
        work = re.sub(r"\bsqrt\(([^()]*)\)", sqrt_repl, work)
    work = TUPLE_LITERAL_RE.sub(tuple_repl, work)

    for word, latex in GREEK_LATEX.items():
        work = re.sub(rf"\b{word}\b", lambda _match, value=latex: value, work, flags=re.I)
    work = re.sub(r"\bdot\b", r"\\cdot", work, flags=re.I)
    work = work.replace("*", r"\cdot ")
    work = work.replace("<=", r"\le ").replace(">=", r"\ge ").replace("=>", r"\Rightarrow ")
    work = re.sub(r"\b(rank|det|dim|nullity|span|mean|var|cov|prob)\s*\(", r"\\operatorname{\1}(", work)
    work = re.sub(r"\b(rank|nullity)\b", r"\\operatorname{\1}", work)
    work = re.sub(r"\b(sin|cos|tan|log|ln|exp)\s*\(", r"\\\1(", work)
    work = re.sub(r"\b([APU])([xvb])\b", r"\1\\vec{\2}", work)
    work = re.sub(r"\b([A-Za-z])([0-9]+)\b", r"\1_{\2}", work)
    work = re.sub(r"\^T(?=[A-Za-z])", r"^{T}", work)
    work = re.sub(r"\^(?!\{)([0-9]+|[A-Za-z])", r"^{\1}", work)

    label = re.match(r"^([A-Za-z][A-Za-z ]{2,24})\s*=", work)
    if label and label.group(1).lower() not in MATH_FUNCTIONS:
        words = label.group(1).split()
        if len(words) > 1 or len(label.group(1)) > 3:
            work = r"\mathrm{" + " ".join(words) + "}" + work[label.end() - 1 :]

    work = re.sub(r"\s+", " ", work).strip()
    for key, value in placeholders.items():
        work = work.replace(key, value)
    return work


def math_span_is_safe(core: str) -> bool:
    if len(core) > 150:
        return False
    words = re.findall(r"[A-Za-z]{2,}", core)
    allowed = MATH_FUNCTIONS | set(GREEK_LATEX) | {"frac", "vec", "hat", "operatorname"}
    return all(word.lower() in allowed or len(word) <= 2 or re.fullmatch(r"[A-Z][a-z]?", word) for word in words)


def latex_text_with_inline_math(text: str, *, tuple_style: str = "tuple") -> str:
    work = str(text).strip()
    placeholders: dict[str, str] = {}

    atom = r"(?:[A-Za-z][A-Za-z0-9_]*|\d+(?:\.\d+)?[A-Za-z]?|\d+(?:\.\d+)?|\([^()]+\)|\[[^\]]+\])"
    term = rf"{atom}(?:\s*(?:\^|_)\s*{atom})?"
    expr = rf"{term}(?:\s*(?:\+|-|\*|/|dot)\s*{term}){{0,8}}"
    equation_re = re.compile(rf"(?<![A-Za-z0-9_])({expr}\s*(?:=|<=|>=|<|>)\s*{expr}(?:\s*(?:=|<=|>=|<|>)\s*{expr})*)")

    def store_math(latex: str) -> str:
        return stash_latex(placeholders, rf"\({latex}\)")

    def equation_repl(match: re.Match[str]) -> str:
        core = match.group(1).strip()
        if not math_span_is_safe(core):
            return match.group(0)
        return store_math(latex_math_expr(core, tuple_style=tuple_style))

    work = equation_re.sub(equation_repl, work)
    inverse_power_re = re.compile(r"(?<![A-Za-z0-9_])([A-Za-z][A-Za-z0-9_]*\^\{\s*-\s*1\s*\})")
    work = inverse_power_re.sub(lambda m: store_math(latex_math_expr(m.group(1), tuple_style=tuple_style)), work)
    work = MATRIX_LITERAL_RE.sub(lambda m: store_math(latex_math_expr(m.group(0), tuple_style="vector")), work)
    work = ROW_MATRIX_RE.sub(lambda m: store_math(latex_math_expr(m.group(0), tuple_style="vector")), work)
    work = re.sub(r"\b(?:sqrt|rank|det|dim|diag)\([^()]+\)", lambda m: store_math(latex_math_expr(m.group(0), tuple_style=tuple_style)), work)
    power_re = re.compile(r"(?<![@A-Za-z0-9_])((?:[A-Za-z]|\d+(?:\.\d+)?)(?:\s*\^\s*(?:[A-Za-z]|\d+(?:\.\d+)?))+)" )
    work = power_re.sub(lambda m: store_math(latex_math_expr(m.group(1), tuple_style=tuple_style)), work)
    work = TUPLE_LITERAL_RE.sub(lambda m: store_math(latex_math_expr(m.group(0), tuple_style=tuple_style)), work)

    escaped = latex_escape(work)
    for key, value in placeholders.items():
        escaped = escaped.replace(latex_escape(key), value)
    return escaped


def short_vector_context(short: dict[str, object]) -> bool:
    haystack = " ".join(
        str(short.get(key, ""))
        for key in ("concept", "formula", "intuition", "hook", "visual_type")
    ).lower()
    return any(term in haystack for term in ("vector", "matrix", "basis", "span", "dot", "projection", "eigen", r"\vec"))


def latex_assignment_text(text: str, *, vector_context: bool) -> str | None:
    matches = [match for match in ASSIGNMENT_RE.finditer(text) if matrix_rows(match.group(2)) or vector_items(match.group(2)) or match.group(2).lower().startswith("diag(")]
    if not matches:
        return None
    first, last = matches[0], matches[-1]
    prefix = text[: first.start()].strip()
    prefix = re.sub(r"(?:,|and|with|where)\s*$", "", prefix, flags=re.I).strip()
    suffix = text[last.end() :].strip()
    suffix = re.sub(r"^[\s,.;]*(?:and\s+)?", "", suffix, flags=re.I).strip()
    suffix = suffix if suffix not in {".", ";", ","} else ""
    math_parts = []
    for match in matches:
        var, value = match.group(1), match.group(2)
        as_vector = vector_context and vector_items(value) is not None
        math_parts.append(f"{latex_variable(var, value)} = {latex_value(value, vector=as_vector)}")
    pieces: list[str] = []
    if prefix:
        pieces.append(latex_escape(prefix))
    pieces.append(r"\[" + "\n" + r",\qquad ".join(math_parts) + "\n" + r"\]")
    if suffix:
        pieces.append(latex_text_with_inline_math(suffix, tuple_style="tuple"))
    return "\n".join(pieces)


def display_math_sentence(sentence: str) -> bool:
    core = sentence.strip().rstrip(".")
    if not core or ("=" not in core and "sqrt(" not in core and " dot " not in core.lower()):
        return False
    if ":" in core and "=" in core and core.index(":") < core.index("="):
        return False
    prose_markers = {"because", "then", "where", "when", "only", "gives", "are", "is", "so", "but", "with", "from"}
    words = [word.lower() for word in re.findall(r"[A-Za-z]{2,}", core)]
    if any(word in prose_markers for word in words):
        return False
    prose = [word for word in words if word not in MATH_FUNCTIONS and word not in GREEK_LATEX and len(word) > 2]
    return len(prose) <= 1


def latex_calculation_text(text: str, *, vector_context: bool) -> str:
    rendered: list[str] = []
    for sentence in re.split(r"(?<=[.!?])\s+", str(text).strip()):
        if not sentence:
            continue
        if display_math_sentence(sentence):
            tuple_style = "vector" if vector_context else "tuple"
            rendered.append(r"\[" + "\n" + latex_math_expr(sentence, tuple_style=tuple_style) + "\n" + r"\]")
        else:
            rendered.append(latex_text_with_inline_math(sentence, tuple_style="tuple"))
    return "\n".join(rendered)


def latex_example_text(text: str, short: dict[str, object], role: str) -> str:
    vector_context = short_vector_context(short)
    if role == "calculation":
        return latex_calculation_text(str(text), vector_context=vector_context)
    assignment = latex_assignment_text(str(text), vector_context=vector_context)
    if assignment:
        return assignment
    return latex_text_with_inline_math(str(text), tuple_style="tuple")


def compact_key_concept(short: dict[str, object]) -> str:
    concept = str(short.get("concept", "Concept"))
    key = str(short.get("key_concept", short.get("hook", ""))).strip()
    prefix = f"{concept}: "
    if key.startswith(prefix):
        key = key[len(prefix) :]
    explanation = str(short.get("concept_explanation", short.get("intuition", ""))).strip()
    if explanation and explanation != key:
        return f"{key} {explanation}"
    return key or str(short.get("intuition", ""))


def plain_formula_read(short: dict[str, object]) -> str:
    formula = str(short.get("formula", ""))
    if not formula:
        return str(short.get("plain_formula", ""))
    if not formula_like_string(formula) or formula_has_unknown_macros(formula) or r"\ " in formula:
        return formula_text_value(formula)
    return plain_math(formula)


def latex_formula_reference(short: dict[str, object]) -> str:
    formula = latex_formula_display(short)
    plain = latex_escape(plain_formula_read(short))
    return rf"\(\displaystyle {formula}\)\par{{\footnotesize {plain}}}"


FIELD_OPENING_QUOTES: dict[str, tuple[str, str]] = {
    "group_theory": (
        "My methods are really methods of working and thinking; this is why they have crept in everywhere anonymously.",
        "Emmy Noether",
    ),
    "algorithms": (
        "An algorithm must be seen to be believed.",
        "Donald E. Knuth",
    ),
    "physics": (
        "If I have seen further it is by standing on the shoulders of Giants.",
        "Isaac Newton",
    ),
    "economics": (
        "Economics is a study of mankind in the ordinary business of life.",
        "Alfred Marshall",
    ),
    "linear_algebra": (
        "We must know. We will know.",
        "David Hilbert",
    ),
    "default": (
        "From the paradise that Cantor created for us no-one shall be able to expel us.",
        "David Hilbert",
    ),
}


def opening_quote(pack: dict[str, object], plan: dict[str, object]) -> tuple[str, str]:
    haystack = json.dumps(
        {
            "pack_title": pack.get("title", ""),
            "source_url": pack.get("source_url", ""),
            "course_title": plan.get("course_title", ""),
            "shorts": plan.get("shorts", []),
        },
        ensure_ascii=False,
    ).lower()
    if "calculus" in haystack:
        return FIELD_OPENING_QUOTES["physics"]
    ranked = sorted(
        ((domain, domain_score(haystack, keywords)) for domain, keywords in DOMAIN_KEYWORDS.items()),
        key=lambda item: item[1],
        reverse=True,
    )
    if ranked and ranked[0][1] >= 4:
        return FIELD_OPENING_QUOTES.get(ranked[0][0], FIELD_OPENING_QUOTES["default"])
    return FIELD_OPENING_QUOTES["default"]


def latex_opening_quote_block(pack: dict[str, object], plan: dict[str, object]) -> str:
    quote, author = opening_quote(pack, plan)
    return """\\small\\itshape %s\\\\[0.45em]
\\normalfont\\hfill %s""" % (latex_escape(quote), latex_escape(author))


def notes_pdf_report_path(run: Path) -> Path:
    return run / "notes_compile_report.json"


def compile_notes_pdf(run: Path, plan: dict[str, object], engine: str = "auto") -> dict[str, object]:
    report: dict[str, object] = {"requested_engine": engine, "status": "not-run"}
    if engine in {"auto", "latex"}:
        latex_report = run_latex_engine(run)
        if latex_report.get("status") == "ok":
            write_json(notes_pdf_report_path(run), latex_report)
            return latex_report
        report = latex_report
        if engine == "latex":
            write_json(notes_pdf_report_path(run), report)
            raise SystemExit(f"LaTeX PDF compile failed: {latex_report.get('message', 'unknown error')}")
    if engine in {"auto", "fallback"}:
        fallback_report = write_fallback_notes_pdf(run, plan, reason=str(report.get("message", "LaTeX engine unavailable")))
        write_json(notes_pdf_report_path(run), fallback_report)
        return fallback_report
    write_json(notes_pdf_report_path(run), report)
    return report


def latex_warning_counts_from_logs(run: Path, names: list[str]) -> dict[str, int]:
    chunks: list[str] = []
    for name in names:
        log = run / name
        if log.exists():
            chunks.append(log.read_text(encoding="utf-8", errors="replace"))
    main_log = run / "notes.log"
    if main_log.exists():
        chunks.append(main_log.read_text(encoding="utf-8", errors="replace"))
    text = "\n".join(chunks)
    return {
        "latex_warnings": len(re.findall(r"(?:LaTeX|Package [^\n]+|Class [^\n]+) Warning:", text)),
        "overfull_hboxes": len(re.findall(r"Overfull \\hbox", text)),
        "underfull_hboxes": len(re.findall(r"Underfull \\hbox", text)),
    }


def run_latex_engine(run: Path) -> dict[str, object]:
    tex = run / "notes.tex"
    latexmk = find_executable("latexmk")
    if latexmk:
        cmd = [latexmk, "-pdf", "-interaction=nonstopmode", "-halt-on-error", "notes.tex"]
        result = subprocess.run(cmd, cwd=run, text=True, capture_output=True, timeout=300)
        (run / "notes_latexmk.log").write_text(result.stdout + "\n" + result.stderr, encoding="utf-8")
        warning_counts = latex_warning_counts_from_logs(run, ["notes_latexmk.log"])
        if result.returncode == 0 and (run / "notes.pdf").exists():
            return {"status": "ok", "engine": "latexmk", "pdf": "notes.pdf", "warning_counts": warning_counts}
        return {"status": "failed", "engine": "latexmk", "message": "latexmk failed; see notes_latexmk.log", "warning_counts": warning_counts}
    pdflatex = find_executable("pdflatex")
    if pdflatex:
        last = None
        for i in range(2):
            last = subprocess.run([pdflatex, "-interaction=nonstopmode", "-halt-on-error", "notes.tex"], cwd=run, text=True, capture_output=True, timeout=300)
            (run / f"notes_pdflatex_pass_{i + 1}.log").write_text(last.stdout + "\n" + last.stderr, encoding="utf-8")
            if last.returncode != 0:
                break
        warning_counts = latex_warning_counts_from_logs(run, ["notes_pdflatex_pass_1.log", "notes_pdflatex_pass_2.log"])
        if last and last.returncode == 0 and (run / "notes.pdf").exists():
            return {"status": "ok", "engine": "pdflatex", "pdf": "notes.pdf", "warning_counts": warning_counts}
        return {"status": "failed", "engine": "pdflatex", "message": "pdflatex failed; see notes_pdflatex_pass_*.log", "warning_counts": warning_counts}
    tectonic = find_executable("tectonic")
    if tectonic:
        result = subprocess.run([tectonic, "notes.tex"], cwd=run, text=True, capture_output=True, timeout=300)
        (run / "notes_tectonic.log").write_text(result.stdout + "\n" + result.stderr, encoding="utf-8")
        warning_counts = latex_warning_counts_from_logs(run, ["notes_tectonic.log"])
        if result.returncode == 0 and (run / "notes.pdf").exists():
            return {"status": "ok", "engine": "tectonic", "pdf": "notes.pdf", "warning_counts": warning_counts}
        return {"status": "failed", "engine": "tectonic", "message": "tectonic failed; see notes_tectonic.log", "warning_counts": warning_counts}
    return {"status": "missing-engine", "engine": None, "message": "No LaTeX engine found: install latexmk, pdflatex, or tectonic."}


def write_fallback_notes_pdf(run: Path, plan: dict[str, object], reason: str) -> dict[str, object]:
    try:
        import fitz  # type: ignore
    except Exception as exc:
        raise SystemExit(f"Could not create notes.pdf: no LaTeX engine and PyMuPDF fallback unavailable ({exc}).")

    doc = fitz.open()
    width, height = 612, 792
    margin = 54
    y = margin

    def add_page() -> fitz.Page:
        nonlocal y
        new_page = doc.new_page(width=width, height=height)
        y = margin
        return new_page

    page = add_page()

    def write_line(text: str, size: int = 10, color: tuple[float, float, float] = (0, 0, 0), leading: float = 1.35) -> None:
        nonlocal page, y
        wrapped = textwrap.wrap(re.sub(r"\s+", " ", text).strip(), width=max(40, int(96 - size * 2.4))) or [""]
        for line in wrapped:
            if y > height - margin:
                page = add_page()
            page.insert_text((margin, y), line, fontsize=size, fontname="helv", color=color)
            y += size * leading

    def heading(text: str, size: int = 16) -> None:
        nonlocal page, y
        if y > height - margin - 50:
            page = add_page()
        y += 8
        write_line(text, size=size, color=(0.05, 0.19, 0.38), leading=1.45)
        y += 3

    title = str(plan.get("course_title", "Course"))
    heading(f"{title} Notes", 22)
    write_line("PDF generated from notes.tex data. LaTeX engine note: " + reason, 9, color=(0.45, 0.2, 0.0))
    heading("Key Concepts And Explanations", 15)
    for short in plan.get("shorts", []):
        if not isinstance(short, dict):
            continue
        write_line(f"{short.get('index')}. {short.get('concept')}", 12, color=(0.05, 0.19, 0.38))
        write_line(f"Key concept: {short.get('key_concept', short.get('hook', ''))}")
        write_line(f"Explanation: {short.get('concept_explanation', short.get('intuition', ''))}")
        write_line(f"How to recognize it: {short.get('recognition_cue', '')}")
        y += 5
    heading("Core Concepts", 15)
    for short in plan.get("shorts", []):
        if not isinstance(short, dict):
            continue
        ex = short.get("worked_example", {}) if isinstance(short.get("worked_example"), dict) else {}
        qp = short.get("question_prompt", {}) if isinstance(short.get("question_prompt"), dict) else {}
        heading(f"{short.get('index')}. {short.get('concept')}", 14)
        write_line(f"Definition: {short.get('intuition', '')}")
        write_line(f"Formula: {short.get('plain_formula', short.get('formula', ''))}")
        write_line(f"Worked example: {ex.get('setup', '')} {ex.get('calculation', '')} {ex.get('takeaway', '')}")
        write_line(f"Common trap: {short.get('misconception', '')}")
        write_line(f"Question: {qp.get('question', '')}")
        write_line(f"Answer idea: {qp.get('answer', '')}")
    pdf = run / "notes.pdf"
    doc.save(pdf)
    doc.close()
    return {"status": "ok", "engine": "pymupdf-fallback", "pdf": "notes.pdf", "message": reason}


def latex_items(items: list[str]) -> str:
    if not items:
        return r"\item None recorded."
    return "\n".join(rf"\item {latex_escape(item)}" for item in items)


def formula_symbol_tokens(formula: str) -> list[tuple[str, str]]:
    tokens: list[tuple[str, str]] = []
    seen: set[str] = set()

    def add(key: str, latex: str) -> None:
        if key not in seen:
            seen.add(key)
            tokens.append((key, latex))

    for match in re.finditer(r"\\(vec|hat)\{([A-Za-z])\}(?:_\{?([A-Za-z0-9]+)\}?)?", formula):
        macro, base, sub = match.group(1), match.group(2), match.group(3)
        latex = rf"\{macro}{{{base}}}" + (rf"_{{{sub}}}" if sub else "")
        add(f"{macro}:{base}:{sub or ''}", latex)
    for macro, latex in SYMBOL_MACROS.items():
        if rf"\{macro}" in formula:
            add(f"macro:{macro}", latex)

    stripped = re.sub(r"\\operatorname\{[^}]+\}", " ", formula)
    stripped = re.sub(r"\\(?:vec|hat)\{[A-Za-z]\}(?:_\{?[A-Za-z0-9]+\}?)?", " ", stripped)
    stripped = re.sub(r"\\[A-Za-z]+", " ", stripped)
    for match in re.finditer(r"(?<![A-Za-z])([A-Za-z])(?:_\{?([A-Za-z0-9]+)\}?)?", stripped):
        base, sub = match.group(1), match.group(2)
        latex = base + (rf"_{{{sub}}}" if sub else "")
        add(f"plain:{base}:{sub or ''}", latex)
    return tokens


def symbol_meaning(key: str, latex: str, short: dict[str, object]) -> str:
    haystack = " ".join(str(short.get(k, "")) for k in ("concept", "formula", "intuition", "hook", "visual_type")).lower()
    vector_match = re.search(r"\\(?:vec|hat)\{([A-Za-z])\}", latex)
    base_match = re.search(r"([A-Za-z])", latex.replace("lambda", ""))
    base = vector_match.group(1) if vector_match else (base_match.group(1) if base_match else latex)
    if any(term in haystack for term in ("group", "subgroup", "coset", "homomorphism", "isomorphism", "kernel", "orbit", "stabilizer", "ring", "field")):
        group_map = {
            "G": "group under discussion",
            "H": "subgroup or distinguished subset",
            "g": "group element acting by the operation",
            "h": "element of the subgroup",
            "e": "identity element",
            "n": "order, exponent, or positive integer",
            "a": "group or ring element",
            "b": "group or ring element",
            "r": "ring element used for multiplication",
            "I": "ideal or identity-like course-defined object",
        }
        if base in group_map:
            return group_map[base]
    if any(term in haystack for term in ("demand", "supply", "elasticity", "consumer", "budget", "market", "cost", "monopoly", "tax", "utility", "surplus")):
        econ_map = {
            "Q": "quantity supplied, demanded, or traded",
            "P": "price",
            "E": "elasticity or response measure",
            "I": "income or budget",
            "x": "quantity of one good or decision variable",
            "y": "quantity of another good or output variable",
            "p": "price or price vector",
            "q": "firm output quantity",
            "L": "labor input",
            "K": "capital input",
            "U": "utility function",
            "M": "marginal quantity such as MC, MB, MR, or MRS",
        }
        if base in econ_map:
            return econ_map[base]
    if latex.startswith(r"\vec"):
        if base in {"x", "b"}:
            return "vector of unknowns, inputs, or target values"
        if base in {"u", "v", "a", "q"}:
            return "vector or direction used by the rule"
        return "vector quantity with ordered components"
    if latex == r"\lambda":
        return "parameter; in eigenvalue topics, the stretch factor"
    if latex == r"\theta":
        return "angle or angular parameter"
    if latex in {r"\mu", r"\sigma"}:
        return "distribution parameter or course-defined constant"
    if latex == r"\Sigma":
        return "summation, covariance, or singular-value matrix depending on context"
    if "_{" in latex:
        return "indexed component, coefficient, or sequence term"
    if base in {"A", "B", "C", "P", "Q", "R", "U", "V", "S"}:
        if any(term in haystack for term in ("matrix", "linear", "eigen", "svd", "markov", "qr")):
            return "matrix, linear transformation, or structured array"
        if "probability" in haystack and base == "P":
            return "probability or transition rule"
        return "named quantity defined by the course context"
    if base in {"x", "y", "z"}:
        return "unknown, input, output, or coordinate variable"
    if base in {"u", "v", "w"}:
        return "vector, direction, or comparison quantity"
    if base in {"i", "j", "k", "n", "r"}:
        return "index, count, dimension, or rank-like value"
    if base in {"c", "d", "a", "b"}:
        return "coefficient, scalar, vector, or course-defined quantity"
    if base == "t":
        return "time or independent variable"
    if base == "f":
        return "function or rule"
    return "symbol whose meaning should be checked in the source context"


def formula_operator_entries(formula: str, short: dict[str, object]) -> list[str]:
    entries: list[str] = []
    operators = {
        "rank": r"$\operatorname{rank}$: number of independent directions or constraints",
        "det": r"$\det$: signed scale factor for area or volume",
        "dim": r"$\dim$: dimension or number of degrees of freedom",
        "span": r"$\operatorname{span}$: all combinations generated by listed objects",
        "proj": r"$\operatorname{proj}$: component kept in a chosen direction or subspace",
        "nullity": r"$\operatorname{nullity}$: number of free or invisible input directions",
    }
    for name, entry in operators.items():
        if name in formula:
            entries.append(entry)
    if r"\frac" in formula:
        entries.append(r"$\frac{\cdot}{\cdot}$: ratio; check numerator and denominator roles before substituting")
    if "=" in formula:
        entries.append(r"$=$: equality to verify by substitution, transformation, or units")
    return entries


def symbol_glossary(short: dict[str, object]) -> str:
    formula = str(short.get("formula", ""))
    if formula and not formula_like_string(formula):
        return "Formula cue is prose; translate it into variables before using it in a calculation."
    entries: list[str] = []
    seen_latex: set[str] = set()
    for key, latex in formula_symbol_tokens(formula):
        if latex in seen_latex:
            continue
        seen_latex.add(latex)
        entries.append(rf"${latex}$: {symbol_meaning(key, latex, short)}")
        if len(entries) >= 8:
            break
    for entry in formula_operator_entries(formula, short):
        if entry not in entries:
            entries.append(entry)
    if not entries:
        entries.append("No stable formula symbols were detected; define the course-specific quantities before applying the rule.")
    return "; ".join(entries)


def visual_label(value: object) -> str:
    labels = {
        "vector_components": "vector-component diagram",
        "linear_combination": "linear-combination diagram",
        "matrix_vector": "matrix-vector diagram",
        "calculus_tangent": "tangent-line diagram",
        "calculus_area": "area-accumulation diagram",
        "physics_force": "force diagram",
        "physics_energy": "energy diagram",
        "physics_wave": "wave diagram",
        "cs_graph": "graph diagram",
        "cs_array": "array-state diagram",
        "state_machine": "state-transition diagram",
        "probability": "probability diagram",
        "chemistry_reaction": "reaction diagram",
        "numeric_rule": "input-rule-output diagram",
        "algebra_ring_field": "ring-field structure diagram",
        "algebra_ideal": "ideal absorption diagram",
        "algebra_quotient_ring": "quotient-ring collapse diagram",
        "algebra_factorization": "domain divisibility diagram",
        "algebra_field_extension": "field-extension tower diagram",
        "algebra_galois": "Galois root-symmetry diagram",
        "game_payoff": "payoff matrix diagram",
        "group_structure": "group operation diagram",
        "group_cosets": "coset partition diagram",
        "group_homomorphism": "structure-preserving map diagram",
        "group_action": "symmetry action diagram",
        "econ_supply_demand": "supply-demand diagram",
        "econ_elasticity": "elasticity curve diagram",
        "econ_budget": "budget-line diagram",
        "econ_curve": "economic curve diagram",
        "econ_tax_wedge": "tax wedge and deadweight-loss diagram",
    }
    key = str(value or "concept diagram").strip().lower()
    if key in labels:
        return labels[key]
    label = re.sub(r"[_-]+", " ", key).strip()
    return f"{label} diagram" if label and "diagram" not in label else (label or "concept diagram")



def detected_domain(pack: dict[str, object], plan: dict[str, object] | None = None) -> str | None:
    payload = {"pack": pack}
    if plan:
        payload["plan"] = plan
    haystack = json.dumps(payload, ensure_ascii=False).lower()
    ranked = sorted(
        ((domain, domain_score(haystack, keywords)) for domain, keywords in DOMAIN_KEYWORDS.items()),
        key=lambda item: item[1],
        reverse=True,
    )
    return ranked[0][0] if ranked and ranked[0][1] >= 4 else None


def concept_to_short(concept: Concept, index: int) -> dict[str, object]:
    short = {
        "index": index,
        "concept": concept.name,
        "hook": concept.hook,
        "intuition": concept.intuition,
        "formula": concept.formula,
        "plain_formula": plain_math(concept.formula),
        "prerequisites": concept.prerequisites,
        "misconception": concept.misconception,
        "worked_example": {
            "setup": concept.example_setup,
            "calculation": concept.example_calc,
            "takeaway": concept.example_takeaway,
        },
        "question_prompt": {
            "question": concept.application_question,
            "answer": concept.application_answer,
        },
        "visual_type": concept.visual_type,
    }
    enrich_short(short, [], index - 1)
    return short


def enrich_short(short: dict[str, object], all_shorts: list[dict[str, object]], index: int) -> None:
    next_concepts = [s["concept"] for s in all_shorts[index + 1 : index + 4]]
    short["key_concept"] = f"{short['concept']}: {short['hook']}"
    short["concept_explanation"] = (
        f"{short['intuition']} The worked example makes the idea testable: "
        f"{short['worked_example']['takeaway']}"
    )
    short["recognition_cue"] = (
        f"Use this concept when a problem asks you to identify the rule, structure, or quantity behind "
        f"{str(short['concept']).lower()} and then check it with a concrete example."
    )
    short["concept_connections"] = {
        "builds_on": short.get("prerequisites", []),
        "prepares_for": next_concepts,
    }


def full_note_shorts(pack: dict[str, object], plan: dict[str, object]) -> list[dict[str, object]]:
    domain = detected_domain(pack, plan)
    concepts = list(DOMAIN_LIBRARY.get(domain or "", []))
    existing = {c.name.lower() for c in concepts}
    for item in plan.get("shorts", []):
        name = str(item.get("concept", "")).lower()
        if name and name not in existing:
            concepts.append(Concept(
                str(item.get("concept", "Topic")),
                str(item.get("hook", "This is a core course idea.")),
                str(item.get("intuition", "Connect the definition, formula, and worked example.")),
                str(item.get("formula", item.get("plain_formula", ""))),
                [str(x) for x in item.get("prerequisites", [])],
                str(item.get("misconception", "Do not memorize without checking a concrete example.")),
                str(item.get("worked_example", {}).get("setup", "Choose a small representative example.")),
                str(item.get("worked_example", {}).get("calculation", "Work through the definition step by step.")),
                str(item.get("worked_example", {}).get("takeaway", "The calculation should reveal the structure.")),
                str(item.get("question_prompt", {}).get("question", "Where does this appear in the course?")),
                str(item.get("question_prompt", {}).get("answer", "Identify the inputs, rule, and output.")),
                str(item.get("visual_type", "numeric_rule")),
            ))
            existing.add(name)
    if not concepts:
        concepts = choose_concepts(pack, max(20, len(plan.get("shorts", []))))
    shorts = [concept_to_short(concept, i) for i, concept in enumerate(concepts, start=1)]
    for i, short in enumerate(shorts):
        enrich_short(short, shorts, i)
    return shorts


def latex_topic_properties(short: dict[str, object]) -> str:
    concept = latex_escape(str(short.get("concept", "Topic")))
    formula = latex_escape(plain_formula_read(short))
    return rf"""
\begin{{itemize}}
\item Identify the object type before using the formula: set, function, transformation, quantity, or constraint.
\item Check the assumptions: prerequisites, domain restrictions, and whether the operation or model applies.
\item Use the formula {formula} only after naming each symbol and unit.
\item Connect {concept} to adjacent course ideas by asking what it preserves, measures, optimizes, or classifies.
\end{{itemize}}
"""


def latex_topic_questions(short: dict[str, object]) -> str:
    concept = latex_escape(str(short.get("concept", "Topic")))
    qp = short.get("question_prompt", {}) if isinstance(short.get("question_prompt"), dict) else {}
    app = latex_text_with_inline_math(str(qp.get("question", "Apply the idea in a concrete setting.")))
    return rf"""
\begin{{questions}}
\item State the definition of {concept} and identify every object it depends on.
\item Give one example that satisfies the definition and one near-example that fails it.
\item Explain the main formula in words, then identify what each symbol is allowed to be.
\item Recreate the worked example without looking, changing one number or object at the end.
\item Describe the visual interpretation: what moves, what stays fixed, and what is measured?
\item Name the most common trap and write a one-sentence warning that would prevent it.
\item Connect this topic to a previous topic and to a later topic in the course.
\item Application: {app}
\item Write a short proof, derivation, or economic/physical explanation for why the formula is reasonable.
\item Create a new problem whose answer uses this topic and one prerequisite.
\end{{questions}}
"""


def latex_topic_answers(short: dict[str, object]) -> str:
    ex = short.get("worked_example", {}) if isinstance(short.get("worked_example"), dict) else {}
    qp = short.get("question_prompt", {}) if isinstance(short.get("question_prompt"), dict) else {}
    answer = latex_example_text(str(qp.get("answer", "Use the definition and worked example to justify the answer.")), short, "answer")
    takeaway = latex_example_text(str(ex.get("takeaway", "The example reveals how the definition is used.")), short, "takeaway")
    return rf"""
\begin{{enumerate}}
\item The definition is the precise test; the example and non-example should differ on exactly one assumption.
\item Symbol meanings come from the formula table and should be checked before substitution.
\item The worked example's key interpretation is: {takeaway}
\item The application answer idea is: {answer}
\item A good original problem names inputs, method, and answer direction before doing algebra.
\end{{enumerate}}
"""



def latex_topic_figure(short: dict[str, object]) -> str:
    """Return a compact topic-specific figure embedded directly in notes.tex."""
    concept = latex_escape(str(short.get("concept") or "topic"))
    visual = str(short.get("visual_type") or "").lower()
    title = latex_escape(visual_label(visual or "concept diagram"))
    formula_text = screen_prose(str(plain_formula_read(short) or short.get("plain_formula") or short.get("formula") or ""))
    formula = latex_escape(textwrap.shorten(formula_text, width=120, placeholder="...")) if formula_text else ""
    haystack = " ".join(str(short.get(key, "")) for key in ("concept", "visual_type", "formula", "intuition", "hook")).lower()

    if any(key in visual or key in haystack for key in ("econ", "demand", "supply", "elasticity", "budget", "curve", "tax", "surplus", "game")):
        if any(key in haystack for key in ("tax", "surplus", "welfare", "externality")):
            body = r"""
\draw[->,thick] (0,0) -- (6.4,0) node[right]{Quantity};
\draw[->,thick] (0,0) -- (0,4.1) node[above]{Price};
\draw[very thick,blue!70!black] (0.7,0.75) -- (5.7,3.45) node[right]{Supply};
\draw[very thick,red!70!black] (0.7,3.65) -- (5.7,0.85) node[right]{Demand};
\draw[fill=green!18,draw=green!45!black] (1.05,3.45) -- (3.05,2.18) -- (1.05,2.18) -- cycle;
\draw[fill=orange!25,draw=orange!70!black] (1.05,0.95) -- (3.05,2.18) -- (1.05,2.18) -- cycle;
\draw[dashed] (3.05,0) -- (3.05,2.18) -- (0,2.18);
\draw[very thick,purple!70!black] (3.75,1.85) -- (3.75,2.65) node[midway,right]{tax wedge};
\node at (2.0,3.05) {CS};
\node at (2.0,1.35) {PS};
"""
        elif any(key in haystack for key in ("game", "nash", "strategy", "dominant")):
            body = r"""
\matrix[matrix of nodes,nodes={draw,minimum width=1.15cm,minimum height=0.65cm,anchor=center},column sep=-\pgflinewidth,row sep=-\pgflinewidth] at (3,1.8) {
 & Left & Right \\
Up & 3,2 & 1,4 \\
Down & 4,1 & 2,3 \\
};
\draw[very thick,green!55!black,rounded corners] (2.42,1.46) rectangle (3.57,2.11);
\node[align=center] at (3,-0.15) {best responses mark stable choices};
"""
        else:
            body = r"""
\draw[->,thick] (0,0) -- (6.4,0) node[right]{Quantity};
\draw[->,thick] (0,0) -- (0,4.1) node[above]{Price};
\draw[very thick,blue!70!black] (0.7,0.8) -- (5.7,3.55) node[right]{Supply};
\draw[very thick,red!70!black] (0.7,3.55) -- (5.7,0.8) node[right]{Demand};
\draw[dashed] (3.2,0) -- (3.2,2.17) -- (0,2.17);
\filldraw[green!55!black] (3.2,2.17) circle (2.2pt) node[above right]{equilibrium};
"""
    elif any(key in visual or key in haystack for key in ("group", "coset", "homomorphism", "action", "ring", "field", "domain")):
        if any(key in haystack for key in ("ring", "field", "domain", "ideal")):
            body = r"""
\node[circle,draw,thick,minimum size=0.75cm] (a) at (0,1.6) {$a$};
\node[circle,draw,thick,minimum size=0.75cm] (b) at (1.55,2.35) {$b$};
\node[circle,draw,thick,minimum size=0.75cm] (c) at (1.55,0.85) {$c$};
\node[draw,thick,rounded corners,minimum width=1.15cm,minimum height=0.72cm] (sum) at (3.25,1.6) {$b+c$};
\node[draw,thick,rounded corners,minimum width=1.25cm,minimum height=0.72cm] (dist) at (5.15,1.6) {$ab+ac$};
\draw[->,blue!70!black,thick] (b) -- (sum);
\draw[->,blue!70!black,thick] (c) -- (sum);
\draw[->,green!50!black,thick] (a) -- (dist);
\draw[->,green!50!black,thick] (sum) -- (dist);
\node[align=center] at (2.75,-0.1) {two operations share one structure};
"""
        elif any(key in haystack for key in ("action", "orbit", "stabilizer", "permutation")):
            body = r"""
\node[circle,draw,thick] (x1) at (0,1.3) {$x$};
\node[circle,draw,thick] (x2) at (1.7,2.25) {$gx$};
\node[circle,draw,thick] (x3) at (3.4,1.3) {$g^2x$};
\node[circle,draw,thick] (x4) at (1.7,0.35) {$hx$};
\draw[->,very thick,blue!70!black] (x1) -- (x2);
\draw[->,very thick,blue!70!black] (x2) -- (x3);
\draw[->,very thick,red!70!black] (x1) -- (x4);
\draw[dashed,rounded corners] (-0.45,-0.2) rectangle (3.85,2.75);
\node at (1.7,-0.55) {orbit of one point};
"""
        elif any(key in haystack for key in ("coset", "quotient", "lagrange", "normal")):
            body = r"""
\draw[rounded corners,thick,fill=blue!8] (0,0) rectangle (1.45,2.4);
\draw[rounded corners,thick,fill=green!10] (1.8,0) rectangle (3.25,2.4);
\draw[rounded corners,thick,fill=orange!13] (3.6,0) rectangle (5.05,2.4);
\node at (0.72,1.35) {$H$};
\node at (2.52,1.35) {$gH$};
\node at (4.32,1.35) {$kH$};
\node[align=center] at (2.52,-0.45) {cosets partition the group};
"""
        else:
            body = r"""
\node[circle,draw,thick,minimum size=0.72cm] (e) at (0,1.25) {$e$};
\node[circle,draw,thick,minimum size=0.72cm] (g) at (2.0,2.35) {$g$};
\node[circle,draw,thick,minimum size=0.72cm] (h) at (4.0,1.25) {$h$};
\node[circle,draw,thick,minimum size=0.72cm] (gh) at (2.0,0.1) {$gh$};
\draw[->,blue!70!black,thick] (e) -- (g);
\draw[->,blue!70!black,thick] (g) -- (h);
\draw[->,blue!70!black,thick] (h) -- (gh);
\draw[->,red!70!black,thick,bend left=16] (gh) to (e);
\node[align=center] at (2.0,-0.95) {operation sends elements\\to structured outputs};
"""
    elif any(key in visual or key in haystack for key in ("matrix", "vector", "linear", "basis", "projection", "eigen", "subspace", "transform")):
        body = r"""
\draw[step=0.55cm,gray!35,very thin] (0,0) grid (2.2,2.2);
\draw[->,very thick,blue!70!black] (0,0) -- (1.65,1.1) node[above] {$x$};
\draw[->,very thick,green!50!black] (3.9,0.2) -- (5.75,1.75) node[above] {$Ax$};
\node[draw,thick,rounded corners,minimum width=1.05cm,minimum height=1.05cm] at (3.0,1.1) {$A$};
\draw[->,thick] (2.1,1.1) -- (2.45,1.1);
\draw[->,thick] (3.55,1.1) -- (3.9,1.1);
\node at (3.0,-0.45) {linear rule};
"""
    elif any(key in visual or key in haystack for key in ("graph", "algorithm", "cs_", "complexity", "state", "recurrence", "array")):
        if any(key in haystack for key in ("array", "sort", "heap", "hash")):
            body = r"""
\foreach \x/\v in {0/7,1/2,2/5,3/9,4/1,5/4}{\node[draw,minimum width=0.65cm,minimum height=0.65cm] at (\x*0.72,1.3) {\v};}
\draw[very thick,green!55!black,->] (0.72,0.65) -- (1.44,0.65) node[midway,below]{scan};
\draw[very thick,blue!70!black,->] (2.88,2.05) -- (1.44,2.05) node[midway,above]{swap/update};
\node[align=center] at (2.0,-0.15) {array state changes one index at a time};
"""
        elif any(key in haystack for key in ("recurrence", "dynamic", "dp")):
            body = r"""
\node[draw,thick] (a) at (0,1.6) {$T(n)$};
\node[draw,thick] (b) at (1.8,2.35) {$T(n/2)$};
\node[draw,thick] (c) at (1.8,0.85) {$T(n/2)$};
\node[draw,thick] (d) at (3.6,2.35) {$T(n/4)$};
\node[draw,thick] (e) at (3.6,0.85) {$T(n/4)$};
\draw[->,thick] (a)--(b); \draw[->,thick] (a)--(c); \draw[->,thick] (b)--(d); \draw[->,thick] (c)--(e);
\node at (2.1,-0.05) {work splits by level};
"""
        else:
            body = r"""
\node[circle,draw,thick] (a) at (0,1.4) {$A$};
\node[circle,draw,thick] (b) at (1.55,2.3) {$B$};
\node[circle,draw,thick] (c) at (3.1,1.35) {$C$};
\node[circle,draw,thick] (d) at (1.65,0.35) {$D$};
\node[circle,draw,thick] (e) at (4.75,0.75) {$E$};
\draw[thick] (a)--(b)--(c)--(e);
\draw[thick] (b)--(d)--(c);
\draw[very thick,green!55!black,->] (a)--(b);
\draw[very thick,green!55!black,->] (b)--(c);
\node[align=center] at (2.4,-0.55) {trace states and invariants};
"""
    elif any(key in visual or key in haystack for key in ("physics", "force", "wave", "energy", "calculus", "area", "slope")):
        if "force" in haystack:
            body = r"""
\draw[thick,fill=gray!15] (2.2,0.55) rectangle (3.25,1.35);
\draw[->,very thick,red!70!black] (3.25,0.95) -- (5.15,0.95) node[right]{$F$};
\draw[->,very thick,blue!70!black] (2.72,1.35) -- (2.72,2.75) node[above]{$N$};
\draw[->,very thick,green!45!black] (2.72,0.55) -- (2.72,-0.75) node[below]{$mg$};
\draw[thick] (0,0.55) -- (6,0.55);
\node at (3,-1.25) {free-body forces balance or accelerate};
"""
        elif any(key in haystack for key in ("energy", "work", "potential")):
            body = r"""
\draw[->,thick] (0,0) -- (6.2,0) node[right]{$x$};
\draw[->,thick] (0,0) -- (0,3.2) node[above]{$E$};
\draw[very thick,blue!70!black] (0.4,2.4) .. controls (1.7,0.55) and (3.9,0.55) .. (5.4,2.4) node[right]{$U$};
\draw[very thick,red!70!black] (0.35,2.85) -- (5.6,2.85) node[right]{$E_{total}$};
\draw[dashed] (3.0,0) -- (3.0,0.72);
\node at (3,-0.45) {motion trades kinetic and potential};
"""
        else:
            body = r"""
\draw[->,thick] (0,0) -- (6.2,0) node[right]{$t$};
\draw[->,thick] (0,-1.4) -- (0,2.4) node[above]{$y$};
\draw[very thick,blue!70!black] plot[smooth] coordinates {(0.25,0.25) (1.0,1.55) (1.8,1.05) (2.7,-0.55) (3.6,-0.85) (4.8,0.7) (5.7,1.65)};
\draw[very thick,red!70!black,->] (2.7,-0.55) -- (3.75,0.05) node[right]{rate/change};
\filldraw[green!55!black] (2.7,-0.55) circle (2.2pt);
"""
    else:
        body = r"""
\node[draw,rounded corners,thick,minimum width=1.45cm,minimum height=0.82cm] (input) at (0,0.8) {input};
\node[draw,rounded corners,thick,minimum width=1.45cm,minimum height=0.82cm] (rule) at (2.6,0.8) {rule};
\node[draw,rounded corners,thick,minimum width=1.45cm,minimum height=0.82cm] (output) at (5.2,0.8) {output};
\draw[->,very thick,blue!70!black] (input) -- (rule);
\draw[->,very thick,green!55!black] (rule) -- (output);
\node[align=center] at (2.6,-0.35) {definition, formula, example\\must agree};
"""

    return rf"""
\paragraph{{Generated figure.}}
\begin{{center}}
\begin{{tikzpicture}}[scale=0.92,every node/.style={{font=\small}}]
{body}
\end{{tikzpicture}}
\end{{center}}
\emph{{Figure for {concept}.}} {title}. Related formula cue: {formula}
"""
def latex_supplemental_topic_notes(pack: dict[str, object], shorts: list[dict[str, object]], limit: int = 40) -> str:
    sections: list[str] = []
    for term in source_coverage_terms(pack, shorts, limit=limit):
        title = latex_escape(term.title())
        snippets = source_snippets(pack, term, limit=3)
        if snippets:
            cues = "\n".join(rf"\item {latex_text_with_inline_math(snippet)}" for snippet in snippets)
        else:
            cues = rf"\item {title} appears in the extracted course vocabulary and should be studied with the nearest planned topic."
        symbol = re.sub(r"[^A-Za-z]", "", term)[:1].lower() or "x"
        sections.append(rf"""
\subsection{{{title}}}
\begin{{definition}}
{title} is a supplemental course term. Learn the object being named, the hypotheses that make it valid, and the calculation, proof move, or modeling decision it supports.
\end{{definition}}

\paragraph{{Course cues.}}
\begin{{itemize}}
{cues}
\end{{itemize}}

\begin{{formula}}
\[
\text{{object}} \longrightarrow \text{{rule or relation}} \longrightarrow \text{{conclusion}}
\]
\textbf{{Notation pattern.}} Assign a stable symbol such as \( {symbol} \), specify its domain, then write the defining relation before using the term in an example.
\end{{formula}}

\small
\begin{{longtable}}{{@{{}}L{{0.26\linewidth}}L{{0.68\linewidth}}@{{}}}}
\toprule
Study angle & Notes to learn \\
\midrule
Definition & Identify the exact object, relation, or process named by {title}. \\
Properties & Record closure, uniqueness, monotonicity, conservation, symmetry, or complexity properties when the course states them. \\
Formula use & Write hypotheses first, then the conclusion or computed quantity. \\
Example & Build the smallest nontrivial example and verify the definition line by line. \\
Common trap & Do not use the term as a label only; check the required conditions before applying it. \\
\bottomrule
\end{{longtable}}
\normalsize

\begin{{example}}
\textbf{{Mini-example template.}} Choose a small object involving {title}. Name the inputs, apply the defining rule once, and explain why the result satisfies the definition or property.
\end{{example}}

\subsubsection*{{Questions}}
\begin{{questions}}
\item What is the formal definition of {title} in this course?
\item Which hypotheses must be checked before the term applies?
\item What is the smallest example and the smallest non-example?
\item Which formula, table, or property usually appears next to this term?
\item How does {title} connect to the nearest planned topic in the course map?
\end{{questions}}
""")
    if not sections:
        return "No additional supplemental topic vocabulary was detected beyond the planned topics."
    return "\n".join(sections)

def cmd_notes(args: argparse.Namespace) -> None:
    run = Path(args.run)
    pack = read_json(run / "source_pack.json")
    plan = read_json(run / "short_plan.json")
    title = str(plan.get("course_title") or pack.get("title") or "Course")
    shorts = full_note_shorts(pack, plan)
    notes_plan = {**plan, "shorts": shorts}

    course_map = "\n".join(
        rf"\item \textbf{{{latex_escape(short['concept'])}}}: prerequisites -- {latex_escape(', '.join(short.get('prerequisites', [])) or 'none')}. Outcome -- {latex_text_with_inline_math(short['intuition'])}"
        for short in shorts
    )
    definition_rows = "\n".join(
        rf"{short['index']} & {latex_escape(short['concept'])} & {latex_text_with_inline_math(compact_key_concept(short))} \\"
        for short in shorts
    )
    formula_rows = "\n".join(
        rf"{short['index']} & {latex_escape(short['concept'])} & {latex_formula_reference(short)} \\"
        for short in shorts
    )
    opening_quote_tex = latex_opening_quote_block(pack, notes_plan)
    symbol_rows = "\n".join(
        rf"{short['index']} & {latex_escape(short['concept'])} & {symbol_glossary(short)} \\"
        for short in shorts
    )
    supplemental_sections = latex_supplemental_topic_notes(pack, shorts, limit=40)
    sections = []
    practice_items = []
    for short in shorts:
        ex = short["worked_example"]
        qp = short["question_prompt"]
        prereq_items = latex_items([str(x) for x in short.get("prerequisites", [])])
        connections = short.get("concept_connections", {})
        builds_on = latex_escape(", ".join(connections.get("builds_on", short.get("prerequisites", []))) or "none")
        prepares_for = latex_escape(", ".join(connections.get("prepares_for", [])) or "later course topics")
        key_concept = latex_text_with_inline_math(short.get("key_concept", short["hook"]))
        concept_explanation = latex_text_with_inline_math(short.get("concept_explanation", short["intuition"]))
        recognition_cue = latex_text_with_inline_math(short.get("recognition_cue", "Use the definition and worked example to decide when this idea applies."))
        setup_tex = latex_example_text(str(ex.get("setup", "")), short, "setup")
        calculation_tex = latex_example_text(str(ex.get("calculation", "")), short, "calculation")
        takeaway_tex = latex_example_text(str(ex.get("takeaway", "")), short, "takeaway")
        answer_tex = latex_example_text(str(qp.get("answer", "")), short, "answer")
        question_tex = latex_text_with_inline_math(str(qp.get("question", "")), tuple_style="tuple")
        sections.append(rf"""
\clearpage
\subsection{{{latex_escape(short['concept'])}}}

\subsubsection*{{Definition and prerequisites}}
\begin{{definition}}
{latex_text_with_inline_math(short['intuition'])}
\end{{definition}}
\begin{{itemize}}
\item \textbf{{Prerequisites.}}
\begin{{itemize}}
{prereq_items}
\end{{itemize}}
\item \textbf{{Key concept.}} {key_concept}
\item \textbf{{Explanation.}} {concept_explanation}
\item \textbf{{Recognition cue.}} {recognition_cue}
\item \textbf{{Connections.}} Builds on {builds_on}. Prepares for {prepares_for}.
\end{{itemize}}

\subsubsection*{{Formula and symbol check}}
\begin{{formula}}
\[
{latex_formula_display(short)}
\]
\textbf{{Plain-language read.}} {latex_escape(plain_formula_read(short))}.\\
\textbf{{Symbols.}} {symbol_glossary(short)}.
\end{{formula}}

\subsubsection*{{Properties and use cases}}
{latex_topic_properties(short)}

\subsubsection*{{Worked example}}
\begin{{example}}
\textbf{{Setup.}} {setup_tex}

\textbf{{Calculation.}} {calculation_tex}

\textbf{{Interpretation.}} {takeaway_tex}
\end{{example}}

\subsubsection*{{Visual and conceptual interpretation}}
Use a {latex_escape(visual_label(short.get('visual_type', 'concept diagram')))}: show the input, animate the rule, label the intermediate quantity, and highlight the output. The important check is not the drawing itself; it is whether the diagram makes the definition, the formula, and the worked example agree.

{latex_topic_figure(short)}

\subsubsection*{{Common trap}}
\begin{{quote}}
{latex_escape(short['misconception'])}
\end{{quote}}

\subsubsection*{{Questions}}
{latex_topic_questions(short)}

\subsubsection*{{Answers and explanations}}
{latex_topic_answers(short)}
""")
        practice_items.append(rf"\item \textbf{{{latex_escape(short['concept'])}.}} {question_tex} \emph{{Answer idea:}} {answer_tex}")
    tex = rf"""% Generated by {NOTES_GENERATOR_VERSION}; template=course-latex-notes
\documentclass[11pt]{{article}}
\usepackage[letterpaper,margin=0.92in]{{geometry}}
\usepackage{{amsmath,amssymb,amsthm,longtable,booktabs,array}}
\usepackage{{tikz}}
\usetikzlibrary{{matrix,arrows.meta,calc,positioning}}
\setlength{{\parskip}}{{0.35em}}
\setlength{{\parindent}}{{0pt}}
\renewcommand{{\arraystretch}}{{1.14}}
\newcolumntype{{L}}[1]{{>{{\raggedright\arraybackslash}}p{{#1}}}}
\newtheorem{{definition}}{{Definition}}[section]
\newtheorem{{formula}}{{Formula}}[section]
\newtheorem{{example}}{{Example}}[section]
\newenvironment{{questions}}{{\begin{{enumerate}}}}{{\end{{enumerate}}}}
\begin{{document}}
\begin{{center}}
\vspace*{{1.35in}}
{{\LARGE {latex_escape(title)} Definitions and Formulas\par}}
\vspace{{0.45in}}
{{\large \today\par}}
\end{{center}}
\vspace{{0.7in}}
\begin{{flushright}}
\begin{{minipage}}{{0.46\textwidth}}
{opening_quote_tex}
\end{{minipage}}
\end{{flushright}}
\vfill
\newpage

\section{{Foundations and Notation}}
\subsection{{Prerequisite Order}}
\begin{{enumerate}}
{course_map}
\end{{enumerate}}

\section{{Definitions}}
\small
\begin{{longtable}}{{@{{}}L{{0.07\linewidth}}L{{0.25\linewidth}}L{{0.62\linewidth}}@{{}}}}
\toprule
No. & Concept & Meaning and use \\
\midrule
\endhead
{definition_rows}
\bottomrule
\end{{longtable}}
\normalsize

\section{{Formula Reference}}
\small
\begin{{longtable}}{{@{{}}L{{0.08\linewidth}}L{{0.28\linewidth}}L{{0.58\linewidth}}@{{}}}}
\toprule
No. & Concept & Formula \\
\midrule
\endhead
{formula_rows}
\bottomrule
\end{{longtable}}
\normalsize

\section{{Notation and Symbol Meanings}}
\small
\begin{{longtable}}{{@{{}}L{{0.07\linewidth}}L{{0.25\linewidth}}L{{0.62\linewidth}}@{{}}}}
\toprule
No. & Concept & Symbols and meanings \\
\midrule
\endhead
{symbol_rows}
\bottomrule
\end{{longtable}}
\normalsize

\section{{Core Topics}}
{''.join(sections)}

\clearpage
\section{{Supplemental Topic Notes}}
{supplemental_sections}

\clearpage
\section{{Cumulative Practice Bank}}
\begin{{enumerate}}
{chr(10).join(practice_items)}
\end{{enumerate}}
\end{{document}}
"""
    (run / "notes.tex").write_text(tex, encoding="utf-8")
    (run / "notes.md").write_text(markdown_notes(notes_plan, pack), encoding="utf-8")
    pdf_engine = "auto" if args.compile and args.pdf_engine == "none" else args.pdf_engine
    if args.compile or pdf_engine != "none":
        compile_notes_pdf(run, notes_plan, pdf_engine)
    print(run / "notes.tex")

def markdown_notes(plan: dict[str, object], pack: dict[str, object] | None = None) -> str:
    lines = [f"# {plan.get('course_title', 'Course')} Definitions and Formulas\n"]
    lines.append("## Definitions\n")
    for short in plan["shorts"]:
        lines.append(f"- **{short['concept']}**: {short.get('concept_explanation', short['intuition'])}")
    lines.append("\n## Formula Reference\n")
    for short in plan["shorts"]:
        lines.append(f"- **{short['concept']}**: `{plain_formula_read(short)}` - {symbol_glossary(short)}")
    lines.append("\n## Core Topics\n")
    for short in plan["shorts"]:
        ex = short["worked_example"]
        qp = short["question_prompt"]
        lines.append(f"## {short['index']}. {short['concept']}\n")
        lines.append(f"**Definition.** {short['intuition']}\n")
        lines.append(f"**Key concept.** {short.get('key_concept', short['hook'])}\n")
        lines.append(f"**Concept explanation.** {short.get('concept_explanation', short['intuition'])}\n")
        lines.append(f"**How to recognize it.** {short.get('recognition_cue', 'Use the definition and worked example to decide when this idea applies.')}\n")
        lines.append(f"**Formula.** `{plain_formula_read(short)}`\n")
        lines.append(f"**Symbols.** {symbol_glossary(short)}\n")
        setup_md = latex_example_text(str(ex.get("setup", "")), short, "setup")
        calculation_md = latex_example_text(str(ex.get("calculation", "")), short, "calculation")
        takeaway_md = latex_example_text(str(ex.get("takeaway", "")), short, "takeaway")
        question_md = latex_text_with_inline_math(str(qp.get("question", "")), tuple_style="tuple")
        answer_md = latex_example_text(str(qp.get("answer", "")), short, "answer")
        lines.append(f"**Worked example.**\n\nSetup: {setup_md}\n\nCalculation: {calculation_md}\n\nInterpretation: {takeaway_md}\n")
        lines.append("**Questions.** Define the idea; give an example and non-example; explain every symbol; redo the example; connect to a prerequisite; answer the application prompt.\n")
        lines.append(f"**Application.** {question_md} Answer idea: {answer_md}\n")
    return "\n".join(lines)

def wrap(text: str, width: int = 34, lines: int = 4) -> list[str]:
    normalized = re.sub(r"\s+", " ", text).strip()
    normalized = re.sub(r"([,;:])(?=\S)", r"\1 ", normalized)
    normalized = re.sub(r"(?<=[A-Za-z])(?=\d)", " ", normalized)
    normalized = re.sub(r"(?<=\d)(?=[A-Za-z])", " ", normalized)
    out = textwrap.wrap(normalized, width=width, break_long_words=False, break_on_hyphens=False)
    if len(out) > lines:
        out = out[: lines - 1] + [out[lines - 1].rstrip(".") + "..."]
    return out or [""]


MATRIX_LITERAL_RE = re.compile(r"\[\s*\[[^\[\]\n]+?\]\s*(?:,\s*\[[^\[\]\n]+?\]\s*)+\]")


def screen_matrix_literal(literal: str) -> str:
    try:
        rows = json.loads(literal)
    except json.JSONDecodeError:
        return "matrix"
    if not isinstance(rows, list) or not all(isinstance(row, list) for row in rows):
        return "matrix"
    row_text = ["(" + ", ".join(str(cell) for cell in row) + ")" for row in rows]
    return "matrix with rows " + "; ".join(row_text)


def screen_prose(text: object) -> str:
    normalized = str(text)
    normalized = MATRIX_LITERAL_RE.sub(lambda match: screen_matrix_literal(match.group(0)), normalized)
    normalized = re.sub(r"\b([A-Za-z]\w*)\s*=\s*matrix with rows", r"\1 is the matrix with rows", normalized)
    normalized = re.sub(r"\b([A-Za-z]\w*)\s*=\s*\[([^\]\n]{1,80})\]", r"\1 is the row matrix with entries \2", normalized)
    normalized = re.sub(r"\\sqrt\{([^{}]+)\}", r"square root of \1", normalized)
    normalized = re.sub(r"\bsqrt\(([^)]*)\)", r"square root of \1", normalized)
    normalized = re.sub(r"([A-Za-z0-9_.]+)\s*\^\s*2\b", r"\1 squared", normalized)
    normalized = re.sub(r"([A-Za-z0-9_.]+)\s*\^\s*\{([^{}]+)\}", r"\1 to the \2", normalized)
    normalized = re.sub(r"([A-Za-z0-9_.]+)\s*\^\s*([A-Za-z0-9]+)", r"\1 to the \2", normalized)
    normalized = re.sub(r"\\sum(?:_\{?([^{}\s]+)\}?)?(?:\^\{?([^{}\s]+)\}?)?", lambda m: "sum" + (f" from {m.group(1)}" if m.group(1) else "") + (f" to {m.group(2)}" if m.group(2) else ""), normalized)
    normalized = re.sub(r"\\prod(?:_\{?([^{}\s]+)\}?)?(?:\^\{?([^{}\s]+)\}?)?", lambda m: "product" + (f" from {m.group(1)}" if m.group(1) else "") + (f" to {m.group(2)}" if m.group(2) else ""), normalized)
    normalized = re.sub(r"\bprod(?:uct)?\s*\(([^)]*)\)", r"product of \1", normalized, flags=re.I)
    normalized = re.sub(r"\bsum\s*\(([^)]*)\)", r"sum of \1", normalized, flags=re.I)
    normalized = re.sub(r"\b([APU])([xvb])\b", r"\1 \2", normalized)
    normalized = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", normalized)
    normalized = re.sub(r"\b([A-Za-z])_\{?([A-Za-z0-9]+)\}?\b", r"\1 sub \2", normalized)
    normalized = normalized.replace("\\cdots", " dot dot dot ").replace("\\times", " times ").replace("\\cdot", " times ")
    normalized = normalized.replace("*", " times ")
    normalized = normalized.replace("\\leq", " <= ").replace("\\geq", " >= ").replace("\\neq", " not equal ")
    normalized = normalized.replace("\\subseteq", " subset of ").replace("\\subset", " subset of ").replace("\\in", " in ")
    normalized = re.sub(r"\s*(<=|>=|=|\+|/|<|>)\s*", r" \1 ", normalized)
    normalized = re.sub(r"(?<![A-Za-z])\s*-\s*(?![A-Za-z])", " - ", normalized)
    normalized = re.sub(r"([A-Za-z])(?=\()", r"\1 ", normalized)
    normalized = re.sub(r"\s+([,.;:])", r"\\1", normalized)
    normalized = re.sub(r"([,;:])(?=\S)", r"\1 ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized

WORDS_PER_SECOND = 2.35
MIN_SHORT_VIDEO_SECONDS = 24.0
SCENE_METADATA_VERSION = "2026-05-11-video-rootfix2"


def spoken_word_count(text: object) -> int:
    return len(re.findall(r"[A-Za-z0-9]+(?:'[A-Za-z0-9]+)?", screen_prose(text)))


def estimate_spoken_seconds(text: object) -> float:
    return spoken_word_count(text) / WORDS_PER_SECOND


def duration_for_texts(texts: list[object], minimum: float, animation_budget: float) -> float:
    speech = sum(estimate_spoken_seconds(text) for text in texts)
    return max(minimum, speech + animation_budget + 1.2)



def float_or_zero(value: object) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return number if math.isfinite(number) else 0.0


def short_video_pacing(short: dict[str, object]) -> dict[str, float]:
    ex = short["worked_example"] if isinstance(short.get("worked_example"), dict) else {}
    qp = short["question_prompt"] if isinstance(short.get("question_prompt"), dict) else {}
    intro_texts = [short.get("hook", ""), short.get("intuition", ""), short.get("key_concept", ""), short.get("concept_explanation", ""), short.get("plain_formula", short.get("formula", ""))]
    example_texts = [ex.get("setup", ""), ex.get("calculation", ""), ex.get("takeaway", "")]
    recall_texts = [short.get("recognition_cue", ""), short.get("misconception", ""), qp.get("question", ""), qp.get("answer", "")]
    groups = [intro_texts, example_texts, recall_texts]
    floors = [14.0, 15.0, 11.5]
    fixed_motion = [7.7, 6.1, 5.3]

    voice_target = float_or_zero(short.get("voice_duration_seconds") or short.get("narration_duration_seconds"))
    if voice_target > 0:
        target_total = max(sum(floors), MIN_SHORT_VIDEO_SECONDS, min(92.0, voice_target + 0.35))
        weights = [max(1, sum(spoken_word_count(text) for text in group)) for group in groups]
        remaining = max(0.0, target_total - sum(floors))
        total_weight = sum(weights) or 1
        durations = [floors[i] + remaining * weights[i] / total_weight for i in range(3)]
    else:
        durations = [
            duration_for_texts(intro_texts, minimum=floors[0], animation_budget=6.4),
            duration_for_texts(example_texts, minimum=floors[1], animation_budget=5.6),
            duration_for_texts(recall_texts, minimum=floors[2], animation_budget=4.8),
        ]
        target_total = sum(durations)

    intro_duration, example_duration, recall_duration = durations
    intro_hold = max(0.8, intro_duration - fixed_motion[0])
    example_hold = max(0.8, example_duration - fixed_motion[1])
    recall_hold = max(0.8, recall_duration - fixed_motion[2])
    total = fixed_motion[0] + intro_hold + fixed_motion[1] + example_hold + fixed_motion[2] + recall_hold
    return {
        "intro_duration": round(fixed_motion[0] + intro_hold, 2),
        "example_duration": round(fixed_motion[1] + example_hold, 2),
        "recall_duration": round(fixed_motion[2] + recall_hold, 2),
        "intro_hold": round(intro_hold, 2),
        "example_hold": round(example_hold, 2),
        "recall_hold": round(recall_hold, 2),
        "total": round(total, 2),
    }


def srt_timestamp(seconds: float) -> str:
    millis = int(round(seconds * 1000))
    hours, rem = divmod(millis, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, ms = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def distribute_cue_durations(total: float, texts: list[object], minimum: float = 2.4) -> list[float]:
    if not texts:
        return []
    floor = min(minimum, total / len(texts))
    weights = [max(1, spoken_word_count(text)) for text in texts]
    remaining = max(0.0, total - floor * len(texts))
    weight_total = sum(weights) or len(texts)
    return [floor + remaining * weight / weight_total for weight in weights]


def caption_cues(short: dict[str, object], target_duration: float | None = None) -> list[tuple[str, str, str]]:
    ex = short["worked_example"] if isinstance(short.get("worked_example"), dict) else {}
    qp = short["question_prompt"] if isinstance(short.get("question_prompt"), dict) else {}
    pacing = short_video_pacing(short)
    groups = [
        (
            pacing["intro_duration"],
            [
                screen_prose(short.get("hook", "")),
                screen_prose(short.get("intuition", "")),
                screen_prose(short.get("key_concept", "")),
                screen_prose(short.get("concept_explanation", "")),
                screen_prose(short.get("plain_formula", short.get("formula", ""))),
            ],
        ),
        (
            pacing["example_duration"],
            [
                f"Example: {screen_prose(ex.get('setup', ''))}",
                screen_prose(ex.get("calculation", "")),
                f"Takeaway: {screen_prose(ex.get('takeaway', ''))}",
            ],
        ),
        (
            pacing["recall_duration"],
            [
                f"Recognition cue: {screen_prose(short.get('recognition_cue', ''))}",
                f"Common trap: {screen_prose(short.get('misconception', ''))}",
                f"Try this: {screen_prose(qp.get('question', ''))}",
                f"Answer: {screen_prose(qp.get('answer', ''))}",
            ],
        ),
    ]
    raw_cues: list[tuple[float, float, str]] = []
    cursor = 0.0
    for total, texts in groups:
        for duration, cue_text in zip(distribute_cue_durations(total, texts), texts):
            start = cursor
            cursor += duration
            raw_cues.append((start, cursor, cue_text))
    if target_duration and cursor > 0:
        scale = max(0.25, float(target_duration) / cursor)
        raw_cues = [(start * scale, end * scale, cue_text) for start, end, cue_text in raw_cues]
    return [(srt_timestamp(start), srt_timestamp(end), cue_text) for start, end, cue_text in raw_cues]


def numeric_literals(text: str) -> list[object]:
    values: list[object] = []
    pairs = {"[": "]", "(": ")"}
    for start, opener in enumerate(text):
        if opener not in pairs:
            continue
        closer = pairs[opener]
        depth = 0
        for end in range(start, len(text)):
            char = text[end]
            if char == opener:
                depth += 1
            elif char == closer:
                depth -= 1
                if depth == 0:
                    candidate = text[start : end + 1]
                    try:
                        values.append(ast.literal_eval(candidate))
                    except Exception:
                        pass
                    break
    return values


def is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def numeric_vector(value: object) -> list[float] | None:
    if isinstance(value, (list, tuple)) and value and all(is_number(item) for item in value):
        return [float(item) for item in value]
    return None


def numeric_matrix(value: object) -> list[list[float]] | None:
    if not isinstance(value, (list, tuple)) or not value:
        return None
    rows: list[list[float]] = []
    width: int | None = None
    for row in value:
        if not isinstance(row, (list, tuple)) or not row or not all(is_number(item) for item in row):
            return None
        numeric_row = [float(item) for item in row]
        width = width or len(numeric_row)
        if len(numeric_row) != width:
            return None
        rows.append(numeric_row)
    return rows


def format_scalar(value: object) -> str:
    try:
        number = float(value)
    except Exception:
        return str(value)
    if math.isfinite(number) and abs(number - round(number)) < 1e-9:
        return str(int(round(number)))
    return f"{number:.3g}"


def display_matrix(rows: list[list[float]]) -> list[list[str]]:
    return [[format_scalar(cell) for cell in row] for row in rows]


def display_vector(values: list[float]) -> list[str]:
    return [format_scalar(value) for value in values]


def extract_numbers(text: str, limit: int = 6) -> list[str]:
    out: list[str] = []
    for match in re.findall(r"(?<![A-Za-z])-?\d+(?:\.\d+)?", text):
        value = format_scalar(match)
        if value not in out:
            out.append(value)
        if len(out) >= limit:
            break
    return out or ["2", "5", "8"]


def short_text(short: dict[str, object]) -> str:
    ex = short.get("worked_example", {}) if isinstance(short.get("worked_example"), dict) else {}
    qp = short.get("question_prompt", {}) if isinstance(short.get("question_prompt"), dict) else {}
    return " ".join(
        str(part)
        for part in [
            short.get("concept", ""),
            short.get("hook", ""),
            short.get("intuition", ""),
            short.get("formula", ""),
            ex.get("setup", ""),
            ex.get("calculation", ""),
            ex.get("takeaway", ""),
            qp.get("question", ""),
            qp.get("answer", ""),
        ]
    )


def matrix_vector_data(short: dict[str, object]) -> dict[str, object]:
    text = short_text(short)
    literals = numeric_literals(text)
    matrices = [matrix for value in literals if (matrix := numeric_matrix(value))]
    vectors = [vector for value in literals if (vector := numeric_vector(value))]
    matrix = matrices[0] if matrices else [[2.0, 1.0], [1.0, 3.0]]
    row_count = len(matrix)
    col_count = len(matrix[0]) if matrix else 0
    vector: list[float] | None = None
    output: list[float] | None = None
    for candidate in vectors:
        if vector is None and len(candidate) == col_count:
            vector = candidate
            continue
        if output is None and len(candidate) == row_count:
            output = candidate
    if vector is None:
        vector = [4.0, 2.0][:col_count] or [1.0]
    if output is None:
        output = [sum(row[i] * vector[i] for i in range(min(len(row), len(vector)))) for row in matrix]
    columns = [[matrix[row][col] for row in range(row_count)] for col in range(col_count)]
    row_calcs = []
    for row, result in zip(matrix, output):
        terms = [f"{format_scalar(a)} * {format_scalar(b)}" for a, b in zip(row, vector)]
        row_calcs.append(f"{' + '.join(terms)} = {format_scalar(result)}")
    return {
        "matrix": display_matrix(matrix),
        "vector": display_vector(vector),
        "output": display_vector(output),
        "columns": [display_vector(column) for column in columns],
        "row_calcs": row_calcs,
    }


def vector_example_data(short: dict[str, object]) -> dict[str, object]:
    vectors = [vector for value in numeric_literals(short_text(short)) if (vector := numeric_vector(value))]
    vector = vectors[0] if vectors else [3.0, 4.0]
    if len(vector) < 2:
        vector = [vector[0], 0.0]
    length = math.sqrt(vector[0] * vector[0] + vector[1] * vector[1])
    return {
        "vector": display_vector(vector[:2]),
        "length": format_scalar(length),
        "x_range": [-1, max(5, int(abs(vector[0])) + 2), 1],
        "y_range": [-1, max(5, int(abs(vector[1])) + 2), 1],
    }


def linear_combo_data(short: dict[str, object]) -> dict[str, object]:
    text = short_text(short)
    vectors = [vector for value in numeric_literals(text) if (vector := numeric_vector(value))]
    a = vectors[0] if len(vectors) > 0 else [1.0, 0.0]
    b = vectors[1] if len(vectors) > 1 else [1.0, 1.0]
    target = vectors[2] if len(vectors) > 2 else [5.0, 2.0]
    weights = [3.0, 2.0]
    match = re.search(r"([+-]?\d+(?:\.\d+)?)\s*\*?\s*a\s*\+\s*([+-]?\d+(?:\.\d+)?)\s*\*?\s*b", text, re.I)
    if match:
        weights = [float(match.group(1)), float(match.group(2))]
    return {
        "a": display_vector(a[:2]),
        "b": display_vector(b[:2]),
        "target": display_vector(target[:2]),
        "weights": display_vector(weights),
    }



def text_has_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def semantic_visual_kind(text: str) -> str | None:
    if text_has_any(text, ("payoff", "nash", "dominant strateg", "best response", "game theory", "oligopoly", "strategic interaction", "prisoner")):
        return "game_payoff"
    if text_has_any(text, ("galois", "automorphism", "root symmetr", "gal(")):
        return "algebra_galois"
    if text_has_any(text, ("field extension", "extension degree", "algebraic element", "minimal polynomial", "finite field", "adjoin", "sqrt(2)", "q(sqrt")):
        return "algebra_field_extension"
    if text_has_any(text, ("polynomial ring", "quotient ring", "quotient rings", "f[x]", "r/i", "modular arithmetic")):
        return "algebra_quotient_ring"
    if text_has_any(text, ("euclidean domain", "principal ideal domain", "unique factorization", "ufd", "pid", "irreducible", "factorization")):
        return "algebra_factorization"
    if text_has_any(text, ("ideal", "ideals", "kernel", "absorb multiplication")) and "ring" in text:
        return "algebra_ideal"
    if text_has_any(text, ("ring", "rings", "field", "fields", "zero divisor", "inverse modulo", "modulo")):
        return "algebra_ring_field"
    if text_has_any(text, ("cache", "memory", "stack", "queue", "heap", "pointer", "array", "hash", "linked list")):
        return "cs_array"
    if text_has_any(text, ("recursion", "dynamic programming", "divide and conquer", "control flow", "branch", "loop", "algorithm", "sort", "search", "complexity", "runtime", "big-o", "o(")):
        return "cs_array"
    if text_has_any(text, ("graph", "tree", "network", "path", "node", "edge", "bfs", "dfs")):
        return "cs_graph"
    if text_has_any(text, ("state", "automaton", "transition", "markov")):
        return "state_machine"
    if text_has_any(text, ("free body", "force", "newton", "acceleration", "velocity", "momentum", "vector field")):
        return "physics_force"
    if text_has_any(text, ("energy", "work", "potential", "kinetic", "conservation")):
        return "physics_energy"
    if text_has_any(text, ("wave", "frequency", "amplitude", "oscillation", "phase")):
        return "physics_wave"
    return None


def infer_visual_kind(short: dict[str, object]) -> str:
    explicit = str(short.get("visual_type", "generic")).strip().lower()
    text = short_text(short).lower()
    concept = str(short.get("concept", "")).lower()
    concept_visuals = (
        (("galois",), "algebra_galois"),
        (("field extension", "algebraic element", "finite field"), "algebra_field_extension"),
        (("quotient ring", "polynomial ring"), "algebra_quotient_ring"),
        (("euclidean domain", "principal ideal domain", "unique factorization", "ufd"), "algebra_factorization"),
        (("ideal",), "algebra_ideal"),
        (("ring", "field"), "algebra_ring_field"),
        (("nash", "dominant strateg", "oligopoly", "payoff"), "game_payoff"),
        (("tax", "incidence", "deadweight", "wedge"), "econ_tax_wedge"),
        (("surplus", "ceiling", "floor", "externalit", "public good", "welfare"), "econ_supply_demand"),
        (("budget", "consumer choice", "preference", "utility", "indifference", "marginal rate of substitution", "marginal utility"), "econ_budget"),
        (("elasticity",), "econ_elasticity"),
        (("income", "substitution", "comparative statics", "cost", "production", "returns", "marginal product", "marginal cost", "average cost", "shutdown", "competition", "monopoly", "revenue", "price discrimination", "adverse selection", "moral hazard", "coase"), "econ_curve"),
    )
    inferred = next((kind for terms, kind in concept_visuals if any(term in concept for term in terms)), None) or semantic_visual_kind(text)
    generic_fallbacks = {"", "generic", "numeric_rule", "state_machine"}
    if inferred:
        return inferred
    if explicit and explicit not in generic_fallbacks:
        return explicit
    if any(term in text for term in ("matrix", "linear system", "ax=", "a\\vec", "row operation")):
        return "matrix_vector"
    if "vector" in text or "coordinate" in text:
        return "vector_components"
    if any(term in text for term in ("derivative", "tangent", "slope", "gradient", "rate of change")):
        return "calculus_tangent"
    if any(term in text for term in ("integral", "area under", "accumulation", "riemann")):
        return "calculus_area"
    if any(term in text for term in ("probability", "bayes", "distribution", "random", "expectation")):
        return "probability"
    if any(term in text for term in ("reaction", "molecule", "atom", "equilibrium", "chemical")):
        return "chemistry_reaction"
    return "numeric_rule"

def visual_data_for(short: dict[str, object], kind: str) -> dict[str, object]:
    data: dict[str, object] = {"numbers": extract_numbers(short_text(short))}
    if kind == "matrix_vector":
        data["matrix_vector"] = matrix_vector_data(short)
    if kind == "vector_components":
        data["vector"] = vector_example_data(short)
    if kind == "linear_combination":
        data["linear_combo"] = linear_combo_data(short)
    return data


MANIM_SCENE_HELPERS = '''
def fmt(self, value):
    text = str(value)
    try:
        number = float(text)
    except Exception:
        return text
    if abs(number - round(number)) < 1e-9:
        return str(int(round(number)))
    return f"{number:.3g}"

def palette(self, index):
    colors = ["#58A6FF", "#F7C948", "#7EE787", "#FF7B72", "#A371F7"]
    return colors[index % len(colors)]

def fit_in(self, mob, max_width=7.8, max_height=6.0):
    if mob.width > max_width:
        mob.scale(max_width / mob.width)
    if mob.height > max_height:
        mob.scale(max_height / mob.height)
    return mob

def layout_registry(self):
    if not hasattr(self, "_layout_registry"):
        self._layout_registry = []
    return self._layout_registry

def validate_layout(self, mob, name="mobject", pad=0.36):
    left_limit = -config.frame_width / 2 + pad
    right_limit = config.frame_width / 2 - pad
    bottom_limit = -config.frame_height / 2 + pad
    top_limit = config.frame_height / 2 - pad
    if mob.get_left()[0] < left_limit or mob.get_right()[0] > right_limit:
        self.fit_in(mob, max_width=config.frame_width - 2 * pad, max_height=config.frame_height - 2 * pad)
    if mob.get_bottom()[1] < bottom_limit:
        mob.shift(UP * (bottom_limit - mob.get_bottom()[1]))
    if mob.get_top()[1] > top_limit:
        mob.shift(DOWN * (mob.get_top()[1] - top_limit))
    return mob

def boxes_overlap(self, a, b, pad=0.12):
    return not (
        a.get_right()[0] + pad < b.get_left()[0]
        or b.get_right()[0] + pad < a.get_left()[0]
        or a.get_top()[1] + pad < b.get_bottom()[1]
        or b.get_top()[1] + pad < a.get_bottom()[1]
    )

def avoid_layout_collisions(self, mob, top=6.05, bottom=-7.15, pad=0.14):
    registry = [other for other in self.layout_registry() if other is not mob and hasattr(other, "get_left")]
    for _ in range(18):
        overlapping = [other for other in registry if self.boxes_overlap(mob, other, pad=pad)]
        if not overlapping:
            break
        other = max(overlapping, key=lambda item: abs(item.get_center()[1] - mob.get_center()[1]))
        if mob.get_center()[1] <= other.get_center()[1]:
            shift = other.get_bottom()[1] - mob.get_top()[1] - pad
        else:
            shift = other.get_top()[1] - mob.get_bottom()[1] + pad
        if abs(shift) < 0.05:
            shift = -0.18 if mob.get_center()[1] <= other.get_center()[1] else 0.18
        mob.shift(UP * shift)
        if mob.get_top()[1] > top:
            mob.shift(DOWN * (mob.get_top()[1] - top))
        if mob.get_bottom()[1] < bottom:
            mob.shift(UP * (bottom - mob.get_bottom()[1]))
    return mob

def remember_layout(self, mob):
    registry = self.layout_registry()
    if mob not in registry:
        registry.append(mob)
    return mob

def safe_place(self, mob, y=0, max_width=7.8, max_height=6.0, top=6.05, bottom=-7.15, remember=True):
    self.fit_in(mob, max_width=max_width, max_height=max_height)
    mob.move_to(UP * y)
    if mob.get_top()[1] > top:
        mob.shift(DOWN * (mob.get_top()[1] - top))
    if mob.get_bottom()[1] < bottom:
        mob.shift(UP * (bottom - mob.get_bottom()[1]))
    self.validate_layout(mob)
    if remember:
        self.avoid_layout_collisions(mob, top=top, bottom=bottom)
        self.validate_layout(mob)
        self.remember_layout(mob)
    return mob

def text_block(self, lines, font_size=25, color="#EAF2FF", max_width=7.4, line_buff=0.12, max_height=2.3):
    clean_lines = [str(line).strip() for line in lines if str(line).strip()]
    if not clean_lines:
        clean_lines = [""]
    group = VGroup(*[Text(line, font_size=font_size, color=color, disable_ligatures=True) for line in clean_lines]).arrange(DOWN, buff=line_buff)
    return self.fit_in(group, max_width=max_width, max_height=max_height)

def formula_fallback_text(self, latex, plain):
    fallback = str(latex or plain or "")
    slash = chr(92)
    slash_pattern = re.escape(slash)
    fallback = re.sub(slash_pattern + r"operatorname\{([^{}]+)\}", r"\\1", fallback)
    fallback = re.sub(slash_pattern + r"frac\{([^{}]+)\}\{([^{}]+)\}", r"(\\1)/(\\2)", fallback)
    fallback = re.sub(slash_pattern + r"sqrt\{([^{}]+)\}", chr(8730) + r"(\\1)", fallback)
    replacements = [
        (slash + "subseteq", " " + chr(8838) + " "),
        (slash + "subset", " " + chr(8834) + " "),
        (slash + "notin", " " + chr(8713) + " "),
        (slash + "in", " " + chr(8712) + " "),
        (slash + "leq", " " + chr(8804) + " "),
        (slash + "geq", " " + chr(8805) + " "),
        (slash + "neq", " " + chr(8800) + " "),
        (slash + "Rightarrow", " " + chr(8658) + " "),
        (slash + "times", " " + chr(215) + " "),
        (slash + "cdot", " " + chr(183) + " "),
        (slash + "langle", "<"),
        (slash + "rangle", ">"),
        (slash + "mathbb", ""),
        (slash + "mathcal", ""),
        (slash + "mathbf", ""),
        (slash + "vec", ""),
        (slash + "hat", ""),
    ]
    for old, new in replacements:
        fallback = fallback.replace(old, new)
    fallback = re.sub(r"_\{([^{}]+)\}", r"_\\1", fallback)
    fallback = re.sub(r"\^\{([^{}]+)\}", r"^\\1", fallback)
    fallback = fallback.replace("{", "").replace("}", "")
    fallback = fallback.replace(slash, "")
    fallback = " ".join(fallback.split())
    if not fallback:
        fallback = " ".join(str(plain or "").replace(slash, " ").split()) or "formula cue"
    return fallback

def formula_block(self, latex, plain, font_size=32, color="#F7C948", max_width=7.6):
    candidates = []
    for candidate in (latex, str(latex).strip().strip("$")):
        candidate = str(candidate).strip()
        if candidate and candidate not in candidates:
            candidates.append(candidate)
    for candidate in candidates:
        try:
            mob = MathTex(candidate, font_size=font_size, color=color)
            return self.fit_in(mob, max_width=max_width, max_height=1.15)
        except Exception:
            pass
    mob = Text(self.formula_fallback_text(latex, plain), font_size=font_size, color=color, disable_ligatures=True)
    return self.fit_in(mob, max_width=max_width, max_height=1.15)

def section_label(self, text, color="#F7C948"):
    label = Text(text, font_size=30, weight="BOLD", color=color)
    return self.safe_place(label, y=5.7, max_width=7.6, max_height=0.65, top=6.05, bottom=5.15)

def fade_all_except(self, keep=None, run_time=0.6):
    keep = keep or []
    keep_family = set()
    for mob in keep:
        keep_family.add(mob)
        if hasattr(mob, "get_family"):
            keep_family.update(mob.get_family())
    fading = [mob for mob in self.mobjects if mob not in keep_family]
    if fading:
        self.play(*[FadeOut(mob) for mob in fading], run_time=run_time)
    self._layout_registry = [mob for mob in keep if hasattr(mob, "get_left")]


def semantic_beat_hold(self, duration, focus=None, label=None):
    remaining = max(0.0, float(duration or 0))
    if remaining <= 0.05:
        return
    focus = [mob for mob in (focus or []) if hasattr(mob, "animate")]
    if not focus:
        focus = [mob for mob in self.mobjects if hasattr(mob, "animate") and getattr(mob, "width", 0) > 0.2 and getattr(mob, "height", 0) > 0.2]
    if not focus:
        self.wait(remaining)
        return
    index = 0
    while remaining > 0.05:
        mob = focus[index % len(focus)]
        step = min(1.25, remaining)
        accent = self.palette(index)
        if index % 3 == 2:
            animation = Circumscribe(mob, color=accent, fade_out=True, time_width=0.35, buff=0.08)
        else:
            animation = Indicate(mob, scale_factor=1.035, color=accent)
        self.play(animation, run_time=step)
        remaining -= step
        index += 1

def active_hold(self, duration, focus=None):
    self.semantic_beat_hold(duration, focus, "key beat")

def matrix_block(self, rows, font_size=30, color="#EAF2FF", bracket_color="#8FD3FF", column_colors=None, cell_colors=None):
    row_groups = VGroup()
    cell_colors = cell_colors or {}
    for r, row in enumerate(rows):
        cells = VGroup()
        for c, cell in enumerate(row):
            cell_color = cell_colors.get((r, c))
            if cell_color is None and column_colors:
                cell_color = column_colors[c % len(column_colors)]
            cells.add(Text(str(cell), font_size=font_size, color=cell_color or color))
        row_groups.add(cells.arrange(RIGHT, buff=0.42))
    row_groups.arrange(DOWN, buff=0.22)
    left = Text("[", font_size=78, color=bracket_color).stretch_to_fit_height(row_groups.height + 0.35).next_to(row_groups, LEFT, buff=0.12)
    right = Text("]", font_size=78, color=bracket_color).stretch_to_fit_height(row_groups.height + 0.35).next_to(row_groups, RIGHT, buff=0.12)
    return VGroup(left, row_groups, right)

def matrix_equation(self, data, font_size=28):
    col_colors = [self.palette(i) for i in range(max(1, len(data.get("columns", []))))]
    matrix = self.matrix_block(data["matrix"], font_size=font_size, bracket_color="#58A6FF", column_colors=col_colors)
    vector = self.matrix_block([[v] for v in data["vector"]], font_size=font_size, color="#F7C948", bracket_color="#F7C948")
    output = self.matrix_block([[v] for v in data["output"]], font_size=font_size, color="#7EE787", bracket_color="#7EE787")
    return VGroup(matrix, Text("x", font_size=font_size + 2, color="#EAF2FF"), vector, Text("=", font_size=font_size + 2, color="#EAF2FF"), output).arrange(RIGHT, buff=0.24)

def matrix_column_combo(self, data, font_size=24, include_output=True):
    parts = VGroup()
    columns = data.get("columns", [])
    for i, column in enumerate(columns):
        if i:
            parts.add(Text("+", font_size=font_size, color="#EAF2FF"))
        parts.add(Text(str(data["vector"][i]), font_size=font_size + 1, color="#EAF2FF"))
        parts.add(self.matrix_block([[v] for v in column], font_size=font_size, color=self.palette(i), bracket_color=self.palette(i)))
    if include_output:
        parts.add(Text("=", font_size=font_size, color="#EAF2FF"))
        parts.add(self.matrix_block([[v] for v in data["output"]], font_size=font_size, color="#7EE787", bracket_color="#7EE787"))
    return parts.arrange(RIGHT, buff=0.14)

def play_matrix_vector_intro(self, data):
    equation = self.matrix_equation(data, font_size=30)
    self.safe_place(equation, y=1.55, max_width=8.0, max_height=2.25, top=3.95, bottom=-0.35)
    combo = self.matrix_column_combo(data, font_size=24)
    self.safe_place(combo, y=-1.65, max_width=8.15, max_height=2.35, top=0.0, bottom=-3.65)
    box = SurroundingRectangle(combo[-1], color="#7EE787", buff=0.12)
    self.play(FadeIn(equation, shift=UP * 0.1), run_time=1.0)
    self.play(LaggedStart(*[FadeIn(mob, shift=UP * 0.08) for mob in combo], lag_ratio=0.12), run_time=1.5)
    self.play(Create(box), Indicate(combo[-1]), run_time=0.9)

def play_matrix_vector_example(self, data, setup_lines, calc_lines, takeaway_lines):
    setup_caption = Text("Let the matrix A act on the input vector x.", font_size=20, color="#8FD3FF")
    setup_math = VGroup(
        Text("A =", font_size=20, color="#EAF2FF"),
        self.matrix_block(data["matrix"], font_size=18, bracket_color="#58A6FF", column_colors=[self.palette(i) for i in range(len(data.get("columns", [])))]),
        Text("x =", font_size=20, color="#EAF2FF"),
        self.matrix_block([[v] for v in data["vector"]], font_size=18, color="#F7C948", bracket_color="#F7C948"),
    ).arrange(RIGHT, buff=0.14)
    setup = VGroup(setup_caption, setup_math).arrange(DOWN, buff=0.14)
    self.safe_place(setup, y=4.55, max_width=7.7, max_height=1.25, top=5.2, bottom=3.85)
    equation = self.matrix_equation(data, font_size=27)
    self.safe_place(equation, y=2.55, max_width=8.05, max_height=2.0, top=3.8, bottom=1.25)
    row_group = VGroup(*[Text(line, font_size=25, color=self.palette(i)) for i, line in enumerate(data.get("row_calcs", []))]).arrange(DOWN, buff=0.22)
    self.safe_place(row_group, y=0.0, max_width=7.8, max_height=1.45, top=0.9, bottom=-1.0)
    combo = self.matrix_column_combo(data, font_size=23)
    self.safe_place(combo, y=-2.55, max_width=8.1, max_height=2.15, top=-1.25, bottom=-4.0)
    takeaway = self.text_block(takeaway_lines, font_size=23, color="#7EE787", max_width=7.4)
    self.safe_place(takeaway, y=-5.65, max_height=1.05, top=-5.0, bottom=-6.55)
    self.play(FadeIn(setup, shift=UP * 0.08), FadeIn(equation, shift=UP * 0.08), run_time=1.0)
    matrix = equation[0]
    row_box = None
    for i, row_text in enumerate(row_group):
        new_box = SurroundingRectangle(matrix[1][i], color=self.palette(i), buff=0.08)
        if row_box is None:
            row_box = new_box
            self.play(Create(row_box), FadeIn(row_text, shift=UP * 0.08), run_time=0.75)
        else:
            self.play(Transform(row_box, new_box), FadeIn(row_text, shift=UP * 0.08), run_time=0.75)
    if row_box is not None:
        self.play(FadeOut(row_box), run_time=0.35)
    self.play(LaggedStart(*[FadeIn(mob, shift=UP * 0.08) for mob in combo], lag_ratio=0.08), run_time=1.2)
    self.play(Indicate(combo[-1]), FadeIn(takeaway, shift=UP * 0.08), run_time=1.0)

def play_matrix_vector_recall(self, data, question_lines, answer_lines):
    prompt = self.text_block(question_lines, font_size=22, color="#EAF2FF", max_width=7.4)
    self.safe_place(prompt, y=4.65, max_height=1.1, top=5.1, bottom=3.8)
    matrix = self.matrix_block(data["matrix"], font_size=24, bracket_color="#58A6FF", column_colors=[self.palette(i) for i in range(len(data.get("columns", [])))])
    vector = self.matrix_block([[v] for v in data["vector"]], font_size=24, color="#F7C948", bracket_color="#F7C948")
    unknown = self.matrix_block([["?"] for _ in data["output"]], font_size=24, color="#7EE787", bracket_color="#7EE787")
    pipeline = VGroup(VGroup(Text("effects", font_size=18, color="#58A6FF"), matrix).arrange(DOWN, buff=0.12), Text("x", font_size=28), VGroup(Text("weights", font_size=18, color="#F7C948"), vector).arrange(DOWN, buff=0.12), Text("->", font_size=28), VGroup(Text("response", font_size=18, color="#7EE787"), unknown).arrange(DOWN, buff=0.12)).arrange(RIGHT, buff=0.2)
    self.safe_place(pipeline, y=1.35, max_width=8.1, max_height=2.8, top=3.1, bottom=-0.6)
    combo = self.matrix_column_combo(data, font_size=22)
    self.safe_place(combo, y=-1.8, max_width=8.1, max_height=2.0, top=-0.8, bottom=-3.3)
    answer = self.text_block(answer_lines, font_size=22, color="#7EE787", max_width=7.4)
    self.safe_place(answer, y=-5.25, max_height=1.35, top=-4.35, bottom=-6.35)
    self.play(FadeIn(prompt, shift=UP * 0.08), FadeIn(pipeline, shift=UP * 0.08), run_time=1.1)
    self.play(LaggedStart(*[FadeIn(mob, shift=UP * 0.06) for mob in combo], lag_ratio=0.08), run_time=1.15)
    self.play(Transform(unknown, self.matrix_block([[v] for v in data["output"]], font_size=24, color="#7EE787", bracket_color="#7EE787").move_to(unknown)), FadeIn(answer, shift=UP * 0.08), run_time=1.0)
    self.play(Indicate(combo[-1]), run_time=0.8)

def vector_plane_objects(self, data):
    vx = float(data["vector"][0])
    vy = float(data["vector"][1])
    plane = NumberPlane(x_range=data.get("x_range", [-1, 5, 1]), y_range=data.get("y_range", [-1, 5, 1]), x_length=6.7, y_length=4.9, background_line_style={"stroke_color": "#1F3558", "stroke_width": 1, "stroke_opacity": 0.7})
    self.safe_place(plane, y=0.9, max_width=7.3, max_height=5.0, top=3.9, bottom=-2.1)
    origin = plane.c2p(0, 0)
    x_end = plane.c2p(vx, 0)
    end = plane.c2p(vx, vy)
    x_leg = Arrow(origin, x_end, buff=0, color="#F7C948", stroke_width=7)
    y_leg = Arrow(x_end, end, buff=0, color="#7EE787", stroke_width=7)
    vec = Arrow(origin, end, buff=0, color="#58A6FF", stroke_width=8)
    labels = VGroup(Text(str(data["vector"][0]), font_size=26, color="#F7C948").next_to(x_leg, DOWN), Text(str(data["vector"][1]), font_size=26, color="#7EE787").next_to(y_leg, RIGHT), Text("length " + str(data["length"]), font_size=26, color="#8FD3FF").next_to(vec, UP))
    return plane, x_leg, y_leg, vec, labels

def play_vector_intro(self, data):
    plane, x_leg, y_leg, vec, labels = self.vector_plane_objects(data)
    self.play(Create(plane), GrowArrow(x_leg), GrowArrow(y_leg), run_time=1.1)
    self.play(GrowArrow(vec), FadeIn(labels), run_time=1.2)
    self.play(Indicate(labels[2]), run_time=0.8)

def play_vector_example(self, data, setup_lines, calc_lines, takeaway_lines):
    setup = self.text_block(setup_lines, font_size=21, color="#8FD3FF")
    self.safe_place(setup, y=4.65, max_height=0.85, top=5.1, bottom=4.0)
    plane, x_leg, y_leg, vec, labels = self.vector_plane_objects(data)
    formula = Text(f"{data['vector'][0]}^2 + {data['vector'][1]}^2 -> length {data['length']}", font_size=27, color="#F7C948")
    self.safe_place(formula, y=-3.4, max_width=7.4, max_height=0.55, top=-3.05, bottom=-3.8)
    takeaway = self.text_block(takeaway_lines, font_size=23, color="#7EE787")
    self.safe_place(takeaway, y=-5.45, max_height=1.0, top=-4.8, bottom=-6.3)
    self.play(FadeIn(setup), Create(plane), GrowArrow(x_leg), GrowArrow(y_leg), run_time=1.1)
    self.play(GrowArrow(vec), FadeIn(labels), run_time=1.0)
    self.play(Write(formula), FadeIn(takeaway, shift=UP * 0.08), run_time=1.0)

def play_vector_recall(self, data, question_lines, answer_lines):
    prompt = self.text_block(question_lines, font_size=22)
    self.safe_place(prompt, y=4.55, max_height=1.1, top=5.1, bottom=3.75)
    plane, x_leg, y_leg, vec, labels = self.vector_plane_objects(data)
    answer = self.text_block(answer_lines, font_size=22, color="#7EE787")
    self.safe_place(answer, y=-5.1, max_height=1.4, top=-4.25, bottom=-6.3)
    self.play(FadeIn(prompt), Create(plane), GrowArrow(x_leg), GrowArrow(y_leg), run_time=1.1)
    self.play(GrowArrow(vec), FadeIn(labels), run_time=1.0)
    self.play(FadeIn(answer, shift=UP * 0.08), Indicate(labels[2]), run_time=0.9)

def linear_combo_objects(self, data):
    ax, ay = [float(v) for v in data["a"]]
    bx, by = [float(v) for v in data["b"]]
    tx, ty = [float(v) for v in data["target"]]
    plane = NumberPlane(x_range=[-1, max(6, int(max(abs(ax), abs(bx), abs(tx))) + 2), 1], y_range=[-1, max(5, int(max(abs(ay), abs(by), abs(ty))) + 2), 1], x_length=6.8, y_length=4.8, background_line_style={"stroke_color": "#1F3558", "stroke_width": 1, "stroke_opacity": 0.7})
    self.safe_place(plane, y=0.8, max_width=7.3, max_height=5.0, top=3.8, bottom=-2.1)
    origin = plane.c2p(0, 0)
    a = Arrow(origin, plane.c2p(ax, ay), buff=0, color="#58A6FF", stroke_width=7)
    b = Arrow(origin, plane.c2p(bx, by), buff=0, color="#F7C948", stroke_width=7)
    first = Arrow(origin, plane.c2p(ax * float(data["weights"][0]), ay * float(data["weights"][0])), buff=0, color="#58A6FF", stroke_width=8)
    second = Arrow(first.get_end(), plane.c2p(tx, ty), buff=0, color="#F7C948", stroke_width=8)
    target = Dot(plane.c2p(tx, ty), radius=0.09, color="#7EE787")
    label = Text(f"{data['weights'][0]}a + {data['weights'][1]}b = ({data['target'][0]}, {data['target'][1]})", font_size=25, color="#7EE787")
    self.safe_place(label, y=-3.35, max_width=7.4, max_height=0.55, top=-3.05, bottom=-3.8)
    return plane, a, b, first, second, target, label

def play_linear_combo_intro(self, data):
    plane, a, b, first, second, target, label = self.linear_combo_objects(data)
    self.play(Create(plane), GrowArrow(a), GrowArrow(b), run_time=1.1)
    self.play(TransformFromCopy(a, first), TransformFromCopy(b, second), FadeIn(target, scale=1.3), run_time=1.25)
    self.play(FadeIn(label), Flash(target, color="#7EE787"), run_time=0.9)

def play_linear_combo_example(self, data, setup_lines, calc_lines, takeaway_lines):
    setup = self.text_block(setup_lines, font_size=21, color="#8FD3FF")
    self.safe_place(setup, y=4.65, max_height=0.85, top=5.1, bottom=4.0)
    plane, a, b, first, second, target, label = self.linear_combo_objects(data)
    takeaway = self.text_block(takeaway_lines, font_size=23, color="#7EE787")
    self.safe_place(takeaway, y=-5.45, max_height=1.0, top=-4.8, bottom=-6.3)
    self.play(FadeIn(setup), Create(plane), GrowArrow(a), GrowArrow(b), run_time=1.1)
    self.play(GrowArrow(first), GrowArrow(second), FadeIn(target), run_time=1.1)
    self.play(FadeIn(label), FadeIn(takeaway, shift=UP * 0.08), Indicate(target), run_time=1.0)

def play_linear_combo_recall(self, data, question_lines, answer_lines):
    prompt = self.text_block(question_lines, font_size=22)
    self.safe_place(prompt, y=4.55, max_height=1.1, top=5.1, bottom=3.75)
    plane, a, b, first, second, target, label = self.linear_combo_objects(data)
    answer = self.text_block(answer_lines, font_size=22, color="#7EE787")
    self.safe_place(answer, y=-5.1, max_height=1.4, top=-4.25, bottom=-6.3)
    self.play(FadeIn(prompt), Create(plane), GrowArrow(a), GrowArrow(b), run_time=1.1)
    self.play(GrowArrow(first), GrowArrow(second), FadeIn(target), FadeIn(label), run_time=1.1)
    self.play(FadeIn(answer, shift=UP * 0.08), Flash(target, color="#7EE787"), run_time=0.9)

def play_calculus_visual(self, kind, phase, data, primary_lines, secondary_lines=None, result_lines=None):
    caption = self.text_block(primary_lines, font_size=21, color="#8FD3FF")
    self.safe_place(caption, y=4.55, max_height=1.0, top=5.1, bottom=3.85)
    axes = Axes(x_range=[-1, 4, 1], y_range=[0, 5, 1], x_length=6.7, y_length=4.6, tips=False).shift(DOWN * 0.1)
    self.safe_place(axes, y=0.65, max_width=7.2, max_height=4.8, top=3.3, bottom=-2.2)
    curve = axes.plot(lambda x: 0.45 * (x - 0.5) * (x - 0.5) + 0.8, x_range=[-0.4, 3.7], color="#F7C948", stroke_width=6)
    if kind == "calculus_area":
        rects = axes.get_riemann_rectangles(curve, x_range=[0.2, 3.2], dx=0.5, color="#58A6FF", fill_opacity=0.45, stroke_width=1)
        result = self.text_block(result_lines or secondary_lines or ["accumulated area"], font_size=22, color="#7EE787")
        self.safe_place(result, y=-5.15, max_height=1.3, top=-4.25, bottom=-6.35)
        self.play(FadeIn(caption), Create(axes), Create(curve), run_time=1.0)
        self.play(LaggedStart(*[FadeIn(rect, shift=UP * 0.05) for rect in rects], lag_ratio=0.05), run_time=1.2)
        self.play(FadeIn(result, shift=UP * 0.08), Indicate(rects), run_time=0.9)
        return
    p1 = Dot(axes.c2p(1.0, 0.45 * (1.0 - 0.5) * (1.0 - 0.5) + 0.8), color="#58A6FF")
    p2 = Dot(axes.c2p(2.6, 0.45 * (2.6 - 0.5) * (2.6 - 0.5) + 0.8), color="#7EE787")
    secant = Line(p1.get_center(), p2.get_center(), color="#58A6FF", stroke_width=5)
    tangent = Line(axes.c2p(0.0, 0.55), axes.c2p(2.2, 1.55), color="#7EE787", stroke_width=5)
    result = self.text_block(result_lines or secondary_lines or ["local slope"], font_size=22, color="#7EE787")
    self.safe_place(result, y=-5.15, max_height=1.3, top=-4.25, bottom=-6.35)
    self.play(FadeIn(caption), Create(axes), Create(curve), FadeIn(p1), FadeIn(p2), run_time=1.0)
    self.play(Create(secant), run_time=0.7)
    self.play(Transform(secant, tangent), FadeIn(result, shift=UP * 0.08), run_time=1.1)

def play_physics_visual(self, kind, phase, data, primary_lines, secondary_lines=None, result_lines=None):
    caption = self.text_block(primary_lines, font_size=21, color="#8FD3FF")
    self.safe_place(caption, y=4.55, max_height=1.0, top=5.1, bottom=3.85)
    block = RoundedRectangle(width=1.4, height=0.9, corner_radius=0.1, color="#EAF2FF", fill_color="#101A33", fill_opacity=0.9)
    self.safe_place(block, y=0.65, max_width=2.0, max_height=1.2, top=1.4, bottom=-0.1)
    floor = Line(LEFT * 3.2, RIGHT * 3.2, color="#1F3558", stroke_width=4).next_to(block, DOWN, buff=0.05)
    force = Arrow(block.get_right(), block.get_right() + RIGHT * 2.1, buff=0.05, color="#58A6FF", stroke_width=8)
    friction = Arrow(block.get_left(), block.get_left() + LEFT * 1.2, buff=0.05, color="#FF7B72", stroke_width=6)
    accel = Arrow(block.get_top(), block.get_top() + RIGHT * 1.4 + UP * 0.7, buff=0.05, color="#7EE787", stroke_width=7)
    result = self.text_block(result_lines or secondary_lines or ["net change"], font_size=22, color="#7EE787")
    self.safe_place(result, y=-5.05, max_height=1.35, top=-4.2, bottom=-6.25)
    self.play(FadeIn(caption), FadeIn(block), Create(floor), run_time=0.9)
    self.play(GrowArrow(force), GrowArrow(friction), run_time=0.9)
    self.play(GrowArrow(accel), FadeIn(result, shift=UP * 0.08), Indicate(block), run_time=1.0)

def play_wave_visual(self, phase, data, primary_lines, secondary_lines=None, result_lines=None):
    caption = self.text_block(primary_lines, font_size=21, color="#8FD3FF")
    self.safe_place(caption, y=4.55, max_height=1.0, top=5.1, bottom=3.85)
    axes = Axes(x_range=[0, 7, 1], y_range=[-1.5, 1.5, 1], x_length=7.0, y_length=3.8, tips=False)
    self.safe_place(axes, y=0.55, max_width=7.4, max_height=4.0, top=2.8, bottom=-2.0)
    wave = axes.plot(lambda x: math.sin(2 * x), x_range=[0, 6.6], color="#58A6FF", stroke_width=6)
    dot = Dot(axes.c2p(1.0, math.sin(2.0)), color="#F7C948")
    dot2 = Dot(axes.c2p(2.2, math.sin(4.4)), color="#F7C948")
    result = self.text_block(result_lines or secondary_lines or ["amplitude and phase move together"], font_size=22, color="#7EE787")
    self.safe_place(result, y=-5.05, max_height=1.35, top=-4.2, bottom=-6.25)
    self.play(FadeIn(caption), Create(axes), Create(wave), FadeIn(dot), run_time=1.0)
    self.play(Transform(dot, dot2), FadeIn(result, shift=UP * 0.08), run_time=1.1)

def play_cs_visual(self, kind, phase, data, primary_lines, secondary_lines=None, result_lines=None):
    caption = self.text_block(primary_lines, font_size=21, color="#8FD3FF")
    self.safe_place(caption, y=4.55, max_height=1.0, top=5.1, bottom=3.85)
    if kind == "cs_graph":
        nodes = VGroup(*[Circle(radius=0.28, color=self.palette(i), fill_opacity=0.15) for i in range(5)])
        positions = [LEFT * 2.4 + UP * 0.7, LEFT * 0.8 + UP * 1.2, RIGHT * 0.8 + UP * 0.25, LEFT * 0.4 + DOWN * 1.0, RIGHT * 2.3 + DOWN * 0.55]
        for i, node in enumerate(nodes):
            node.move_to(positions[i])
            node.add(Text(chr(65 + i), font_size=20, color=self.palette(i)).move_to(node))
        edges = VGroup(Line(nodes[0].get_center(), nodes[1].get_center(), color="#1F3558"), Line(nodes[1].get_center(), nodes[2].get_center(), color="#1F3558"), Line(nodes[1].get_center(), nodes[3].get_center(), color="#1F3558"), Line(nodes[2].get_center(), nodes[4].get_center(), color="#1F3558"))
        graph = VGroup(edges, nodes)
        self.safe_place(graph, y=0.4, max_width=7.0, max_height=4.0, top=2.8, bottom=-2.4)
        path = VGroup(*[Line(nodes[i].get_center(), nodes[j].get_center(), color="#7EE787", stroke_width=6) for i, j in [(0, 1), (1, 2), (2, 4)]])
        result = self.text_block(result_lines or secondary_lines or ["trace the reachable path"], font_size=22, color="#7EE787")
        self.safe_place(result, y=-5.05, max_height=1.35, top=-4.2, bottom=-6.25)
        self.play(FadeIn(caption), Create(edges), FadeIn(nodes), run_time=1.0)
        self.play(LaggedStart(*[Create(edge) for edge in path], lag_ratio=0.18), FadeIn(result, shift=UP * 0.08), run_time=1.2)
        return
    values = data.get("numbers", ["4", "1", "7", "3", "9"])
    cells = VGroup(*[VGroup(Square(0.72, color=self.palette(i), fill_opacity=0.18), Text(str(values[i % len(values)]), font_size=22, color="#EAF2FF")) for i in range(5)]).arrange(RIGHT, buff=0.08)
    self.safe_place(cells, y=0.75, max_width=7.4, max_height=1.2, top=1.55, bottom=0.0)
    pointer = Triangle(color="#F7C948", fill_opacity=0.9).scale(0.18).rotate(PI).next_to(cells[0], UP, buff=0.18)
    result = self.text_block(result_lines or secondary_lines or ["state changes one step at a time"], font_size=22, color="#7EE787")
    self.safe_place(result, y=-5.05, max_height=1.35, top=-4.2, bottom=-6.25)
    self.play(FadeIn(caption), FadeIn(cells), FadeIn(pointer), run_time=0.9)
    for cell in cells[1:4]:
        self.play(pointer.animate.next_to(cell, UP, buff=0.18), cell[0].animate.set_fill(self.palette(2), opacity=0.35), run_time=0.35)
    self.play(FadeIn(result, shift=UP * 0.08), Indicate(cells[3]), run_time=0.8)

def play_probability_visual(self, phase, data, primary_lines, secondary_lines=None, result_lines=None):
    caption = self.text_block(primary_lines, font_size=21, color="#8FD3FF")
    self.safe_place(caption, y=4.55, max_height=1.0, top=5.1, bottom=3.85)
    heights = [1.0, 1.9, 2.8, 1.4]
    bars = VGroup()
    for i, height in enumerate(heights):
        rect = Rectangle(width=0.62, height=height, color=self.palette(i), fill_opacity=0.45).align_to(ORIGIN, DOWN)
        bars.add(rect)
    bars.arrange(RIGHT, buff=0.22).move_to(ORIGIN)
    self.safe_place(bars, y=0.5, max_width=5.2, max_height=3.2, top=2.4, bottom=-1.9)
    brace = Brace(bars[1:3], UP, color="#F7C948")
    result = self.text_block(result_lines or secondary_lines or ["update the mass, then compare"], font_size=22, color="#7EE787")
    self.safe_place(result, y=-5.05, max_height=1.35, top=-4.2, bottom=-6.25)
    self.play(FadeIn(caption), LaggedStart(*[GrowFromEdge(bar, DOWN) for bar in bars], lag_ratio=0.1), run_time=1.1)
    self.play(GrowFromCenter(brace), bars[2].animate.set_fill("#7EE787", opacity=0.7), FadeIn(result, shift=UP * 0.08), run_time=1.0)

def play_chemistry_visual(self, phase, data, primary_lines, secondary_lines=None, result_lines=None):
    caption = self.text_block(primary_lines, font_size=21, color="#8FD3FF")
    self.safe_place(caption, y=4.55, max_height=1.0, top=5.1, bottom=3.85)
    left = VGroup(Circle(0.28, color="#58A6FF", fill_opacity=0.25), Circle(0.28, color="#F7C948", fill_opacity=0.25).shift(RIGHT * 0.48)).arrange(RIGHT, buff=-0.08)
    right = VGroup(Circle(0.28, color="#58A6FF", fill_opacity=0.25), Circle(0.28, color="#F7C948", fill_opacity=0.25), Circle(0.28, color="#7EE787", fill_opacity=0.25)).arrange(RIGHT, buff=-0.08)
    reaction = VGroup(left, Text("+", font_size=28), Circle(0.25, color="#7EE787", fill_opacity=0.25), Text("->", font_size=28), right).arrange(RIGHT, buff=0.24)
    self.safe_place(reaction, y=0.75, max_width=7.3, max_height=1.4, top=1.7, bottom=-0.2)
    result = self.text_block(result_lines or secondary_lines or ["rearrange pieces, conserve counts"], font_size=22, color="#7EE787")
    self.safe_place(result, y=-5.05, max_height=1.35, top=-4.2, bottom=-6.25)
    self.play(FadeIn(caption), FadeIn(reaction[:3]), run_time=0.9)
    self.play(FadeIn(reaction[3:]), FadeIn(result, shift=UP * 0.08), Indicate(right), run_time=1.0)

def play_numeric_rule_visual(self, phase, data, primary_lines, secondary_lines=None, result_lines=None):
    caption = self.text_block(primary_lines, font_size=21, color="#8FD3FF")
    self.safe_place(caption, y=4.55, max_height=1.0, top=5.1, bottom=3.85)
    nums = data.get("numbers", ["2", "5", "8"])
    inputs = VGroup(*[VGroup(Circle(0.26, color=self.palette(i), fill_opacity=0.18), Text(str(num), font_size=18, color="#EAF2FF")) for i, num in enumerate(nums[:3])]).arrange(DOWN, buff=0.12)
    rule_box = RoundedRectangle(width=1.65, height=1.0, corner_radius=0.12, color="#F7C948", fill_color="#101A33", fill_opacity=0.92)
    rule = VGroup(rule_box, Text("rule", font_size=23, color="#F7C948").move_to(rule_box))
    outputs = VGroup(*[VGroup(Circle(0.26, color="#7EE787", fill_opacity=0.18), Text("?", font_size=18, color="#7EE787")) for _ in nums[:3]]).arrange(DOWN, buff=0.12)
    diagram = VGroup(inputs, Text("->", font_size=28), rule, Text("->", font_size=28), outputs).arrange(RIGHT, buff=0.22)
    self.safe_place(diagram, y=0.65, max_width=7.4, max_height=2.4, top=2.15, bottom=-1.3)
    result = self.text_block(result_lines or secondary_lines or ["watch input, rule, output"], font_size=22, color="#7EE787")
    self.safe_place(result, y=-5.05, max_height=1.35, top=-4.2, bottom=-6.25)
    self.play(FadeIn(caption), FadeIn(inputs), FadeIn(rule), run_time=0.9)
    self.play(LaggedStart(*[Transform(outputs[i][1], Text(str(nums[min(i + 1, len(nums) - 1)]), font_size=18, color="#7EE787").move_to(outputs[i][1])) for i in range(len(outputs))], lag_ratio=0.12), FadeIn(outputs), run_time=1.1)
    self.play(FadeIn(result, shift=UP * 0.08), Indicate(rule), run_time=0.9)

def play_group_visual(self, kind, phase, data, primary_lines, secondary_lines=None, result_lines=None):
    caption = self.text_block(primary_lines, font_size=21, color="#8FD3FF")
    self.safe_place(caption, y=4.55, max_height=1.0, top=5.1, bottom=3.85)
    result = self.text_block(result_lines or secondary_lines or ["structure is preserved"], font_size=22, color="#7EE787")
    self.safe_place(result, y=-5.05, max_height=1.35, top=-4.2, bottom=-6.25)
    if kind == "group_cosets":
        blocks = VGroup()
        labels = ["H", "gH", "kH"]
        for i, label in enumerate(labels):
            rect = RoundedRectangle(width=1.55, height=2.35, corner_radius=0.1, color=self.palette(i), fill_color="#101A33", fill_opacity=0.75)
            dots = VGroup(*[Dot(radius=0.045, color=self.palette(i)).shift(RIGHT * ((j % 2) - 0.5) * 0.45 + UP * (0.55 - (j // 2) * 0.45)) for j in range(6)])
            dots.move_to(rect)
            blocks.add(VGroup(rect, dots, Text(label, font_size=25, color=self.palette(i)).next_to(rect, UP, buff=0.14)))
        blocks.arrange(RIGHT, buff=0.45)
        self.safe_place(blocks, y=0.4, max_width=7.4, max_height=3.8, top=2.7, bottom=-2.4)
        self.play(FadeIn(caption), LaggedStart(*[FadeIn(block, shift=UP * 0.08) for block in blocks], lag_ratio=0.18), run_time=1.2)
        self.play(*[Indicate(block[0]) for block in blocks], FadeIn(result, shift=UP * 0.08), run_time=1.1)
        return
    if kind == "group_homomorphism":
        left = VGroup(Circle(radius=1.1, color="#58A6FF"), Text("G", font_size=28, color="#58A6FF")).arrange(DOWN, buff=-0.25)
        right = VGroup(Circle(radius=1.1, color="#7EE787"), Text("H", font_size=28, color="#7EE787")).arrange(DOWN, buff=-0.25)
        left.shift(LEFT * 2.25)
        right.shift(RIGHT * 2.25)
        arrows = VGroup(*[Arrow(left.get_center() + UP * y + RIGHT * 0.65, right.get_center() + UP * (y * 0.55) + LEFT * 0.65, buff=0.02, stroke_width=4, color=self.palette(i)) for i, y in enumerate([-0.55, 0.0, 0.55])])
        law = Text("phi(ab) = phi(a) phi(b)", font_size=26, color="#F7C948")
        diagram = VGroup(left, right, arrows, law.next_to(arrows, DOWN, buff=0.45))
        self.safe_place(diagram, y=0.35, max_width=7.7, max_height=4.7, top=3.0, bottom=-2.7)
        self.play(FadeIn(caption), FadeIn(left), FadeIn(right), run_time=0.9)
        self.play(LaggedStart(*[GrowArrow(arrow) for arrow in arrows], lag_ratio=0.18), Write(law), run_time=1.35)
        self.play(FadeIn(result, shift=UP * 0.08), Indicate(law), run_time=1.0)
        return
    if kind == "group_action":
        square = Square(side_length=2.7, color="#58A6FF")
        vertices = VGroup(*[Dot(square.get_corner(corner), radius=0.075, color=self.palette(i)) for i, corner in enumerate([UL, UR, DR, DL])])
        labels = VGroup(*[Text(str(i + 1), font_size=22, color=self.palette(i)).next_to(vertices[i], [UL, UR, DR, DL][i], buff=0.12) for i in range(4)])
        arrow = CurvedArrow(square.get_top() + UP * 0.45, square.get_right() + RIGHT * 0.45, radius=1.6, color="#F7C948")
        diagram = VGroup(square, vertices, labels, arrow)
        self.safe_place(diagram, y=0.45, max_width=6.8, max_height=4.7, top=3.0, bottom=-2.8)
        self.play(FadeIn(caption), Create(square), FadeIn(vertices), FadeIn(labels), run_time=1.0)
        self.play(Create(arrow), Rotate(vertices, angle=PI / 2, about_point=square.get_center()), run_time=1.2)
        self.play(FadeIn(result, shift=UP * 0.08), Indicate(vertices), run_time=0.9)
        return
    nodes = VGroup()
    names = ["e", "g", "h", "gh"]
    for i, name in enumerate(names):
        angle = TAU * i / len(names) + PI / 4
        node = VGroup(Circle(radius=0.35, color=self.palette(i), fill_opacity=0.18), Text(name, font_size=24, color=self.palette(i)))
        node.move_to(RIGHT * math.cos(angle) * 2.2 + UP * math.sin(angle) * 1.55)
        nodes.add(node)
    arrows = VGroup(*[CurvedArrow(nodes[i].get_center(), nodes[(i + 1) % len(nodes)].get_center(), radius=1.8, color=self.palette(i), stroke_width=4) for i in range(len(nodes))])
    law = Text("combine, stay inside, return to identity", font_size=24, color="#F7C948")
    diagram = VGroup(nodes, arrows, law.next_to(nodes, DOWN, buff=0.45))
    self.safe_place(diagram, y=0.35, max_width=7.5, max_height=4.5, top=2.95, bottom=-2.7)
    self.play(FadeIn(caption), LaggedStart(*[FadeIn(node, scale=1.1) for node in nodes], lag_ratio=0.12), run_time=1.0)
    self.play(LaggedStart(*[Create(arrow) for arrow in arrows], lag_ratio=0.1), Write(law), run_time=1.35)
    self.play(FadeIn(result, shift=UP * 0.08), Indicate(nodes[-1]), run_time=0.9)


def play_algebra_visual(self, kind, phase, data, primary_lines, secondary_lines=None, result_lines=None):
    caption = self.text_block(primary_lines, font_size=21, color="#8FD3FF")
    self.safe_place(caption, y=4.55, max_height=1.0, top=5.1, bottom=3.85)
    result = self.text_block(result_lines or secondary_lines or ["verify the algebraic structure"], font_size=22, color="#7EE787")
    self.safe_place(result, y=-5.05, max_height=1.35, top=-4.2, bottom=-6.25)
    if kind == "algebra_ideal":
        ring = Circle(radius=1.65, color="#58A6FF", fill_opacity=0.08)
        ideal = Circle(radius=0.72, color="#F7C948", fill_opacity=0.2).move_to(ring)
        arrows = VGroup(*[Arrow(ring.get_center() + RIGHT * 2.7 + UP * y, ideal.get_center() + RIGHT * 0.42 + UP * (y * 0.35), buff=0.06, color=self.palette(i), stroke_width=4) for i, y in enumerate([-0.55, 0.0, 0.55])])
        labels = VGroup(Text("R", font_size=30, color="#58A6FF").next_to(ring, UP), Text("I", font_size=28, color="#F7C948").move_to(ideal), Text("rI stays in I", font_size=24, color="#7EE787").next_to(ring, DOWN, buff=0.35))
        diagram = VGroup(ring, ideal, arrows, labels)
        self.safe_place(diagram, y=0.35, max_width=7.5, max_height=4.7, top=3.0, bottom=-2.65)
        self.play(FadeIn(caption), Create(ring), FadeIn(ideal), run_time=1.0)
        self.play(LaggedStart(*[GrowArrow(arrow) for arrow in arrows], lag_ratio=0.15), FadeIn(labels), run_time=1.2)
        self.play(FadeIn(result, shift=UP * 0.08), Indicate(ideal), run_time=0.9)
        return
    if kind == "algebra_quotient_ring":
        blocks = VGroup()
        for i, label in enumerate(["0+I", "a+I", "b+I"]):
            rect = RoundedRectangle(width=1.65, height=1.1, corner_radius=0.1, color=self.palette(i), fill_color="#101A33", fill_opacity=0.82)
            blocks.add(VGroup(rect, Text(label, font_size=24, color=self.palette(i)).move_to(rect)))
        blocks.arrange(RIGHT, buff=0.34)
        collapse = Text("I -> 0", font_size=28, color="#F7C948").next_to(blocks, DOWN, buff=0.38)
        diagram = VGroup(blocks, collapse)
        self.safe_place(diagram, y=0.35, max_width=7.6, max_height=3.7, top=2.6, bottom=-2.0)
        self.play(FadeIn(caption), LaggedStart(*[FadeIn(block, shift=UP * 0.08) for block in blocks], lag_ratio=0.14), run_time=1.1)
        self.play(Write(collapse), blocks[0].animate.set_fill("#7EE787", opacity=0.35), run_time=1.0)
        self.play(FadeIn(result, shift=UP * 0.08), Indicate(collapse), run_time=0.9)
        return
    if kind == "algebra_factorization":
        root = Text("a", font_size=34, color="#EAF2FF")
        factors = VGroup(Text("u", font_size=28, color="#8FD3FF"), Text("p1", font_size=28, color="#F7C948"), Text("p2", font_size=28, color="#7EE787"), Text("p3", font_size=28, color="#FF7B72")).arrange(RIGHT, buff=0.35)
        factors.next_to(root, DOWN, buff=1.2)
        arrows = VGroup(*[Line(root.get_bottom(), factor.get_top(), color=self.palette(i), stroke_width=4) for i, factor in enumerate(factors)])
        label = Text("unique up to order and units", font_size=24, color="#F7C948").next_to(factors, DOWN, buff=0.35)
        diagram = VGroup(root, arrows, factors, label)
        self.safe_place(diagram, y=0.35, max_width=7.5, max_height=4.4, top=2.9, bottom=-2.6)
        self.play(FadeIn(caption), FadeIn(root), run_time=0.8)
        self.play(LaggedStart(*[Create(arrow) for arrow in arrows], *[FadeIn(f) for f in factors], lag_ratio=0.09), Write(label), run_time=1.35)
        self.play(FadeIn(result, shift=UP * 0.08), Indicate(factors), run_time=0.9)
        return
    if kind in {"algebra_field_extension", "algebra_galois"}:
        base = RoundedRectangle(width=2.2, height=0.8, corner_radius=0.1, color="#58A6FF", fill_opacity=0.15)
        mid = RoundedRectangle(width=3.0, height=0.8, corner_radius=0.1, color="#F7C948", fill_opacity=0.15).next_to(base, UP, buff=0.55)
        top = RoundedRectangle(width=3.8, height=0.8, corner_radius=0.1, color="#7EE787", fill_opacity=0.15).next_to(mid, UP, buff=0.55)
        labels = VGroup(Text("F", font_size=26, color="#58A6FF").move_to(base), Text("F(alpha)", font_size=25, color="#F7C948").move_to(mid), Text("roots / K", font_size=25, color="#7EE787").move_to(top))
        tower = VGroup(base, mid, top, labels)
        if kind == "algebra_galois":
            roots = VGroup(*[Dot(radius=0.08, color=self.palette(i)).move_to(top.get_center() + RIGHT * (i - 1) * 0.55) for i in range(3)])
            arrow = CurvedArrow(roots[0].get_center() + UP * 0.25, roots[2].get_center() + UP * 0.25, radius=1.0, color="#F7C948")
            tower.add(roots, arrow)
        self.safe_place(tower, y=0.15, max_width=7.3, max_height=4.7, top=3.0, bottom=-2.6)
        self.play(FadeIn(caption), FadeIn(base), run_time=0.8)
        self.play(FadeIn(mid, shift=UP * 0.1), FadeIn(top, shift=UP * 0.1), FadeIn(labels), run_time=1.1)
        if kind == "algebra_galois":
            self.play(Create(arrow), Rotate(roots, angle=TAU / 3, about_point=top.get_center()), run_time=1.1)
        self.play(FadeIn(result, shift=UP * 0.08), Indicate(top), run_time=0.9)
        return
    nodes = VGroup(Text("+", font_size=34, color="#58A6FF"), Text("x", font_size=34, color="#F7C948"), Text("1", font_size=34, color="#7EE787"), Text("inverse?", font_size=26, color="#FF7B72")).arrange(RIGHT, buff=0.45)
    frame = RoundedRectangle(width=6.7, height=1.45, corner_radius=0.1, color="#58A6FF", fill_color="#101A33", fill_opacity=0.7).move_to(nodes)
    law = Text("closed operations + distributive law", font_size=24, color="#EAF2FF").next_to(frame, DOWN, buff=0.35)
    diagram = VGroup(frame, nodes, law)
    self.safe_place(diagram, y=0.35, max_width=7.7, max_height=3.8, top=2.7, bottom=-2.2)
    self.play(FadeIn(caption), Create(frame), FadeIn(nodes), run_time=1.0)
    self.play(Write(law), nodes[-1].animate.set_color("#7EE787"), run_time=1.1)
    self.play(FadeIn(result, shift=UP * 0.08), Indicate(nodes), run_time=0.9)

def play_game_visual(self, phase, data, primary_lines, secondary_lines=None, result_lines=None):
    caption = self.text_block(primary_lines, font_size=21, color="#8FD3FF")
    self.safe_place(caption, y=4.55, max_height=1.0, top=5.1, bottom=3.85)
    cells = VGroup()
    payoffs = [["3,3", "0,5"], ["5,0", "1,1"]]
    for r in range(2):
        row = VGroup()
        for c in range(2):
            box = Square(1.05, color=self.palette(r * 2 + c), fill_opacity=0.14)
            row.add(VGroup(box, Text(payoffs[r][c], font_size=24, color="#EAF2FF").move_to(box)))
        row.arrange(RIGHT, buff=0.08)
        cells.add(row)
    cells.arrange(DOWN, buff=0.08)
    row_labels = VGroup(Text("High", font_size=20, color="#F7C948"), Text("Low", font_size=20, color="#F7C948")).arrange(DOWN, buff=0.72).next_to(cells, LEFT, buff=0.25)
    col_labels = VGroup(Text("High", font_size=20, color="#58A6FF"), Text("Low", font_size=20, color="#58A6FF")).arrange(RIGHT, buff=0.42).next_to(cells, UP, buff=0.18)
    marker = SurroundingRectangle(cells[1][1], color="#7EE787", buff=0.06)
    diagram = VGroup(cells, row_labels, col_labels, marker)
    self.safe_place(diagram, y=0.35, max_width=7.4, max_height=4.6, top=3.0, bottom=-2.6)
    result = self.text_block(result_lines or secondary_lines or ["best responses meet at a stable cell"], font_size=22, color="#7EE787")
    self.safe_place(result, y=-5.05, max_height=1.35, top=-4.2, bottom=-6.25)
    self.play(FadeIn(caption), FadeIn(cells), FadeIn(row_labels), FadeIn(col_labels), run_time=1.0)
    self.play(Create(marker), Indicate(cells[1][1]), run_time=1.0)
    self.play(FadeIn(result, shift=UP * 0.08), Flash(marker, color="#7EE787"), run_time=0.9)

def play_econ_visual(self, kind, phase, data, primary_lines, secondary_lines=None, result_lines=None):
    caption = self.text_block(primary_lines, font_size=21, color="#8FD3FF")
    self.safe_place(caption, y=4.55, max_height=1.0, top=5.1, bottom=3.85)
    result = self.text_block(result_lines or secondary_lines or ["compare the margin"], font_size=22, color="#7EE787")
    self.safe_place(result, y=-5.05, max_height=1.35, top=-4.2, bottom=-6.25)
    axes = Axes(x_range=[0, 10, 2], y_range=[0, 10, 2], x_length=6.4, y_length=4.7, tips=False, axis_config={"color": "#EAF2FF", "stroke_width": 2})
    self.safe_place(axes, y=0.4, max_width=7.0, max_height=5.0, top=3.0, bottom=-2.55)
    if kind == "econ_tax_wedge":
        demand = Line(axes.c2p(1, 8.4), axes.c2p(8.6, 1.7), color="#58A6FF", stroke_width=6)
        supply = Line(axes.c2p(1.0, 1.4), axes.c2p(8.1, 7.8), color="#F7C948", stroke_width=6)
        taxed_supply = Line(axes.c2p(1.0, 2.55), axes.c2p(8.1, 8.95), color="#FF7B72", stroke_width=6)
        before = Dot(axes.c2p(4.75, 5.1), color="#7EE787", radius=0.1)
        after = Dot(axes.c2p(4.05, 5.75), color="#FF7B72", radius=0.1)
        seller_price = Dot(axes.c2p(4.05, 4.55), color="#F7C948", radius=0.08)
        wedge = DoubleArrow(axes.c2p(4.05, 4.55), axes.c2p(4.05, 5.75), buff=0.03, color="#FF7B72", stroke_width=5, max_tip_length_to_length_ratio=0.18)
        lost_trade = Polygon(axes.c2p(4.05, 4.55), axes.c2p(4.05, 5.75), axes.c2p(5.15, 4.85), color="#A371F7", fill_color="#A371F7", fill_opacity=0.28, stroke_width=3)
        q_drop = Arrow(axes.c2p(4.75, 1.0), axes.c2p(4.05, 1.0), buff=0.02, color="#8FD3FF", stroke_width=4)
        labels = VGroup(
            Text("tax wedge", font_size=22, color="#FF7B72").next_to(wedge, RIGHT, buff=0.18),
            Text("lost trades", font_size=21, color="#A371F7").next_to(lost_trade, DOWN, buff=0.2),
            Text("quantity falls", font_size=20, color="#8FD3FF").next_to(q_drop, DOWN, buff=0.18),
        )
        self.safe_place(labels, y=-3.25, max_width=7.4, max_height=1.2, top=-2.55, bottom=-3.95)
        self.play(FadeIn(caption), Create(axes), Create(demand), Create(supply), FadeIn(before, scale=1.2), run_time=1.15)
        self.play(TransformFromCopy(supply, taxed_supply), before.animate.move_to(after), run_time=1.25)
        self.play(GrowArrow(wedge), FadeIn(seller_price, scale=1.2), FadeIn(labels[0], shift=UP * 0.06), run_time=0.95)
        self.play(Create(lost_trade), GrowArrow(q_drop), FadeIn(labels[1:], shift=UP * 0.06), run_time=1.05)
        self.play(FadeIn(result, shift=UP * 0.08), Indicate(VGroup(wedge, lost_trade, after), scale_factor=1.08), run_time=0.95)
        return
    if kind == "econ_budget":
        budget = Line(axes.c2p(0, 8), axes.c2p(8, 0), color="#F7C948", stroke_width=6)
        choice = Dot(axes.c2p(4.6, 3.4), color="#7EE787", radius=0.09)
        curve = axes.plot(lambda x: 12 / (x + 0.9) - 0.6, x_range=[1.0, 7.4], color="#58A6FF", stroke_width=5)
        label = Text("best affordable bundle", font_size=23, color="#7EE787")
        self.safe_place(label, y=-3.25, max_width=7.0, max_height=0.55, top=-2.9, bottom=-3.7)
        self.play(FadeIn(caption), Create(axes), Create(budget), run_time=1.0)
        self.play(Create(curve), FadeIn(choice, scale=1.3), FadeIn(label, shift=UP * 0.05), run_time=1.2)
        self.play(FadeOut(label, shift=DOWN * 0.08), FadeIn(result, shift=UP * 0.08), Flash(choice, color="#7EE787"), run_time=0.9)
        return
    if kind == "econ_elasticity":
        curve = axes.plot(lambda x: 8.5 - 0.55 * x, x_range=[0.7, 8.4], color="#58A6FF", stroke_width=6)
        p1 = Dot(axes.c2p(3.0, 6.85), color="#F7C948")
        p2 = Dot(axes.c2p(5.2, 5.64), color="#7EE787")
        brace_q = Brace(Line(axes.c2p(3.0, 1.0), axes.c2p(5.2, 1.0)), DOWN, color="#7EE787")
        brace_p = Brace(Line(axes.c2p(8.8, 6.85), axes.c2p(8.8, 5.64)), RIGHT, color="#F7C948")
        label = Text("percent response", font_size=23, color="#F7C948")
        self.safe_place(label, y=-3.25, max_width=7.0, max_height=0.55, top=-2.9, bottom=-3.7)
        self.play(FadeIn(caption), Create(axes), Create(curve), run_time=1.0)
        self.play(FadeIn(p1), TransformFromCopy(p1, p2), GrowFromCenter(brace_q), GrowFromCenter(brace_p), FadeIn(label, shift=UP * 0.05), run_time=1.25)
        self.play(FadeOut(label, shift=DOWN * 0.08), FadeIn(result, shift=UP * 0.08), Indicate(VGroup(p1, p2)), run_time=0.9)
        return
    demand = Line(axes.c2p(1, 8.4), axes.c2p(8.5, 1.8), color="#58A6FF", stroke_width=6)
    supply = Line(axes.c2p(1.1, 1.4), axes.c2p(8.3, 8.2), color="#F7C948", stroke_width=6)
    eq = Dot(axes.c2p(4.8, 5.0), color="#7EE787", radius=0.1)
    if kind == "econ_curve":
        supply.set_color("#7EE787")
        demand.set_color("#F7C948")
    label = Text("equilibrium", font_size=23, color="#7EE787")
    self.safe_place(label, y=-3.25, max_width=7.0, max_height=0.55, top=-2.9, bottom=-3.7)
    self.play(FadeIn(caption), Create(axes), Create(demand), run_time=1.0)
    self.play(Create(supply), FadeIn(eq, scale=1.3), FadeIn(label, shift=UP * 0.05), run_time=1.25)
    self.play(FadeOut(label, shift=DOWN * 0.08), FadeIn(result, shift=UP * 0.08), Flash(eq, color="#7EE787"), run_time=0.9)


def play_generic_visual(self, kind, phase, data, primary_lines, secondary_lines=None, result_lines=None):
    if kind in {"algebra_ring_field", "algebra_ideal", "algebra_quotient_ring", "algebra_factorization", "algebra_field_extension", "algebra_galois"}:
        return self.play_algebra_visual(kind, phase, data, primary_lines, secondary_lines, result_lines)
    if kind == "game_payoff":
        return self.play_game_visual(phase, data, primary_lines, secondary_lines, result_lines)
    if kind in {"group_structure", "group_cosets", "group_homomorphism", "group_action"}:
        return self.play_group_visual(kind, phase, data, primary_lines, secondary_lines, result_lines)
    if kind in {"econ_supply_demand", "econ_elasticity", "econ_budget", "econ_curve", "econ_tax_wedge"}:
        return self.play_econ_visual(kind, phase, data, primary_lines, secondary_lines, result_lines)
    if kind in {"calculus_tangent", "calculus_area"}:
        return self.play_calculus_visual(kind, phase, data, primary_lines, secondary_lines, result_lines)
    if kind in {"physics_force", "physics_energy"}:
        return self.play_physics_visual(kind, phase, data, primary_lines, secondary_lines, result_lines)
    if kind == "physics_wave":
        return self.play_wave_visual(phase, data, primary_lines, secondary_lines, result_lines)
    if kind in {"cs_array", "cs_graph", "state_machine"}:
        return self.play_cs_visual("cs_graph" if kind == "state_machine" else kind, phase, data, primary_lines, secondary_lines, result_lines)
    if kind in {"probability", "markov"}:
        return self.play_probability_visual(phase, data, primary_lines, secondary_lines, result_lines)
    if kind == "chemistry_reaction":
        return self.play_chemistry_visual(phase, data, primary_lines, secondary_lines, result_lines)
    return self.play_numeric_rule_visual(phase, data, primary_lines, secondary_lines, result_lines)

def play_intro_visual(self, kind, data):
    if kind == "matrix_vector":
        return self.play_matrix_vector_intro(data["matrix_vector"])
    if kind == "vector_components":
        return self.play_vector_intro(data["vector"])
    if kind == "linear_combination":
        return self.play_linear_combo_intro(data["linear_combo"])
    if kind in {"basis", "subspace", "transform_grid", "systems", "least_squares", "elimination", "matrix_factor", "projection", "eigen", "svd", "area", "dimension_bar", "quadratic"}:
        mapped = {"projection": "calculus_tangent", "area": "calculus_area", "quadratic": "calculus_tangent"}.get(kind, "numeric_rule")
        return self.play_generic_visual(mapped, "intro", data, ["visualize the structure"], ["follow the colored objects"], ["highlight the output"])
    intro_lines = {
        "algebra_ring_field": ["operations define the structure"],
        "algebra_ideal": ["absorption makes quotients work"],
        "algebra_quotient_ring": ["collapse an ideal to zero"],
        "algebra_factorization": ["divisibility becomes structure"],
        "algebra_field_extension": ["a larger field adds roots"],
        "algebra_galois": ["symmetries move roots"],
        "game_payoff": ["payoffs make incentives visible"],
    }.get(kind, ["input -> rule -> output"])
    return self.play_generic_visual(kind, "intro", data, intro_lines, ["follow the colored objects"], ["watch the key relation"])

def play_example_visual(self, kind, data, setup_lines, calc_lines, takeaway_lines):
    if kind == "matrix_vector":
        return self.play_matrix_vector_example(data["matrix_vector"], setup_lines, calc_lines, takeaway_lines)
    if kind == "vector_components":
        return self.play_vector_example(data["vector"], setup_lines, calc_lines, takeaway_lines)
    if kind == "linear_combination":
        return self.play_linear_combo_example(data["linear_combo"], setup_lines, calc_lines, takeaway_lines)
    mapped = {"projection": "calculus_tangent", "area": "calculus_area", "quadratic": "calculus_tangent", "markov": "probability"}.get(kind, kind)
    return self.play_generic_visual(mapped, "example", data, setup_lines, calc_lines, takeaway_lines)

def play_recall_visual(self, kind, data, question_lines, answer_lines):
    if kind == "matrix_vector":
        return self.play_matrix_vector_recall(data["matrix_vector"], question_lines, answer_lines)
    if kind == "vector_components":
        return self.play_vector_recall(data["vector"], question_lines, answer_lines)
    if kind == "linear_combination":
        return self.play_linear_combo_recall(data["linear_combo"], question_lines, answer_lines)
    mapped = {"projection": "calculus_tangent", "area": "calculus_area", "quadratic": "calculus_tangent", "markov": "probability"}.get(kind, kind)
    return self.play_generic_visual(mapped, "recall", data, question_lines, answer_lines, answer_lines)
'''


def manim_scene(short: dict[str, object], class_name: str) -> str:
    visual_kind = infer_visual_kind(short)
    setup = screen_prose(short["worked_example"]["setup"])
    calc = screen_prose(short["worked_example"]["calculation"])
    takeaway = screen_prose(short["worked_example"]["takeaway"])
    question = screen_prose(short["question_prompt"]["question"])
    answer = screen_prose(short["question_prompt"]["answer"])
    visual_data = visual_data_for(short, visual_kind)
    pacing = short_video_pacing(short)
    return f'''# generated_by: tools/stem_course.py; scene_metadata_version={SCENE_METADATA_VERSION}; visual_kind={visual_kind}; concept={str(short.get("concept", "")).replace(chr(10), " ")!r}
from manim import *
import math
import re

config.pixel_width = 1080
config.pixel_height = 1920
config.frame_width = 9
config.frame_height = 16
config.background_color = "#0B1020"


class {class_name}(Scene):
{textwrap.indent(MANIM_SCENE_HELPERS, "    ")}

    def construct(self):
        self.camera.background_color = "#0B1020"
        visual_kind = {visual_kind!r}
        visual_data = {visual_data!r}
        pacing = {pacing!r}
        setup_lines = {wrap(setup, 30, 3)!r}
        calc_lines = {wrap(calc, 30, 3)!r}
        takeaway_lines = {wrap(takeaway, 30, 3)!r}
        question_lines = {wrap(question, 40, 3)!r}
        answer_lines = {wrap(answer, 40, 3)!r}

        title = Text({short["concept"]!r}, font_size=45, weight="BOLD", color="#EAF2FF", disable_ligatures=True)
        self.safe_place(title, y=7.08, max_width=8.1, max_height=0.8, top=7.48, bottom=6.58)
        hook = self.text_block({wrap(str(short["hook"]), 34, 3)!r}, font_size=26, color="#8FD3FF", max_width=7.4, max_height=1.15)
        self.safe_place(hook, y=5.95, max_width=7.4, max_height=1.15, top=6.42, bottom=5.22)
        self.play(FadeIn(title, shift=DOWN * 0.1), LaggedStart(*[FadeIn(x) for x in hook], lag_ratio=0.12), run_time=1.2)

        {visual_template(visual_kind, "intro")}
        self.fade_all_except([title, hook], run_time=0.45)

        formula = self.formula_block({sanitize_formula_latex(str(short["formula"]))!r}, {screen_math(str(short["formula"]))!r}, font_size=32, color="#F7C948")
        self.safe_place(formula, y=-4.95, max_width=7.4, max_height=0.9, top=-4.45, bottom=-5.55)
        intuition = self.text_block({wrap(str(short["intuition"]), 42, 3)!r}, font_size=23, color="#EAF2FF", max_width=7.25, max_height=1.15)
        self.safe_place(intuition, y=-6.55, max_width=7.25, max_height=1.15, top=-5.9, bottom=-7.25)
        self.play(Write(formula), run_time=0.9)
        self.play(FadeIn(intuition, shift=UP * 0.12), run_time=0.9)
        self.semantic_beat_hold(pacing["intro_hold"], [formula, intuition], "formula")
        self.fade_all_except([title], run_time=0.7)
        self.play(title.animate.scale(0.72).to_edge(UP, buff=0.35), run_time=0.45)

        section = self.section_label("Worked example", "#F7C948")
        self.play(FadeIn(section, shift=DOWN * 0.08), run_time=0.45)
        {visual_template(visual_kind, "example")}
        self.semantic_beat_hold(pacing["example_hold"], label="example step")
        self.fade_all_except([title], run_time=0.7)

        section = self.section_label("Active recall", "#F7C948")
        self.play(FadeIn(section, shift=DOWN * 0.08), run_time=0.45)
        {visual_template(visual_kind, "recall")}
        self.semantic_beat_hold(pacing["recall_hold"], label="recall check")
        self.play(*[FadeOut(mob) for mob in self.mobjects], run_time=0.6)
        self.wait(0.15)
'''


def visual_template(kind: str, phase: str = "intro") -> str:
    if phase == "example":
        return "self.play_example_visual(visual_kind, visual_data, setup_lines, calc_lines, takeaway_lines)"
    if phase == "recall":
        return "self.play_recall_visual(visual_kind, visual_data, question_lines, answer_lines)"
    return "self.play_intro_visual(visual_kind, visual_data)"


def cmd_manim(args: argparse.Namespace) -> None:
    run = Path(args.run)
    plan = read_json(run / "short_plan.json")
    scenes = run / "scenes"
    scripts = run / "scripts"
    captions = run / "captions"
    scenes.mkdir(exist_ok=True)
    scripts.mkdir(exist_ok=True)
    captions.mkdir(exist_ok=True)
    for short in plan["shorts"]:
        slug = slugify(short["concept"])
        class_name = "".join(part.title() for part in slug.split("-")) + "Short"
        short["class_name"] = class_name
        short["scene_file"] = f"scenes/short_{short['index']:02d}_{slug}.py"
        short["srt_file"] = f"captions/short_{short['index']:02d}_{slug}.srt"
        short["target_duration_seconds"] = short_video_pacing(short)["total"]
        (run / short["scene_file"]).write_text(manim_scene(short, class_name), encoding="utf-8")
        (run / short["srt_file"]).write_text(make_srt(short), encoding="utf-8")
        (scripts / f"short_{short['index']:02d}_{slug}.md").write_text(script_markdown(short), encoding="utf-8")
    write_json(run / "short_plan.json", plan)
    print(scenes)


def make_srt(short: dict[str, object], target_duration: float | None = None) -> str:
    cues = caption_cues(short, target_duration=target_duration)
    return "\n\n".join(f"{i}\n{a} --> {b}\n{textwrap.fill(str(t), width=42)}" for i, (a, b, t) in enumerate(cues, start=1)) + "\n"


def script_clock(timestamp: str) -> str:
    head = timestamp.split(",", 1)[0]
    hours, minutes, seconds = head.split(":")
    if hours != "00":
        return f"{int(hours)}:{minutes}:{seconds}"
    return f"{int(minutes)}:{seconds}"


def script_markdown(short: dict[str, object]) -> str:
    target_seconds = short_video_pacing(short)["total"]
    rows = []
    for start, end, cue_text in caption_cues(short):
        cleaned = str(cue_text).replace("|", "-")
        rows.append(f"| {script_clock(start)}-{script_clock(end)} | {cleaned} |")
    beat_rows = "\n".join(rows)
    return f"""# Short {short['index']:02d}: {short['concept']}

Target length: about {target_seconds:.0f} seconds from script-paced captions; keep going until the concept, worked example, and recall question are clear.

## Beats

| Time | Beat |
| --- | --- |
{beat_rows}
"""


def audio_duration(path: Path) -> float:
    ffprobe = Path(FFMPEG).with_name("ffprobe") if FFMPEG else None
    if not ffprobe or not ffprobe.exists() or not path.exists():
        return 0.0
    result = subprocess.run([str(ffprobe), "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)], text=True, capture_output=True)
    try:
        return float(result.stdout.strip())
    except Exception:
        return 0.0


def make_voiceover(text: str, out: Path, engine: str) -> dict[str, object]:
    out.parent.mkdir(exist_ok=True)
    if engine == "none":
        return {"status": "skipped", "engine": engine}
    if engine == "say":
        say = shutil.which("say")
        if not say:
            return {"status": "failed", "engine": engine, "message": "say not found"}
        aiff = out.with_suffix(".aiff")
        configured_voice = os.environ.get("COURSE_SHORTS_SAY_VOICE", "Samantha")
        voices = []
        for candidate in [configured_voice, "Samantha", "Daniel", "Karen", "Fred"]:
            if candidate and candidate not in voices:
                voices.append(candidate)
        attempts = []
        for voice in voices:
            result = subprocess.run([say, "-v", voice, "-o", str(aiff), text], text=True, capture_output=True)
            dur = audio_duration(aiff)
            attempts.append(f"{voice}:{dur:.3f}s")
            if result.returncode == 0 and dur >= 0.75:
                return {"status": "ok", "engine": engine, "voice": voice, "file": str(aiff), "duration": dur}
        return {"status": "failed", "engine": engine, "message": "say produced invalid audio (" + ", ".join(attempts) + ")"}
    if engine == "edge-tts":
        edge = shutil.which("edge-tts")
        if not edge:
            return {"status": "failed", "engine": engine, "message": "edge-tts not found; install requirements.txt"}
        subprocess.run([edge, "--text", text, "--write-media", str(out)], check=False)
        dur = audio_duration(out)
        return {"status": "ok" if dur > 0.75 else "failed", "engine": engine, "file": str(out), "duration": dur}
    if engine == "openai":
        token = os.environ.get("OPENAI_API_KEY")
        if not token:
            return {"status": "failed", "engine": engine, "message": "OPENAI_API_KEY is not set"}
        import requests
        response = requests.post(
            "https://api.openai.com/v1/audio/speech",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"model": os.environ.get("OPENAI_TTS_MODEL", "gpt-4o-mini-tts"), "voice": os.environ.get("OPENAI_TTS_VOICE", "alloy"), "input": text},
            timeout=120,
        )
        if response.status_code >= 300:
            return {"status": "failed", "engine": engine, "message": response.text[:500]}
        out.write_bytes(response.content)
        dur = audio_duration(out)
        return {"status": "ok" if dur > 0.75 else "failed", "engine": engine, "file": str(out), "duration": dur}
    return {"status": "failed", "engine": engine, "message": "unknown voice engine"}



def narration_text(short: dict[str, object]) -> str:
    ex = short["worked_example"] if isinstance(short.get("worked_example"), dict) else {}
    qp = short["question_prompt"] if isinstance(short.get("question_prompt"), dict) else {}
    pieces = [
        short.get("hook", ""),
        short.get("intuition", ""),
        short.get("key_concept", ""),
        short.get("concept_explanation", ""),
        short.get("plain_formula", short.get("formula", "")),
        ex.get("setup", ""),
        ex.get("calculation", ""),
        ex.get("takeaway", ""),
        short.get("recognition_cue", ""),
        short.get("misconception", ""),
        qp.get("question", ""),
        qp.get("answer", ""),
    ]
    return " ".join(screen_prose(piece) for piece in pieces if str(piece).strip())


def mux_voiceover(raw: Path, voice_file: Path, final: Path, raw_duration: float, voice_duration: float, log_path: Path) -> dict[str, object]:
    if not FFMPEG:
        return {"status": "failed", "message": "ffmpeg not found"}
    target_duration = max(MIN_SHORT_VIDEO_SECONDS, voice_duration + 0.35 if voice_duration > 0 else raw_duration)
    if raw_duration > 0 and voice_duration > 0:
        video_time_scale = max(0.55, min(1.85, voice_duration / raw_duration))
    else:
        video_time_scale = 1.0
    scaled_video_duration = raw_duration * video_time_scale if raw_duration > 0 else target_duration
    video_tail_pad = max(0.0, target_duration - scaled_video_duration)
    audio_pad = max(0.0, target_duration - voice_duration)
    video_filter = f"[0:v]setpts={video_time_scale:.8f}*PTS"
    if video_tail_pad > 0.05:
        video_filter += f",fade=t=out:st={max(0.0, scaled_video_duration - min(0.45, video_tail_pad)):.3f}:d={min(0.45, video_tail_pad):.3f},tpad=stop_mode=add:stop_duration={video_tail_pad:.3f}:color=0x0B1020"
    video_filter += "[v]"
    filter_complex = video_filter + ";[1:a]apad,asetpts=PTS-STARTPTS[a]"
    cmd = [
        FFMPEG,
        "-y",
        "-i",
        str(raw),
        "-i",
        str(voice_file),
        "-filter_complex",
        filter_complex,
        "-map",
        "[v]",
        "-map",
        "[a]",
        "-t",
        f"{target_duration:.3f}",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-movflags",
        "+faststart",
        str(final),
    ]
    result = subprocess.run(cmd, text=True, capture_output=True, timeout=900)
    log_path.write_text(result.stdout + "\n" + result.stderr, encoding="utf-8")
    return {
        "status": "ok" if result.returncode == 0 else "failed",
        "returncode": result.returncode,
        "target_duration": target_duration,
        "video_time_scale": video_time_scale,
        "scaled_video_duration": scaled_video_duration,
        "video_tail_pad_seconds": video_tail_pad,
        "video_pad_seconds": video_tail_pad,
        "audio_pad_seconds": audio_pad,
        "message": result.stderr.strip()[-500:] if result.returncode else "",
    }



def cmd_render(args: argparse.Namespace) -> None:
    run = Path(args.run)
    plan = read_json(run / "short_plan.json")
    videos = run / "videos"
    audio = run / "audio"
    logs = run / "logs"
    scenes = run / "scenes"
    scripts = run / "scripts"
    captions = run / "captions"
    for directory in (videos, audio, logs, scenes, scripts, captions):
        directory.mkdir(exist_ok=True)
    results = []
    for short in plan["shorts"]:
        slug = slugify(short["concept"])
        class_name = str(short.get("class_name") or "".join(part.title() for part in slug.split("-")) + "Short")
        short["class_name"] = class_name
        short["scene_file"] = f"scenes/short_{short['index']:02d}_{slug}.py"
        short["srt_file"] = f"captions/short_{short['index']:02d}_{slug}.srt"
        scene = run / short["scene_file"]
        raw = videos / f"short_{short['index']:02d}_{slug}_raw.mp4"
        final = videos / f"short_{short['index']:02d}_{slug}_final.mp4"

        voice = make_voiceover(narration_text(short), audio / f"short_{short['index']:02d}_{slug}.mp3", args.voice_engine)
        voice_duration = float(voice.get("duration", 0) or 0)
        if voice.get("status") == "ok":
            short["voice_duration_seconds"] = round(voice_duration, 3)
            short["narration_duration_seconds"] = round(voice_duration, 3)
        else:
            short.pop("voice_duration_seconds", None)
            short.pop("narration_duration_seconds", None)

        short["target_duration_seconds"] = short_video_pacing(short)["total"]
        scene.write_text(manim_scene(short, class_name), encoding="utf-8")
        (run / str(short["srt_file"])).write_text(make_srt(short, target_duration=short["target_duration_seconds"]), encoding="utf-8")
        (scripts / f"short_{short['index']:02d}_{slug}.md").write_text(script_markdown(short), encoding="utf-8")

        qflag = "-ql" if args.quality == "l" else "-qm"
        media_dir = run / "manim_media"
        scene_media = media_dir / "videos" / scene.stem
        shutil.rmtree(scene_media, ignore_errors=True)
        cmd = [sys.executable, "-m", "manim", qflag, "--media_dir", str(media_dir), str(scene), class_name]
        manim = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=1200)
        log_text = manim.stdout + "\n" + manim.stderr
        if manim.returncode != 0:
            shutil.rmtree(scene_media, ignore_errors=True)
            retry = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=1200)
            log_text += "\n\n--- retry after clearing Manim scene media ---\n" + retry.stdout + "\n" + retry.stderr
            if retry.returncode == 0:
                manim = retry
        (logs / f"short_{short['index']:02d}_manim.log").write_text(log_text, encoding="utf-8")
        if manim.returncode != 0:
            results.append({"index": short["index"], "status": "failed", "stage": "manim", "voiceover": voice})
            continue
        rendered = newest_mp4(run / "manim_media", class_name)
        if not rendered:
            results.append({"index": short["index"], "status": "failed", "stage": "locate", "voiceover": voice})
            continue
        shutil.copy2(rendered, raw)

        raw_duration = audio_duration(raw)
        sync: dict[str, object] = {"raw_duration": raw_duration, "voice_duration": voice_duration, "target_duration": raw_duration, "video_pad_seconds": 0.0, "audio_pad_seconds": 0.0, "video_time_scale": 1.0}
        if voice.get("status") == "ok" and raw_duration and voice_duration < max(2.0, raw_duration * 0.15):
            voice = {**voice, "status": "failed", "message": f"voiceover too short for video: {voice_duration:.3f}s vs {raw_duration:.3f}s"}
        if voice.get("status") == "ok" and FFMPEG:
            mux = mux_voiceover(raw, Path(str(voice["file"])), final, raw_duration, voice_duration, logs / f"short_{short['index']:02d}_ffmpeg.log")
            sync.update(mux)
            if mux.get("status") != "ok":
                voice = {**voice, "status": "failed", "message": f"ffmpeg mux failed: {mux.get('message', 'unknown error')}"}
                shutil.copy2(raw, final)
        else:
            shutil.copy2(raw, final)

        duration = audio_duration(final)
        target_duration = float(sync.get("target_duration") or duration or raw_duration or short_video_pacing(short)["total"])
        if duration > 0:
            target_duration = duration
        if short.get("srt_file"):
            (run / str(short["srt_file"])).write_text(make_srt(short, target_duration=target_duration), encoding="utf-8")
        short["target_duration_seconds"] = round(target_duration, 3)
        short["video_file"] = str(final.relative_to(run))
        short["voiceover"] = voice
        short["duration_seconds"] = duration
        sync["final_duration"] = duration
        results.append({"index": short["index"], "status": "rendered", "duration_seconds": duration, "voiceover": voice, "sync": sync})
    write_json(run / "short_plan.json", plan)
    write_json(run / "render_report.json", {"results": results})
    print(run / "render_report.json")


def newest_mp4(root: Path, class_name: str) -> Path | None:
    files = list(root.rglob(f"{class_name}.mp4")) or list(root.rglob("*.mp4"))
    return max(files, key=lambda p: p.stat().st_mtime) if files else None


def public_video_url(base_url: str | None, video_file: str) -> str | None:
    base = base_url or os.environ.get("PUBLIC_VIDEO_BASE_URL")
    if not base:
        return None
    return urllib.parse.urljoin(base.rstrip("/") + "/", Path(video_file).name)


def cmd_queue(args: argparse.Namespace) -> None:
    run = Path(args.run)
    plan = read_json(run / "short_plan.json")
    items = []
    for short in plan["shorts"]:
        if "video_file" not in short:
            continue
        ex = short["worked_example"]
        caption = textwrap.shorten(
            f"{plan['course_title']} [{short['index']:02d}/{len(plan['shorts']):02d}] - {short['concept']}\n\n"
            f"{short['hook']}\n\nExample: {ex['setup']} {ex['calculation']} {ex['takeaway']}\n\n"
            f"Try this: {short['question_prompt']['question']}\nAnswer idea: {short['question_prompt']['answer']}\n\n"
            f"#stem #math #manim #education #reels",
            width=2200,
            placeholder="...",
        )
        video_file = short["video_file"]
        item = {"short_index": short["index"], "concept": short["concept"], "playlist": args.playlist or plan["course_title"], "video_file": video_file, "caption": caption, "worked_example": ex, "question_prompt": short["question_prompt"], "voiceover": short.get("voiceover"), "status": "ready", "platform": "instagram_reels"}
        video_url = public_video_url(args.public_base_url, video_file)
        if video_url:
            item["video_url"] = video_url
        items.append(item)
    queue = {"run": str(run), "playlist": args.playlist or plan["course_title"], "created_at": int(time.time()), "items": items}
    write_json(run / "instagram_publish_queue.json", queue)
    print(run / "instagram_publish_queue.json")


def graph_base_url() -> str:
    version = os.environ.get("META_GRAPH_VERSION", "v21.0").strip("/")
    return f"https://graph.facebook.com/{version}"


def graph_request(path: str, params: dict[str, str], method: str = "POST") -> dict[str, object]:
    encoded = urllib.parse.urlencode(params).encode("utf-8")
    if method == "GET":
        url = graph_base_url() + path + "?" + encoded.decode("utf-8")
        req = urllib.request.Request(url, headers={"User-Agent": "course-shorts-skills/0.1"})
    else:
        req = urllib.request.Request(graph_base_url() + path, data=encoded, headers={"User-Agent": "course-shorts-skills/0.1"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return {"error": body, "http_status": exc.code}


def cmd_publish(args: argparse.Namespace) -> None:
    run = Path(args.run)
    queue_path = run / "instagram_publish_queue.json"
    queue = read_json(queue_path)
    token = os.environ.get("META_ACCESS_TOKEN") or os.environ.get("IG_ACCESS_TOKEN")
    ig_user_id = os.environ.get("IG_USER_ID")
    results = []
    for item in queue.get("items", []):
        if not isinstance(item, dict):
            continue
        video_url = item.get("video_url")
        result = {"short_index": item.get("short_index"), "concept": item.get("concept"), "video_url": video_url}
        if args.dry_run:
            result.update({"status": "dry-run", "message": "Would create a Reel media container, poll processing, then publish."})
            results.append(result)
            continue
        if not token or not ig_user_id:
            result.update({"status": "skipped", "message": "Set IG_USER_ID and META_ACCESS_TOKEN or IG_ACCESS_TOKEN."})
            results.append(result)
            continue
        if not video_url:
            result.update({"status": "skipped", "message": "Queue item has no public video_url. Host videos and rerun queue with --public-base-url."})
            results.append(result)
            continue
        create = graph_request(f"/{ig_user_id}/media", {"media_type": "REELS", "video_url": str(video_url), "caption": str(item.get("caption", "")), "access_token": token})
        creation_id = create.get("id")
        if not creation_id:
            result.update({"status": "failed", "stage": "create", "response": create})
            results.append(result)
            continue
        status_payload = {}
        for _ in range(args.poll_attempts):
            time.sleep(args.poll_seconds)
            status_payload = graph_request(f"/{creation_id}", {"fields": "status_code,status", "access_token": token}, method="GET")
            if status_payload.get("status_code") == "FINISHED":
                break
            if status_payload.get("status_code") in {"ERROR", "EXPIRED"}:
                break
        if status_payload.get("status_code") != "FINISHED":
            result.update({"status": "failed", "stage": "process", "creation_id": creation_id, "response": status_payload})
            results.append(result)
            continue
        publish = graph_request(f"/{ig_user_id}/media_publish", {"creation_id": str(creation_id), "access_token": token})
        if publish.get("id"):
            result.update({"status": "published", "creation_id": creation_id, "media_id": publish.get("id")})
        else:
            result.update({"status": "failed", "stage": "publish", "creation_id": creation_id, "response": publish})
        results.append(result)
    write_json(run / "instagram_publish_results.json", {"created_at": int(time.time()), "results": results})
    print(run / "instagram_publish_results.json")


def cmd_all(args: argparse.Namespace) -> None:
    out = Path(args.out)
    extract_args = argparse.Namespace(url=args.url, out=str(out), sample=args.sample, max_pages=args.max_pages, max_pdfs=args.max_pdfs)
    cmd_extract(extract_args)
    cmd_plan(argparse.Namespace(run=str(out), max_shorts=args.max_shorts))
    cmd_notes(argparse.Namespace(run=str(out), compile=not args.no_pdf, pdf_engine=args.pdf_engine if not args.no_pdf else "none"))
    cmd_manim(argparse.Namespace(run=str(out)))
    if not args.no_render:
        cmd_render(argparse.Namespace(run=str(out), quality=args.quality, voice_engine=args.voice_engine))
        cmd_queue(argparse.Namespace(run=str(out), playlist=args.playlist, public_base_url=args.public_base_url))


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Course-to-notes-and-shorts workflow for Codex skills.")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("extract")
    p.add_argument("url", nargs="?", default="")
    p.add_argument("--out", required=True)
    p.add_argument("--sample", choices=["linear_algebra"])
    p.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES)
    p.add_argument("--max-pdfs", type=int, default=DEFAULT_MAX_PDFS)
    p.set_defaults(func=cmd_extract)
    p = sub.add_parser("plan")
    p.add_argument("--run", required=True)
    p.add_argument("--max-shorts", type=int, default=DEFAULT_SHORTS)
    p.set_defaults(func=cmd_plan)
    p = sub.add_parser("notes")
    p.add_argument("--run", required=True)
    p.add_argument("--compile", action="store_true")
    p.add_argument("--pdf-engine", choices=["auto", "latex", "fallback", "none"], default="none")
    p.set_defaults(func=cmd_notes)
    p = sub.add_parser("manim")
    p.add_argument("--run", required=True)
    p.set_defaults(func=cmd_manim)
    p = sub.add_parser("render")
    p.add_argument("--run", required=True)
    p.add_argument("--quality", choices=["l", "m"], default="l")
    p.add_argument("--voice-engine", choices=["none", "say", "edge-tts", "openai"], default="none")
    p.set_defaults(func=cmd_render)
    p = sub.add_parser("queue")
    p.add_argument("--run", required=True)
    p.add_argument("--playlist", default=None)
    p.add_argument("--public-base-url", default=None)
    p.set_defaults(func=cmd_queue)
    p = sub.add_parser("publish")
    p.add_argument("--run", required=True)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--poll-seconds", type=int, default=10)
    p.add_argument("--poll-attempts", type=int, default=30)
    p.set_defaults(func=cmd_publish)
    p = sub.add_parser("all")
    p.add_argument("url", nargs="?", default="")
    p.add_argument("--out", required=True)
    p.add_argument("--sample", choices=["linear_algebra"])
    p.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES)
    p.add_argument("--max-pdfs", type=int, default=DEFAULT_MAX_PDFS)
    p.add_argument("--max-shorts", type=int, default=DEFAULT_SHORTS)
    p.add_argument("--quality", choices=["l", "m"], default="l")
    p.add_argument("--voice-engine", choices=["none", "say", "edge-tts", "openai"], default="none")
    p.add_argument("--playlist", default=None)
    p.add_argument("--public-base-url", default=None)
    p.add_argument("--pdf-engine", choices=["auto", "latex", "fallback", "none"], default="auto")
    p.add_argument("--no-pdf", action="store_true")
    p.add_argument("--no-render", action="store_true")
    p.set_defaults(func=cmd_all)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
