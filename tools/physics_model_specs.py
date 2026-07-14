"""Typed, side-effect-free mechanics model selection.

The registry deliberately stays independent of ``stem_course`` so that the
course generator can import it without creating a circular dependency.  Its
visual-kind vocabulary mirrors ``stem_course.PHYSICS_VISUAL_KINDS``.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata
from types import MappingProxyType
from typing import Final, Literal, Mapping, Optional, overload


PhysicsVisualKind = Literal[
    "physics_force",
    "physics_kinematics",
    "physics_vector",
    "physics_center_of_mass",
    "physics_rocket",
    "physics_mass_transfer",
    "physics_ode",
    "physics_work",
    "physics_energy",
    "physics_momentum",
    "physics_potential",
    "physics_circular",
    "physics_rotation",
    "physics_recoil",
    "physics_wave",
]

StatementKind = Literal[
    "definition",
    "kinematic_relation",
    "constraint",
    "dynamical_law",
    "interaction_law",
    "conservation_law",
    "constitutive_law",
    "geometric_relation",
    "differential_equation",
    "wave_relation",
]


PHYSICS_VISUAL_KINDS: Final[frozenset[PhysicsVisualKind]] = frozenset(
    {
        "physics_force",
        "physics_kinematics",
        "physics_vector",
        "physics_center_of_mass",
        "physics_rocket",
        "physics_mass_transfer",
        "physics_ode",
        "physics_work",
        "physics_energy",
        "physics_momentum",
        "physics_potential",
        "physics_circular",
        "physics_rotation",
        "physics_recoil",
        "physics_wave",
    }
)


@dataclass(frozen=True)
class SymbolRow:
    """One exact symbol-to-meaning row for notes and visual labels."""

    symbol: str
    meaning: str

    def as_dict(self) -> dict[str, str]:
        return {"symbol": self.symbol, "meaning": self.meaning}


@dataclass(frozen=True)
class PhysicsModelSpec:
    """Canonical content and evidence contract for one mechanics model."""

    model_id: str
    visual_kind: PhysicsVisualKind
    canonical_formula: str
    prerequisites: tuple[str, ...]
    statement_kind: StatementKind
    exact_symbol_rows: tuple[SymbolRow, ...]
    required_example_tokens: tuple[str, ...]
    required_figure_tokens: tuple[str, ...]

    @property
    def symbol_rows(self) -> tuple[SymbolRow, ...]:
        """Short alias for consumers that already use ``symbol_rows``."""

        return self.exact_symbol_rows

    def as_dict(self) -> dict[str, object]:
        """Return a serialization-friendly copy without exposing mutable state."""

        return {
            "model_id": self.model_id,
            "visual_kind": self.visual_kind,
            "canonical_formula": self.canonical_formula,
            "prerequisites": list(self.prerequisites),
            "statement_kind": self.statement_kind,
            "exact_symbol_rows": [row.as_dict() for row in self.exact_symbol_rows],
            "required_example_tokens": list(self.required_example_tokens),
            "required_figure_tokens": list(self.required_figure_tokens),
        }


def _model(
    model_id: str,
    visual_kind: PhysicsVisualKind,
    canonical_formula: str,
    prerequisites: tuple[str, ...],
    statement_kind: StatementKind,
    symbol_rows: tuple[tuple[str, str], ...],
    required_example_tokens: tuple[str, ...],
    required_figure_tokens: tuple[str, ...],
) -> PhysicsModelSpec:
    return PhysicsModelSpec(
        model_id=model_id,
        visual_kind=visual_kind,
        canonical_formula=canonical_formula,
        prerequisites=prerequisites,
        statement_kind=statement_kind,
        exact_symbol_rows=tuple(SymbolRow(symbol, meaning) for symbol, meaning in symbol_rows),
        required_example_tokens=required_example_tokens,
        required_figure_tokens=required_figure_tokens,
    )


_MODEL_SPECS: Final[tuple[PhysicsModelSpec, ...]] = (
    _model(
        "kinematics_1d",
        "physics_kinematics",
        r"x(t)=x_0+v_0t+\frac{1}{2}at^2,\quad v(t)=v_0+at",
        ("algebra", "signed quantities", "units"),
        "kinematic_relation",
        (
            ("x(t)", "position on the selected axis at elapsed time t"),
            ("x_0", "initial position on that axis"),
            ("v_0", "initial signed velocity"),
            ("a", "constant signed acceleration"),
            ("t", "elapsed time"),
        ),
        ("initial_position", "initial_velocity", "acceleration", "elapsed_time"),
        ("number_line", "position_marker", "velocity_arrow", "time_readout"),
    ),
    _model(
        "kinematics_2d",
        "physics_kinematics",
        r"\vec r(t)=\vec r_0+\vec v_0t+\frac{1}{2}\vec a t^2",
        ("vectors", "components", "constant-acceleration kinematics"),
        "kinematic_relation",
        (
            (r"\vec r(t)", "two-dimensional position at elapsed time t"),
            (r"\vec r_0", "initial position vector"),
            (r"\vec v_0", "initial velocity vector"),
            (r"\vec a", "constant acceleration vector"),
            ("t", "elapsed time"),
        ),
        ("initial_position_vector", "initial_velocity_vector", "acceleration_vector", "elapsed_time"),
        ("coordinate_axes", "trajectory", "position_vector", "velocity_vector"),
    ),
    _model(
        "projectile_motion",
        "physics_kinematics",
        r"x=x_0+v_0\cos\theta\,t,\quad y=y_0+v_0\sin\theta\,t-\frac{1}{2}gt^2",
        ("two-dimensional kinematics", "trigonometry", "gravity near Earth"),
        "kinematic_relation",
        (
            ("x,y", "horizontal and vertical projectile coordinates"),
            ("x_0,y_0", "launch coordinates"),
            ("v_0", "launch-speed magnitude"),
            (r"\theta", "launch angle measured from the positive horizontal axis"),
            ("g", "positive gravitational-acceleration magnitude"),
            ("t", "elapsed time after launch"),
        ),
        ("launch_position", "initial_speed", "launch_angle", "gravity", "elapsed_time"),
        ("coordinate_axes", "parabolic_trajectory", "velocity_vector", "gravity_arrow"),
    ),
    _model(
        "rolling_kinematics",
        "physics_kinematics",
        r"v_{\mathrm{cm}}=\omega R,\quad a_{\mathrm{cm}}=\alpha R",
        ("translation", "angular kinematics", "no-slip constraint"),
        "constraint",
        (
            (r"v_{\mathrm{cm}}", "center-of-mass speed along the surface"),
            (r"a_{\mathrm{cm}}", "center-of-mass tangential acceleration"),
            (r"\omega", "angular speed"),
            (r"\alpha", "angular acceleration"),
            ("R", "rolling radius"),
        ),
        ("radius", "angular_speed", "center_speed", "no_slip"),
        ("rolling_body", "ground", "contact_point", "translation_arrow", "rotation_arrow"),
    ),
    _model(
        "force_balance",
        "physics_force",
        r"\sum \vec F_{\mathrm{ext}}=m\vec a",
        ("vectors", "free-body diagrams", "kinematics"),
        "dynamical_law",
        (
            (r"\sum \vec F_{\mathrm{ext}}", "vector sum of external forces on the chosen system"),
            ("m", "mass of the chosen system"),
            (r"\vec a", "acceleration of that system"),
        ),
        ("system", "mass", "external_forces", "acceleration"),
        ("body", "system_boundary", "force_arrows", "net_force_arrow", "acceleration_arrow"),
    ),
    _model(
        "newton_first_law",
        "physics_force",
        r"\sum \vec F_{\mathrm{ext}}=0\;\Longrightarrow\;\frac{d\vec v}{dt}=0",
        ("vectors", "inertial frames", "velocity"),
        "dynamical_law",
        (
            (r"\sum \vec F_{\mathrm{ext}}", "net external force"),
            (r"\vec v", "constant velocity in an inertial frame"),
            ("t", "time"),
        ),
        ("inertial_frame", "external_forces", "initial_velocity", "time_interval"),
        ("body", "balanced_force_arrows", "velocity_arrow", "inertial_axes"),
    ),
    _model(
        "newton_second_law",
        "physics_force",
        r"\sum \vec F_{\mathrm{ext}}=\frac{d\vec p}{dt}=m\vec a\quad(m\ \mathrm{constant})",
        ("vectors", "momentum", "free-body diagrams"),
        "dynamical_law",
        (
            (r"\sum \vec F_{\mathrm{ext}}", "net external force"),
            (r"\vec p", "linear momentum of the system"),
            ("m", "constant system mass in the final equality"),
            (r"\vec a", "center-of-mass acceleration"),
            ("t", "time"),
        ),
        ("system", "mass", "external_forces", "acceleration"),
        ("body", "free_body_diagram", "net_force_arrow", "acceleration_arrow"),
    ),
    _model(
        "newton_laws",
        "physics_force",
        r"\sum \vec F_{\mathrm{ext}}=\frac{d\vec p}{dt}",
        ("vectors", "inertial frames", "momentum"),
        "dynamical_law",
        (
            (r"\sum \vec F_{\mathrm{ext}}", "net external force on the chosen system"),
            (r"\vec p", "linear momentum of that system"),
            ("t", "time measured in an inertial frame"),
        ),
        ("inertial_frame", "system", "external_forces", "momentum_change"),
        ("system_boundary", "force_arrows", "momentum_vector", "inertial_axes"),
    ),
    _model(
        "action_reaction",
        "physics_force",
        r"\vec F_{A\to B}=-\vec F_{B\to A}",
        ("interactions", "vectors", "free-body diagrams"),
        "interaction_law",
        (
            (r"\vec F_{A\to B}", "force exerted by A on B"),
            (r"\vec F_{B\to A}", "force exerted by B on A"),
            ("A,B", "the two interacting bodies"),
        ),
        ("body_a", "body_b", "force_on_a_by_b", "force_on_b_by_a"),
        ("two_bodies", "interaction_pair", "equal_length_arrows", "separate_free_body_diagrams"),
    ),
    _model(
        "gravity_force",
        "physics_force",
        r"\vec F_g=m\vec g",
        ("vectors", "mass", "gravitational field"),
        "interaction_law",
        (
            (r"\vec F_g", "gravitational force on the body"),
            ("m", "gravitational mass"),
            (r"\vec g", "local gravitational-field vector"),
        ),
        ("mass", "gravitational_field", "weight"),
        ("body", "gravity_arrow", "field_direction", "reference_surface"),
    ),
    _model(
        "contact_force",
        "physics_force",
        r"\vec F_{\mathrm{contact}}=N\hat n+f\hat t",
        ("vectors", "surfaces", "free-body diagrams"),
        "interaction_law",
        (
            (r"\vec F_{\mathrm{contact}}", "total force exerted by the surface"),
            ("N", "normal-force magnitude"),
            ("f", "signed tangential friction magnitude"),
            (r"\hat n", "unit normal away from the surface"),
            (r"\hat t", "selected unit tangent along the surface"),
        ),
        ("body", "surface", "normal_force", "friction_force"),
        ("contact_point", "surface", "normal_arrow", "friction_arrow", "free_body_diagram"),
    ),
    _model(
        "tension_force",
        "physics_force",
        r"\vec T=T\hat\ell",
        ("vectors", "strings and ropes", "free-body diagrams"),
        "interaction_law",
        (
            (r"\vec T", "tension force on the selected body"),
            ("T", "tension magnitude"),
            (r"\hat\ell", "unit direction along the rope away from the body"),
        ),
        ("body", "rope", "tension_magnitude", "rope_direction"),
        ("body", "rope_segment", "tension_arrow", "attachment_point"),
    ),
    _model(
        "spring_force",
        "physics_force",
        r"\vec F_s=-k\vec x",
        ("vectors", "equilibrium", "linear response"),
        "constitutive_law",
        (
            (r"\vec F_s", "restoring force exerted by the spring"),
            ("k", "spring constant"),
            (r"\vec x", "displacement from equilibrium"),
        ),
        ("spring_constant", "equilibrium_position", "displacement", "spring_force"),
        ("spring", "equilibrium_marker", "displacement_arrow", "restoring_force_arrow"),
    ),
    _model(
        "pulley_constraint",
        "physics_force",
        r"\ell=\mathrm{constant},\quad a_1=-a_2",
        ("tension", "kinematics", "ideal strings and pulleys"),
        "constraint",
        (
            (r"\ell", "fixed total length of the inextensible string"),
            ("a_1,a_2", "signed accelerations of the linked masses"),
            ("T", "common tension for an ideal massless string and pulley"),
        ),
        ("mass_1", "mass_2", "string_length", "tension", "acceleration_constraint"),
        ("two_masses", "pulley", "continuous_rope", "tension_arrows", "acceleration_arrows"),
    ),
    _model(
        "linear_drag",
        "physics_force",
        r"\vec F_D=-b\vec v",
        ("vectors", "velocity", "linear differential equations"),
        "constitutive_law",
        (
            (r"\vec F_D", "linear drag force"),
            ("b", "positive linear-drag coefficient"),
            (r"\vec v", "body velocity relative to the fluid"),
        ),
        ("drag_coefficient", "relative_velocity", "drag_force"),
        ("body", "fluid", "velocity_arrow", "opposing_drag_arrow"),
    ),
    _model(
        "quadratic_drag",
        "physics_force",
        r"\vec F_D=-\frac{1}{2}\rho C_D A\lVert\vec v\rVert\vec v",
        ("vectors", "relative velocity", "fluid density"),
        "constitutive_law",
        (
            (r"\vec F_D", "quadratic drag force"),
            (r"\rho", "fluid density"),
            ("C_D", "dimensionless drag coefficient"),
            ("A", "reference area"),
            (r"\vec v", "body velocity relative to the fluid"),
        ),
        ("fluid_density", "drag_coefficient", "reference_area", "relative_velocity"),
        ("body", "fluid", "velocity_arrow", "opposing_drag_arrow", "area_marker"),
    ),
    _model(
        "drag_force",
        "physics_force",
        r"\vec F_D=-D(v)\hat v",
        ("vectors", "relative velocity", "fluid forces"),
        "constitutive_law",
        (
            (r"\vec F_D", "drag force exerted by the fluid"),
            ("D(v)", "nonnegative speed-dependent drag magnitude"),
            (r"\hat v", "direction of velocity relative to the fluid"),
        ),
        ("relative_velocity", "drag_law", "drag_force"),
        ("body", "fluid", "relative_velocity_arrow", "opposing_drag_arrow"),
    ),
    _model(
        "momentum_definition",
        "physics_momentum",
        r"\vec p=m\vec v",
        ("mass", "vectors", "velocity"),
        "definition",
        (
            (r"\vec p", "linear momentum"),
            ("m", "body mass"),
            (r"\vec v", "velocity in the selected inertial frame"),
        ),
        ("mass", "velocity", "momentum"),
        ("body", "velocity_arrow", "momentum_arrow", "reference_frame"),
    ),
    _model(
        "impulse_momentum",
        "physics_momentum",
        r"\vec J=\int_{t_i}^{t_f}\vec F_{\mathrm{ext}}\,dt=\Delta\vec p",
        ("momentum", "force", "integration"),
        "dynamical_law",
        (
            (r"\vec J", "external impulse over the stated interval"),
            (r"\vec F_{\mathrm{ext}}", "net external force as a function of time"),
            ("t_i,t_f", "initial and final times"),
            (r"\Delta\vec p", "final momentum minus initial momentum"),
        ),
        ("initial_momentum", "final_momentum", "force_history", "time_interval"),
        ("force_time_graph", "impulse_area", "momentum_before", "momentum_after"),
    ),
    _model(
        "momentum_conservation",
        "physics_momentum",
        r"\sum_i\vec p_{i}=\sum_i\vec p_{f}\quad(\vec J_{\mathrm{ext}}=0)",
        ("momentum", "systems", "vectors"),
        "conservation_law",
        (
            (r"\vec p_i", "momentum of a body before the interaction"),
            (r"\vec p_f", "momentum of a body after the interaction"),
            (r"\vec J_{\mathrm{ext}}", "net external impulse on the system"),
        ),
        ("system", "initial_momenta", "final_momenta", "external_impulse"),
        ("system_boundary", "before_state", "after_state", "momentum_vectors", "total_momentum_marker"),
    ),
    _model(
        "elastic_collision",
        "physics_momentum",
        r"\sum\vec p_i=\sum\vec p_f,\quad K_i=K_f",
        ("momentum conservation", "kinetic energy", "isolated systems"),
        "conservation_law",
        (
            (r"\vec p_i,\vec p_f", "total momentum before and after collision"),
            ("K_i,K_f", "total kinetic energy before and after collision"),
            ("m_1,m_2", "colliding masses"),
            (r"\vec v_{1i},\vec v_{2i}", "initial velocities"),
            (r"\vec v_{1f},\vec v_{2f}", "final velocities"),
        ),
        ("mass_1", "mass_2", "initial_velocities", "final_velocities", "kinetic_energy_before", "kinetic_energy_after"),
        ("system_boundary", "before_state", "after_state", "separated_bodies", "velocity_arrows", "kinetic_energy_meter"),
    ),
    _model(
        "inelastic_collision",
        "physics_momentum",
        r"\sum\vec p_i=\sum\vec p_f,\quad K_f<K_i",
        ("momentum conservation", "kinetic energy", "isolated systems"),
        "conservation_law",
        (
            (r"\vec p_i,\vec p_f", "total momentum before and after collision"),
            ("K_i,K_f", "total kinetic energy before and after collision"),
            ("m_1,m_2", "colliding masses"),
            (r"\vec v_{1f},\vec v_{2f}", "possibly distinct final velocities"),
        ),
        ("mass_1", "mass_2", "initial_velocities", "final_velocities", "kinetic_energy_loss"),
        ("system_boundary", "before_state", "after_state", "velocity_arrows", "energy_transfer_meter"),
    ),
    _model(
        "perfectly_inelastic_collision",
        "physics_momentum",
        r"\vec v_f=\frac{m_1\vec v_{1i}+m_2\vec v_{2i}}{m_1+m_2}",
        ("momentum conservation", "center of mass", "isolated systems"),
        "conservation_law",
        (
            (r"\vec v_f", "shared velocity after the bodies stick"),
            ("m_1,m_2", "colliding masses"),
            (r"\vec v_{1i},\vec v_{2i}", "velocities before collision"),
        ),
        ("mass_1", "mass_2", "initial_velocities", "shared_final_velocity", "sticking"),
        ("system_boundary", "before_state", "stuck_after_state", "velocity_arrows", "shared_velocity_arrow"),
    ),
    _model(
        "collision_momentum",
        "physics_momentum",
        r"\sum\vec p_i+\vec J_{\mathrm{ext}}=\sum\vec p_f",
        ("momentum", "impulse", "systems"),
        "dynamical_law",
        (
            (r"\vec p_i,\vec p_f", "total system momentum before and after collision"),
            (r"\vec J_{\mathrm{ext}}", "external impulse during collision"),
            ("i,f", "states immediately before and after the collision"),
        ),
        ("system", "initial_momenta", "final_momenta", "external_impulse"),
        ("system_boundary", "before_state", "impact_state", "after_state", "momentum_vectors"),
    ),
    _model(
        "work_definition",
        "physics_work",
        r"W_{A\to B}=\int_A^B\vec F\cdot d\vec r",
        ("forces", "dot products", "integration"),
        "definition",
        (
            ("W_{A\to B}", "work done along the path from A to B"),
            (r"\vec F", "force acting along the path"),
            (r"d\vec r", "infinitesimal displacement along the path"),
        ),
        ("force", "path", "initial_position", "final_position", "displacement"),
        ("path", "force_vector", "displacement_vector", "work_accumulator"),
    ),
    _model(
        "work_energy_theorem",
        "physics_work",
        r"W_{\mathrm{net}}=\Delta K=K_f-K_i",
        ("work", "kinetic energy", "net force"),
        "dynamical_law",
        (
            (r"W_{\mathrm{net}}", "net work done on the body"),
            (r"\Delta K", "change in kinetic energy"),
            ("K_i,K_f", "initial and final kinetic energy"),
        ),
        ("net_work", "initial_speed", "final_speed", "mass", "kinetic_energy_change"),
        ("body", "force_path", "initial_speed_arrow", "final_speed_arrow", "kinetic_energy_meter"),
    ),
    _model(
        "gravitational_potential_energy",
        "physics_energy",
        r"\Delta U_g=mg(y_f-y_i)",
        ("gravity", "work", "reference levels"),
        "definition",
        (
            (r"\Delta U_g", "change in near-Earth gravitational potential energy"),
            ("m", "body mass"),
            ("g", "local gravitational-acceleration magnitude"),
            ("y_i,y_f", "initial and final vertical coordinates"),
        ),
        ("mass", "gravity", "initial_height", "final_height", "reference_level"),
        ("body", "height_axis", "reference_level", "gravity_arrow", "potential_energy_meter"),
    ),
    _model(
        "spring_potential_energy",
        "physics_energy",
        r"U_s=\frac{1}{2}kx^2",
        ("spring force", "work", "equilibrium"),
        "definition",
        (
            ("U_s", "elastic potential energy stored by the spring"),
            ("k", "spring constant"),
            ("x", "extension or compression from equilibrium"),
        ),
        ("spring_constant", "equilibrium_position", "displacement", "stored_energy"),
        ("spring", "equilibrium_marker", "displacement_marker", "potential_energy_meter"),
    ),
    _model(
        "energy_conservation",
        "physics_energy",
        r"K_i+U_i+W_{\mathrm{nc}}=K_f+U_f",
        ("kinetic energy", "potential energy", "system boundaries"),
        "conservation_law",
        (
            ("K_i,K_f", "initial and final kinetic energy"),
            ("U_i,U_f", "initial and final potential energy"),
            ("W_{\mathrm{nc}}", "work transferred by nonconservative interactions"),
        ),
        ("system", "initial_kinetic_energy", "initial_potential_energy", "final_kinetic_energy", "final_potential_energy", "nonconservative_work"),
        ("initial_state", "final_state", "kinetic_energy_meter", "potential_energy_meter", "total_energy_marker"),
    ),
    _model(
        "potential_energy",
        "physics_energy",
        r"\vec F=-\nabla U",
        ("forces", "work", "multivariable calculus"),
        "definition",
        (
            (r"\vec F", "conservative force"),
            ("U", "potential-energy function"),
            (r"\nabla U", "spatial gradient of potential energy"),
        ),
        ("potential_function", "position", "force"),
        ("position_axes", "potential_surface", "force_arrow", "gradient_arrow"),
    ),
    _model(
        "potential_energy_diagram",
        "physics_potential",
        r"K(x)=E-U(x)\geq0,\quad U(x_t)=E",
        ("energy conservation", "graphs", "turning points"),
        "constraint",
        (
            ("U(x)", "potential energy as a function of position"),
            ("E", "fixed total mechanical energy"),
            ("K(x)", "kinetic energy available at position x"),
            ("x_t", "turning point where kinetic energy is zero"),
        ),
        ("potential_function", "total_energy", "position_samples", "turning_points"),
        ("position_axis", "potential_curve", "total_energy_line", "allowed_region", "turning_point_markers"),
    ),
    _model(
        "circular_position",
        "physics_circular",
        r"\vec r(t)=R\langle\cos(\omega t+\phi_0),\sin(\omega t+\phi_0)\rangle",
        ("vectors", "trigonometry", "radians"),
        "kinematic_relation",
        (
            (r"\vec r(t)", "position relative to the circle center"),
            ("R", "circle radius"),
            (r"\omega", "constant angular speed"),
            (r"\phi_0", "initial angular phase"),
            ("t", "elapsed time"),
        ),
        ("radius", "angular_speed", "initial_phase", "elapsed_time"),
        ("circle", "center", "radius_vector", "position_marker", "angle_marker"),
    ),
    _model(
        "uniform_circular_motion",
        "physics_circular",
        r"v=\omega R,\quad T=\frac{2\pi}{\omega}",
        ("radians", "speed", "periodic motion"),
        "kinematic_relation",
        (
            ("v", "constant tangential speed"),
            (r"\omega", "constant angular speed"),
            ("R", "circle radius"),
            ("T", "time for one revolution"),
        ),
        ("radius", "speed", "angular_speed", "period"),
        ("circle", "center", "moving_body", "tangent_velocity_arrow", "lap_phase"),
    ),
    _model(
        "radial_acceleration",
        "physics_circular",
        r"\vec a_r=-\frac{v^2}{R}\hat r=-\omega^2\vec r",
        ("uniform circular motion", "vectors", "acceleration"),
        "kinematic_relation",
        (
            (r"\vec a_r", "inward radial acceleration"),
            ("v", "tangential speed"),
            ("R", "circle radius"),
            (r"\omega", "angular speed"),
            (r"\hat r", "outward radial unit vector"),
        ),
        ("radius", "speed", "radial_acceleration"),
        ("circle", "center", "tangent_velocity_arrow", "inward_acceleration_arrow", "velocity_difference"),
    ),
    _model(
        "circular_dynamics",
        "physics_circular",
        r"\sum F_{\mathrm{inward}}=m\frac{v^2}{R}=m\omega^2R",
        ("free-body diagrams", "Newton's second law", "circular kinematics"),
        "dynamical_law",
        (
            (r"\sum F_{\mathrm{inward}}", "net force component toward the circle center"),
            ("m", "moving mass"),
            ("v", "tangential speed"),
            ("R", "path radius"),
            (r"\omega", "angular speed"),
        ),
        ("mass", "radius", "speed", "inward_forces"),
        ("circle", "center", "body", "force_arrows", "net_inward_force_arrow"),
    ),
    _model(
        "rigid_body_motion",
        "physics_rotation",
        r"\vec v_P=\vec v_O+\vec\omega\times\vec r_{P/O}",
        ("vectors", "translation", "angular velocity"),
        "kinematic_relation",
        (
            (r"\vec v_P", "velocity of material point P"),
            (r"\vec v_O", "velocity of reference point O on the rigid body"),
            (r"\vec\omega", "rigid body's angular-velocity vector"),
            (r"\vec r_{P/O}", "fixed body-relative vector from O to P"),
        ),
        ("reference_point", "material_point", "reference_velocity", "angular_velocity", "relative_position"),
        ("rigid_body", "reference_point", "material_point", "translation_arrow", "rotation_arrow"),
    ),
    _model(
        "moment_of_inertia",
        "physics_rotation",
        r"I_O=\int r_\perp^2\,dm",
        ("mass distributions", "integration", "rotation axes"),
        "definition",
        (
            ("I_O", "moment of inertia about axis through O"),
            (r"r_\perp", "perpendicular distance from the axis"),
            ("dm", "differential mass element"),
        ),
        ("mass_distribution", "rotation_axis", "perpendicular_distances"),
        ("rigid_body", "rotation_axis", "mass_elements", "radius_markers"),
    ),
    _model(
        "torque",
        "physics_rotation",
        r"\vec\tau_O=\vec r\times\vec F",
        ("vectors", "cross products", "forces"),
        "definition",
        (
            (r"\vec\tau_O", "torque about origin or pivot O"),
            (r"\vec r", "vector from O to the force application point"),
            (r"\vec F", "applied force"),
        ),
        ("pivot", "application_point", "lever_arm", "force"),
        ("rigid_body", "pivot", "lever_arm", "force_arrow", "torque_arc"),
    ),
    _model(
        "rotational_dynamics",
        "physics_rotation",
        r"\sum\tau_O=I_O\alpha",
        ("torque", "moment of inertia", "angular kinematics"),
        "dynamical_law",
        (
            (r"\sum\tau_O", "net external torque about the fixed axis through O"),
            ("I_O", "moment of inertia about that axis"),
            (r"\alpha", "angular acceleration about that axis"),
        ),
        ("rotation_axis", "external_torques", "moment_of_inertia", "angular_acceleration"),
        ("rigid_body", "rotation_axis", "torque_arrows", "angular_acceleration_arrow"),
    ),
    _model(
        "point_particle_angular_momentum",
        "physics_rotation",
        r"\vec L_O=\vec r\times\vec p",
        ("linear momentum", "cross products", "choice of origin"),
        "definition",
        (
            (r"\vec L_O", "particle angular momentum about O"),
            (r"\vec r", "position from O to the particle"),
            (r"\vec p", "particle linear momentum"),
            ("O", "declared origin"),
        ),
        ("origin", "particle_position", "particle_momentum"),
        ("origin", "point_particle", "position_vector", "momentum_vector", "angular_momentum_direction"),
    ),
    _model(
        "rigid_body_angular_momentum",
        "physics_rotation",
        r"\vec L_O=\mathbf I_O\vec\omega",
        ("rigid bodies", "moment of inertia", "angular velocity"),
        "definition",
        (
            (r"\vec L_O", "rigid-body angular momentum about O"),
            (r"\mathbf I_O", "inertia tensor about O"),
            (r"\vec\omega", "angular-velocity vector"),
        ),
        ("rigid_body", "rotation_axis", "inertia_tensor", "angular_velocity"),
        ("rigid_body", "rotation_axis", "angular_velocity_arrow", "angular_momentum_arrow"),
    ),
    _model(
        "angular_momentum",
        "physics_rotation",
        r"\vec L_O=\sum_i\vec r_i\times\vec p_i",
        ("linear momentum", "cross products", "systems"),
        "definition",
        (
            (r"\vec L_O", "total angular momentum about O"),
            (r"\vec r_i", "position of component i relative to O"),
            (r"\vec p_i", "linear momentum of component i"),
        ),
        ("origin", "component_positions", "component_momenta"),
        ("origin", "system_boundary", "position_vectors", "momentum_vectors", "angular_momentum_arrow"),
    ),
    _model(
        "angular_impulse",
        "physics_rotation",
        r"\int_{t_i}^{t_f}\vec\tau_O\,dt=\Delta\vec L_O",
        ("torque", "angular momentum", "integration"),
        "dynamical_law",
        (
            (r"\vec\tau_O", "net external torque about O"),
            ("t_i,t_f", "initial and final times"),
            (r"\Delta\vec L_O", "change in angular momentum about O"),
        ),
        ("origin", "torque_history", "time_interval", "initial_angular_momentum", "final_angular_momentum"),
        ("torque_time_graph", "angular_impulse_area", "angular_momentum_before", "angular_momentum_after"),
    ),
    _model(
        "rolling_dynamics",
        "physics_rotation",
        r"\sum F_x=Ma_{\mathrm{cm}},\quad\sum\tau_{\mathrm{cm}}=I_{\mathrm{cm}}\alpha,\quad a_{\mathrm{cm}}=\alpha R",
        ("Newton's second law", "rotational dynamics", "static friction"),
        "dynamical_law",
        (
            (r"\sum F_x", "net force along the rolling surface"),
            ("M", "total rolling-body mass"),
            (r"a_{\mathrm{cm}}", "center-of-mass acceleration"),
            (r"\sum\tau_{\mathrm{cm}}", "net torque about the center of mass"),
            (r"I_{\mathrm{cm}}", "moment of inertia about the center of mass"),
            (r"\alpha", "angular acceleration"),
            ("R", "rolling radius"),
        ),
        ("mass", "radius", "moment_of_inertia", "external_forces", "center_acceleration", "angular_acceleration", "no_slip"),
        ("rolling_body", "surface", "free_body_diagram", "contact_point", "translation_arrow", "rotation_arrow"),
    ),
    _model(
        "rolling_kinetic_energy",
        "physics_rotation",
        r"K=\frac{1}{2}Mv_{\mathrm{cm}}^2+\frac{1}{2}I_{\mathrm{cm}}\omega^2",
        ("kinetic energy", "center-of-mass motion", "moment of inertia"),
        "definition",
        (
            ("K", "total kinetic energy of the rolling rigid body"),
            ("M", "total mass"),
            (r"v_{\mathrm{cm}}", "center-of-mass speed"),
            (r"I_{\mathrm{cm}}", "moment of inertia about the center of mass"),
            (r"\omega", "angular speed"),
        ),
        ("mass", "center_speed", "moment_of_inertia", "angular_speed", "translational_energy", "rotational_energy"),
        ("rolling_body", "translation_arrow", "rotation_arrow", "translational_energy_meter", "rotational_energy_meter"),
    ),
    _model(
        "rolling_angular_momentum",
        "physics_rotation",
        r"L_C=I_{\mathrm{cm}}\omega,\quad L_P=(I_{\mathrm{cm}}+MR^2)\omega",
        ("angular momentum", "parallel-axis theorem", "rolling kinematics"),
        "definition",
        (
            ("L_C", "angular momentum about the center of mass"),
            ("L_P", "angular momentum about the instantaneous contact point"),
            (r"I_{\mathrm{cm}}", "moment of inertia about the center of mass"),
            ("M", "total mass"),
            ("R", "rolling radius"),
            (r"\omega", "angular speed"),
        ),
        ("mass", "radius", "moment_of_inertia", "angular_speed", "reference_point"),
        ("rolling_body", "center_of_mass", "contact_point", "rotation_arrow", "angular_momentum_arrow"),
    ),
    _model(
        "continuous_mass_transfer",
        "physics_rocket",
        r"\sum\vec F_{\mathrm{ext}}=\frac{d\vec P_{\mathrm{cv}}}{dt}+\sum_{\mathrm{out}}\dot m\vec v-\sum_{\mathrm{in}}\dot m\vec v",
        ("momentum", "control volumes", "mass-flow rate"),
        "conservation_law",
        (
            (r"\sum\vec F_{\mathrm{ext}}", "net external force on the control volume"),
            (r"\vec P_{\mathrm{cv}}", "momentum stored inside the control volume"),
            (r"\dot m", "positive mass-flow rate through a port"),
            (r"\vec v", "flow velocity in the selected inertial frame"),
        ),
        ("control_volume", "mass_flow_rate", "inlet_velocity", "outlet_velocity", "external_force"),
        ("control_volume_boundary", "inlet", "outlet", "flow_arrows", "momentum_flux_labels"),
    ),
    _model(
        "rocket_equation",
        "physics_rocket",
        r"\Delta v=v_e\ln\!\left(\frac{m_i}{m_f}\right)",
        ("momentum conservation", "variable mass", "logarithms"),
        "dynamical_law",
        (
            (r"\Delta v", "ideal rocket velocity change"),
            ("v_e", "effective exhaust speed relative to the rocket"),
            ("m_i", "initial vehicle mass including propellant"),
            ("m_f", "final vehicle mass after propellant is expelled"),
        ),
        ("initial_mass", "final_mass", "exhaust_speed", "delta_velocity"),
        ("rocket", "exhaust_stream", "velocity_arrow", "mass_readout", "delta_velocity_readout"),
    ),
    _model(
        "center_of_mass",
        "physics_center_of_mass",
        r"\vec r_{\mathrm{cm}}=\frac{\sum_i m_i\vec r_i}{\sum_i m_i}",
        ("mass", "vectors", "weighted averages"),
        "definition",
        (
            (r"\vec r_{\mathrm{cm}}", "center-of-mass position"),
            ("m_i", "mass of component i"),
            (r"\vec r_i", "position of component i"),
            (r"\sum_i m_i", "total system mass"),
        ),
        ("component_masses", "component_positions", "total_mass", "center_position"),
        ("mass_markers", "position_axis", "center_of_mass_marker", "balance_indicator"),
    ),
    _model(
        "recoil",
        "physics_recoil",
        r"m_1\vec v_{1f}+m_2\vec v_{2f}=\vec P_i",
        ("momentum conservation", "signed velocity", "system boundaries"),
        "conservation_law",
        (
            ("m_1,m_2", "masses of the separating bodies"),
            (r"\vec v_{1f},\vec v_{2f}", "velocities after separation in one frame"),
            (r"\vec P_i", "total momentum before separation"),
        ),
        ("mass_1", "mass_2", "initial_total_momentum", "final_velocity_1", "final_velocity_2"),
        ("system_boundary", "before_state", "separation_state", "opposite_momentum_arrows", "reference_frame"),
    ),
    _model(
        "relative_velocity",
        "physics_recoil",
        r"\vec v_{A/B}=\vec v_{A/O}-\vec v_{B/O}",
        ("vectors", "reference frames", "velocity"),
        "kinematic_relation",
        (
            (r"\vec v_{A/B}", "velocity of A measured relative to B"),
            (r"\vec v_{A/O}", "velocity of A in reference frame O"),
            (r"\vec v_{B/O}", "velocity of B in the same frame O"),
        ),
        ("object_a_velocity", "object_b_velocity", "common_reference_frame", "relative_velocity"),
        ("object_a", "object_b", "reference_frame", "two_velocity_arrows", "relative_velocity_arrow"),
    ),
    _model(
        "ordinary_differential_equation",
        "physics_ode",
        r"\dot{\vec y}=\vec f(t,\vec y),\quad\vec y(t_0)=\vec y_0",
        ("derivatives", "functions", "initial conditions"),
        "differential_equation",
        (
            (r"\vec y(t)", "time-dependent state"),
            (r"\dot{\vec y}", "instantaneous state derivative"),
            (r"\vec f", "state-evolution rule"),
            ("t_0", "initial time"),
            (r"\vec y_0", "initial state"),
        ),
        ("state", "rate_law", "initial_time", "initial_condition", "evaluation_time"),
        ("time_axis", "state_trajectory", "initial_condition_marker", "slope_indicator"),
    ),
    _model(
        "unit_vector",
        "physics_vector",
        r"\hat u=\frac{\vec u}{\lVert\vec u\rVert}\quad(\vec u\ne\vec0)",
        ("vector components", "Pythagorean theorem", "division"),
        "definition",
        (
            (r"\vec u", "nonzero source vector"),
            (r"\lVert\vec u\rVert", "Euclidean magnitude of the source vector"),
            (r"\hat u", "unit vector in the same direction"),
        ),
        ("vector_components", "vector_magnitude", "normalized_components"),
        ("coordinate_axes", "source_vector", "unit_vector", "magnitude_label"),
    ),
    _model(
        "vectors",
        "physics_vector",
        r"\vec u=u_x\hat i+u_y\hat j,\quad\hat u=\frac{\vec u}{\lVert\vec u\rVert}",
        ("coordinates", "algebra", "geometry"),
        "definition",
        (
            (r"\vec A", "geometric vector"),
            ("A_x,A_y,A_z", "components in the selected basis"),
            (r"\hat i,\hat j,\hat k", "basis unit vectors"),
        ),
        ("vector_components", "coordinate_basis", "magnitude", "direction", "normalized_components"),
        ("coordinate_axes", "vector_arrow", "component_arrows", "magnitude_label", "direction_angle", "unit_vector"),
    ),
    _model(
        "waves",
        "physics_wave",
        r"y(x,t)=A\cos(kx-\omega t+\phi),\quad v=\frac{\omega}{k}=\lambda f",
        ("trigonometry", "periodic motion", "units"),
        "wave_relation",
        (
            ("y(x,t)", "wave displacement at position x and time t"),
            ("A", "amplitude"),
            ("k", "wave number"),
            (r"\omega", "angular frequency"),
            (r"\phi", "phase constant"),
            ("v", "phase speed"),
            (r"\lambda", "wavelength"),
            ("f", "frequency"),
        ),
        ("amplitude", "wavelength", "frequency", "phase", "time"),
        ("equilibrium_axis", "wave_profile", "amplitude_marker", "wavelength_marker", "propagation_arrow"),
    ),
)


# The broad mechanics registry above remains useful for free-form course titles.
# These additional models are the semantic identities needed by the official
# MIT 8.01 outline.  In particular, two units may share mathematical notation
# without sharing a model id, scenario mode, or video route.
_MIT_8_01_ADDITIONAL_MODEL_SPECS: Final[tuple[PhysicsModelSpec, ...]] = (
    _model(
        "kinematics_position_velocity",
        "physics_kinematics",
        r"x(t)=x_0+v_0t+\frac{1}{2}at^2,\quad v(t)=v_0+at",
        ("signed position", "velocity", "constant acceleration"),
        "kinematic_relation",
        (("x(t)", "position at time t"), ("v(t)", "velocity at time t"), ("a", "constant acceleration")),
        ("initial_position", "initial_velocity", "acceleration", "elapsed_time", "final_position", "final_velocity"),
        ("number_line", "moving_particle", "position_graph", "velocity_graph", "shared_clock"),
    ),
    _model(
        "kinematics_acceleration",
        "physics_kinematics",
        r"a=\frac{dv}{dt},\quad v(t)=v_0+at,\quad x(t)=x_0+v_0t+\frac{1}{2}at^2",
        ("velocity", "derivatives", "constant acceleration"),
        "kinematic_relation",
        (("a", "rate of change of velocity"), ("v(t)", "velocity at time t"), ("x(t)", "position at time t")),
        ("initial_position", "initial_velocity", "acceleration", "elapsed_time", "velocity_change"),
        ("number_line", "moving_particle", "velocity_graph", "acceleration_graph", "shared_clock"),
    ),
    _model(
        "newton_laws_of_motion",
        "physics_force",
        r"\sum\vec F_{ext}=m\vec a,\quad\vec F_{A\to B}=-\vec F_{B\to A}",
        ("inertial frames", "vectors", "free-body diagrams"),
        "dynamical_law",
        ((r"\sum\vec F_{ext}", "external-force sum on one body"), (r"\vec a", "that body's acceleration"), (r"\vec F_{A\to B}", "force on B by A")),
        ("masses", "interaction_force", "force_pair", "accelerations", "different_bodies"),
        ("skater_a", "skater_b", "separate_free_body_diagrams", "interaction_pair", "acceleration_arrows"),
    ),
    _model(
        "tension_and_springs",
        "physics_force",
        r"\vec T=T\hat\ell,\quad\vec F_s=-k\vec x,\quad\sum\vec F=m\vec a",
        ("force vectors", "Hooke's law", "Newton's second law"),
        "interaction_law",
        ((r"\vec T", "rope tension along the rope"), (r"\vec F_s", "spring restoring force"), ("k", "spring constant"), (r"\vec x", "spring displacement")),
        ("mass", "tension_force", "spring_constant", "displacement", "spring_force", "acceleration"),
        ("body", "rope", "tension_arrow", "spring", "equilibrium_marker", "restoring_force_arrow"),
    ),
    _model(
        "massive_rope",
        "physics_force",
        r"\frac{dT}{dx}=\lambda a,\quad T(L)-T(0)=Ma",
        ("Newton's second law", "linear mass density", "distributed systems"),
        "dynamical_law",
        (("T(x)", "tension at position x along the rope"), (r"\lambda", "rope mass per unit length"), ("a", "common rope acceleration")),
        ("rope_mass", "rope_length", "trailing_tension", "leading_tension", "tension_gradient", "acceleration"),
        ("massive_rope", "rope_segments", "trailing_tension_arrow", "leading_tension_arrow", "tension_gradient_plot"),
    ),
    _model(
        "continuous_mass_accumulation",
        "physics_mass_transfer",
        r"\frac{dM_{cv}}{dt}=\sum\dot m_{in}-\sum\dot m_{out}",
        ("control volumes", "rates", "mass conservation"),
        "conservation_law",
        ((r"M_{cv}", "mass stored inside the stationary control region"), (r"\dot m_{in}", "inlet mass-flow rate"), (r"\dot m_{out}", "outlet mass-flow rate")),
        ("initial_mass", "inlet_mass_flow", "outlet_mass_flow", "duration", "net_mass_flow", "final_mass"),
        ("fixed_control_volume", "inlet_flux_arrow", "outlet_flux_arrow", "stored_mass_readout", "accumulation_graph"),
    ),
    _model(
        "work_energy_1d",
        "physics_work",
        r"W=Fd,\quad W_{net}=\Delta K",
        ("signed force", "one-dimensional displacement", "kinetic energy"),
        "dynamical_law",
        (("F", "signed force along the path"), ("d", "signed displacement"), ("K", "kinetic energy")),
        ("mass", "initial_speed", "force", "distance", "work", "final_kinetic_energy", "final_speed"),
        ("track", "sled", "force_arrow", "displacement_arrow", "kinetic_energy_meter"),
    ),
    _model(
        "work_energy_multidimensional",
        "physics_work",
        r"W=\vec F\cdot\Delta\vec r,\quad W_{net}=\Delta K",
        ("vectors", "dot products", "kinetic energy"),
        "dynamical_law",
        ((r"\vec F", "force vector"), (r"\Delta\vec r", "displacement vector"), ("K", "kinetic energy")),
        ("mass", "initial_speed", "force_vector", "displacement_vector", "dot_product_work", "final_kinetic_energy", "final_speed"),
        ("coordinate_axes", "puck", "force_vector", "displacement_vector", "projection_marker", "kinetic_energy_meter"),
    ),
    _model(
        "conservative_nonconservative_forces",
        "physics_energy",
        r"W_c=-\Delta U,\quad\Delta(K+U)=W_{nc}",
        ("work", "potential energy", "system boundaries"),
        "conservation_law",
        (("W_c", "work by conservative forces"), (r"\Delta U", "potential-energy change"), (r"W_{nc}", "work by nonconservative forces")),
        ("conservative_force", "nonconservative_force", "displacement", "conservative_work", "nonconservative_work", "mechanical_energy_change"),
        ("body", "path", "conservative_force_arrow", "nonconservative_force_arrow", "potential_store", "dissipation_meter"),
    ),
    _model(
        "potential_energy_configuration",
        "physics_energy",
        r"U_s=\frac{1}{2}kx^2,\quad\vec F=-\nabla U",
        ("conservative force", "configuration", "reference energy"),
        "definition",
        (("U", "potential energy of a configuration"), ("k", "spring constant"), ("x", "displacement from equilibrium")),
        ("mass", "spring_constant", "displacement", "reference_position", "stored_energy", "release_speed"),
        ("block", "spring", "equilibrium_marker", "displacement_marker", "potential_energy_bar", "kinetic_energy_bar"),
    ),
    _model(
        "collision_classification",
        "physics_momentum",
        r"\vec p_i=\vec p_f,\quad K_f=K_i\ \mathrm{(elastic)},\quad K_f<K_i\ \mathrm{(inelastic)}",
        ("linear momentum", "kinetic energy", "isolated systems"),
        "conservation_law",
        ((r"\vec p", "total momentum"), ("K_i", "kinetic energy before collision"), ("K_f", "kinetic energy after collision")),
        ("masses", "initial_velocities", "final_velocities", "momentum_before", "momentum_after", "kinetic_energy_before", "kinetic_energy_after", "classification"),
        ("body_a", "body_b", "before_velocity_arrows", "after_velocity_arrows", "momentum_balance", "kinetic_energy_comparison", "sticking_marker"),
    ),
    _model(
        "rolling_energy_angular_momentum",
        "physics_rotation",
        r"K=\frac12Mv_{cm}^2+\frac12I_{cm}\omega^2,\quad L_{cm}=I_{cm}\omega,\quad v_{cm}=\omega R",
        ("rolling kinematics", "kinetic energy", "angular momentum"),
        "definition",
        (("K", "total rolling kinetic energy"), (r"L_{cm}", "angular momentum about the center of mass"), (r"I_{cm}", "center-of-mass moment of inertia"), (r"\omega", "angular speed")),
        ("mass", "radius", "moment_of_inertia", "center_speed", "angular_speed", "translational_energy", "rotational_energy", "total_kinetic_energy", "angular_momentum_cm"),
        ("rolling_body", "ground", "contact_point", "translation_arrow", "rotation_arrow", "energy_split_meter", "angular_momentum_arrow"),
    ),
)


PHYSICS_MODEL_REGISTRY: Final[Mapping[str, PhysicsModelSpec]] = MappingProxyType(
    {spec.model_id: spec for spec in _MODEL_SPECS + _MIT_8_01_ADDITIONAL_MODEL_SPECS}
)


@dataclass(frozen=True)
class PhysicsTitleContract:
    """Exact official-title identity shared by planning, scenarios, and video."""

    unit_number: int
    exact_title: str
    model_id: str
    scenario_mode: str
    video_route_key: str
    mechanism_ids: tuple[str, ...]

    @property
    def spec(self) -> PhysicsModelSpec:
        return PHYSICS_MODEL_REGISTRY[self.model_id]

    @property
    def canonical_formula(self) -> str:
        return self.spec.canonical_formula

    def as_dict(self) -> dict[str, object]:
        return {
            "unit_number": self.unit_number,
            "exact_title": self.exact_title,
            "model_id": self.model_id,
            "scenario_mode": self.scenario_mode,
            "video_route_key": self.video_route_key,
            "mechanism_ids": list(self.mechanism_ids),
            "canonical_formula": self.canonical_formula,
            "visual_kind": self.spec.visual_kind,
        }


def _title_contract(unit_number: int, title: str, model_id: str, *mechanisms: str) -> PhysicsTitleContract:
    return PhysicsTitleContract(
        unit_number=unit_number,
        exact_title=title,
        model_id=model_id,
        scenario_mode=model_id,
        video_route_key=f"physics:mit-8-01:{unit_number:02d}:{model_id}",
        mechanism_ids=mechanisms or (model_id,),
    )


MIT_8_01_TITLE_CONTRACTS: Final[tuple[PhysicsTitleContract, ...]] = (
    _title_contract(1, "Vectors", "vectors", "vector_normalization"),
    _title_contract(2, "1D Kinematics - Position and Velocity", "kinematics_position_velocity"),
    _title_contract(3, "1D Kinematics - Acceleration", "kinematics_acceleration"),
    _title_contract(4, "2D Kinematics", "kinematics_2d"),
    _title_contract(5, "Newton's Laws of Motion", "newton_laws_of_motion", "force_balance", "action_reaction"),
    _title_contract(6, "Gravity", "gravity_force"),
    _title_contract(7, "Contact Forces", "contact_force", "normal_force", "friction_force"),
    _title_contract(8, "Tension and Springs", "tension_and_springs", "tension", "spring_restoring_force"),
    _title_contract(9, "Circular Motion - Position and Velocity", "circular_position"),
    _title_contract(10, "Uniform Circular Motion", "uniform_circular_motion"),
    _title_contract(11, "Circular Motion \N{EN DASH} Acceleration", "radial_acceleration"),
    _title_contract(12, "Newton's 2nd Law and Circular Motion", "circular_dynamics", "radial_force_balance"),
    _title_contract(13, "Pulleys and Constraints", "pulley_constraint"),
    _title_contract(14, "Massive Rope", "massive_rope", "distributed_mass", "tension_gradient"),
    _title_contract(15, "Resistive Forces", "drag_force"),
    _title_contract(16, "Momentum and Impulse", "impulse_momentum"),
    _title_contract(17, "Conservation of Momentum", "momentum_conservation"),
    _title_contract(18, "Center of Mass and Motion", "center_of_mass"),
    _title_contract(19, "Relative Velocity and Recoil", "recoil", "relative_velocity", "recoil"),
    _title_contract(20, "Continuous Mass Transfer", "continuous_mass_accumulation", "inlet_flux", "outlet_flux", "stored_mass"),
    _title_contract(21, "Kinetic Energy and Work in 1D", "work_energy_1d"),
    _title_contract(22, "Kinetic Energy and Work in 2D and 3D", "work_energy_multidimensional", "dot_product_work"),
    _title_contract(23, "Conservative and Non-Conservative Forces", "conservative_nonconservative_forces", "conservative_work", "nonconservative_work"),
    _title_contract(24, "Potential Energy", "potential_energy_configuration"),
    _title_contract(25, "Conservation of Energy", "energy_conservation"),
    _title_contract(26, "Potential Energy Diagrams", "potential_energy_diagram"),
    _title_contract(27, "Types of Collision", "collision_classification", "momentum_check", "kinetic_energy_classification", "sticking"),
    _title_contract(28, "Elastic Collisions", "elastic_collision"),
    _title_contract(29, "Motion of a Rigid Body", "rigid_body_motion"),
    _title_contract(30, "Moment of Inertia", "moment_of_inertia"),
    _title_contract(31, "Torque", "torque"),
    _title_contract(32, "Rotational Dynamics", "rotational_dynamics"),
    _title_contract(33, "Angular Momentum of a Point Particle", "point_particle_angular_momentum"),
    _title_contract(34, "Angular Momentum of a Rigid Body", "rigid_body_angular_momentum"),
    _title_contract(35, "Torque and Angular Impulse", "angular_impulse"),
    _title_contract(36, "Rolling Kinematics", "rolling_kinematics"),
    _title_contract(37, "Rolling Dynamics", "rolling_dynamics"),
    _title_contract(38, "Rolling Kinetic Energy & Angular Momentum", "rolling_energy_angular_momentum", "rolling_kinetic_energy", "center_of_mass_angular_momentum"),
)


if len(MIT_8_01_TITLE_CONTRACTS) != 38:
    raise RuntimeError("MIT 8.01 title registry must contain exactly 38 units")
if len({row.model_id for row in MIT_8_01_TITLE_CONTRACTS}) != 38:
    raise RuntimeError("every MIT 8.01 title must have a unique model id")
if len({row.video_route_key for row in MIT_8_01_TITLE_CONTRACTS}) != 38:
    raise RuntimeError("every MIT 8.01 title must have a unique video route")


MIT_8_01_TITLE_REGISTRY: Final[Mapping[str, PhysicsTitleContract]] = MappingProxyType(
    {row.exact_title: row for row in MIT_8_01_TITLE_CONTRACTS}
)


_TOKEN_RE: Final[re.Pattern[str]] = re.compile(r"[a-z0-9]+")


def _normalize_words(value: str) -> tuple[str, ...]:
    separated_value = "".join(" " if unicodedata.category(char) == "Pd" else char for char in value)
    ascii_value = unicodedata.normalize("NFKD", separated_value).encode("ascii", "ignore").decode("ascii")
    ascii_value = ascii_value.replace("'", "")
    return tuple(_TOKEN_RE.findall(ascii_value.casefold()))


def _word_matches(actual: str, marker: str) -> bool:
    if actual == marker:
        return True
    if len(marker) <= 2:
        return False
    if marker.endswith("y") and actual == marker[:-1] + "ies":
        return True
    return actual in {marker + "s", marker + "es"}


def _contains_phrase(words: tuple[str, ...], phrase: str) -> bool:
    marker_words = _normalize_words(phrase)
    if not marker_words or len(marker_words) > len(words):
        return False
    width = len(marker_words)
    return any(
        all(_word_matches(actual, marker) for actual, marker in zip(words[start : start + width], marker_words))
        for start in range(len(words) - width + 1)
    )


@dataclass(frozen=True)
class PhysicsModelRule:
    """An ordered title rule; every phrase group must contribute one match."""

    model_id: str
    phrase_groups: tuple[tuple[str, ...], ...]
    excluded_phrases: tuple[str, ...] = ()

    def matches(self, words: tuple[str, ...]) -> bool:
        return all(any(_contains_phrase(words, phrase) for phrase in group) for group in self.phrase_groups) and not any(
            _contains_phrase(words, phrase) for phrase in self.excluded_phrases
        )


def _rule(
    model_id: str,
    *phrase_groups: tuple[str, ...],
    exclude: tuple[str, ...] = (),
) -> PhysicsModelRule:
    return PhysicsModelRule(model_id, phrase_groups, exclude)


# Specific compound models precede every broad family that could absorb them.
PHYSICS_MODEL_RULES: Final[tuple[PhysicsModelRule, ...]] = (
    _rule("rocket_equation", ("rocket equation", "tsiolkovsky equation", "ideal rocket")),
    _rule("continuous_mass_transfer", ("continuous mass transfer", "mass transfer", "mass flow", "momentum flux", "control volume momentum")),
    _rule("center_of_mass", ("center of mass", "centre of mass", "barycenter")),
    _rule("potential_energy_diagram", ("potential energy diagram", "potential energy curve", "energy landscape", "turning point")),
    _rule("rolling_kinetic_energy", ("rolling kinetic energy", "kinetic energy of rolling", "rolling energy")),
    _rule("rolling_angular_momentum", ("rolling angular momentum", "angular momentum of rolling")),
    _rule("rigid_body_angular_momentum", ("gyroscope", "gyroscopes", "gyroscopic precession")),
    _rule("rolling_dynamics", ("rolling dynamics", "dynamics of rolling", "rolling down an incline")),
    _rule("rolling_kinematics", ("rolling kinematics", "rolling without slipping", "pure rolling", "no slip rolling", "rolling motion")),
    _rule("perfectly_inelastic_collision", ("perfectly inelastic collision", "complete inelastic collision", "stick together collision")),
    _rule("inelastic_collision", ("inelastic collision",)),
    _rule("elastic_collision", ("elastic collision",)),
    _rule("point_particle_angular_momentum", ("angular momentum",), ("point particle", "point mass", "single particle", "particle about")),
    _rule("rigid_body_angular_momentum", ("angular momentum",), ("rigid body", "extended body", "solid body", "fixed axis")),
    _rule("angular_impulse", ("angular impulse", "torque impulse", "torque and angular impulse")),
    _rule("moment_of_inertia", ("moment of inertia", "rotational inertia", "mass moment of inertia")),
    _rule("rotational_dynamics", ("rotational dynamics", "rotation dynamics", "torque and angular acceleration")),
    _rule("circular_position", ("circular motion position", "position in circular motion", "orbital position")),
    _rule("circular_position", ("circular", "orbit"), ("position", "phase")),
    _rule("radial_acceleration", ("radial acceleration", "centripetal acceleration", "circular motion acceleration", "inward acceleration")),
    _rule("circular_dynamics", ("circular dynamics", "circular motion dynamics", "centripetal force", "radial force")),
    _rule("circular_dynamics", ("circular", "orbital"), ("dynamics", "force balance", "net force", "force")),
    _rule("uniform_circular_motion", ("uniform circular motion", "constant speed circular motion")),
    _rule("rigid_body_motion", ("rigid body motion", "motion of a rigid body", "rigid motion", "rigid body kinematics", "rigid body rotation", "rotational motion of a rigid body", "rotational kinematics")),
    _rule("projectile_motion", ("projectile motion", "projectile", "ballistic trajectory", "launch angle")),
    _rule("kinematics_2d", ("2d", "2 d", "two dimensional", "two dimension", "motion in two dimensions", "motion in a plane", "plane motion", "planar motion", "plane kinematics", "vector kinematics"), ("kinematics", "motion", "position and velocity")),
    _rule("kinematics_1d", ("1d", "1 d", "one dimensional", "one dimension", "motion in one dimension", "motion on a line"), ("kinematics", "motion", "position and velocity")),
    _rule("spring_potential_energy", ("spring", "elastic"), ("potential energy", "stored energy", "spring energy", "elastic energy")),
    _rule("gravitational_potential_energy", ("gravity", "gravitational"), ("potential energy", "energy change", "energy conservation", "gravitational energy", "gravity energy")),
    _rule("work_energy_theorem", ("work energy theorem", "work and energy", "kinetic energy and work", "net work", "work kinetic energy")),
    _rule("energy_conservation", ("conservation of energy", "energy conservation", "mechanical energy conservation", "potential energy and energy conservation")),
    _rule("spring_force", ("spring force", "hooke law", "hookes law", "spring")),
    _rule("quadratic_drag", ("quadratic drag", "high speed drag")),
    _rule("linear_drag", ("linear drag", "viscous drag", "stokes drag")),
    _rule("drag_force", ("drag force", "drag", "air resistance", "fluid resistance", "resistive force")),
    _rule("action_reaction", ("action reaction", "equal and opposite force", "newtons third law", "newton third law", "third law")),
    _rule("newton_first_law", ("newtons first law", "newton first law", "first law of motion", "law of inertia")),
    _rule("newton_second_law", ("newtons second law", "newton second law", "second law of motion", "f ma")),
    _rule("pulley_constraint", ("pulley", "atwood machine")),
    _rule("tension_force", ("tension force", "rope tension", "string tension", "massive rope", "tension")),
    _rule("contact_force", ("contact force", "contact interaction", "normal force", "friction force", "friction")),
    _rule("gravity_force", ("gravity force", "gravitational force", "weight force", "gravity", "weight")),
    _rule("recoil", ("recoil", "explosion momentum", "separation momentum")),
    _rule("relative_velocity", ("relative velocity", "velocity relative to", "relative motion")),
    _rule("angular_momentum", ("angular momentum", "conservation of angular momentum")),
    _rule("torque", ("torque", "moment of force", "lever arm")),
    _rule("collision_momentum", ("collision", "impact")),
    _rule("momentum_conservation", ("conservation of momentum", "momentum conservation", "conserved momentum")),
    _rule("impulse_momentum", ("impulse momentum", "impulse", "force time")),
    _rule("momentum_definition", ("linear momentum", "momentum")),
    _rule("work_definition", ("mechanical work", "work done", "work")),
    _rule("potential_energy", ("potential energy", "conservative potential")),
    _rule("energy_conservation", ("mechanical energy", "energy")),
    _rule("ordinary_differential_equation", ("ordinary differential equation", "differential equation", "equation of motion", "ode", "initial value problem", "state evolution", "first order decay")),
    _rule("unit_vector", ("unit vector", "vector normalization", "normalized vector", "normalize vector")),
    _rule("waves", ("wave motion", "traveling wave", "wave speed", "wavelength", "frequency and period", "simple harmonic motion", "oscillation", "frequency", "period", "wave", "oscillation and wave")),
    _rule("vectors", ("vector component", "vector addition", "vector", "vectors"), exclude=("matrix vector",)),
    _rule("newton_laws", ("newtons laws", "newton laws", "laws of motion", "newtonian mechanics", "newton")),
    _rule("force_balance", ("free body diagram", "free body", "net force", "force balance", "force", "forces")),
    _rule("uniform_circular_motion", ("circular motion", "orbital motion")),
    _rule("kinematics_1d", ("kinematics", "position and velocity", "position velocity", "trajectory")),
)


@overload
def resolve_physics_model(title: str, fail_closed: Literal[True]) -> PhysicsModelSpec:
    ...


@overload
def resolve_physics_model(title: str, fail_closed: Literal[False] = False) -> Optional[PhysicsModelSpec]:
    ...


@overload
def resolve_physics_model(title: str, fail_closed: bool = False) -> Optional[PhysicsModelSpec]:
    ...


def resolve_physics_model(title: str, fail_closed: bool = False) -> Optional[PhysicsModelSpec]:
    """Resolve explicit model IDs, then exact course titles, then loose aliases."""

    if not isinstance(title, str):
        raise TypeError("title must be a string")
    exact_model = PHYSICS_MODEL_REGISTRY.get(title.strip())
    if exact_model is not None:
        return exact_model
    exact_contract = MIT_8_01_TITLE_REGISTRY.get(title.strip())
    if exact_contract is not None:
        return exact_contract.spec
    words = _normalize_words(title)
    normalized_model_id = "_".join(words)
    exact_normalized_model = PHYSICS_MODEL_REGISTRY.get(normalized_model_id)
    if exact_normalized_model is not None:
        return exact_normalized_model
    for rule in PHYSICS_MODEL_RULES:
        if rule.matches(words):
            return PHYSICS_MODEL_REGISTRY[rule.model_id]
    if fail_closed:
        raise ValueError(
            f"Unsupported physics topic {title!r}: add a mechanics model and a data-driven visual before planning it."
        )
    return None


@overload
def resolve_physics_title_contract(title: str, fail_closed: Literal[True]) -> PhysicsTitleContract:
    ...


@overload
def resolve_physics_title_contract(
    title: str, fail_closed: Literal[False] = False
) -> Optional[PhysicsTitleContract]:
    ...


def resolve_physics_title_contract(
    title: str, fail_closed: bool = False
) -> Optional[PhysicsTitleContract]:
    """Resolve only an official exact title; broad family inference is excluded."""

    if not isinstance(title, str):
        raise TypeError("title must be a string")
    contract = MIT_8_01_TITLE_REGISTRY.get(title.strip())
    if contract is None and fail_closed:
        raise ValueError(f"Unsupported exact MIT 8.01 title: {title!r}")
    return contract


__all__ = [
    "MIT_8_01_TITLE_CONTRACTS",
    "MIT_8_01_TITLE_REGISTRY",
    "PHYSICS_MODEL_REGISTRY",
    "PHYSICS_MODEL_RULES",
    "PHYSICS_VISUAL_KINDS",
    "PhysicsModelRule",
    "PhysicsModelSpec",
    "PhysicsTitleContract",
    "PhysicsVisualKind",
    "StatementKind",
    "SymbolRow",
    "resolve_physics_model",
    "resolve_physics_title_contract",
]
