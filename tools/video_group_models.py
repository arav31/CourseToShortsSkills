"""Exact, renderer-neutral semantic models for MIT 18.703 course videos.

The calendar title is the routing authority.  There is intentionally no fuzzy
fallback: a renderer receives a curated mathematical trace for an exact course
unit or the resolver fails closed.  The trace owns all persistent identities
and complete before/after snapshots, so renderers never have to invent an
example or recompute the mathematics.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, TypedDict


MIT_18_703_CALENDAR_TITLES: tuple[str, ...] = (
    "Groups",
    "Subgroups",
    "Cosets",
    "Cyclic Groups",
    "Permutation Groups",
    "Conjugation in S_n",
    "Isomorphisms",
    "Homomorphisms and Kernels",
    "Quotient Groups",
    "Isomorphism Theorems",
    "Alternating Groups",
    "Presentations and Groups of Small Order",
    "Sylow Theorems and Applications",
    "Rings",
    "Basic Properties of Rings",
    "Ring Homomorphisms and Ideals",
    "Field of Fractions",
    "Prime and Maximal Ideals",
    "Special Domains",
    "Euclidean Domains",
    "Polynomial Rings",
    "A Quick Primality Test",
    "Group Actions and Automorphisms",
    "Review",
)

# Name used by the notes pipeline; kept local so this module does not import
# the much larger stem_course module.
MIT_18_703_CALENDAR_ORDER = MIT_18_703_CALENDAR_TITLES


class WorkedExamplePayload(TypedDict):
    setup: str
    calculation: str
    takeaway: str
    question: str
    answer: str


class PersistentObjectPayload(TypedDict):
    id: str
    role: str
    color: str
    persistent: bool
    initial_state: str


class SemanticTransitionPayload(TypedDict):
    id: str
    kind: str
    claim: str
    action: str
    reveal: str
    persistent_object_ids: list[str]
    changed_object_ids: list[str]
    before: dict[str, str]
    after: dict[str, str]
    evidence: dict[str, object]


class RevealContractPayload(TypedDict):
    sequence: list[str]
    final_state: dict[str, str]
    final_claim: str


class ValidationPayload(TypedDict):
    valid: bool
    exact_title_route: bool
    exact_worked_example: bool
    persistent_identity: bool
    complete_snapshots: bool
    causal_continuity: bool
    minimum_transition_count: bool
    exact_semantics: bool


class FiniteMapElementPayload(TypedDict):
    id: str
    label: str


class FiniteMapRenderGeometryPayload(TypedDict):
    kind: str
    domain: list[FiniteMapElementPayload]
    codomain: list[FiniteMapElementPayload]
    mapping: list[int]
    identity_target: int
    kernel_indices: list[int]
    image_indices: list[int]


class _OptionalRenderGeometryPayload(TypedDict, total=False):
    render_geometry: FiniteMapRenderGeometryPayload


class GroupVideoPayload(_OptionalRenderGeometryPayload):
    payload_type: str
    topic_domain: str
    title: str
    exact_title: str
    route_key: str
    family: str
    visual_family: str
    visual_kind: str
    canonical_formula: str
    worked_example: WorkedExamplePayload
    question: str
    answer: str
    invariant: str
    reveal: str
    reveal_contract: RevealContractPayload
    subject_id: str
    objects: list[PersistentObjectPayload]
    persistent_objects: list[PersistentObjectPayload]
    transitions: list[SemanticTransitionPayload]
    validation: ValidationPayload


@dataclass(frozen=True)
class GroupVideoRoute:
    """Stable routing metadata for one exact MIT 18.703 calendar title."""

    title: str
    route_key: str
    visual_family: str
    topic_domain: str
    canonical_formula: str


@dataclass(frozen=True)
class _ObjectTemplate:
    slug: str
    role: str
    initial_state: str


@dataclass(frozen=True)
class _TransitionTemplate:
    slug: str
    kind: str
    claim: str
    action: str
    reveal: str
    updates: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class _TopicDefinition:
    route: GroupVideoRoute
    worked_example: WorkedExamplePayload
    invariant: str
    final_reveal: str
    objects: tuple[_ObjectTemplate, ...]
    transitions: tuple[_TransitionTemplate, ...]


_COLORS = ("#58A6FF", "#EAF2FF", "#F7C948", "#A371F7", "#7EE787", "#FF8C69")


def _object(slug: str, role: str, initial_state: str) -> _ObjectTemplate:
    return _ObjectTemplate(slug, role, initial_state)


def _transition(
    slug: str,
    kind: str,
    claim: str,
    action_text: str,
    reveal_text: str,
    **updates: str,
) -> _TransitionTemplate:
    return _TransitionTemplate(slug, kind, claim, action_text, reveal_text, tuple(updates.items()))


def _worked(
    setup: str,
    calculation: str,
    takeaway: str,
    question: str,
    answer: str,
) -> WorkedExamplePayload:
    return {
        "setup": setup,
        "calculation": calculation,
        "takeaway": takeaway,
        "question": question,
        "answer": answer,
    }


def _definition(
    title: str,
    route_slug: str,
    visual_family: str,
    topic_domain: str,
    canonical_formula: str,
    worked_example: WorkedExamplePayload,
    invariant: str,
    final_reveal: str,
    objects: tuple[_ObjectTemplate, ...],
    transitions: tuple[_TransitionTemplate, ...],
) -> _TopicDefinition:
    return _TopicDefinition(
        route=GroupVideoRoute(
            title=title,
            route_key=f"modern_algebra:mit_18_703:{route_slug}",
            visual_family=visual_family,
            topic_domain=topic_domain,
            canonical_formula=canonical_formula,
        ),
        worked_example=worked_example,
        invariant=invariant,
        final_reveal=final_reveal,
        objects=objects,
        transitions=transitions,
    )


_DEFINITIONS: tuple[_TopicDefinition, ...] = (
    _definition(
        "Groups",
        "group_axioms",
        "group_laws",
        "group_theory",
        r"ab\in G,\quad e a=a e=a,\quad aa^{-1}=e,\quad (ab)c=a(bc)",
        _worked(
            "Let G={e,r,r^2} be the rotations of an equilateral triangle, with composition and r^3=e.",
            "r r^2=e is closed; e r=r; r^{-1}=r^2; and (r r)r=r(r r)=e.",
            "The same operation satisfies closure, identity, inverse, and associativity on every listed rotation.",
            "Which element is the inverse of r?",
            "r^2, because r r^2=r^3=e.",
        ),
        "The carrier and composition law remain fixed while each group axiom is checked on the same rotations.",
        "All four group axioms hold, so the triangle rotations form a group.",
        (
            _object("carrier", "rotation carrier G", "G={e,r,r^2}; r^3=e"),
            _object("operation", "composition and closure check", "composition selected; closure unchecked"),
            _object("identity", "identity witness", "identity unchecked"),
            _object("inverse", "inverse witness", "inverse unchecked"),
            _object("associativity", "associativity comparison", "associativity unchecked"),
        ),
        (
            _transition("closure", "axiom_check", "Composition stays in G.", "Compose r with r^2 and retain the resulting rotation.", "r r^2=e belongs to G.", operation="r r^2=e in G; closure verified"),
            _transition("identity", "axiom_check", "One rotation fixes every element under composition.", "Apply e on both sides of r.", "e r=r e=r.", identity="e r=r e=r; identity verified"),
            _transition("inverse", "axiom_check", "Every displayed rotation has an inverse in G.", "Pair r with r^2.", "r^{-1}=r^2 because r r^2=e.", inverse="r pairs with r^2; e pairs with e; inverses verified"),
            _transition("associativity", "axiom_check", "Composition is associative.", "Compare both parenthesizations of three copies of r.", "(r r)r=r(r r)=e.", associativity="(r r)r=r(r r)=e; associativity verified"),
        ),
    ),
    _definition(
        "Subgroups",
        "subgroup_test_even_integers",
        "subgroup_cosets",
        "group_theory",
        r"H\le G\iff H\ne\varnothing\ \text{and}\ xy^{-1}\in H\ \text{for all }x,y\in H",
        _worked(
            "Test H=2Z inside the additive group (Z,+) with the one-step subgroup test.",
            "0=2(0) lies in 2Z, and for x=2a and y=2b, x-y=2a-2b=2(a-b) lies in 2Z.",
            "Nonemptiness and closure under x-y prove 2Z<=Z without separately rechecking every group axiom.",
            "Why does subtracting two even integers stay in 2Z?",
            "Their difference is 2(a-b), another integer multiple of 2.",
        ),
        "The ambient operation is addition in Z, and every witness remains an even integer throughout the test.",
        "The subgroup test certifies 2Z<=Z.",
        (
            _object("ambient", "ambient additive group", "(Z,+) fixed"),
            _object("candidate", "candidate subset", "H not yet selected"),
            _object("witness", "nonempty witness", "nonemptiness unchecked"),
            _object("difference", "generic subgroup-test difference", "x-y unresolved"),
            _object("verdict", "subgroup verdict", "subgroup status unresolved"),
        ),
        (
            _transition("select", "subset_selection", "Select the even integers inside Z.", "Highlight precisely the multiples of 2.", "H=2Z is the candidate.", candidate="H=2Z selected inside Z"),
            _transition("nonempty", "identity_witness", "The candidate is nonempty.", "Expose 0 as 2 times 0.", "0=2(0) lies in H.", witness="0=2(0) in 2Z"),
            _transition("difference", "closure_test", "A generic difference remains even.", "Write x=2a and y=2b, then subtract.", "x-y=2(a-b) lies in 2Z.", difference="x-y=2a-2b=2(a-b) in 2Z"),
            _transition("conclude", "subgroup_resolution", "The one-step subgroup criterion now applies.", "Join the nonempty witness to the generic difference calculation.", "2Z<=Z.", verdict="nonempty and difference-closed; 2Z<=Z"),
        ),
    ),
    _definition(
        "Cosets",
        "cosets_of_3z",
        "subgroup_cosets",
        "group_theory",
        r"a+H=\{a+h:h\in H\},\qquad a+H=b+H\iff a-b\in H",
        _worked(
            "Let H=3Z in (Z,+) and translate H by integer representatives.",
            "0+H=3Z, 1+H={3k+1}, and 2+H={3k+2}; every integer lies in exactly one of these cosets.",
            "The three cosets are equal-sized, disjoint residue classes that partition Z.",
            "When do a+3Z and b+3Z name the same coset?",
            "Exactly when a-b is divisible by 3.",
        ),
        "The subgroup H=3Z is translated but never deformed; equal cosets merge and distinct cosets stay disjoint.",
        "Z is partitioned into 0+3Z, 1+3Z, and 2+3Z.",
        (
            _object("ambient", "ambient integer line", "Z visible; no partition marked"),
            _object("subgroup", "persistent subgroup being translated", "H not yet fixed"),
            _object("representative", "coset representative marker", "representative unset"),
            _object("cosets", "translated coset blocks", "no cosets exposed"),
            _object("partition", "partition verdict", "coverage and disjointness unchecked"),
        ),
        (
            _transition("fix_subgroup", "subgroup_selection", "Fix one subgroup for every translation.", "Mark all multiples of 3.", "H=3Z remains the persistent template.", subgroup="H=3Z fixed as the translation template"),
            _transition("identity_coset", "coset_translation", "Translate H by representative 0.", "Place the representative at 0 and retain the original copy.", "0+H=3Z.", representative="representative 0", cosets="0+H=3Z exposed"),
            _transition("other_cosets", "coset_translation", "Translate the same H by 1 and 2.", "Move copies without changing their spacing.", "1+H={3k+1}; 2+H={3k+2}.", representative="representatives 0,1,2", cosets="0+H, 1+H, 2+H exposed"),
            _transition("partition", "partition_resolution", "The distinct translates cover Z exactly once.", "Join all integer positions to one of the three retained blocks.", "The cosets partition Z.", partition="three disjoint cosets cover Z"),
        ),
    ),
    _definition(
        "Cyclic Groups",
        "cyclic_generator_z6",
        "group_laws",
        "group_theory",
        r"\langle g\rangle=\{g^k:k\in\mathbb Z\}",
        _worked(
            "In the additive group Z/6Z, test whether [1] is a generator.",
            "0[1]=[0], 1[1]=[1], 2[1]=[2], ..., 5[1]=[5], and 6[1]=[0].",
            "Repeated use of the single element [1] reaches every residue exactly before returning to [0].",
            "What is the order of [1] in Z/6Z?",
            "6, because 6[1]=[0] and no smaller positive multiple is [0].",
        ),
        "The generator marker stays [1] while its successive multiples accumulate in one orbit.",
        "<[1]>=Z/6Z and |[1]|=6.",
        (
            _object("carrier", "cyclic carrier", "Z/6Z residues visible"),
            _object("generator", "candidate generator", "generator not selected"),
            _object("orbit", "successive multiples", "only [0] marked"),
            _object("return_time", "first return to identity", "return time unknown"),
            _object("verdict", "generation verdict", "generation unresolved"),
        ),
        (
            _transition("select", "generator_selection", "Select one persistent candidate.", "Mark [1] without replacing the carrier.", "g=[1].", generator="g=[1] selected"),
            _transition("advance", "cyclic_iteration", "Repeated addition reaches the nonzero residues.", "Advance through [1],[2],[3],[4],[5].", "The orbit now contains all six residues.", orbit="[0]->[1]->[2]->[3]->[4]->[5]"),
            _transition("return", "order_detection", "The next step first returns to the identity.", "Add [1] once more.", "6[1]=[0], so the order is 6.", return_time="first positive return: 6[1]=[0]"),
            _transition("conclude", "generator_resolution", "The orbit equals the whole carrier.", "Compare the retained orbit with all residues.", "<[1]>=Z/6Z.", verdict="[1] generates every element; order 6"),
        ),
    ),
    _definition(
        "Permutation Groups",
        "permutation_composition",
        "permutation_cycles",
        "group_theory",
        r"(\sigma\tau)(i)=\sigma(\tau(i))",
        _worked(
            "In S3 let sigma=(12), tau=(123), and compose right-to-left.",
            "1->tau 2->sigma 1, 2->tau 3->sigma 3, and 3->tau 1->sigma 2, so sigma tau=(23).",
            "Permutation composition follows each input through tau first and sigma second; order matters.",
            "What is sigma tau for sigma=(12) and tau=(123)?",
            "(23), with 1 fixed and 2,3 exchanged.",
        ),
        "The labels 1,2,3 persist while every arrow is followed through tau and then sigma.",
        "The complete mapping is 1->1, 2->3, 3->2, hence sigma tau=(23).",
        (
            _object("points", "persistent symbols 1,2,3", "symbols 1,2,3 fixed"),
            _object("tau", "first-applied permutation", "tau=(123) visible"),
            _object("sigma", "second-applied permutation", "sigma=(12) visible"),
            _object("mapping", "composite mapping table", "no composite images recorded"),
            _object("cycle", "resolved cycle notation", "composite unresolved"),
        ),
        (
            _transition("track_1", "composition_trace", "Track input 1 through tau then sigma.", "Follow 1->2->1.", "(sigma tau)(1)=1.", mapping="1->tau 2->sigma 1"),
            _transition("track_2", "composition_trace", "Track input 2 through the same order.", "Follow 2->3->3.", "(sigma tau)(2)=3.", mapping="1->1; 2->tau 3->sigma 3"),
            _transition("track_3", "composition_trace", "Track input 3 through the same order.", "Follow 3->1->2.", "(sigma tau)(3)=2.", mapping="1->1; 2->3; 3->tau 1->sigma 2"),
            _transition("write_cycle", "cycle_resolution", "Convert the completed map to cycle notation.", "Keep 1 fixed and connect 2 with 3.", "sigma tau=(23).", cycle="sigma tau=(23)"),
        ),
    ),
    _definition(
        "Conjugation in S_n",
        "conjugation_relabels_cycle",
        "permutation_cycles",
        "group_theory",
        r"\tau(a_1\ a_2\ \cdots\ a_k)\tau^{-1}=(\tau(a_1)\ \tau(a_2)\ \cdots\ \tau(a_k))",
        _worked(
            "In S3 set sigma=(123) and tau=(23), so tau^{-1}=tau.",
            "Conjugation relabels 1,2,3 as tau(1),tau(2),tau(3)=1,3,2; therefore tau(123)tau^{-1}=(132).",
            "Conjugation changes labels but preserves cycle length and cycle type.",
            "What is (23)(123)(23)^{-1}?",
            "(132).",
        ),
        "The original three-cycle remains a three-cycle; conjugation only transports its labels through tau.",
        "tau(123)tau^{-1}=(132), with cycle type preserved.",
        (
            _object("cycle", "original cycle sigma", "sigma=(123) fixed"),
            _object("conjugator", "conjugating permutation tau", "tau not selected"),
            _object("inverse", "inverse conjugator", "tau^{-1} hidden"),
            _object("labels", "transported cycle labels", "labels not transported"),
            _object("conjugate", "resolved conjugate", "conjugate unresolved"),
        ),
        (
            _transition("select_tau", "conjugator_selection", "Choose the transposition that swaps labels 2 and 3.", "Set tau=(23).", "tau=(23).", conjugator="tau=(23) selected"),
            _transition("inverse", "inverse_resolution", "A transposition is its own inverse.", "Compose tau with itself.", "tau^{-1}=(23).", inverse="tau^{-1}=tau=(23)"),
            _transition("relabel", "label_transport", "Transport every cycle entry through tau.", "Replace (1,2,3) by (tau(1),tau(2),tau(3)).", "(1,2,3) becomes (1,3,2).", labels="tau(1),tau(2),tau(3)=1,3,2"),
            _transition("resolve", "conjugation_resolution", "Read the transported labels as a cycle.", "Retain the three-cycle shape and write its new labels.", "tau(123)tau^{-1}=(132).", conjugate="tau(123)tau^{-1}=(132)"),
        ),
    ),
    _definition(
        "Isomorphisms",
        "square_rotations_z4",
        "homomorphism_quotient",
        "group_theory",
        r"\phi(r^k)=[k]_4,\qquad \phi(r^i r^j)=\phi(r^i)+\phi(r^j)",
        _worked(
            "Let R={e,r,r^2,r^3} be square rotations and define phi(r^k)=[k]_4 in Z/4Z.",
            "phi(r^3r^2)=phi(r^5)=phi(r)=[1]_4, while [3]_4+[2]_4=[1]_4; all four rotations map bijectively.",
            "The map converts composition of quarter-turns into addition mod 4 and loses no element.",
            "Which residue corresponds to a 180-degree rotation?",
            "[2]_4, because r^2 is two quarter-turns.",
        ),
        "Each square rotation keeps one residue label, and both operation paths end at the same paired object.",
        "The bijective homomorphism phi identifies square rotations with Z/4Z.",
        (
            _object("rotations", "square-rotation group", "R={e,r,r^2,r^3}"),
            _object("residues", "additive residue group", "Z/4Z={[0],[1],[2],[3]}"),
            _object("map", "persistent rotation-to-residue arrows", "phi not assigned"),
            _object("operation", "homomorphism comparison", "operation compatibility unchecked"),
            _object("verdict", "isomorphism verdict", "bijectivity and homomorphism unresolved"),
        ),
        (
            _transition("pair", "bijection_construction", "Pair every rotation with its quarter-turn count.", "Draw e->[0], r->[1], r^2->[2], r^3->[3].", "All four objects are paired once.", map="e->[0], r->[1], r^2->[2], r^3->[3]"),
            _transition("compose", "source_operation", "Compose r^3 with r^2 in the rotation group.", "Reduce r^5 using r^4=e.", "r^3r^2=r.", operation="source path: r^3r^2=r^5=r"),
            _transition("add", "target_operation", "Add the paired residues in Z/4Z.", "Compute [3]+[2]=[5]=[1].", "Both paths reach the pair r<->[1].", operation="source r; target [3]+[2]=[1]; paths agree"),
            _transition("conclude", "isomorphism_resolution", "The pairing is bijective and operation preserving.", "Join the completed pairing and operation square.", "R is isomorphic to Z/4Z.", verdict="phi is a bijective homomorphism; R isomorphic to Z/4Z"),
        ),
    ),
    _definition(
        "Homomorphisms and Kernels",
        "z8_to_z2_kernel_image",
        "homomorphism_quotient",
        "group_theory",
        r"\phi:\mathbb Z/8\mathbb Z\to\mathbb Z/2\mathbb Z,\quad \phi([k]_8)=[k]_2",
        _worked(
            "Define phi:Z/8Z->Z/2Z by phi([k]_8)=[k]_2.",
            "The even classes [0],[2],[4],[6] map to [0], the odd classes map to [1], so ker(phi)={[0],[2],[4],[6]} and im(phi)=Z/2Z.",
            "The kernel records exactly what collapses to the identity; the image records every value reached.",
            "What are the kernel and image of phi?",
            "ker(phi)={[0],[2],[4],[6]} and im(phi)={[0],[1]}=Z/2Z.",
        ),
        "Every domain class keeps its identity while its arrow ends at exactly one parity class.",
        "The parity map has a four-element kernel and surjective image Z/2Z.",
        (
            _object("domain", "domain Z/8Z", "eight residue classes visible"),
            _object("codomain", "codomain Z/2Z", "[0] and [1] visible"),
            _object("map", "homomorphism arrows", "phi not applied"),
            _object("kernel", "identity fiber", "kernel unresolved"),
            _object("image", "reached codomain values", "image unresolved"),
        ),
        (
            _transition("define", "map_definition", "Define reduction from mod 8 to mod 2.", "Attach each [k]_8 to [k]_2.", "phi([k]_8)=[k]_2.", map="phi([k]_8)=[k]_2 defined"),
            _transition("map_even", "fiber_trace", "All even classes reach the codomain identity.", "Route [0],[2],[4],[6] to [0].", "The identity fiber contains four classes.", map="even classes->[0]; odd classes not yet grouped"),
            _transition("kernel", "kernel_resolution", "The identity fiber is the kernel.", "Enclose precisely the four even domain classes.", "ker(phi)={[0],[2],[4],[6]}.", kernel="ker(phi)={[0],[2],[4],[6]}"),
            _transition("image", "image_resolution", "Both codomain classes are reached.", "Route [1],[3],[5],[7] to [1] and retain the even arrows.", "im(phi)=Z/2Z.", map="even classes->[0]; odd classes->[1]", image="im(phi)={[0],[1]}=Z/2Z"),
        ),
    ),
    _definition(
        "Quotient Groups",
        "normal_coset_operation",
        "subgroup_cosets",
        "group_theory",
        r"N\trianglelefteq G\Longrightarrow (gN)(hN)=(gh)N",
        _worked(
            "Take N=A3={e,(123),(132)} inside S3; its two cosets are N and (12)N.",
            "N has index 2, hence is normal, and ((12)N)^2=(12)^2N=N, while N acts as the quotient identity.",
            "Normality makes coset multiplication independent of representatives, producing S3/A3 of order 2.",
            "Why is multiplication of cosets well-defined here?",
            "Because A3 is normal in S3, so changing representatives does not change the product coset.",
        ),
        "The two coset blocks persist, and representative changes never alter their quotient product.",
        "Normality gives the well-defined two-element quotient S3/A3.",
        (
            _object("group", "ambient group S3", "six permutations visible"),
            _object("normal", "candidate normal subgroup A3", "A3 selected; normality unchecked"),
            _object("cosets", "quotient coset blocks", "cosets not formed"),
            _object("operation", "coset multiplication", "quotient operation unresolved"),
            _object("verdict", "well-defined quotient verdict", "quotient status unresolved"),
        ),
        (
            _transition("normality", "normality_check", "An index-two subgroup is normal.", "Compare the left and right odd cosets.", "A3 is normal in S3.", normal="A3 has index 2; A3 normal in S3"),
            _transition("form_cosets", "quotient_partition", "Collapse S3 into its two A3-cosets.", "Form N and (12)N.", "S3/N={N,(12)N}.", cosets="quotient blocks N and (12)N"),
            _transition("multiply", "quotient_operation", "Multiply cosets through representatives.", "Compute ((12)N)((12)N)=(12)^2N.", "The odd coset squares to N.", operation="((12)N)^2=(12)^2N=N"),
            _transition("well_defined", "quotient_resolution", "Normality removes representative ambiguity.", "Retain both blocks and certify every product.", "S3/A3 is a group of order 2.", verdict="operation well-defined; |S3/A3|=2"),
        ),
    ),
    _definition(
        "Isomorphism Theorems",
        "first_isomorphism_z_to_z3",
        "homomorphism_quotient",
        "group_theory",
        r"G/\ker\phi\cong\operatorname{im}\phi",
        _worked(
            "Let phi:Z->Z/3Z be phi(n)=[n]_3.",
            "ker(phi)=3Z and im(phi)=Z/3Z, so the induced map n+3Z->[n]_3 gives Z/3Z congruent to im(phi).",
            "The first isomorphism theorem factors a homomorphism into a quotient by exactly its kernel and an isomorphism onto its image.",
            "What quotient of Z is isomorphic to the image of phi?",
            "Z/3Z, because ker(phi)=3Z.",
        ),
        "Integers in one kernel coset remain together from the original map through the induced isomorphism.",
        "The map factors as Z -> Z/3Z -> im(phi), with the second arrow an isomorphism.",
        (
            _object("map", "original homomorphism", "phi not defined"),
            _object("kernel", "kernel subgroup", "kernel unresolved"),
            _object("quotient", "kernel-coset quotient", "quotient not formed"),
            _object("induced", "induced map to the image", "induced map hidden"),
            _object("verdict", "first-isomorphism verdict", "isomorphism unresolved"),
        ),
        (
            _transition("define", "map_definition", "Reduce each integer modulo 3.", "Set phi(n)=[n]_3.", "The homomorphism is surjective.", map="phi(n)=[n]_3; image=Z/3Z"),
            _transition("kernel", "kernel_resolution", "Find the integers sent to [0].", "Solve [n]_3=[0].", "ker(phi)=3Z.", kernel="ker(phi)=3Z"),
            _transition("quotient", "quotient_factor", "Collapse exactly the kernel cosets.", "Replace n by the class n+3Z.", "Z/ker(phi)=Z/3Z.", quotient="cosets n+3Z form Z/3Z"),
            _transition("induce", "isomorphism_resolution", "Send each kernel coset to its common image.", "Define bar(phi)(n+3Z)=[n]_3 and check bijectivity.", "Z/ker(phi) is isomorphic to im(phi).", induced="bar(phi)(n+3Z)=[n]_3 is bijective", verdict="Z/ker(phi) isomorphic to im(phi)"),
        ),
    ),
    _definition(
        "Alternating Groups",
        "parity_kernel_a3",
        "permutation_cycles",
        "group_theory",
        r"A_n=\ker(\operatorname{sgn}:S_n\to\{\pm1\})",
        _worked(
            "Apply the sign homomorphism to every element of S3.",
            "sgn(e)=sgn((123))=sgn((132))=+1, while each transposition has sign -1; therefore ker(sgn)=A3={e,(123),(132)}.",
            "The even permutations form a normal index-two subgroup because they are a homomorphism kernel.",
            "Which elements of S3 lie in A3?",
            "e, (123), and (132), exactly the permutations with sign +1.",
        ),
        "Each permutation keeps its cycle identity while the sign map sorts it into the +1 or -1 fiber.",
        "The +1 fiber is ker(sgn)=A3, hence A3 is normal in S3.",
        (
            _object("group", "permutations of S3", "six permutations visible"),
            _object("sign", "sign homomorphism", "sign values hidden"),
            _object("even", "even-permutation fiber", "+1 fiber empty"),
            _object("kernel", "kernel identification", "kernel unresolved"),
            _object("normality", "normal index-two conclusion", "normality unresolved"),
        ),
        (
            _transition("sign_identity", "parity_classification", "The identity has even parity.", "Send e to +1.", "sgn(e)=+1.", sign="e->+1; other signs hidden", even="+1 fiber={e}"),
            _transition("sign_cycles", "parity_classification", "Three-cycles are even.", "Write each three-cycle as two transpositions.", "(123) and (132) join the +1 fiber.", sign="e,(123),(132)->+1; transpositions->-1", even="+1 fiber={e,(123),(132)}"),
            _transition("kernel", "kernel_resolution", "The +1 fiber is the sign kernel.", "Label the retained even fiber A3.", "ker(sgn)=A3.", kernel="ker(sgn)=A3={e,(123),(132)}"),
            _transition("normal", "normality_resolution", "Every homomorphism kernel is normal.", "Carry the kernel status back into S3.", "A3 is normal and has index 2.", normality="A3 normal in S3; [S3:A3]=2"),
        ),
    ),
    _definition(
        "Presentations and Groups of Small Order",
        "d4_presentation_order",
        "finite_group_structure",
        "group_theory",
        r"D_4=\langle r,s\mid r^4=s^2=e,\ srs=r^{-1}\rangle",
        _worked(
            "Use r for a quarter-turn and s for a reflection of a square.",
            "The relation sr=r^{-1}s reduces every word to r^k or sr^k with 0<=k<4, giving 8 elements; by comparison |C4|=|V4|=4 and |S3|=6.",
            "Presentation relations are rewrite rules, and the resulting normal forms expose the order of D4 and distinguish it from smaller familiar groups.",
            "How many normal forms does the displayed D4 presentation have?",
            "Eight: e,r,r^2,r^3,s,sr,sr^2,sr^3.",
        ),
        "The generators r,s persist while relations shorten words without changing represented group elements.",
        "Exactly eight normal forms remain, so |D4|=8, unlike order-4 groups and S3 of order 6.",
        (
            _object("generators", "geometric generators r and s", "generators not assigned"),
            _object("relations", "presentation relations", "relations not applied"),
            _object("words", "rewritten normal forms", "word space unreduced"),
            _object("orders", "small-group order comparison", "comparison hidden"),
            _object("verdict", "presentation order verdict", "|D4| unresolved"),
        ),
        (
            _transition("assign", "generator_selection", "Assign r and s to square symmetries.", "Mark a quarter-turn and one reflection.", "r^4=e and s^2=e.", generators="r=quarter-turn; s=reflection"),
            _transition("rewrite", "relation_rewrite", "Move every reflection symbol to the left.", "Use sr=r^{-1}s, equivalent to srs=r^{-1}.", "Every word becomes r^k or sr^k.", relations="r^4=s^2=e; sr=r^{-1}s", words="normal-form shapes r^k or sr^k"),
            _transition("enumerate", "normal_form_count", "Bound k by the rotation relation.", "List k=0,1,2,3 in both word shapes.", "Eight normal forms remain.", words="e,r,r^2,r^3,s,sr,sr^2,sr^3"),
            _transition("compare", "order_resolution", "Compare the counted order with familiar small groups.", "Place |C4|=|V4|=4, |S3|=6, and |D4|=8 on one order line.", "D4 has order 8.", orders="|C4|=|V4|=4; |S3|=6; |D4|=8", verdict="presentation yields |D4|=8"),
        ),
    ),
    _definition(
        "Sylow Theorems and Applications",
        "sylow_order_15",
        "finite_group_structure",
        "group_theory",
        r"n_p\mid |G|/p^a,\qquad n_p\equiv1\pmod p",
        _worked(
            "Let |G|=15=3*5 and count Sylow 5-subgroups.",
            "Sylow gives n5|3 and n5=1 mod 5; among divisors {1,3}, only 1 satisfies the congruence, so n5=1.",
            "A unique Sylow subgroup is invariant under conjugation and therefore normal.",
            "Why must a group of order 15 have a normal subgroup of order 5?",
            "Its Sylow count n5 is forced to be 1, and uniqueness implies normality.",
        ),
        "The candidate Sylow 5-subgroups are counted under both divisibility and congruence constraints.",
        "n5=1, so the unique subgroup of order 5 is normal in G.",
        (
            _object("order", "group order factorization", "|G|=15=3*5"),
            _object("divisibility", "Sylow divisibility constraint", "n5 divisibility unchecked"),
            _object("congruence", "Sylow congruence constraint", "n5 congruence unchecked"),
            _object("count", "surviving Sylow count", "n5 unresolved"),
            _object("normality", "normality consequence", "normality unresolved"),
        ),
        (
            _transition("divide", "sylow_constraint", "The number of Sylow 5-subgroups divides 3.", "List the positive divisors of 15/5.", "n5 is 1 or 3.", divisibility="n5|3, so n5 in {1,3}"),
            _transition("congruence", "sylow_constraint", "The count is congruent to 1 modulo 5.", "Filter candidates by n5=1 mod 5.", "Only 1 survives.", congruence="n5=1 mod 5"),
            _transition("count", "count_resolution", "Intersect both exact constraints.", "Retain the common candidate.", "n5=1.", count="{1,3} intersect {1 mod 5}={1}; n5=1"),
            _transition("normal", "normality_resolution", "Conjugation cannot move a unique Sylow subgroup elsewhere.", "Apply uniqueness under conjugation.", "The Sylow 5-subgroup is normal.", normality="unique Sylow 5-subgroup P; P normal in G"),
        ),
    ),
    _definition(
        "Rings",
        "ring_distributivity",
        "ring_laws_ideals",
        "ring_theory",
        r"a(b+c)=ab+ac,\qquad (a+b)c=ac+bc",
        _worked(
            "In Z compare both distributive evaluation paths for a=2,b=3,c=4.",
            "2(3+4)=2*7=14, while 2*3+2*4=6+8=14.",
            "A ring carries compatible addition and multiplication, joined by the distributive laws.",
            "What common result do the two distributive paths produce?",
            "14.",
        ),
        "The integers 2,3,4 and both ring operations remain fixed while the two paths meet at one value.",
        "Both paths equal 14, visibly verifying distributivity in Z.",
        (
            _object("carrier", "ring carrier Z", "Z with + and multiplication fixed"),
            _object("operands", "persistent operands", "a=2,b=3,c=4"),
            _object("sum", "inner additive result", "b+c unresolved"),
            _object("left", "left distributive path", "a(b+c) unresolved"),
            _object("right", "right distributive path and verdict", "ab+ac unresolved"),
        ),
        (
            _transition("add", "ring_addition", "Evaluate the inner sum in Z.", "Combine b=3 and c=4.", "b+c=7.", sum="3+4=7"),
            _transition("left", "ring_multiplication", "Complete the left path.", "Multiply 2 by the retained sum 7.", "2(3+4)=14.", left="2(3+4)=2*7=14"),
            _transition("split", "distributive_transform", "Distribute the same 2 across both addends.", "Form 2*3 and 2*4 without changing operands.", "The right path is 6+8.", right="2*3+2*4=6+8"),
            _transition("match", "law_resolution", "Evaluate and join both paths.", "Add 6+8 and compare with 14.", "2(3+4)=2*3+2*4=14.", right="2*3+2*4=6+8=14; matches left path"),
        ),
    ),
    _definition(
        "Basic Properties of Rings",
        "ring_zero_and_negatives",
        "ring_laws_ideals",
        "ring_theory",
        r"0a=a0=0,\qquad (-a)b=-(ab),\qquad (-a)(-b)=ab",
        _worked(
            "Derive the sign rules in an arbitrary ring, then check a=3,b=4 in Z.",
            "0a=(0+0)a=0a+0a implies 0a=0; then (-a)b+ab=0 gives (-a)b=-(ab), so (-3)(-4)=12.",
            "Zero absorption and negative-product identities follow from distributivity and additive inverses; they are not extra ring axioms.",
            "Why is (-a)(-b)=ab in every ring?",
            "Apply (-a)b=-(ab) twice, so (-a)(-b)=-(-(ab))=ab.",
        ),
        "Every equality is derived inside one fixed ring using only distributivity and additive cancellation.",
        "The zero and sign identities follow from the ring axioms, with (-3)(-4)=12 as a check.",
        (
            _object("axioms", "distributivity and additive group laws", "ring axioms available"),
            _object("zero", "zero-product derivation", "0a unresolved"),
            _object("single_negative", "single-negative product", "(-a)b unresolved"),
            _object("double_negative", "double-negative product", "(-a)(-b) unresolved"),
            _object("example", "integer check", "numerical check hidden"),
        ),
        (
            _transition("zero", "derived_identity", "Distributivity forces zero to absorb multiplication.", "Expand (0+0)a and cancel one 0a.", "0a=0.", zero="0a=(0+0)a=0a+0a, hence 0a=0"),
            _transition("single", "derived_identity", "A single negative negates the product.", "Expand ((-a)+a)b=0b and use the zero identity.", "(-a)b=-(ab).", single_negative="(-a)b+ab=0, hence (-a)b=-(ab)"),
            _transition("double", "derived_identity", "Two negatives restore the product.", "Apply the single-negative identity to the second factor and cancel signs.", "(-a)(-b)=ab.", double_negative="(-a)(-b)=-((-a)b)=-(-(ab))=ab"),
            _transition("check", "example_resolution", "Check the derived identity in Z.", "Substitute a=3,b=4.", "(-3)(-4)=12=3*4.", example="(-3)(-4)=12=3*4"),
        ),
    ),
    _definition(
        "Ring Homomorphisms and Ideals",
        "ring_map_kernel_ideal",
        "ring_laws_ideals",
        "ring_theory",
        r"f(a+b)=f(a)+f(b),\quad f(ab)=f(a)f(b),\quad \ker f\triangleleft R",
        _worked(
            "Let f:Z->Z/6Z be reduction modulo 6.",
            "f(n)=[n]_6 preserves addition and multiplication, ker(f)=6Z is an ideal, and im(f)=Z/6Z; hence Z/6Z is isomorphic to im(f).",
            "The kernel of a ring homomorphism is an absorbing additive subgroup—an ideal—and determines the quotient through which the map factors.",
            "Which ideal is the kernel of reduction modulo 6?",
            "6Z.",
        ),
        "Each integer remains attached to its residue while the zero fiber becomes the kernel ideal and quotient zero class.",
        "Reduction modulo 6 factors through the ideal 6Z and identifies Z/6Z with the image.",
        (
            _object("domain", "domain ring Z", "integers visible"),
            _object("codomain", "codomain ring Z/6Z", "six residue classes visible"),
            _object("map", "ring homomorphism f", "f not defined"),
            _object("kernel", "kernel ideal", "kernel unresolved"),
            _object("quotient", "quotient-to-image factor", "factorization unresolved"),
        ),
        (
            _transition("define", "map_definition", "Reduce every integer modulo 6.", "Set f(n)=[n]_6.", "The map reaches every residue.", map="f(n)=[n]_6; image=Z/6Z"),
            _transition("preserve", "homomorphism_check", "The map preserves both ring operations.", "Compare f(a+b), f(ab) with residue operations.", "f(a+b)=f(a)+f(b) and f(ab)=f(a)f(b).", map="operation-preserving reduction f(n)=[n]_6"),
            _transition("kernel", "ideal_resolution", "The zero fiber is the multiples of 6 and absorbs Z-multiplication.", "Solve [n]_6=[0] and multiply 6k by arbitrary r.", "ker(f)=6Z is an ideal.", kernel="ker(f)=6Z; r(6k)=6(rk) in 6Z"),
            _transition("factor", "quotient_resolution", "Collapse the kernel ideal to obtain the image.", "Send n+6Z to [n]_6.", "Z/6Z is isomorphic to im(f).", quotient="n+6Z->[n]_6 is an isomorphism onto im(f)"),
        ),
    ),
    _definition(
        "Field of Fractions",
        "fraction_field_construction",
        "domain_factorization",
        "ring_theory",
        r"\frac ab=\frac cd\iff ad=bc,\qquad \frac ab+\frac cd=\frac{ad+bc}{bd}",
        _worked(
            "Construct fractions from the integral domain Z and add 2/3+1/6.",
            "Pairs (2,3) and (1,6) give (2*6+1*3)/(3*6)=15/18=5/6; equality is certified by cross-products, for example 15*6=5*18.",
            "Cross-product equivalence makes pair representatives independent and turns Z into its fraction field Q.",
            "Why do 15/18 and 5/6 represent the same fraction?",
            "Because 15*6=90=5*18.",
        ),
        "Equivalent numerator-denominator pairs stay in one fraction class while operations change representatives, not values.",
        "The construction yields 2/3+1/6=5/6 in Frac(Z)=Q.",
        (
            _object("domain", "integral domain Z", "Z fixed; denominators must be nonzero"),
            _object("pairs", "numerator-denominator pairs", "fraction pairs not selected"),
            _object("equivalence", "cross-product equivalence", "equivalence unchecked"),
            _object("sum", "fraction operation", "sum unresolved"),
            _object("field", "fraction-field conclusion", "field status unresolved"),
        ),
        (
            _transition("select", "pair_construction", "Represent the two inputs by nonzero-denominator pairs.", "Select (2,3) and (1,6).", "The pair classes denote 2/3 and 1/6.", pairs="(2,3) and (1,6) selected"),
            _transition("add", "fraction_operation", "Use the pair addition rule.", "Form (2*6+1*3,3*6).", "The sum has representative (15,18).", sum="(2*6+1*3)/(3*6)=15/18"),
            _transition("identify", "equivalence_resolution", "Replace the result by an equivalent reduced pair.", "Compare (15,18) and (5,6) by cross-products.", "15/18=5/6 because 15*6=5*18.", equivalence="15*6=90=5*18; (15,18)~(5,6)", sum="sum class represented by 5/6"),
            _transition("field", "field_resolution", "Every nonzero fraction class has a reciprocal.", "Swap numerator and denominator for a nonzero class.", "Frac(Z)=Q is a field.", field="nonzero a/b has inverse b/a; Frac(Z)=Q"),
        ),
    ),
    _definition(
        "Prime and Maximal Ideals",
        "prime_maximal_quotients",
        "ring_laws_ideals",
        "ring_theory",
        r"P\text{ prime}\iff R/P\text{ is a domain},\qquad M\text{ maximal}\iff R/M\text{ is a field}",
        _worked(
            "Examine the ideal (5)=5Z in Z through its quotient.",
            "Z/(5)=Z/5Z is a field, hence also an integral domain; therefore (5) is maximal and prime. In contrast, 2*3 lies in (6) although neither factor lies in (6).",
            "Quotient structure distinguishes prime and maximal ideals, and the composite ideal (6) supplies a concrete nonexample.",
            "Why is (5) maximal in Z?",
            "Because Z/(5) is the field Z/5Z.",
        ),
        "The ideal stays fixed while its quotient is tested first for field structure and then for domain structure.",
        "Because Z/(5) is a field, (5) is maximal and therefore prime.",
        (
            _object("ring", "ambient ring Z", "Z fixed"),
            _object("ideal", "candidate ideal", "ideal not selected"),
            _object("quotient", "quotient ring", "quotient not formed"),
            _object("tests", "field and domain tests", "quotient properties unchecked"),
            _object("verdict", "prime/maximal verdict", "ideal classification unresolved"),
        ),
        (
            _transition("select", "ideal_selection", "Select the proper ideal generated by 5.", "Mark all multiples of 5.", "I=(5).", ideal="I=(5)=5Z selected"),
            _transition("quotient", "quotient_construction", "Collapse differences by multiples of 5.", "Form the five residue classes.", "Z/(5)=Z/5Z.", quotient="Z/(5)={[0],[1],[2],[3],[4]}"),
            _transition("field", "quotient_test", "Every nonzero quotient class has an inverse.", "Expose [1]^-1=[1], [2]^-1=[3], [4]^-1=[4].", "Z/5Z is a field and a domain.", tests="Z/5Z is a field, hence an integral domain"),
            _transition("classify", "ideal_resolution", "Apply the quotient characterizations.", "Transfer field and domain status back to the ideal.", "(5) is maximal and prime.", verdict="(5) maximal; therefore (5) prime"),
        ),
    ),
    _definition(
        "Special Domains",
        "ed_pid_ufd_hierarchy",
        "domain_factorization",
        "ring_theory",
        r"\mathrm{ED}\Longrightarrow\mathrm{PID}\Longrightarrow\mathrm{UFD}",
        _worked(
            "Place Z in the domain hierarchy using the Euclidean norm d(n)=|n|.",
            "Euclidean division makes Z an ED; every ideal is nZ, so Z is a PID; hence Z is a UFD, as illustrated by 84=2^2*3*7 up to units and order.",
            "Each implication adds a structural consequence: Euclidean division gives principal ideals, which give unique factorization.",
            "Which implication chain connects Euclidean domains to unique factorization domains?",
            "ED=>PID=>UFD.",
        ),
        "One integral domain moves forward through implications; no converse is asserted and the domain is never treated as a group-only structure.",
        "Z witnesses the valid hierarchy ED=>PID=>UFD.",
        (
            _object("domain", "integral domain Z", "Z selected as an integral domain"),
            _object("euclidean", "Euclidean division property", "Euclidean status unchecked"),
            _object("principal", "principal-ideal consequence", "PID status unchecked"),
            _object("factorization", "unique-factorization consequence", "UFD status unchecked"),
            _object("chain", "one-way implication chain", "hierarchy unresolved"),
        ),
        (
            _transition("euclidean", "domain_classification", "Absolute value supplies Euclidean division in Z.", "For a,b with b nonzero retain a=bq+r with 0<=r<|b|.", "Z is a Euclidean domain.", euclidean="d(n)=|n| and a=bq+r with 0<=r<|b|; Z is ED"),
            _transition("pid", "implication", "A Euclidean gcd generates every ideal.", "Choose a nonzero ideal element of least Euclidean value and reduce all others by it.", "Every ideal of Z is principal.", principal="every ideal is nZ; Z is PID"),
            _transition("ufd", "implication", "Principal ideals force irreducible factorizations to be unique.", "Apply PID=>UFD to the same domain.", "Z is a UFD.", factorization="Z is UFD; 84=2^2*3*7 up to units and order"),
            _transition("chain", "hierarchy_resolution", "Record only the proved forward implications.", "Join ED to PID to UFD with one-way arrows.", "ED=>PID=>UFD.", chain="ED=>PID=>UFD; converses not asserted"),
        ),
    ),
    _definition(
        "Euclidean Domains",
        "euclidean_algorithm",
        "domain_factorization",
        "ring_theory",
        r"a=bq+r,\quad d(r)<d(b)",
        _worked(
            "Run the Euclidean algorithm in Z for 252 and 105.",
            "252=2*105+42, 105=2*42+21, 42=2*21+0; thus gcd(252,105)=21=5*105-2*252.",
            "Strictly decreasing remainders terminate at the gcd, and back-substitution produces a Bezout combination.",
            "What is gcd(252,105)?",
            "21.",
        ),
        "The same dividend-divisor pair advances by replacing it with divisor-remainder pairs of strictly smaller norm.",
        "The final nonzero remainder is 21, with 21=5*105-2*252.",
        (
            _object("pair", "current dividend-divisor pair", "(252,105)"),
            _object("quotient", "current Euclidean quotient", "quotient unresolved"),
            _object("remainder", "strictly smaller remainder", "remainder unresolved"),
            _object("gcd", "last nonzero remainder", "gcd unresolved"),
            _object("bezout", "back-substitution identity", "Bezout coefficients unresolved"),
        ),
        (
            _transition("divide_1", "euclidean_division", "Divide 252 by 105 with smaller remainder.", "Compute quotient 2 and remainder 42.", "252=2*105+42.", pair="next pair (105,42)", quotient="q1=2", remainder="r1=42<105"),
            _transition("divide_2", "euclidean_division", "Divide 105 by the retained remainder 42.", "Compute quotient 2 and remainder 21.", "105=2*42+21.", pair="next pair (42,21)", quotient="q2=2", remainder="r2=21<42"),
            _transition("divide_3", "termination", "The next remainder is zero.", "Compute 42=2*21+0.", "The last nonzero remainder is 21.", pair="terminal pair (21,0)", quotient="q3=2", remainder="r3=0", gcd="gcd(252,105)=21"),
            _transition("back_substitute", "bezout_resolution", "Express the gcd in the original inputs.", "Substitute 42=252-2*105 into 21=105-2*42.", "21=5*105-2*252.", bezout="21=105-2(252-2*105)=5*105-2*252"),
        ),
    ),
    _definition(
        "Polynomial Rings",
        "polynomial_division",
        "domain_factorization",
        "ring_theory",
        r"f(x)=q(x)g(x)+r(x),\qquad \deg r<\deg g",
        _worked(
            "Divide f(x)=x^3-1 by g(x)=x-1 in Q[x].",
            "Long division gives quotient x^2+x+1 and remainder 0, since (x-1)(x^2+x+1)=x^3-1.",
            "Over a field, leading-term cancellation yields a unique quotient and a remainder of smaller degree.",
            "What are the quotient and remainder of (x^3-1)/(x-1)?",
            "q(x)=x^2+x+1 and r(x)=0.",
        ),
        "The dividend identity is preserved after every leading-term cancellation, and the remainder degree strictly decreases.",
        "x^3-1=(x-1)(x^2+x+1)+0.",
        (
            _object("dividend", "persistent dividend f(x)", "f=x^3-1"),
            _object("divisor", "persistent divisor g(x)", "g=x-1"),
            _object("quotient", "accumulating quotient", "q=0"),
            _object("remainder", "current remainder", "r=x^3-1"),
            _object("identity", "division identity", "f=qg+r unresolved"),
        ),
        (
            _transition("cancel_x3", "leading_term_cancellation", "Cancel the leading term x^3.", "Add x^2 to q and subtract x^2(x-1).", "The new remainder is x^2-1.", quotient="q=x^2", remainder="r=x^2-1"),
            _transition("cancel_x2", "leading_term_cancellation", "Cancel the new leading term x^2.", "Add x to q and subtract x(x-1).", "The new remainder is x-1.", quotient="q=x^2+x", remainder="r=x-1"),
            _transition("cancel_x", "leading_term_cancellation", "Cancel the remaining leading term x.", "Add 1 to q and subtract x-1.", "The remainder is zero.", quotient="q=x^2+x+1", remainder="r=0"),
            _transition("verify", "division_resolution", "Reassemble divisor, quotient, and remainder.", "Multiply (x-1)(x^2+x+1) and add 0.", "The result is x^3-1.", identity="x^3-1=(x-1)(x^2+x+1)+0; deg condition holds"),
        ),
    ),
    _definition(
        "A Quick Primality Test",
        "aks_primality_steps",
        "algorithmic_algebra",
        "ring_theory",
        r"(X+a)^n\equiv X^n+a\pmod{n,\,X^r-1}",
        _worked(
            "Apply the AKS-style decision steps to n=31.",
            "31 is not a perfect power; r=29 works because ord_29(31)=ord_29(2)=28>(log_2 31)^2; gcd(a,31)=1 for 2<=a<=29; and the prime Frobenius congruence holds for 1<=a<=26, where 26=floor(sqrt(phi(29))*log_2 31).",
            "The procedure combines a perfect-power gate, an order bound, gcd checks, and bounded polynomial congruences before certifying prime.",
            "Which polynomial congruence is the final AKS-style certificate?",
            "(X+a)^n congruent to X^n+a modulo both n and X^r-1 for the required bounded values of a.",
        ),
        "The candidate n=31 persists through every gate; no step silently replaces it with a generic modular-addition example.",
        "All AKS-style gates pass for n=31, so the procedure returns prime.",
        (
            _object("candidate", "integer candidate n", "n=31 selected"),
            _object("power", "perfect-power gate", "perfect-power status unchecked"),
            _object("order", "multiplicative-order radius r", "r unresolved"),
            _object("gcd", "small-factor gcd gate", "gcd checks unresolved"),
            _object("polynomial", "bounded polynomial congruence gate", "congruences unresolved"),
        ),
        (
            _transition("power_gate", "primality_gate", "Reject nontrivial perfect powers first.", "Exhaust b=2,3,4: squares 4,9,16,25; cubes 8,27; and the fourth power 16. For b>=5, a^b>=2^5=32>31.", "None equals 31, so 31 is not a perfect power.", power="all a^b<=31 for a>1 are exhausted: b=2,3,4 are enumerated and b>=5 implies a^b>=32; 31 is not a perfect power"),
            _transition("choose_r", "order_search", "Choose r with multiplicative order larger than the logarithmic bound.", "Use 31=2 mod 29 and 2^14=-1 mod 29, so ord_29(31)=28.", "r=29 and 28>(log_2 31)^2.", order="r=29; ord_29(31)=28>(log_2 31)^2"),
            _transition("gcd_gate", "factor_gate", "Exclude a proper factor visible below r.", "Compute gcd(a,31) for 2<=a<=29.", "Every gcd is 1, and 31>29 so continue.", gcd="gcd(a,31)=1 for 2<=a<=29; n>r"),
            _transition("polynomial_gate", "congruence_resolution", "Verify the bounded Frobenius congruences.", "Check 1<=a<=floor(sqrt(phi(29))*log_2 31)=26 in (Z/31Z)[X]/(X^29-1).", "All congruences hold; return prime.", polynomial="(X+a)^31=X^31+a mod (31,X^29-1) for 1<=a<=26; prime"),
        ),
    ),
    _definition(
        "Group Actions and Automorphisms",
        "square_action_automorphism",
        "group_action_automorphism",
        "group_theory",
        r"\rho:G\to\operatorname{Sym}(X),\qquad |G|=|G\cdot x|\,|G_x|",
        _worked(
            "Let D4 act on the four vertices of a square and let s be a reflection.",
            "A vertex orbit has size 4 and its stabilizer has size 2, so 8=4*2; conjugation by s is an automorphism with c_s(r)=srs^{-1}=r^{-1}.",
            "An action turns group elements into permutations, while conjugation supplies structure-preserving automorphisms of the group itself.",
            "What automorphism does reflection conjugation induce on the rotation r?",
            "It sends r to r^{-1}.",
        ),
        "The same D4 elements act on vertices and conjugate group elements; both maps preserve multiplication.",
        "The square action satisfies orbit-stabilizer, and conjugation by s gives r->r^{-1}.",
        (
            _object("group", "acting group D4", "D4 with eight symmetries"),
            _object("vertices", "four-point action set", "vertices v1,v2,v3,v4 fixed"),
            _object("action", "action homomorphism rho", "rho not evaluated"),
            _object("orbit", "orbit and stabilizer", "orbit-stabilizer data unresolved"),
            _object("automorphism", "conjugation automorphism", "automorphism unresolved"),
        ),
        (
            _transition("define_action", "action_definition", "Send each symmetry to its vertex permutation.", "Define rho(g)(v)=g.v.", "rho:D4->Sym({v1,v2,v3,v4}).", action="rho(g)(v)=g.v; rho is an action homomorphism"),
            _transition("orbit", "orbit_trace", "Move v1 through all reachable vertices.", "Apply the four rotations to v1.", "D4.v1 contains all four vertices.", orbit="orbit(v1)={v1,v2,v3,v4}; size 4"),
            _transition("stabilizer", "orbit_stabilizer", "Identify the symmetries fixing v1.", "Retain e and the diagonal reflection through v1.", "|G_v1|=2 and 8=4*2.", orbit="orbit size 4; stabilizer size 2; |D4|=4*2=8"),
            _transition("automorphism", "automorphism_resolution", "Conjugation by a reflection preserves products and reverses r.", "Compute c_s(r)=srs^{-1}=srs=r^{-1}.", "c_s is an automorphism with r->r^{-1}.", automorphism="c_s(g)=sgs^{-1}; c_s(r)=r^{-1}"),
        ),
    ),
    _definition(
        "Review",
        "map_kernel_quotient_workflow",
        "homomorphism_quotient",
        "synthesis",
        r"G\xrightarrow{\phi}H,\quad \ker\phi\trianglelefteq G,\quad G/\ker\phi\cong\operatorname{im}\phi",
        _worked(
            "Review the map-kernel-quotient workflow with phi:Z/12Z->Z/4Z, phi([x]_12)=[x]_4.",
            "The map is well-defined and onto; ker(phi)={[0],[4],[8]}; collapsing those three-element cosets gives (Z/12Z)/ker(phi) isomorphic to Z/4Z.",
            "A reliable review workflow defines the map, computes its kernel and image, checks normality, forms the quotient, and only then invokes the isomorphism theorem.",
            "What quotient does the workflow identify with Z/4Z?",
            "(Z/12Z)/{[0],[4],[8]}.",
        ),
        "Each source element remains attached to its image, kernel fiber, and quotient coset throughout the workflow.",
        "Map -> kernel/image -> normal quotient -> induced isomorphism completes the review workflow.",
        (
            _object("source", "source group Z/12Z", "twelve classes visible"),
            _object("target", "target group Z/4Z", "four classes visible"),
            _object("map", "review homomorphism", "map not checked"),
            _object("kernel", "kernel and quotient blocks", "kernel unresolved; quotient not formed"),
            _object("isomorphism", "induced isomorphism", "final theorem not applied"),
        ),
        (
            _transition("map", "workflow_map", "Define and check the proposed homomorphism first.", "Send [x]_12 to [x]_4; changing x by 12 changes its image by 0 mod 4.", "phi is well-defined and onto.", map="phi([x]_12)=[x]_4 is well-defined and surjective"),
            _transition("kernel", "workflow_kernel", "Compute the identity fiber before forming a quotient.", "Solve [x]_4=[0].", "ker(phi)={[0],[4],[8]}.", kernel="ker(phi)={[0],[4],[8]}; quotient not formed"),
            _transition("quotient", "workflow_quotient", "Use kernel normality to form the quotient.", "Collapse each three-element kernel coset in Z/12Z.", "The quotient has four cosets.", kernel="kernel normal; four quotient cosets formed"),
            _transition("isomorphism", "workflow_resolution", "Map each quotient coset to its common target value.", "Apply the first isomorphism theorem to the checked map.", "(Z/12Z)/ker(phi) is isomorphic to Z/4Z.", isomorphism="bar(phi):[x]_12+ker(phi)->[x]_4 is an isomorphism"),
        ),
    ),
)


_DEFINITION_BY_TITLE: dict[str, _TopicDefinition] = {
    definition.route.title: definition for definition in _DEFINITIONS
}

if tuple(_DEFINITION_BY_TITLE) != MIT_18_703_CALENDAR_TITLES:
    raise RuntimeError("MIT 18.703 group-video definitions must match all 24 exact calendar titles in order")

GROUP_VIDEO_ROUTES: tuple[GroupVideoRoute, ...] = tuple(
    definition.route for definition in _DEFINITIONS
)
GROUP_VIDEO_ROUTE_BY_TITLE: Mapping[str, GroupVideoRoute] = {
    route.title: route for route in GROUP_VIDEO_ROUTES
}


def resolve_group_video_model(
    title: str,
    *,
    fail_closed: bool = True,
) -> GroupVideoRoute | None:
    """Resolve only an exact MIT 18.703 calendar title.

    Case folding, substring routing, and generic group fallbacks are omitted on
    purpose.  ``fail_closed=False`` is supplied only for callers that need to
    probe support without raising.
    """

    if not isinstance(title, str):
        raise TypeError("title must be a string")
    route = GROUP_VIDEO_ROUTE_BY_TITLE.get(title)
    if route is None and fail_closed:
        raise ValueError(f"Unsupported MIT 18.703 video title: {title!r}")
    return route


def resolve_group_video_route(
    title: str,
    *,
    fail_closed: bool = True,
) -> GroupVideoRoute | None:
    """Integration alias for :func:`resolve_group_video_model`."""

    return resolve_group_video_model(title, fail_closed=fail_closed)


def _object_id(route: GroupVideoRoute, slug: str) -> str:
    return f"{route.route_key}:{slug}"


def _z8_to_z2_render_geometry() -> FiniteMapRenderGeometryPayload:
    return {
        "kind": "finite_map",
        "domain": [
            {"id": f"z8_{index}", "label": f"[{index}]_8"}
            for index in range(8)
        ],
        "codomain": [
            {"id": f"z2_{index}", "label": f"[{index}]_2"}
            for index in range(2)
        ],
        "mapping": [index % 2 for index in range(8)],
        "identity_target": 0,
        "kernel_indices": [0, 2, 4, 6],
        "image_indices": [0, 1],
    }


def _core_payload(definition: _TopicDefinition) -> dict[str, object]:
    route = definition.route
    object_ids = [_object_id(route, template.slug) for template in definition.objects]
    initial_state = {
        object_id: template.initial_state
        for object_id, template in zip(object_ids, definition.objects)
    }
    objects: list[PersistentObjectPayload] = [
        {
            "id": object_id,
            "role": template.role,
            "color": _COLORS[index % len(_COLORS)],
            "persistent": True,
            "initial_state": template.initial_state,
        }
        for index, (object_id, template) in enumerate(zip(object_ids, definition.objects))
    ]

    transitions: list[SemanticTransitionPayload] = []
    state = dict(initial_state)
    object_id_by_slug = {
        template.slug: object_id
        for template, object_id in zip(definition.objects, object_ids)
    }
    for index, template in enumerate(definition.transitions, start=1):
        before = dict(state)
        changed_object_ids: list[str] = []
        for slug, value in template.updates:
            try:
                object_id = object_id_by_slug[slug]
            except KeyError as exc:
                raise RuntimeError(
                    f"{route.title} transition {template.slug!r} updates unknown object {slug!r}"
                ) from exc
            state[object_id] = value
            changed_object_ids.append(object_id)
        after = dict(state)
        transitions.append(
            {
                "id": f"{route.route_key}:{index:02d}:{template.slug}",
                "kind": template.kind,
                "claim": template.claim,
                "action": template.action,
                "reveal": template.reveal,
                "persistent_object_ids": list(object_ids),
                "changed_object_ids": changed_object_ids,
                "before": before,
                "after": after,
                "evidence": {
                    "title": route.title,
                    "formula": route.canonical_formula,
                    "changed_states": {
                        object_id: after[object_id] for object_id in changed_object_ids
                    },
                },
            }
        )

    worked_example = dict(definition.worked_example)
    reveal_contract: RevealContractPayload = {
        "sequence": [transition["reveal"] for transition in transitions],
        "final_state": dict(state),
        "final_claim": definition.final_reveal,
    }
    payload: dict[str, object] = {
        "payload_type": "group_theory",
        "topic_domain": route.topic_domain,
        "title": route.title,
        "exact_title": route.title,
        "route_key": route.route_key,
        "family": route.visual_family,
        "visual_family": route.visual_family,
        "visual_kind": route.visual_family,
        "canonical_formula": route.canonical_formula,
        "worked_example": worked_example,
        "question": worked_example["question"],
        "answer": worked_example["answer"],
        "invariant": definition.invariant,
        "reveal": definition.final_reveal,
        "reveal_contract": reveal_contract,
        "subject_id": object_ids[0],
        "objects": objects,
        "persistent_objects": [dict(row) for row in objects],
        "transitions": transitions,
    }
    if route.title == "Homomorphisms and Kernels":
        payload["render_geometry"] = _z8_to_z2_render_geometry()
    return payload


_VALIDATION_KEYS = (
    "valid",
    "exact_title_route",
    "exact_worked_example",
    "persistent_identity",
    "complete_snapshots",
    "causal_continuity",
    "minimum_transition_count",
    "exact_semantics",
)


def validate_finite_map_render_geometry(geometry: object) -> list[str]:
    """Validate renderer-neutral finite-map identities and derived index sets."""

    if not isinstance(geometry, Mapping):
        return ["render_geometry must be a mapping"]

    errors: list[str] = []
    if geometry.get("kind") != "finite_map":
        errors.append("render_geometry kind must be finite_map")

    domain = geometry.get("domain")
    codomain = geometry.get("codomain")
    domain_rows = domain if isinstance(domain, list) else []
    codomain_rows = codomain if isinstance(codomain, list) else []
    if not domain_rows:
        errors.append("finite map domain must be a nonempty list")
    if not codomain_rows:
        errors.append("finite map codomain must be a nonempty list")

    element_ids: list[str] = []
    for collection_name, rows in (("domain", domain_rows), ("codomain", codomain_rows)):
        for index, row in enumerate(rows):
            if not isinstance(row, Mapping):
                errors.append(f"{collection_name} element {index} must be a mapping")
                continue
            element_id = row.get("id")
            label = row.get("label")
            if not isinstance(element_id, str) or not element_id:
                errors.append(f"{collection_name} element {index} needs a nonempty id")
            else:
                element_ids.append(element_id)
            if not isinstance(label, str) or not label:
                errors.append(f"{collection_name} element {index} needs a nonempty label")
    if len(element_ids) != len(set(element_ids)):
        errors.append("finite map element ids must be unique")

    mapping = geometry.get("mapping")
    mapping_values = mapping if isinstance(mapping, list) else []
    if not isinstance(mapping, list) or len(mapping_values) != len(domain_rows):
        errors.append("finite map mapping must be total on the domain")
    mapping_in_range = bool(codomain_rows) and all(
        type(target) is int and 0 <= target < len(codomain_rows)
        for target in mapping_values
    )
    if not mapping_in_range:
        errors.append("finite map mapping targets must be codomain indices")

    identity_target = geometry.get("identity_target")
    identity_in_range = (
        type(identity_target) is int
        and 0 <= identity_target < len(codomain_rows)
    )
    if not identity_in_range:
        errors.append("finite map identity_target must be a codomain index")

    kernel_indices = geometry.get("kernel_indices")
    if not isinstance(kernel_indices, list) or not all(
        type(index) is int for index in kernel_indices
    ):
        errors.append("finite map kernel_indices must be integer domain indices")
    elif mapping_in_range and identity_in_range:
        expected_kernel = [
            index
            for index, target in enumerate(mapping_values)
            if target == identity_target
        ]
        if kernel_indices != expected_kernel:
            errors.append("finite map kernel_indices must equal the identity preimage")

    image_indices = geometry.get("image_indices")
    if not isinstance(image_indices, list) or not all(
        type(index) is int for index in image_indices
    ):
        errors.append("finite map image_indices must be integer codomain indices")
    elif mapping_in_range:
        expected_image = sorted(set(mapping_values))
        if image_indices != expected_image:
            errors.append("finite map image_indices must equal the mapping range")

    return errors


def validate_group_video_payload(payload: Mapping[str, object]) -> list[str]:
    """Return deterministic contract errors for a group-video payload."""

    if not isinstance(payload, Mapping):
        return ["payload must be a mapping"]

    errors: list[str] = []
    title = payload.get("exact_title")
    if not isinstance(title, str) or title not in _DEFINITION_BY_TITLE:
        errors.append("exact_title must be one of the 24 MIT 18.703 calendar titles")
        return errors

    definition = _DEFINITION_BY_TITLE[title]
    expected = _core_payload(definition)
    exact_fields = (
        "payload_type",
        "topic_domain",
        "title",
        "exact_title",
        "route_key",
        "family",
        "visual_family",
        "visual_kind",
        "canonical_formula",
        "worked_example",
        "question",
        "answer",
        "invariant",
        "reveal",
        "reveal_contract",
        "subject_id",
    )
    for field in exact_fields:
        if payload.get(field) != expected[field]:
            errors.append(f"{field} does not match the exact-title semantic definition")

    objects = payload.get("objects")
    persistent_objects = payload.get("persistent_objects")
    if objects != expected["objects"]:
        errors.append("objects do not match the exact persistent-object definition")
    if persistent_objects != expected["persistent_objects"] or persistent_objects != objects:
        errors.append("persistent_objects must exactly mirror objects")

    render_geometry = payload.get("render_geometry")
    if render_geometry != expected.get("render_geometry"):
        errors.append("render_geometry does not match the exact-title semantic definition")
    if render_geometry is not None or "render_geometry" in expected:
        errors.extend(validate_finite_map_render_geometry(render_geometry))

    object_rows = objects if isinstance(objects, list) else []
    object_ids = [
        str(row.get("id", "")) for row in object_rows if isinstance(row, Mapping)
    ]
    expected_ids = set(object_ids)
    if (
        len(object_ids) < 4
        or len(object_ids) != len(set(object_ids))
        or any(not object_id for object_id in object_ids)
        or any(
            not isinstance(row, Mapping) or row.get("persistent") is not True
            for row in object_rows
        )
    ):
        errors.append("at least four unique objects must be explicitly persistent")

    transitions = payload.get("transitions")
    transition_rows = transitions if isinstance(transitions, list) else []
    if len(transition_rows) < 4:
        errors.append("group video payload needs at least four semantic transitions")
    if transitions != expected["transitions"]:
        errors.append("transitions do not match the exact-title causal calculation")

    previous_after: dict[str, str] | None = None
    seen_transition_ids: set[str] = set()
    for position, transition in enumerate(transition_rows, start=1):
        if not isinstance(transition, Mapping):
            errors.append(f"transition {position} must be a mapping")
            continue
        transition_id = transition.get("id")
        before = transition.get("before")
        after = transition.get("after")
        persistent_ids = transition.get("persistent_object_ids")
        changed_ids = transition.get("changed_object_ids")
        if not isinstance(transition_id, str) or not transition_id or transition_id in seen_transition_ids:
            errors.append(f"transition {position} needs a unique id")
        else:
            seen_transition_ids.add(transition_id)
        if (
            not isinstance(before, Mapping)
            or not isinstance(after, Mapping)
            or set(before) != expected_ids
            or set(after) != expected_ids
        ):
            errors.append(f"transition {position} must carry complete before/after snapshots")
            before_map: dict[str, object] = {}
            after_map: dict[str, object] = {}
        else:
            before_map = dict(before)
            after_map = dict(after)
            if before_map == after_map:
                errors.append(f"transition {position} does not change semantic state")
        if not isinstance(persistent_ids, list) or set(persistent_ids) != expected_ids:
            errors.append(f"transition {position} loses persistent object identities")
        if not isinstance(changed_ids, list) or not changed_ids or not set(changed_ids) <= expected_ids:
            errors.append(f"transition {position} needs declared changed object identities")
        elif before_map and after_map:
            actual_changed = {
                object_id
                for object_id in expected_ids
                if before_map[object_id] != after_map[object_id]
            }
            if actual_changed != set(changed_ids):
                errors.append(f"transition {position} changed-object evidence is inconsistent")
        if previous_after is not None and before_map != previous_after:
            errors.append(f"transition {position} breaks causal state continuity")
        if after_map:
            previous_after = {str(key): str(value) for key, value in after_map.items()}
        for field in ("kind", "claim", "action", "reveal"):
            if not isinstance(transition.get(field), str) or not str(transition.get(field)).strip():
                errors.append(f"transition {position} needs a nonempty {field}")

    validation = payload.get("validation")
    if not isinstance(validation, Mapping):
        errors.append("validation must be a mapping")
    else:
        if set(validation) != set(_VALIDATION_KEYS):
            errors.append("validation fields are incomplete")
        if any(validation.get(key) is not True for key in _VALIDATION_KEYS):
            errors.append("all embedded validation checks must pass")
    return errors


def build_group_video_payload(
    title: str,
    worked_example: Mapping[str, object] | None = None,
) -> GroupVideoPayload:
    """Build the exact curated payload for one supported calendar title.

    ``worked_example`` is accepted for drop-in integration with existing video
    builders, but deliberately does not override the authoritative example.
    That prevents generic or unrelated examples from replacing topic semantics.
    """

    del worked_example
    route = resolve_group_video_model(title, fail_closed=True)
    assert route is not None
    definition = _DEFINITION_BY_TITLE[route.title]
    payload = _core_payload(definition)
    payload["validation"] = {
        "valid": True,
        "exact_title_route": True,
        "exact_worked_example": True,
        "persistent_identity": True,
        "complete_snapshots": True,
        "causal_continuity": True,
        "minimum_transition_count": True,
        "exact_semantics": True,
    }
    errors = validate_group_video_payload(payload)
    if errors:
        raise ValueError("Invalid MIT 18.703 group video payload: " + "; ".join(errors))
    return payload  # type: ignore[return-value]


def build_all_group_video_payloads() -> dict[str, GroupVideoPayload]:
    """Build all 24 exact payloads in authoritative calendar order."""

    return {
        title: build_group_video_payload(title)
        for title in MIT_18_703_CALENDAR_TITLES
    }


# Explicit integration aliases for callers that name the domain before "video".
resolve_video_group_model = resolve_group_video_model
build_video_group_payload = build_group_video_payload
validate_video_group_payload = validate_group_video_payload


__all__ = [
    "GROUP_VIDEO_ROUTES",
    "GROUP_VIDEO_ROUTE_BY_TITLE",
    "FiniteMapElementPayload",
    "FiniteMapRenderGeometryPayload",
    "GroupVideoPayload",
    "GroupVideoRoute",
    "MIT_18_703_CALENDAR_ORDER",
    "MIT_18_703_CALENDAR_TITLES",
    "PersistentObjectPayload",
    "RevealContractPayload",
    "SemanticTransitionPayload",
    "ValidationPayload",
    "WorkedExamplePayload",
    "build_all_group_video_payloads",
    "build_group_video_payload",
    "build_video_group_payload",
    "resolve_group_video_model",
    "resolve_group_video_route",
    "resolve_video_group_model",
    "validate_group_video_payload",
    "validate_finite_map_render_geometry",
    "validate_video_group_payload",
]
