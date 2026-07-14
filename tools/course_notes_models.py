"""Deterministic, model-bound note content for mechanics and microeconomics.

The public builder in this module does not infer mathematics from a topic
string.  It resolves an immutable model specification, recomputes that
model's registered numerical scenario, and writes learner-facing prose only
from those two sources.  That makes the payload reusable by ``stem_course``
without coupling this module to the notes renderer.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
import math
import re
from typing import Any

try:
    from tools.economics_model_scenarios import build_economics_model_scenario
    from tools.economics_model_specs import resolve_economics_model
    from tools.physics_model_scenarios import build_physics_model_scenario
    from tools.physics_model_specs import resolve_physics_model
except ModuleNotFoundError:  # Direct execution from the tools directory.
    from economics_model_scenarios import build_economics_model_scenario
    from economics_model_specs import resolve_economics_model
    from physics_model_scenarios import build_physics_model_scenario
    from physics_model_specs import resolve_physics_model


_DOMAIN_ALIASES = {
    "mechanics": "physics",
    "physical science": "physics",
    "physics": "physics",
    "econ": "economics",
    "economics": "economics",
    "microeconomics": "economics",
}

_PHYSICS_NOTES_PUBLIC_ALIASES = {
    "continuous mass transfer": "continuous_mass_transfer",
    "mass accumulation": "continuous_mass_accumulation",
    "newton's laws of motion": "newton_laws",
    "potential energy": "potential_energy",
}

_MODEL_DEFINITIONS = {
    "kinematics_position_velocity": "Position locates a particle on a chosen axis, while velocity is the signed rate at which that position changes with time.",
    "kinematics_acceleration": "Acceleration is the signed rate of change of velocity; under constant acceleration it produces a linear velocity change and a quadratic position change.",
    "kinematics_1d": "One-dimensional kinematics describes motion along a chosen axis; position, velocity, and acceleration are signed scalar components on that axis.",
    "kinematics_2d": "Two-dimensional kinematics resolves motion into perpendicular components and combines them into position and velocity vectors.",
    "projectile_motion": "Projectile motion is free motion near Earth's surface when gravity is the only modeled acceleration and air resistance is neglected.",
    "rolling_kinematics": "Rolling without slipping constrains the center-of-mass motion to the angular motion at the contact point.",
    "force_balance": "Force balance is the vector sum of all external forces acting on a clearly specified body or system.",
    "newton_first_law": "Newton's first law identifies inertial motion: a body with zero net external force has constant velocity.",
    "newton_second_law": "Newton's second law relates the net external force on a body to the acceleration of its center of mass.",
    "newton_laws": "Newton's laws connect inertial motion, force-driven acceleration, and reciprocal forces between interacting bodies.",
    "newton_laws_of_motion": "Newton's laws connect the external-force sum on each body to its acceleration and distinguish that balance from equal-and-opposite interaction forces on different bodies.",
    "action_reaction": "An interaction produces equal-magnitude, opposite-direction forces on two different bodies.",
    "gravity_force": "Near Earth's surface, weight is the gravitational force on a mass and points downward in the local vertical direction.",
    "contact_force": "A contact force combines a normal component perpendicular to a surface with any frictional component tangent to it.",
    "tension_force": "Ideal-rope tension is a pulling force directed along the rope away from the body on which it acts.",
    "spring_force": "Hooke's law models an ideal spring as a restoring force proportional to displacement from equilibrium.",
    "tension_and_springs": "Tension acts along a taut rope, while an ideal spring exerts a restoring force opposite its displacement from equilibrium.",
    "massive_rope": "A massive accelerating rope generally has nonuniform tension because each cross section must accelerate a different amount of rope mass.",
    "pulley_constraint": "An ideal inextensible string imposes a fixed-length constraint that links the displacements and accelerations of connected masses.",
    "linear_drag": "Linear drag is a resistive force proportional to velocity and opposite to the direction of motion.",
    "quadratic_drag": "Quadratic drag is a resistive force proportional to speed squared and directed opposite to velocity.",
    "drag_force": "A drag law summarizes the force exerted by a fluid against relative motion through that fluid.",
    "momentum_definition": "Linear momentum is the vector product of a particle's mass and velocity in a specified inertial frame.",
    "impulse_momentum": "Impulse is the time integral of force and equals the resulting change in linear momentum.",
    "momentum_conservation": "Total linear momentum is constant when the net external impulse on the chosen system is zero.",
    "elastic_collision": "An elastic collision conserves both total linear momentum and total kinetic energy.",
    "inelastic_collision": "An inelastic collision conserves total momentum but converts some kinetic energy into other forms.",
    "perfectly_inelastic_collision": "In a perfectly inelastic collision the bodies stick together and share one final velocity.",
    "collision_momentum": "Collision analysis combines momentum balance with an additional impact condition, such as a coefficient of restitution.",
    "collision_classification": "Collision type is determined by comparing total momentum and kinetic energy before and after impact, with sticking identifying the perfectly inelastic case.",
    "work_definition": "Mechanical work is the line integral of the force component along a body's displacement.",
    "work_energy_1d": "In one dimension, signed force times signed displacement transfers energy, and net work equals the change in kinetic energy.",
    "work_energy_multidimensional": "In multiple dimensions, only the component of force along displacement contributes to work, represented by their dot product.",
    "work_energy_theorem": "The net work done on a particle equals its change in kinetic energy.",
    "gravitational_potential_energy": "Near Earth's surface, gravitational potential energy records the reversible energy associated with height relative to a chosen zero level.",
    "spring_potential_energy": "Spring potential energy is the energy stored by an ideal spring displaced from equilibrium.",
    "energy_conservation": "Mechanical energy is conserved when only conservative interactions transfer energy within the chosen system.",
    "conservative_nonconservative_forces": "Conservative work can be represented by a potential-energy change, while nonconservative work changes the system's mechanical energy.",
    "potential_energy_configuration": "Potential energy belongs to a system configuration relative to a chosen reference, and its spatial gradient determines the associated conservative force.",
    "potential_energy": "Potential energy represents a conservative interaction, records configuration relative to a declared reference level, and determines force through its spatial gradient.",
    "potential_energy_diagram": "A potential-energy diagram compares a fixed total energy with the position-dependent potential to locate allowed motion and turning points.",
    "circular_position": "Circular motion represents position by a radius vector of fixed magnitude whose direction changes with angular position.",
    "uniform_circular_motion": "Uniform circular motion has constant speed but changing velocity because the direction of motion continually turns.",
    "radial_acceleration": "Radial acceleration is the inward acceleration required to bend a velocity vector into a circular path.",
    "circular_dynamics": "Circular dynamics identifies the net inward force that supplies radial acceleration; centripetal force is a role, not a new interaction.",
    "rigid_body_motion": "A rigid body is an idealization in which the distance between every pair of material points remains fixed; its instantaneous motion decomposes into translation and rotation.",
    "moment_of_inertia": "Moment of inertia measures how mass is distributed relative to a chosen rotation axis.",
    "torque": "Torque is the moment of a force about a specified origin or axis and depends on the perpendicular lever arm.",
    "rotational_dynamics": "Rotational dynamics relates net torque about an axis to angular acceleration through the moment of inertia.",
    "point_particle_angular_momentum": "A point particle's angular momentum about an origin is the cross product of its position and linear momentum.",
    "rigid_body_angular_momentum": "A rigid body's angular momentum is obtained by applying its inertia tensor to its angular velocity.",
    "angular_momentum": "The angular momentum of a system is the sum of each component's moment of linear momentum about the same origin.",
    "angular_impulse": "Angular impulse is the time integral of external torque and equals the change in angular momentum.",
    "rolling_dynamics": "Rolling dynamics couples center-of-mass translation to rotation, with static friction supplying whatever contact force the no-slip constraint requires.",
    "rolling_kinetic_energy": "A rolling rigid body's kinetic energy is the sum of translational and rotational kinetic energy.",
    "rolling_angular_momentum": "Rolling angular momentum contains orbital motion of the center of mass and spin about the center of mass, both measured about one reference point.",
    "rolling_energy_angular_momentum": "For rolling without slipping, translation and rotation jointly determine kinetic energy and angular momentum while the contact constraint links center speed to angular speed.",
    "continuous_mass_transfer": "A control-volume momentum balance accounts for momentum carried across a boundary by continuously entering and leaving mass.",
    "continuous_mass_accumulation": "A stationary-region mass balance states that stored mass changes at the total inlet mass-flow rate minus the total outlet mass-flow rate.",
    "rocket_equation": "The ideal rocket equation relates velocity gain to exhaust speed and the ratio of initial to final mass.",
    "center_of_mass": "The center of mass is the mass-weighted average position of all components in a system.",
    "recoil": "Recoil is the opposite motion required by momentum conservation when parts of an initially combined system separate.",
    "relative_velocity": "Relative velocity is the difference between two velocities measured in the same reference frame.",
    "ordinary_differential_equation": "An ordinary differential equation specifies how a state changes with one independent variable, usually time, together with an initial condition.",
    "unit_vector": "A unit vector has magnitude one and records direction independently of scale.",
    "vectors": "A vector is determined by its components in a chosen basis, with magnitude and direction following from those components.",
    "waves": "A traveling wave repeats in space and time; its speed equals wavelength times frequency.",
    "supply_demand_intro": "Demand records buyers' desired quantity at each price, while supply records sellers' desired quantity at each price, holding non-price shifters fixed.",
    "market_equilibrium": "A competitive market equilibrium is a price and quantity at which quantity demanded equals quantity supplied.",
    "demand_curve": "A demand curve relates price to quantity demanded while income, tastes, and other demand shifters are held fixed.",
    "supply_curve": "A supply curve relates price to quantity supplied while technology, input prices, and other supply shifters are held fixed.",
    "supply_demand_curves": "A supply-and-demand model places buyers' and sellers' price-quantity relations in one market diagram.",
    "comparative_statics": "Comparative statics compares two equilibria before and after an exogenous primitive changes.",
    "price_ceiling_shortage": "A price ceiling is a legal maximum price; when it binds below equilibrium, quantity demanded exceeds quantity supplied.",
    "price_floor_surplus": "A price floor is a legal minimum price; when it binds above equilibrium, quantity supplied exceeds quantity demanded.",
    "price_controls": "Price controls constrain the market price and can prevent the decentralized quantity from clearing the market.",
    "consumer_preferences": "Consumer preferences rank feasible bundles according to the consumer's tastes, independently of the numerical utility labels used to represent that ranking.",
    "utility_representation": "A utility function assigns numbers that preserve a preference ordering; only the ranking, not the utility units, is economically meaningful.",
    "budget_constraint": "A budget constraint divides bundles into affordable and unaffordable sets at given prices and income.",
    "marginal_rate_of_substitution": "The marginal rate of substitution is the local rate at which a consumer is willing to exchange one good for another along an indifference curve.",
    "consumer_choice": "Constrained consumer choice selects the most preferred affordable bundle at given prices and income.",
    "income_substitution_effects": "A price-induced change in demand can be decomposed into a substitution effect at compensated purchasing power and an income effect.",
    "own_price_elasticity": "Own-price elasticity measures the percentage response of quantity demanded to a one-percent change in the good's own price.",
    "income_elasticity": "Income elasticity measures the percentage response of demand to a one-percent change in income.",
    "cross_price_elasticity": "Cross-price elasticity measures how demand for one good responds to the price of another good.",
    "production_function": "A production function gives the maximum output obtainable from specified inputs under a given technology.",
    "labor_market": "A labor-market equilibrium equates firms' labor demand with workers' labor supply at an equilibrium wage.",
    "labor_input_market": "A competitive firm hires labor until the value of the marginal product of labor equals the wage, subject to an interior solution.",
    "capital_input_market": "A competitive firm rents capital until the value of the marginal product of capital equals its rental price.",
    "factor_input_markets": "Factor demand follows from the marginal revenue products of labor and capital relative to their factor prices.",
    "intertemporal_choice": "Intertemporal choice allocates resources between present and future consumption through saving or borrowing at an interest rate.",
    "cost_curves": "A firm's cost curves separate fixed and variable cost and relate total, average, and marginal cost to output.",
    "perfect_competition": "A perfectly competitive firm takes market price as given and chooses output to maximize profit.",
    "competitive_shutdown": "A competitive firm produces in the short run only when price covers average variable cost at the profit-maximizing output.",
    "monopoly": "A monopolist recognizes that selling more output requires moving down the market demand curve and chooses quantity where marginal revenue equals marginal cost.",
    "marginal_revenue": "Marginal revenue is the change in total revenue from selling one additional unit and lies below price for a downward-sloping demand curve.",
    "price_discrimination": "Price discrimination charges different prices for units or customer groups when resale is limited and willingness to pay differs.",
    "oligopoly": "An oligopoly contains a small number of firms whose optimal decisions depend on rivals' decisions.",
    "oligopoly_collusion": "Collusion coordinates oligopoly output to maximize joint profit, restricting total quantity and raising price relative to the noncooperative Cournot equilibrium.",
    "strategic_game": "A strategic-form game specifies players, available strategies, and a payoff for every strategy profile.",
    "nash_equilibrium": "A Nash equilibrium is a strategy profile in which every player's strategy is a best response to the others.",
    "dominant_strategy": "A dominant strategy gives a player at least as high a payoff as every alternative for each action of the other players.",
    "consumer_surplus": "Consumer surplus is willingness to pay minus expenditure for the units purchased.",
    "producer_surplus": "Producer surplus is revenue above variable opportunity cost for the units sold.",
    "total_surplus": "Total surplus is the sum of consumer and producer surplus generated by completed trades.",
    "welfare_surplus": "Welfare analysis compares feasible allocations using surplus or another explicitly stated social objective.",
    "tax_incidence": "Tax incidence describes how a tax wedge is divided between the price paid by buyers and the price received by sellers.",
    "tax_deadweight_loss": "The deadweight loss of a tax is the surplus from mutually beneficial trades that no longer occur because of the tax wedge.",
    "externality": "An externality creates a gap between private and social marginal costs or benefits because an action affects third parties.",
    "coase_bargaining": "Coasean bargaining asks whether parties can internalize an externality through voluntary exchange when rights are clear and transaction costs are low.",
    "common_resource": "A common resource is rival but difficult to exclude users from, creating incentives for excessive use.",
    "public_good": "A public good is nonrival and nonexcludable, so efficient provision depends on the sum of individual marginal benefits.",
    "international_trade": "Trade at a world price separates domestic consumption from domestic production and creates imports or exports.",
    "tariff": "A tariff on imports raises the domestic price above the world price, reduces imports, creates government revenue, and prevents some mutually beneficial trades.",
    "choice_under_uncertainty": "Choice under uncertainty compares probability-weighted utility across state-contingent outcomes.",
    "social_insurance": "Social insurance pools risk and redistributes resources across states or people while potentially changing incentives.",
    "adverse_selection": "Adverse selection arises when privately known risk affects who enters a contract or insurance pool.",
    "moral_hazard": "Moral hazard arises when coverage changes an action that is costly to observe or contract upon.",
    "equity_efficiency": "Equity concerns the distribution of outcomes, whereas efficiency concerns whether additional mutually beneficial gains remain available.",
    "behavioral_economics": "Behavioral economics studies systematic departures from a benchmark model, such as present bias or inconsistent intertemporal choice.",
    "health_economics": "Health economics studies medical-care demand, insurance, provider incentives, and the distinction between patient prices and social resource costs.",
}

_STRUCTURAL_PROPERTIES = {
    "accounting_identity": "Every term must refer to the same population, period, and accounting boundary before the identity is applied.",
    "behavioral_relation": "The relation is conditional on the shifters held fixed; changing a shifter moves the relation rather than producing movement along it.",
    "best_response_condition": "A best response compares one player's available deviations while the other players' strategies are held fixed.",
    "budget_constraint": "Feasibility is checked before preferences are used; a preferred bundle outside the affordable set cannot be chosen.",
    "classification_rule": "Classification follows the sign or magnitude of the computed statistic and depends on the stated baseline.",
    "comparative_static": "Only the changed primitive and the equilibrium conditions are needed to compare the two static outcomes; the adjustment path is not specified.",
    "conservation_law": "Internal transfers cancel in the system total, whereas an external impulse or flux can change that total.",
    "constitutive_law": "The proportionality law is an idealization with a stated range of validity; outside that range a different response law may be required.",
    "constraint": "Admissible states satisfy the constraint simultaneously, so one constrained variable cannot be chosen independently of the others.",
    "definition": "The defining relation fixes the quantity's meaning and the conventions required to compare its values.",
    "differential_equation": "A differential equation and an initial condition are both needed to select one trajectory from the family of solutions.",
    "dynamical_law": "A dynamical law connects a system's state change to the net interaction or momentum transfer represented in the model.",
    "equilibrium_condition": "An equilibrium requires all relevant conditions to hold at the same candidate price, quantity, or strategy profile.",
    "expected_utility": "Probabilities must be nonnegative and sum to one, and utility curvature determines attitudes toward risk.",
    "geometric_relation": "Signs and components depend on the chosen coordinates, while the underlying geometric vector relation is coordinate independent.",
    "incentive_condition": "The condition compares the payoff from complying with the payoff from a feasible deviation under the same information.",
    "interaction_law": "Each effect is assigned to the body or agent on which it acts before individual or aggregate conditions are formed.",
    "kinematic_relation": "Kinematics describes the geometry of motion; forces enter only when a separate dynamical law is added.",
    "optimality_condition": "An interior first-order condition is not enough by itself: the candidate must be feasible and compared with any boundary or corner alternatives.",
    "policy_wedge": "The policy rule constrains a price or marginal condition, after which the underlying behavioral relations determine quantities and any imbalance.",
    "resource_constraint": "Resources allocated to one use are unavailable for another, so all feasible allocations obey the same aggregate limit.",
    "wave_relation": "Frequency and period describe time repetition, whereas wavelength describes spatial repetition; wave speed links the two.",
    "welfare_measure": "A welfare conclusion depends on the stated surplus or social objective and does not by itself determine how gains are distributed.",
}

_SECOND_RESULT_HEADINGS = {
    "accounting_identity": "Accounting implication",
    "behavioral_relation": "Behavioral implication",
    "best_response_condition": "Best-response condition",
    "budget_constraint": "Feasibility condition",
    "classification_rule": "Classification consequence",
    "comparative_static": "Equilibrium comparison",
    "conservation_law": "Conservation consequence",
    "constitutive_law": "Response implication",
    "constraint": "Constraint consequence",
    "definition": "Computed quantity",
    "differential_equation": "Solution at the evaluation point",
    "dynamical_law": "Dynamical consequence",
    "equilibrium_condition": "Equilibrium condition",
    "expected_utility": "Risk comparison",
    "geometric_relation": "Geometric consequence",
    "incentive_condition": "Incentive implication",
    "interaction_law": "Interaction consequence",
    "kinematic_relation": "Kinematic consequence",
    "optimality_condition": "Feasibility and optimality",
    "policy_wedge": "Policy implication",
    "resource_constraint": "Resource-allocation consequence",
    "wave_relation": "Wave consequence",
    "welfare_measure": "Welfare implication",
}

_SECOND_HEADING_BY_MODEL = {
    "continuous_mass_transfer": "Steady-flow momentum balance",
    "international_trade": "Open-economy quantity identity",
    "nash_equilibrium": "Mutual best responses",
    "potential_energy_diagram": "Allowed-motion condition",
    "production_function": "Cobb-Douglas output and marginal products",
    "rocket_equation": "Mass-ratio consequence",
    "tax_incidence": "Incidence shares",
    "waves": "Wave relations",
    "welfare_surplus": "Efficient quantity and surplus",
}

_STATEMENT_KIND_LABELS = {
    "accounting_identity": "accounting identity",
    "behavioral_relation": "behavioral relation",
    "best_response_condition": "best-response condition",
    "budget_constraint": "budget constraint",
    "classification_rule": "classification rule",
    "comparative_static": "comparative-static relation",
    "conservation_law": "conservation law",
    "constitutive_law": "constitutive law",
    "constraint": "constraint",
    "definition": "definition",
    "differential_equation": "differential equation",
    "dynamical_law": "dynamical law",
    "equilibrium_condition": "equilibrium condition",
    "expected_utility": "expected-utility relation",
    "geometric_relation": "geometric relation",
    "incentive_condition": "incentive condition",
    "interaction_law": "interaction law",
    "kinematic_relation": "kinematic relation",
    "optimality_condition": "optimality condition",
    "policy_wedge": "policy condition",
    "resource_constraint": "resource constraint",
    "wave_relation": "wave relation",
    "welfare_measure": "welfare measure",
}

_DEVELOPMENT_LABELS = {
    "accounting_identity": ("Accounting frame", "Reconciliation", "Boundary check"),
    "behavioral_relation": ("Maintained schedule", "Evaluation", "Shifter check"),
    "best_response_condition": ("Decision frame", "Payoff check", "Deviation check"),
    "budget_constraint": ("Feasible set", "Affordability check", "Budget change"),
    "classification_rule": ("Classification basis", "Threshold check", "Baseline check"),
    "comparative_static": ("Two-state setup", "Initial comparison", "Primitive shift"),
    "conservation_law": ("System boundary", "Balance calculation", "External change"),
    "constitutive_law": ("Response regime", "State evaluation", "Parameter check"),
    "constraint": ("Admissible state", "Constraint check", "Input change"),
    "definition": ("Quantity definition", "Numerical evaluation", "Input response"),
    "differential_equation": ("Initial-value problem", "Trajectory check", "Data change"),
    "dynamical_law": ("System and interactions", "State update", "Forcing change"),
    "equilibrium_condition": ("Joint conditions", "Clearing calculation", "Equilibrium shift"),
    "expected_utility": ("States and probabilities", "Lottery evaluation", "Risk change"),
    "geometric_relation": ("Reference geometry", "Component calculation", "Geometry change"),
    "incentive_condition": ("Available deviations", "Incentive check", "Payoff change"),
    "interaction_law": ("Interacting bodies", "Interaction calculation", "Input change"),
    "kinematic_relation": ("Motion data", "State propagation", "Kinematic change"),
    "optimality_condition": ("Feasible choices", "Candidate check", "Optimum shift"),
    "policy_wedge": ("Policy rule", "Constrained outcome", "Policy change"),
    "resource_constraint": ("Resource limit", "Allocation check", "Endowment change"),
    "wave_relation": ("Wave state", "Phase evaluation", "Wave-parameter change"),
    "welfare_measure": ("Welfare criterion", "Surplus calculation", "Allocation change"),
}

_DEVELOPMENT_TITLES = {
    "accounting_identity": "Reconciling the accounting boundary",
    "behavioral_relation": "Reading a schedule and its held-fixed shifters",
    "best_response_condition": "Checking responses one deviation at a time",
    "budget_constraint": "Constructing and testing the feasible set",
    "classification_rule": "Computing the statistic and applying its threshold",
    "comparative_static": "Comparing two model-consistent states",
    "conservation_law": "Balancing transfers across a chosen system boundary",
    "constitutive_law": "Evaluating the response within its valid regime",
    "constraint": "Solving quantities that must hold simultaneously",
    "definition": "Evaluating the defined quantity",
    "differential_equation": "Selecting and checking the trajectory",
    "dynamical_law": "From net interaction to state change",
    "equilibrium_condition": "Solving the joint equilibrium conditions",
    "expected_utility": "Weighting outcomes across states",
    "geometric_relation": "Resolving the geometry in one reference convention",
    "incentive_condition": "Comparing compliance with a feasible deviation",
    "interaction_law": "Assigning and evaluating the interaction",
    "kinematic_relation": "Propagating the motion state",
    "optimality_condition": "Testing interior and boundary candidates",
    "policy_wedge": "Tracing a policy rule through the market",
    "resource_constraint": "Allocating a fixed resource",
    "wave_relation": "Connecting phase, repetition, and displacement",
    "welfare_measure": "Applying the stated welfare criterion",
}

_QUANTITY_NOTATION = {
    "CS": "CS",
    "PS": "PS",
    "TS": "TS",
    "acceleration": "a",
    "acceleration_vector": r"\vec a",
    "amplitude": "A",
    "angular_acceleration": r"\alpha",
    "angular_impulse": r"\Delta L",
    "angular_momentum_vector": r"\vec L",
    "angular_momentum_z": "L_z",
    "angular_speed": r"\omega",
    "angular_velocity": r"\omega",
    "angular_velocity_vector": r"\vec\omega",
    "allowed_samples": r"\{K(x_j)\geq0\}",
    "absolute_demand_elasticity": r"|\varepsilon_d|",
    "body_relative_distance": r"|\vec r_{P/O}|",
    "buyer_burden": r"\Delta P_b",
    "buyer_price": "P_b",
    "center_position": r"\vec r_{\mathrm{cm}}",
    "chosen_consumption_later": "c_1^*",
    "chosen_consumption_now": "c_0^*",
    "chosen_output": "q^*",
    "chosen_x": "x^*",
    "chosen_y": "y^*",
    "coefficient_of_restitution": "e",
    "column_aa": r"u_C(A,A)",
    "column_ab": r"u_C(A,B)",
    "column_ba": r"u_C(B,A)",
    "column_bb": r"u_C(B,B)",
    "consumer_surplus": "CS",
    "cross_price_elasticity": r"\varepsilon_{xy}",
    "curvature": r"\kappa",
    "delta_velocity": r"\Delta v",
    "demand_intercept": "a_d",
    "demand_slope": "b_d",
    "displacement": r"y(x,t)",
    "displacement_vector": r"\Delta\vec r",
    "duration": r"\Delta t",
    "elapsed_time": "t",
    "employment": "L^*",
    "equilibrium_price": "P^*",
    "efficient_quantity": "Q^*",
    "equilibrium_quantity": "Q^*",
    "equilibrium_wage": "w^*",
    "exhaust_speed": "v_e",
    "expenditure": r"p_xx+p_yy",
    "external_force": r"\vec F_{\mathrm{ext}}",
    "final_angular_momentum": "L_f",
    "final_angular_speed": r"\omega_f",
    "final_kinetic_energy": "K_f",
    "final_mass": "m_f",
    "final_mechanical_energy": "E_f",
    "final_momentum": "p_f",
    "final_position": "x_f",
    "final_position_vector": r"\vec r_f",
    "final_potential_energy": "U_f",
    "final_speed": "v_f",
    "final_total_momentum": "P_f",
    "final_velocity": "v_f",
    "final_velocity_1": "v_{1f}",
    "final_velocity_2": "v_{2f}",
    "final_velocity_vector": r"\vec v_f",
    "floor_energy": "U_{\min}",
    "force_vector": r"\vec F",
    "frequency": "f",
    "gravity": "g",
    "gravitational_field": "g",
    "income": "I",
    "income_elasticity": r"\varepsilon_I",
    "initial_vertical_velocity": "v_{0y}",
    "initial_angular_momentum": "L_i",
    "initial_angular_speed": r"\omega_i",
    "initial_condition": "y_0",
    "initial_height": "h_i",
    "initial_kinetic_energy": "K_i",
    "initial_mass": "m_i",
    "initial_momentum": "p_i",
    "initial_position": "x_0",
    "initial_position_vector": r"\vec r_0",
    "initial_potential_energy": "U_i",
    "initial_speed": "v_0",
    "initial_time": "t_0",
    "initial_total_momentum": "P_i",
    "initial_velocity": "v_0",
    "initial_velocity_vector": r"\vec v_0",
    "interest_rate": "r",
    "labor": "L",
    "labor_input": "L^*",
    "launch_angle": r"\theta",
    "launch_position": r"\vec r_0",
    "lever_arm_vector": r"\vec r",
    "marginal_cost": "MC",
    "marginal_product_capital": "MP_K",
    "marginal_product_labor": "MP_L",
    "marginal_rate_of_substitution": "MRS",
    "marginal_revenue": "MR",
    "market_price": "P",
    "market_quantity": "Q",
    "mass": "m",
    "mass_1": "m_1",
    "mass_2": "m_2",
    "mass_flow_rate": r"\dot m",
    "material_point_velocity": r"\vec v_P",
    "moment_of_inertia": "I_{\mathrm{rot}}",
    "monopoly_price": "P_m",
    "monopoly_quantity": "Q_m",
    "nash_equilibrium_count": "N_{\mathrm{NE}}",
    "net_force": r"\sum\vec F",
    "new_equilibrium_price": "P_1^*",
    "new_equilibrium_quantity": "Q_1^*",
    "new_income": "I_1",
    "new_price": "P_1",
    "new_quantity": "Q_1",
    "normal_force": "N",
    "own_price": "P_x",
    "own_price_elasticity": r"\varepsilon_{x,P_x}",
    "period": "T",
    "position": "x",
    "position_samples": "x_j",
    "position_vector": r"\vec r",
    "potential_samples": "U(x_j)",
    "pre_tax_price": "P_0",
    "price": "P",
    "price_x": "p_x",
    "price_y": "p_y",
    "producer_surplus": "PS",
    "profit": r"\pi",
    "quantity": "Q",
    "quantity_demanded": "Q_d",
    "quantity_supplied": "Q_s",
    "quantity_x": "x",
    "quantity_y": "y",
    "radial_acceleration": "a_r",
    "radius": "R",
    "reference_velocity": r"\vec v_O",
    "relative_position": r"\vec r_{P/O}",
    "relative_speed": "v_{A/B}",
    "relative_velocity": r"\vec v_{A/B}",
    "relative_velocity_vector": r"\vec v_{A/B}",
    "rental_price": "r_K",
    "saving_now": "s_0",
    "seller_burden": r"\Delta P_s",
    "seller_price": "P_s",
    "speed": "v",
    "spring_constant": "k",
    "spring_force": "F_s",
    "supply_intercept": "a_s",
    "supply_elasticity": r"\varepsilon_s",
    "supply_slope": "b_s",
    "tax": "t",
    "tax_wedge": r"P_b-P_s",
    "turning_points": "x_t",
    "time": "t",
    "time_interval": r"\Delta t",
    "total_cost": "TC",
    "total_energy": "E",
    "total_quantity": "Q",
    "total_revenue": "TR",
    "total_surplus": "TS",
    "torque_z": r"\tau_z",
    "utility": "U",
    "utility_share_x": r"\alpha",
    "velocity": "v",
    "velocity_vector": r"\vec v",
    "wage": "w",
    "wave_speed": "v_w",
    "wavelength": r"\lambda",
    "world_price": "P_w",
    "horizontal_velocity": "v_x",
    "gravity_drop": r"\tfrac12gt^2",
    "kinetic_energy_samples": "K(x_j)",
    "largest_nash_total_payoff": r"\max_{s\in NE}\sum_i u_i(s)",
    "row_aa": r"u_R(A,A)",
    "row_ab": r"u_R(A,B)",
    "row_ba": r"u_R(B,A)",
    "row_bb": r"u_R(B,B)",
    "unilateral_deviation_gain_at_aa": r"\Delta u_i(A,A)",
}

_FIGURE_GUIDANCE = {
    "econ_budget": "Read the intercepts as the maximum affordable amount of each good, the slope as the relative price, and the marked bundle as the feasible choice selected by preferences.",
    "econ_curve": "Read each axis as the variable named beside it, and interpret slopes or gaps only through the relation defined for that topic.",
    "econ_elasticity": "Compare percentage changes between the two marked observations; the ratio, not the absolute movement on either axis, determines the elasticity classification.",
    "econ_supply_demand": "Locate the common price-quantity point where the two market relations agree, then distinguish movement along a curve from a shift of the curve itself.",
    "econ_tax_wedge": "The vertical separation between buyer and seller prices is the tax, while the horizontal contraction records the trades displaced by the wedge.",
    "game_payoff": "For each strategy profile, compare one player's payoff across unilateral deviations before marking best responses and mutual best responses.",
    "physics_center_of_mass": "The center marker must lie at the mass-weighted average of the component positions and therefore moves toward the heavier component.",
    "physics_circular": "The velocity is tangent to the path, whereas the radial acceleration and required net force point toward the center.",
    "physics_energy": "Compare the initial and final energy stores on one common scale so that transfers and any nonconservative work can be read directly.",
    "physics_force": "Every arrow begins on the body receiving the force; its direction and label identify the interaction before components are summed.",
    "physics_kinematics": "Read position from the trajectory, velocity tangent to the trajectory, and acceleration from the change in velocity rather than from the direction of travel alone.",
    "physics_momentum": "Place before-and-after momentum vectors in the same frame and compare their vector sum for the chosen system.",
    "physics_ode": "The plotted solution passes through the initial condition, and its local slope agrees with the differential equation at each displayed point.",
    "physics_potential": "Motion is allowed where total energy is at least the potential; intersections mark turning points where kinetic energy vanishes.",
    "physics_recoil": "The oppositely directed momentum arrows add to the initial system momentum, making the sign convention visible.",
    "physics_rocket": "Separate the rocket from the expelled mass and track momentum flux across the moving boundary before reading the rocket's velocity change.",
    "physics_rotation": "Mark the rotation axis, measure perpendicular distances from that axis, and use the indicated right-hand-rule convention for signed angular quantities.",
    "physics_vector": "The component arrows add head-to-tail to the resultant, while the scale and axis directions determine the component signs.",
    "physics_wave": "Measure wavelength between equal-phase points and period between equal-phase times; their ratio gives propagation speed.",
    "physics_work": "Only the component of force tangent to the displacement contributes to the accumulated work along the path.",
}

_MODEL_FIGURE_GUIDANCE = {
    "action_reaction": "Place each member of the force pair on the free-body diagram of the body that receives it; the arrows have equal lengths and opposite directions but never belong to the same force sum.",
    "budget_constraint": "Read the two intercepts as maximum affordable quantities, the slope as the relative price, and the marked candidate only as affordable or unaffordable.",
    "continuous_mass_transfer": "Draw the fixed system boundary with separate inlet arrow and outlet arrow; label each momentum flux as mass-flow rate times signed velocity and show the external-force direction required by their difference.",
    "consumer_preferences": "Compare the two marked bundles through the preference ranking; no budget line or price slope is implied unless one is separately supplied.",
    "externality": "Mark the unregulated quantity where private marginal benefit meets private marginal cost and the efficient quantity where social marginal benefit meets social marginal cost; their horizontal separation is overproduction or underproduction.",
    "income_substitution_effects": "Separate the compensated movement along the original utility level from the remaining movement caused by changed purchasing power.",
    "intertemporal_choice": "Read current consumption on one axis and future consumption on the other; the intertemporal budget slope is determined by the interest rate.",
    "labor_market": "Read the common labor quantity and wage at the intersection of labor demand and labor supply, then distinguish a demand shift from movement along labor supply.",
    "marginal_rate_of_substitution": "Use the tangent to the indifference curve to read the local tradeoff between the two goods.",
    "moment_of_inertia": "Measure each perpendicular radius from the marked axis to its mass element; the contribution grows with the square of that distance.",
    "price_ceiling_shortage": "At the ceiling price, read quantity demanded and quantity supplied from their separate curve intersections; the horizontal distance between them is the shortage.",
    "price_controls": "At each controlled price, read demand and supply separately; excess demand appears as a horizontal shortage gap and excess supply as a horizontal surplus gap.",
    "price_floor_surplus": "At the floor price, read quantity demanded and quantity supplied from their separate curve intersections; the horizontal distance between them is the surplus.",
    "production_function": "Use an output-versus-labor slice fixing \\(K=16\\), or an isoquant map in labor-capital space; the marginal-product tangent is a derivative, not a price.",
    "rigid_body_motion": "Use head-to-tail addition for the reference-point velocity and rotational contribution at the material point.",
    "rocket_equation": "Show the vehicle's initial and final mass states beside the velocity-increment arrow.",
    "rolling_kinematics": "Show the center translation, rotation direction, and instantaneous contact point together; zero contact-point speed is the visible no-slip check.",
    "utility_representation": "Compare the marked bundles by their utility ranking and indifference curves; the numerical utility labels have ordinal meaning only.",
    "uniform_circular_motion": "Show one complete lap, a tangent velocity arrow, and the elapsed-period marker; speed is the path length per period.",
    "waves": "Keep the speed and period marks fixed when only amplitude changes; those invariants remain unchanged.",
    "welfare_surplus": "Mark the efficient intersection, shade consumer surplus above \\(P^*\\) and below \\(MB\\), and producer surplus below \\(P^*\\) and above \\(MC\\).",
}

_MODEL_FIGURE_AXIS = {
    "action_reaction": "Use the same coordinate directions on the two separate free-body diagrams, with each force arrow attached to the body on which that force acts.",
    "continuous_mass_transfer": "Use one signed flow axis for inlet velocity, outlet velocity, momentum-flux arrows, and the net external-force arrow across the fixed control-volume boundary.",
    "moment_of_inertia": r"Measure every \(r_\perp\) from the same marked rotation axis; because \(r_\perp^2\) enters the sum, a signed radius is neither needed nor used.",
    "rolling_kinematics": "Use the surface direction for center translation and the indicated rotation sense for angular quantities, with the contact point marked on the surface.",
}

_MODEL_FIGURE_STATE_LEADS = {
    "budget_constraint": "Label expenditure, slack, intercepts, slope, and the candidate's affordability with",
    "labor_market": "Label the labor-demand/labor-supply intersection with",
    "market_equilibrium": "Label the demand-supply intersection and clearing values with",
    "moment_of_inertia": "Label the mass contributions and total moment of inertia with",
    "monopoly": "Mark the monopoly quantity, demand price, marginal-revenue condition, and profit with",
    "rolling_kinematics": "Label center translation, angular motion, and the contact-point check with",
    "uniform_circular_motion": "Label the lap period and tangential speed with",
}

_MODEL_FIGURE_COMPARISON_ACTIONS = {
    "budget_constraint": "Draw the shifted budget line and highlight",
    "labor_market": "Draw the shifted labor-demand curve and compare",
    "moment_of_inertia": "Move the selected mass to its changed perpendicular radius and update",
    "rolling_kinematics": "Update the radius, center-motion arrows, and contact-point check for",
    "uniform_circular_motion": "Update the lap circumference and period marker for",
}

_VISUAL_FIGURE_AXIS = {
    "physics_center_of_mass": "Every component position and the center marker use the same origin and coordinate scale.",
    "physics_circular": "The radius, tangent, and inward radial direction are marked at the same point on the circular path.",
    "physics_energy": "All energy levels use one vertical scale and one declared zero of potential energy.",
    "physics_force": "Force-arrow components are read against the coordinate axes drawn beside the selected body.",
    "physics_kinematics": "Position, velocity, and acceleration components use the coordinate directions marked beside the trajectory.",
    "physics_momentum": "Before-and-after momentum arrows use one inertial frame, one positive direction, and one vector scale.",
    "physics_ode": "Time is plotted on the horizontal axis and the evolving state on the vertical axis, with the initial point explicitly marked.",
    "physics_potential": "Position is horizontal, energy is vertical, and the potential and total-energy line share one energy reference.",
    "physics_recoil": "Both recoil arrows use one positive axis and a common momentum scale.",
    "physics_rocket": "Mass decreases along the process direction, while exhaust and rocket velocity arrows use the indicated relative directions.",
    "physics_rotation": "The rotation axis, perpendicular distances, and right-hand-rule direction are marked from one reference frame.",
    "physics_vector": "Every component and resultant is drawn in the same basis and vector scale.",
    "physics_wave": "Displacement is vertical, position is horizontal, and the equilibrium line fixes zero displacement.",
    "physics_work": "The path tangent and force direction are shown at the same position so their projection can be read.",
}

_MODEL_CONSISTENCY = {
    "action_reaction": "The two forces have the same force unit and opposite components; each acceleration has units of force divided by its body's mass.",
    "budget_constraint": "Expenditure and budget slack use currency units, each intercept uses units of its good, the slope is a price ratio, and the affordability indicator is dimensionless.",
    "continuous_mass_transfer": r"Each momentum-flux term \(\dot m v\) has dimensions of force, and inlet, outlet, and external-force signs all use the same selected axis.",
    "continuous_mass_accumulation": r"Inlet and outlet rates have units of mass per time, their difference is the storage rate, and multiplying that rate by duration gives a mass change.",
    "moment_of_inertia": r"Every contribution \(m_jr_{\perp,j}^2\) and the total \(I_O\) have units of mass times length squared; the scalar moment of inertia is nonnegative.",
    "price_ceiling_shortage": "Prices use one currency-per-unit measure; demand, supply, and shortage use the same quantity unit; the binding indicator is dimensionless.",
    "price_controls": "Controlled and equilibrium prices use one currency-per-unit measure, shortage and surplus use the market quantity unit, and both binding indicators are dimensionless.",
    "price_floor_surplus": "Prices use one currency-per-unit measure; demand, supply, and surplus use the same quantity unit; the binding indicator is dimensionless.",
    "production_function": r"Output \(q\) has output units, while \(MP_L\) and \(MP_K\) have output per unit of labor and capital; \(\alpha\) is dimensionless.",
    "rolling_kinematics": r"Center displacement has units of length, center speed has units of length per time, and \(R\omega\) has the same speed unit required by no slip.",
    "uniform_circular_motion": r"Period \(T\) has time units, tangential speed has length-per-time units, and both are nonnegative magnitudes.",
    "utility_representation": "Bundle coordinates are quantities of goods, utility labels preserve only order, and the preferred-bundle index identifies the bundle ranked at least as highly.",
    "vectors": "Vector components and magnitude share the vector's physical unit, while the direction angle is dimensionless and reported in degrees.",
    "welfare_surplus": "Marginal benefit and marginal cost use value per unit, their intersection price uses the same vertical unit, and consumer, producer, and total surplus use value units.",
    "work_definition": "Work has energy units because force projected along displacement is integrated over length; its sign records the direction of energy transfer.",
}

_MODEL_PHYSICS_INTERPRETATION = {
    "action_reaction": "The minus sign records opposite force directions on the two bodies; their acceleration magnitudes may differ because their masses differ.",
    "continuous_mass_transfer": "Positive mass-flow rate is a port magnitude; signed velocity and the inlet-minus-outlet convention determine the direction of momentum transfer and external force.",
    "continuous_mass_accumulation": "A positive inlet-minus-outlet rate increases stored mass, while a negative rate decreases it until the nonnegative-storage boundary is reached.",
    "moment_of_inertia": "Moment of inertia is a nonnegative scalar tied to the chosen axis; moving the axis or redistributing mass changes its value.",
    "rolling_kinematics": "Center displacement and speed follow the chosen surface direction, angular signs follow the displayed rotation sense, and zero contact speed expresses no slip.",
    "uniform_circular_motion": "Speed remains tangent and constant in magnitude, while the period is the positive time required for one complete revolution.",
    "work_definition": "Positive work transfers energy through a force component along displacement; a negative value indicates transfer in the opposite sense.",
}

_MODEL_PHYSICS_PROPERTY = {
    "continuous_mass_transfer": r"For steady one-inlet, one-outlet flow with no momentum accumulation, \(\sum F_{\mathrm{ext}}=\dot m(v_{\mathrm{out}}-v_{\mathrm{in}})\).",
    "continuous_mass_accumulation": r"For constant inlet and outlet rates, \(M_{\mathrm{cv}}(t)=M_{\mathrm{cv}}(0)+(\dot m_{\mathrm{in}}-\dot m_{\mathrm{out}})t\).",
    "moment_of_inertia": r"Mass at larger \(r_\perp\) contributes more strongly because distance enters as \(r_\perp^2\).",
    "rolling_kinematics": r"At the no-slip contact, translation and rotation obey \(v_{\mathrm{cm}}=R\omega\); this kinematic constraint does not identify the forces that enforce it.",
}

_ECON_CONDITIONING_BY_MODEL = {
    "budget_constraint": "the stated prices, income, and candidate bundle",
    "externality": "the stated private and social marginal schedules",
    "labor_market": "the stated labor-demand and labor-supply schedules",
    "market_equilibrium": "the stated demand and supply schedules",
    "own_price_elasticity": "the two observed price-quantity points and the stated percentage-change convention",
    "price_ceiling_shortage": "the demand and supply schedules, the legal ceiling, and the rationing environment",
    "price_controls": "the demand and supply schedules, the legal controls, and the rationing environment",
    "price_floor_surplus": "the demand and supply schedules, the legal floor, and any purchase or disposal rule",
    "production_function": "the stated technology, labor and capital inputs, and Cobb-Douglas share parameter",
    "utility_representation": "the stated preference ranking and its chosen utility representation",
    "welfare_surplus": "the stated marginal-benefit and marginal-cost schedules and the total-surplus criterion",
}

_ECON_DISTRIBUTION_INTERPRETATION = {
    "price_ceiling_shortage": "The shortage alone does not identify which buyers obtain the rationed units, so distributional effects require a rationing rule.",
    "price_controls": "Shortage and surplus magnitudes do not determine who trades; distributional conclusions require the allocation rules used under each control.",
    "price_floor_surplus": "The surplus alone does not determine who bears unsold output or whether a government purchaser absorbs it.",
    "tax_incidence": "Buyer and seller burdens describe distribution of the tax wedge; they are distinct from any efficiency loss.",
    "international_trade": "Aggregate gains from trade do not imply that consumers and producers gain by the same amount.",
    "social_insurance": "Transfers and insurance benefits determine who bears costs and receives protection, separately from any efficiency effect.",
    "equity_efficiency": "An efficiency comparison does not determine whether the resulting distribution satisfies an equity criterion.",
}

_ECON_WELFARE_MODELS = {
    "consumer_surplus",
    "producer_surplus",
    "total_surplus",
    "welfare_surplus",
    "tax_deadweight_loss",
    "externality",
    "coase_bargaining",
    "common_resource",
    "public_good",
    "international_trade",
    "social_insurance",
    "equity_efficiency",
    "health_economics",
}

_ECON_DISTRIBUTION_MODELS = {
    "price_ceiling_shortage",
    "price_floor_surplus",
    "price_controls",
    "tax_incidence",
    "international_trade",
    "social_insurance",
    "equity_efficiency",
}

_COMPARISON_FOCUS_BY_MODEL = {
    "continuous_mass_accumulation": "final_mass",
    "continuous_mass_transfer": "external_force",
    "consumer_choice": "chosen_x",
    "international_trade": "imports",
    "nash_equilibrium": "largest_nash_total_payoff",
    "own_price_elasticity": "own_price_elasticity",
    "potential_energy_diagram": "turning_points",
    "price_ceiling_shortage": "shortage",
    "price_controls": "ceiling_shortage",
    "price_floor_surplus": "surplus",
    "production_function": "output",
    "rigid_body_motion": "material_point_velocity",
    "rocket_equation": "delta_velocity",
    "tax_incidence": "buyer_burden",
    "waves": "displacement",
    "welfare_surplus": "efficient_quantity",
}

_COMPARISON_INPUT_BY_MODEL = {
    "continuous_mass_accumulation": "inlet_mass_flow",
    "moment_of_inertia": "perpendicular_distances",
    "own_price_elasticity": "new_price",
    "price_ceiling_shortage": "ceiling_price",
    "price_controls": "ceiling_price",
    "price_floor_surplus": "floor_price",
}

_COMPARISON_HOLDING_BY_KIND = {
    "accounting_identity": "with the accounting boundary and other inputs unchanged",
    "behavioral_relation": "with the remaining shifters unchanged",
    "best_response_condition": "with the other payoff entries unchanged",
    "budget_constraint": "with prices and every other listed input unchanged",
    "classification_rule": "using the same classification rule and other observations",
    "comparative_static": "holding every other exogenous primitive fixed",
    "conservation_law": "with the system boundary and remaining inputs unchanged",
    "constitutive_law": "within the same response regime and with other inputs fixed",
    "constraint": "while the other constrained inputs remain fixed",
    "definition": "using the same definition and leaving other observations unchanged",
    "differential_equation": "with the evolution law and remaining data unchanged",
    "dynamical_law": "with the system and remaining physical inputs unchanged",
    "equilibrium_condition": "with every other model input held constant",
    "expected_utility": "with probabilities and the remaining outcomes unchanged",
    "geometric_relation": "in the same coordinates and with other inputs fixed",
    "incentive_condition": "with the information and remaining payoffs unchanged",
    "interaction_law": "with the interaction specification and other inputs fixed",
    "kinematic_relation": "with the coordinate convention and remaining initial data fixed",
    "optimality_condition": "holding every other primitive constant",
    "policy_wedge": "with the remaining market and policy inputs unchanged",
    "resource_constraint": "with the aggregate resource limit and other inputs fixed",
    "wave_relation": "with the remaining wave parameters unchanged",
    "welfare_measure": "using the same welfare criterion and other inputs",
}

_COMPARISON_HOLDING_BY_MODEL = {
    "continuous_mass_accumulation": "with initial stored mass, outlet rate, duration, and the control-volume boundary unchanged",
    "continuous_mass_transfer": "with inlet velocity, outlet velocity, duration, and the control-volume boundary unchanged",
    "international_trade": "at the same world price and with the supply curve unchanged",
    "production_function": "with labor, capital, and the labor share unchanged",
    "tax_incidence": "with the pre-tax price and both elasticities unchanged",
    "welfare_surplus": "with marginal-cost and marginal-benefit slopes unchanged",
}

_IMPORTANT_INVARIANTS_BY_MODEL = {
    "continuous_mass_accumulation": ("fixed_control_volume",),
    "continuous_mass_transfer": ("mass_flow_is_continuous",),
    "international_trade": ("domestic_supply", "exports"),
    "nash_equilibrium": (
        "nash_equilibrium_count",
        "unilateral_deviation_gain_at_aa",
    ),
    "potential_energy_diagram": ("allowed_samples",),
    "rocket_equation": ("vehicle_mass_decreases",),
    "waves": ("wave_speed", "period"),
}

# Kept only so older private callers of the pre-revision helper still import.
_STATEMENT_FOCUS = _STRUCTURAL_PROPERTIES
_VISUAL_FOCUS = _FIGURE_GUIDANCE

_VISIBLE_SCALAR_FIELDS = (
    "canonical_formula",
    "course_framing",
    "definition",
    "development_title",
    "development",
    "figure_caption",
    "figure_discussion",
)


def _canonical_domain(domain: str) -> str:
    if not isinstance(domain, str):
        raise TypeError("domain must be a string")
    normalized = re.sub(r"[^a-z]+", " ", domain.lower()).strip()
    try:
        return _DOMAIN_ALIASES[normalized]
    except KeyError as exc:
        raise ValueError(
            f"Unsupported notes domain {domain!r}; expected physics or economics"
        ) from exc


def _resolve(topic: str, domain: str) -> tuple[str, Any, Any]:
    if not isinstance(topic, str):
        raise TypeError("topic must be a string")
    if not topic.strip():
        raise ValueError("topic must not be blank")
    canonical_domain = _canonical_domain(domain)
    try:
        if canonical_domain == "physics":
            public_model_id = _PHYSICS_NOTES_PUBLIC_ALIASES.get(
                re.sub(r"\s+", " ", topic.strip().casefold())
            )
            spec = resolve_physics_model(
                public_model_id or topic, fail_closed=True
            )
            scenario = build_physics_model_scenario(spec.model_id)
        else:
            spec = resolve_economics_model(topic, fail_closed=True)
            scenario = build_economics_model_scenario(spec.model_id)
    except ValueError as exc:
        raise ValueError(
            f"Unsupported {canonical_domain} notes topic {topic!r}: {exc}"
        ) from exc
    return canonical_domain, spec, scenario


def _humanize(value: object) -> str:
    text = re.sub(r"[_:]+", " ", str(value))
    text = re.sub(r"\s+", " ", text).strip()
    return text or "value"


def _title(value: object) -> str:
    words = _humanize(value).split()
    small = {"a", "an", "and", "at", "by", "for", "in", "of", "on", "or", "the", "to"}
    rendered = [word if index and word.lower() in small else word[:1].upper() + word[1:] for index, word in enumerate(words)]
    return " ".join(rendered)


def _tex_escape_prose(value: object) -> str:
    text = str(value)
    replacements = {
        "&": r"\&",
        "%": r"\%",
        "#": r"\#",
        "_": r"\_",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


_PROSE_VARIANTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("The defining relation", ("The defining relation", "This definition", "The stated identity", "The model's defining equation")),
    ("The relation", ("The relation", "This equation", "The model condition", "That mathematical relation")),
    ("For the selected body or system", ("For the selected body or system", "After choosing the mechanical system", "With the receiving body isolated", "On the stated system boundary")),
    ("For a concrete evaluation", ("For a concrete evaluation", "In the numerical state", "To evaluate one admissible case", "For the worked parameter values")),
    ("Change only", ("Change only", "Vary just", "Alter no input except", "Hold the other primitives fixed and replace")),
    ("Worked example:", ("Worked example:", "Numerical case:", "Model evaluation:", "Computed state:")),
    ("The calculation", ("The calculation", "Direct evaluation", "Substitution into the model", "The resulting arithmetic")),
    ("This evaluation gives", ("This evaluation gives", "The computed state is", "These substitutions produce", "The resulting outputs are")),
    ("The revised outputs are", ("The revised outputs are", "The comparison state produces", "Re-evaluation yields", "The altered primitive leads to")),
    ("Read each axis as the variable named beside it", ("Read each axis as the variable named beside it", "Use the axis labels to identify the plotted variables", "Interpret coordinates according to their printed quantity labels", "Treat horizontal and vertical coordinates as the named economic quantities")),
    ("Any slope combines those units in the way specified by the model", ("Any slope combines those units in the way specified by the model", "A plotted slope therefore has the model-specific ratio of vertical to horizontal units", "Slope units follow from the quotient of the labeled coordinates", "The governing equation determines how coordinate units combine in a slope")),
    ("Every arrow begins on the body receiving the force", ("Every arrow begins on the body receiving the force", "Draw each interaction arrow from the body on which it acts", "Attach every force vector to its receiving body", "A force arrow is anchored to the object experiencing that interaction")),
    ("Force-arrow components are read against the coordinate axes", ("Force-arrow components are read against the coordinate axes", "Resolve each force using the displayed coordinate directions", "Project the interaction arrows onto the shown axes", "Use the coordinate basis to assign signed force components")),
    ("Mark the rotation axis", ("Mark the rotation axis", "Identify the rotational axis", "Fix the axis of rotation", "Choose and label the angular reference axis")),
    ("Place before-and-after momentum vectors in the same frame", ("Place before-and-after momentum vectors in the same frame", "Compare initial and final momentum arrows in one inertial frame", "Draw both momentum states with a common frame and scale", "Keep the reference frame fixed across the momentum comparison")),
    ("with the system and remaining physical inputs unchanged", ("with the system and remaining physical inputs unchanged", "while preserving the system boundary and all other physical data", "with every unmentioned mechanical input held fixed", "without altering the chosen system or its other parameters")),
    ("holding every other primitive constant", ("holding every other primitive constant", "with all remaining economic primitives fixed", "without changing the model's other exogenous inputs", "conditional on the unchanged primitives")),
    ("Place the worked input-output point and local measures at", ("Place the worked input-output point and local measures at", "Plot the evaluated input-output pair and annotate", "Mark the computed point together with its local quantities at", "Show the numerical model state and local readouts at")),
    ("Add the revised curve or point to compare", ("Add the revised curve or point to compare", "Overlay the comparison state to contrast", "Plot the altered relation or coordinate beside", "Use a second curve or marker to assess")),
    ("An interior first-order condition is not enough by itself", ("An interior first-order condition is not enough by itself", "A first-order interior candidate does not complete the optimization", "Solving the interior marginal condition alone is insufficient", "The interior first-order equation supplies only a candidate")),
    ("the candidate must be feasible and compared with any boundary or corner alternatives", ("the candidate must be feasible and compared with any boundary or corner alternatives", "feasibility and all relevant corner choices still require comparison", "the feasible set and boundary alternatives must also be checked", "confirm feasibility before comparing the candidate with endpoint solutions")),
    ("Any efficiency claim uses the stated surplus or social objective", ("Any efficiency claim uses the stated surplus or social objective", "Efficiency here is judged by the declared surplus or social criterion", "The stated welfare objective supplies the efficiency benchmark", "Interpret efficiency only relative to the model's named social objective")),
    ("the numerical predictions alone do not determine how gains or losses are distributed", ("the numerical predictions alone do not determine how gains or losses are distributed", "these quantities do not by themselves settle incidence across people", "the computed totals leave distributional consequences unresolved", "outcome magnitudes alone cannot identify who receives each gain or loss")),
    ("The rotation axis, perpendicular distances, and right-hand-rule direction are marked from one reference frame", ("The rotation axis, perpendicular distances, and right-hand-rule direction are marked from one reference frame", "One reference frame fixes the axis, lever arms, and signed angular direction", "The drawing uses a common frame for the axis, normal distances, and right-hand-rule orientation", "Axis location, perpendicular offsets, and angular signs share the same reference convention")),
    ("Kinematics describes the geometry of motion", ("Kinematics describes the geometry of motion", "Kinematic relations specify motion geometry", "This kinematic model tracks how the motion state evolves", "The kinematic statement concerns trajectories and their rates")),
    ("Internal transfers cancel in the system total", ("Internal transfers cancel in the system total", "Transfers wholly inside the boundary offset in the aggregate", "Paired internal momentum exchanges sum to zero for the system", "The system total excludes net change from purely internal exchange")),
    ("are descriptive implications conditional on", ("are descriptive implications conditional on", "describe the model outcome given", "are positive predictions maintained under", "follow from the stated primitives together with")),
    ("technology, input prices, demand, and the stated market structure", ("technology, input prices, demand, and the stated market structure", "the specified technology and factor prices within this market environment", "production conditions, demand, factor costs, and market organization", "the maintained technology, input-cost, demand, and conduct assumptions")),
    ("the supply-demand, policy, and institutional primitives stated in the problem", ("the supply-demand, policy, and institutional primitives stated in the problem", "the problem's market schedules, policy rule, and institutional setting", "the declared demand, supply, intervention, and institutional assumptions", "the maintained behavioral curves and policy environment")),
    ("Recheck feasibility and optimality after varying", ("Recheck feasibility and optimality after varying", "Resolve the candidate and its boundaries after changing", "Repeat both the feasibility and objective comparisons for", "Test the interior and corner choices again after altering")),
    ("Check feasibility first, impose the appropriate marginal condition for an interior candidate, and compare boundary choices before reporting", ("Check feasibility first, impose the appropriate marginal condition for an interior candidate, and compare boundary choices before reporting", "Begin with the feasible set, solve the relevant interior marginal equation, and test its boundary alternatives before stating", "Derive an interior candidate from the marginal condition, verify it is feasible, and compare corners to obtain", "Evaluate feasibility and boundary choices alongside the interior optimality condition before concluding")),
    ("Any efficiency conclusion drawn from these outcomes uses the welfare criterion stated in the relation", ("Any efficiency conclusion drawn from these outcomes uses the welfare criterion stated in the relation", "Efficiency conclusions interpret these outcomes through the relation's declared welfare criterion", "The model's welfare rule, rather than the outcomes alone, defines an efficient allocation", "Read efficiency from the stated social criterion applied to these results")),
    ("it does not imply that every participant is better off", ("it does not imply that every participant is better off", "this need not constitute a Pareto improvement for all participants", "some agents may still lose under the efficient aggregate outcome", "aggregate efficiency does not guarantee individual gains")),
    ("in the units named on the two axes", ("in the units named on the two axes", "using the quantities and units printed beside each axis", "according to the horizontal and vertical measurement scales", "with dimensions inherited from the coordinate labels")),
    ("interpret slopes or gaps only through the relation defined for that topic", ("interpret slopes or gaps only through the relation defined for that topic", "read slopes and separations according to this model's economic equation", "give geometric distances meaning through the governing market relation", "connect each slope or gap to the named behavioral condition")),
    ("Keep the selected system fixed and vary", ("Keep the selected system fixed and vary", "Preserve the system boundary while changing", "Hold the chosen body definition constant and alter", "Use the same mechanical system but adjust")),
    ("A dynamical law connects a system's state change to the net interaction or momentum transfer represented in the model", ("A dynamical law connects a system's state change to the net interaction or momentum transfer represented in the model", "Dynamics relates evolution of the chosen state to its net interactions or momentum flux", "The system changes state in response to the aggregate interaction or momentum transfer in its balance law", "Net forces or momentum transport determine the state evolution described by a dynamical equation")),
    ("The horizontal axis measures quantity and the vertical axis measures price", ("The horizontal axis measures quantity and the vertical axis measures price", "Quantity runs horizontally while price is read vertically", "Read market quantity on the horizontal coordinate and price on the vertical coordinate", "The diagram places quantity along the abscissa and price along the ordinate")),
    ("The relation is conditional on the shifters held fixed", ("The relation is conditional on the shifters held fixed", "This behavioral schedule assumes its non-axis determinants remain fixed", "The curve is defined for maintained values of its background shifters", "Interpreting the relation requires holding its exogenous determinants constant")),
    ("changing a shifter moves the relation rather than producing movement along it", ("changing a shifter moves the relation rather than producing movement along it", "altering one of those determinants shifts the schedule instead of changing the coordinate on a fixed schedule", "a new shifter value creates a different relation, not a movement along the original one", "movement along the curve changes its axis variable whereas a shifter relocates the curve")),
    ("The comparison inputs are", ("The comparison inputs are", "For the altered state, use", "The second evaluation takes", "Recompute with the input list")),
    ("are conditional predictions, not interpersonal welfare comparisons", ("are conditional predictions, not interpersonal welfare comparisons", "are positive model outputs rather than comparisons of utility across people", "describe conditional behavior and do not rank welfare between individuals", "follow from the primitives without making an interpersonal welfare judgment")),
    ("Verify the derivation by checking the units and reference conventions for", ("Verify the derivation by checking the units and reference conventions for", "Audit dimensions and reference choices before accepting", "Confirm the calculation uses compatible units and declared reference choices for", "Check dimensional consistency and coordinate conventions throughout", "Validate units, signs, and reference levels for", "Recheck the algebra against the measurement conventions governing", "Use dimensional and reference-frame checks to verify", "Test the calculation's unit and coordinate consistency for")),
    ("A sign, feasibility, boundary, or accounting check on", ("A sign, feasibility, boundary, or accounting check on", "An admissibility and boundary review of", "A physical consistency test applied to", "A limiting-case and sign check for", "A feasibility audit of", "A boundary-condition review centered on", "A units-and-admissibility check of", "An independent consistency check for")),
    ("without feeding those outputs back as assumptions", ("without feeding those outputs back as assumptions", "while keeping derived values out of the premise set", "and do not reuse consequences as initial data", "with outputs reserved for conclusions rather than hypotheses", "without treating computed consequences as primitives", "while maintaining the distinction between data and predictions", "and keep inferred quantities separate from assumptions", "without circularly assuming the values being derived")),
    ("A one-input sensitivity check preserves the model structure while testing", ("A one-input sensitivity check preserves the model structure while testing", "Varying one primitive isolates the response of", "The comparison retains the governing relation and probes", "A controlled input change reveals the sensitivity of", "Holding other data fixed identifies the response in", "The boundary example changes one datum to examine", "One-at-a-time variation tests the dependence of", "A single-parameter comparison keeps the model intact and evaluates")),
    ("should agree with the model condition before interpretation", ("should agree with the model condition before interpretation", "must satisfy the governing condition before physical interpretation", "needs to match the model constraint before drawing conclusions", "should pass the defining balance prior to interpretation", "must remain consistent with the stated relation before analysis", "should obey the model's admissibility rule before interpretation", "needs confirmation against the governing equation before discussion", "must clear the model-specific check before its meaning is assessed")),
    ("Coordinates, reference levels, and units remain fixed throughout the evaluation", ("Coordinates, reference levels, and units remain fixed throughout the evaluation", "Use one coordinate system, reference level, and unit convention for the entire calculation", "The evaluation keeps its origin, measurement units, and reference values unchanged", "All quantities share the declared coordinates, units, and reference choices", "Fix the coordinate basis, zero levels, and measurement system before calculating", "The stated origin, units, and reference levels govern every evaluated quantity", "Do not change coordinate or measurement conventions between setup and result", "One consistent basis, reference level, and unit system applies throughout")),
    ("The selected body or system is evaluated in one inertial frame with all modeled external interactions included", ("The selected body or system is evaluated in one inertial frame with all modeled external interactions included", "Choose one body and inertial frame, then include every modeled external interaction on it", "The force or motion balance uses a fixed system observed from one inertial frame", "Evaluate the declared system in one inertial frame and account for its external interactions", "Keep the body definition and inertial observer fixed while assembling the interaction model", "One inertial frame governs the selected system and its complete external-force inventory", "The calculation holds its system boundary and inertial frame constant across all interactions", "Specify the body and inertial observer once, including each modeled external influence")),
    ("feasibility conditions, and relevant limiting behavior", ("feasibility conditions, and relevant limiting behavior", "admissibility requirements, plus the appropriate limiting case", "physical constraints and a useful boundary limit", "allowed-value conditions together with limiting behavior", "the valid domain and an informative edge case", "model constraints and the expected asymptotic or boundary response", "admissibility criteria and a diagnostic limit", "physical feasibility along with a relevant limiting check")),
    ("A force arrow represents one interaction on the selected body and must not be duplicated when components are taken", ("A force arrow represents one interaction on the selected body and must not be duplicated when components are taken", "Each arrow denotes a distinct interaction acting on the chosen body; resolve it into components only once", "Draw one vector per external interaction, then project that same vector onto the coordinate axes", "The free-body diagram assigns every interaction to its receiving body before resolving directions", "Count each modeled force once on the selected object and use its components only in the vector sum", "An interaction arrow belongs to the body it acts upon and contributes a single vector to the balance", "Keep the force inventory distinct from its coordinate decomposition so no interaction is counted twice", "Identify each external force on the body first, then calculate its signed axis components")),
    ("The defining relation fixes the quantity's meaning and the conventions required to compare its values", ("The defining relation fixes the quantity's meaning and the conventions required to compare its values", "The equation defines the measured quantity together with the convention used for comparisons", "This definition establishes both the quantity and the reference needed to evaluate it", "The stated formula determines what is measured and how two values may be compared", "Its defining equation supplies the quantity's interpretation and measurement convention", "Read the quantity and its comparison rule directly from the declared definition", "The model definition specifies the object of measurement and its governing conventions", "This relation identifies the quantity while fixing the basis for numerical comparison")),
    ("From net interaction to state change", ("From net interaction to state change", "How interactions determine motion", "Force balance and state evolution", "Tracing external influence into response", "Dynamics of the selected system", "Connecting interaction totals to acceleration", "Mechanical response under applied interactions", "State change from the governing balance")),
    ("use the axes and force units shown on the free-body diagram", ("use the axes and force units shown on the free-body diagram", "follow the coordinate directions and force scale declared by the free-body diagram", "share the signed basis and force units marked beside the body", "are measured with the diagram's coordinate and force conventions", "refer to the displayed axes and one consistent force unit", "inherit their signs and units from the labeled free-body construction", "use one coordinate basis and the interaction units stated in the setup", "are interpreted through the axis directions and measurement scale on the diagram")),
)


def _diversify_learner_prose(value: object, seed: str) -> object:
    """Paraphrase shared scaffolds deterministically without changing model data."""

    digest = hashlib.sha256(seed.encode("utf-8")).digest()

    def rewrite(text: str) -> str:
        result = text
        ordered_variants = sorted(_PROSE_VARIANTS, key=lambda row: len(row[0]), reverse=True)
        for offset, (phrase, variants) in enumerate(ordered_variants):
            choice = variants[digest[offset % len(digest)] % len(variants)]
            result = result.replace(phrase, choice)
            result = result.replace(phrase[:1].lower() + phrase[1:], choice[:1].lower() + choice[1:])
        return result

    if isinstance(value, str):
        return rewrite(value)
    if isinstance(value, list):
        return [_diversify_learner_prose(item, seed) for item in value]
    if isinstance(value, dict):
        return {key: _diversify_learner_prose(item, seed) for key, item in value.items()}
    return value


def _model_reading_observations(
    spec: Any,
    symbols: Sequence[Mapping[str, str]],
    setup_names: Sequence[str],
    result_names: Sequence[str],
) -> list[str]:
    """Build model-specific interpretation from registry vocabulary and state fields."""

    model_name = _humanize(spec.model_id)
    setup_cycle = list(setup_names) or ["input"]
    result_cycle = list(result_names) or ["output"]
    observations: list[str] = []
    for index, row in enumerate(symbols[:4]):
        input_name = _quantity_name(setup_cycle[index % len(setup_cycle)])
        output_name = _quantity_name(result_cycle[index % len(result_cycle)])
        observations.append(
            f"{model_name.title()} uses \({row['symbol']}\) for {_tex_escape_prose(row['meaning'])}. "
            f"In {model_name}, connect {input_name} to {output_name} through that symbol's role."
        )
    tokens = [
        rf"\({token}\)" if re.search(r"[\\^_{}]", token) else _humanize(token)
        for token in spec.required_figure_tokens
    ]
    for index, token in enumerate(tokens[:4]):
        companion = tokens[(index + 1) % len(tokens)]
        output_name = _quantity_name(result_cycle[index % len(result_cycle)])
        observations.append(
            f"The {model_name} picture pairs {token} with {companion}. "
            f"That {model_name} pairing makes the interpretation of {output_name} directly checkable."
        )
    return observations


def _format_number(value: float) -> str:
    if not math.isfinite(value):
        raise ValueError("scenario values must be finite")
    if abs(value) < 5e-13:
        return "0"
    if math.isclose(value, round(value), rel_tol=0.0, abs_tol=1e-10):
        return str(int(round(value)))
    magnitude = abs(value)
    if magnitude >= 1e5 or magnitude < 1e-4:
        return f"{value:.4g}"
    return f"{value:.6g}"


def _format_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return _format_number(float(value))
    if isinstance(value, Mapping):
        return "{" + ", ".join(
            f"{_humanize(key)}: {_format_value(child)}" for key, child in value.items()
        ) + "}"
    if isinstance(value, (tuple, list)):
        return "(" + ", ".join(_format_value(child) for child in value) + ")"
    return _tex_escape_prose(value)


def _math_value(value: object) -> str:
    if isinstance(value, bool):
        return r"\mathrm{true}" if value else r"\mathrm{false}"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return _format_number(float(value))
    if isinstance(value, Mapping):
        return r"\left\{" + ", ".join(
            rf"\mathrm{{{_tex_escape_prose(_humanize(key))}}}:{_math_value(child)}"
            for key, child in value.items()
        ) + r"\right\}"
    if isinstance(value, (tuple, list)):
        return r"\left(" + ", ".join(_math_value(child) for child in value) + r"\right)"
    return rf"\mathrm{{{_tex_escape_prose(value)}}}"


def _quantity_name(key: str) -> str:
    boolean_names = {
        "bodies_separate": "whether the bodies separate",
        "bodies_stick": "whether the bodies stick together",
        "different_bodies": "whether the paired forces act on different bodies",
        "direction_is_inward": "whether the direction is inward",
        "kinetic_energy_conserved": "whether kinetic energy is conserved",
        "mass_flow_is_continuous": "whether mass flow is continuous",
        "no_slip_satisfied": "whether the no-slip condition is satisfied",
        "opposes_velocity": "whether the force opposes velocity",
        "point_particle_model": "whether the point-particle approximation applies",
        "trajectory_is_parabolic": "whether the trajectory is parabolic",
        "vehicle_mass_decreases": "whether vehicle mass decreases",
    }
    if key in boolean_names:
        return boolean_names[key]
    notation = _QUANTITY_NOTATION.get(key)
    if notation:
        return rf"\({notation}\)"
    return _humanize(key)


def _boolean_statement(key: str, value: bool) -> str:
    positive = {
        "bodies_separate": "the bodies separate",
        "bodies_stick": "the bodies stick together",
        "different_bodies": "the paired forces act on different bodies",
        "direction_is_inward": "the direction is inward",
        "kinetic_energy_conserved": "kinetic energy is conserved",
        "mass_flow_is_continuous": "the mass flow is continuous",
        "no_slip_satisfied": "the no-slip condition is satisfied",
        "opposes_velocity": "the force opposes the velocity",
        "point_particle_model": "the point-particle approximation applies",
        "trajectory_is_parabolic": "the trajectory is parabolic",
        "vehicle_mass_decreases": "the vehicle mass decreases",
    }.get(key, f"{_humanize(key)} holds")
    if value:
        return positive
    negations = {
        "the bodies separate": "the bodies do not separate",
        "the bodies stick together": "the bodies do not stick together",
        "the paired forces act on different bodies": "the forces are not assigned to different bodies",
        "the direction is inward": "the direction is not inward",
        "kinetic energy is conserved": "kinetic energy is not conserved",
        "the mass flow is continuous": "the mass flow is not continuous",
        "the no-slip condition is satisfied": "the no-slip condition is not satisfied",
        "the force opposes the velocity": "the force does not oppose the velocity",
        "the point-particle approximation applies": "the point-particle approximation does not apply",
        "the trajectory is parabolic": "the trajectory is not parabolic",
        "the vehicle mass decreases": "the vehicle mass does not decrease",
    }
    return negations.get(positive, f"{_humanize(key)} does not hold")


def _uses_plural_verb(key: str, value: object) -> bool:
    plural_suffixes = (
        "_components",
        "_contributions",
        "_momenta",
        "_points",
        "_samples",
        "_terms",
        "_velocities",
    )
    return key.endswith(plural_suffixes) or key in {
        "accelerations",
        "allowed_samples",
        "force_pair",
        "normalized_components",
        "turning_points",
    }


def _assignment(key: str, value: object) -> str:
    if isinstance(value, bool):
        return _boolean_statement(key, value)
    notation = _QUANTITY_NOTATION.get(key)
    if notation:
        return rf"\({notation}={_math_value(value)}\)"
    label = _tex_escape_prose(_humanize(key))
    return rf"\(\text{{{label}}}={_math_value(value)}\)"


def _assignment_list(values: Mapping[str, object], *, limit: int | None = None) -> str:
    rows = list(values.items())
    if limit is not None:
        rows = rows[:limit]
    return _oxford([_assignment(key, value) for key, value in rows])


def _quantity_list(keys: Sequence[str]) -> str:
    return _oxford([_quantity_name(key) for key in keys])


def _concept_title(topic: str, model_id: str) -> str:
    candidate = re.sub(r"[\N{EN DASH}\N{EM DASH}]", " - ", topic).strip()
    candidate = re.sub(
        r"^(?:lec(?:ture)?|lecture summary|lesson)\s+[ivxlcdm0-9]+\s*:\s*",
        "",
        candidate,
        flags=re.IGNORECASE,
    ).strip()
    prefix_match = re.match(
        r"^(?:lec(?:ture)?|lecture summary|lesson)\s+[ivxlcdm0-9]+\s*-\s*(.+)$",
        candidate,
        flags=re.IGNORECASE,
    )
    if prefix_match:
        candidate = prefix_match.group(1).strip()
    if "_" in candidate or not candidate:
        candidate = _title(model_id)
    return candidate


def _change_phrase(key: str, old: object, new: object) -> str:
    if isinstance(old, bool) and isinstance(new, bool):
        return f"{_boolean_statement(key, old)} becomes {_boolean_statement(key, new)}"
    notation = _QUANTITY_NOTATION.get(key)
    if notation:
        return rf"\({notation}:{_math_value(old)}\longrightarrow{_math_value(new)}\)"
    return (
        f"{_humanize(key)} changes from \\({_math_value(old)}\\) "
        f"to \\({_math_value(new)}\\)"
    )


def _comparison_summary(
    changed_key: str,
    old_value: object,
    new_value: object,
    before: Mapping[str, object],
    after: Mapping[str, object],
) -> str:
    changes = _changed_values(before, after)
    direction = "Changing"
    if (
        isinstance(old_value, (int, float))
        and not isinstance(old_value, bool)
        and isinstance(new_value, (int, float))
        and not isinstance(new_value, bool)
    ):
        direction = "Raising" if float(new_value) > float(old_value) else "Lowering"
    primitive = _quantity_name(changed_key)
    outcomes = _oxford([_change_phrase(key, old, new) for key, old, new in changes])
    return (
        f"{direction} {primitive} from \\({_math_value(old_value)}\\) to "
        f"\\({_math_value(new_value)}\\), with the other primitives fixed, gives {outcomes}."
    )


def _transition_clause(key: str, old: object, new: object) -> str:
    return (
        f"{_quantity_name(key)} from \\({_math_value(old)}\\) "
        f"to \\({_math_value(new)}\\)"
    )


def _comparison_analysis(
    model_id: str,
    statement_kind: str,
    changed_key: str,
    old_value: object,
    new_value: object,
    before: Mapping[str, object],
    after: Mapping[str, object],
) -> dict[str, object]:
    changes = _changed_values(before, after)
    if not changes:
        raise RuntimeError(f"comparison for {model_id!r} changes no result")
    changed_keys = [key for key, _old, _new in changes]
    preferred = _COMPARISON_FOCUS_BY_MODEL.get(model_id)
    focus_key = preferred if preferred in changed_keys else changed_keys[0]
    focus_change = next(row for row in changes if row[0] == focus_key)
    other_changes = [row for row in changes if row[0] != focus_key]
    invariants = [key for key in before if key in after and before[key] == after[key]]

    if (
        isinstance(old_value, (int, float))
        and not isinstance(old_value, bool)
        and isinstance(new_value, (int, float))
        and not isinstance(new_value, bool)
    ):
        input_verb = "Raising" if float(new_value) > float(old_value) else "Lowering"
    else:
        input_verb = "Changing"
    holding_clause = _COMPARISON_HOLDING_BY_MODEL.get(
        model_id,
        _COMPARISON_HOLDING_BY_KIND.get(
            statement_kind, "with every other listed input fixed"
        ),
    )
    text_parts = [
        f"{input_verb} {_quantity_name(changed_key)} from \\({_math_value(old_value)}\\) to "
        f"\\({_math_value(new_value)}\\), {holding_clause}, changes "
        f"{_transition_clause(*focus_change)}."
    ]
    if other_changes:
        text_parts.append(
            f"It also changes {_oxford([_transition_clause(*row) for row in other_changes])}."
        )

    requested_invariants = _IMPORTANT_INVARIANTS_BY_MODEL.get(model_id, ())
    described_invariants = [key for key in requested_invariants if key in invariants]
    if not described_invariants and len(invariants) <= 2:
        described_invariants = invariants
    if described_invariants:
        invariant_clauses = []
        for key in described_invariants:
            value = before[key]
            if key == "allowed_samples":
                invariant_clauses.append(
                    "the allowed/forbidden classification of the sampled positions remains unchanged"
                )
            elif isinstance(value, bool):
                invariant_clauses.append(f"{_boolean_statement(key, value)} in both cases")
            else:
                invariant_clauses.append(f"{_assignment(key, value)} remains unchanged")
        text_parts.append(f"Meanwhile, {_oxford(invariant_clauses)}.")

    payload: dict[str, object] = {
        "changed_input": changed_key,
        "focus_output": focus_key,
        "changed_outputs": changed_keys,
        "invariant_outputs": invariants,
        "described_changed_outputs": changed_keys,
        "described_invariant_outputs": described_invariants,
        "before": dict(before),
        "after": dict(after),
        "text": " ".join(text_parts),
    }
    return payload


def _mapping(value: object) -> dict[str, object]:
    if isinstance(value, Mapping):
        return {str(key): child for key, child in value.items()}
    as_dict = getattr(value, "as_dict", None)
    if callable(as_dict):
        exported = as_dict()
        if isinstance(exported, Mapping):
            return {str(key): child for key, child in exported.items()}
    raise TypeError(f"expected a mapping-compatible scenario field, got {type(value).__name__}")


def _pairs_text(values: Mapping[str, object], *, limit: int | None = None) -> str:
    pairs = list(values.items())
    if limit is not None:
        pairs = pairs[:limit]
    return "; ".join(
        f"{_humanize(key)} = {_format_value(value)}" for key, value in pairs
    )


def _oxford(items: Sequence[str]) -> str:
    clean = [item for item in items if item]
    if not clean:
        return "the stated quantities"
    if len(clean) == 1:
        return clean[0]
    if len(clean) == 2:
        return f"{clean[0]} and {clean[1]}"
    return f"{', '.join(clean[:-1])}, and {clean[-1]}"


def _scenario_parts(domain: str, scenario: Any) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    setup = _mapping(scenario.setup)
    if domain == "physics":
        calculation = _mapping(scenario.calculation)
        result = _mapping(scenario.result)
    else:
        calculation = {}
        result = _mapping(scenario.results)
    return setup, calculation, result


def _changed_values(
    before: Mapping[str, object], after: Mapping[str, object]
) -> list[tuple[str, object, object]]:
    changes: list[tuple[str, object, object]] = []
    for key in before:
        if key in after and before[key] != after[key]:
            changes.append((key, before[key], after[key]))
    return changes


def _candidate_values(value: object) -> tuple[object, ...]:
    if isinstance(value, bool):
        return (not value,)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        number = float(value)
        if not math.isfinite(number):
            return ()
        if math.isclose(number, 0.0, abs_tol=1e-12):
            return (1.0, -1.0, 0.5)
        sign = 1.0 if number > 0 else -1.0
        return (number * 1.25, number * 0.75, number * 0.5, number + sign, 0.0)
    if isinstance(value, (tuple, list)) and value:
        first = value[0]
        if isinstance(first, (int, float)) and not isinstance(first, bool):
            candidates = []
            for replacement in _candidate_values(first):
                changed = list(value)
                changed[0] = replacement
                candidates.append(changed)
            return tuple(candidates)
        nested_candidates = _candidate_values(first)
        if nested_candidates:
            candidates = []
            for replacement in nested_candidates:
                changed = list(value)
                changed[0] = replacement
                candidates.append(changed)
            return tuple(candidates)
    return ()


def _comparison_scenario(scenario: Any) -> tuple[Any, str, object, object]:
    setup = _mapping(scenario.setup)
    base_result = _mapping(scenario.result if hasattr(scenario, "result") else scenario.results)
    preferred_key = _COMPARISON_INPUT_BY_MODEL.get(scenario.model_id)
    ordered_keys = list(setup)
    if preferred_key in setup:
        ordered_keys.remove(preferred_key)
        ordered_keys.insert(0, preferred_key)
    for key in ordered_keys:
        old_value = setup[key]
        for candidate in _candidate_values(old_value):
            if candidate == old_value:
                continue
            try:
                rebuilt = scenario.rebuild({key: candidate})
            except (KeyError, TypeError, ValueError, ZeroDivisionError, OverflowError):
                continue
            rebuilt_result = _mapping(
                rebuilt.result if hasattr(rebuilt, "result") else rebuilt.results
            )
            if rebuilt_result != base_result:
                return rebuilt, key, old_value, candidate
    raise RuntimeError(f"No valid comparison scenario for model {scenario.model_id!r}")


def _source_evidence(
    contexts: Sequence[str],
    *,
    title: str,
    vocabulary: Sequence[str],
) -> tuple[list[dict[str, object]], str]:
    if isinstance(contexts, (str, bytes)):
        raise TypeError("source_contexts must be a sequence of strings")
    safe_terms: list[str] = []
    digests: list[dict[str, object]] = []
    vocabulary_rows = [term for term in vocabulary if str(term).strip()]
    for context in contexts:
        if not isinstance(context, str):
            raise TypeError("each source context must be a string")
        normalized = re.sub(r"[^a-z0-9]+", " ", context.lower()).strip()
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        matched: list[str] = []
        context_words = set(normalized.split())
        for term in vocabulary_rows:
            term_words = set(re.sub(r"[^a-z0-9]+", " ", str(term).lower()).split())
            if term_words and term_words.issubset(context_words):
                matched.append(_humanize(term))
                if _humanize(term) not in safe_terms:
                    safe_terms.append(_humanize(term))
        # A hash proves identity, not relevance. Keep evidence only when the
        # excerpt overlaps vocabulary from the resolved model.
        if matched:
            digests.append(
                {
                    "sha256": digest,
                    "word_count": len(normalized.split()),
                    "matched_model_terms": matched,
                }
            )
    return digests, ""


def _state_rows(scenario: Any) -> list[dict[str, object]]:
    return [state.as_dict() for state in scenario.animation_states]


def _figure_data(domain: str, scenario: Any) -> tuple[list[str], list[str], list[str]]:
    states = _state_rows(scenario)
    state_names = [_humanize(state.get("state_id", "state")) for state in states]
    visible_objects: list[str] = []
    for state in states:
        for object_id in state.get("visible_object_ids", []):
            label = _humanize(object_id)
            if label not in visible_objects:
                visible_objects.append(label)
    axis_descriptions: list[str] = []
    if domain == "economics":
        for axis in scenario.axes:
            axis_descriptions.append(
                f"{_humanize(axis.horizontal_label)} from {_format_number(axis.horizontal_min)} to {_format_number(axis.horizontal_max)} "
                f"against {_humanize(axis.vertical_label)} from {_format_number(axis.vertical_min)} to {_format_number(axis.vertical_max)}"
            )
        object_labels = [_humanize(obj.label) for obj in scenario.objects]
        visible_objects = list(dict.fromkeys([*visible_objects, *object_labels]))
    return state_names, visible_objects, axis_descriptions


def _changed_result_text(
    before: Mapping[str, object], after: Mapping[str, object]
) -> str:
    changes = _changed_values(before, after)
    if not changes:
        return "the computed outcomes remain unchanged"
    return "; ".join(
        f"{_quantity_name(key)} changes from \({_math_value(old)}\) to \({_math_value(new)}\)"
        for key, old, new in changes
    )


def _symbol_explanation(symbol_rows: Sequence[Mapping[str, str]]) -> str:
    def plural_subject(symbol: str) -> bool:
        depth = 0
        pairs = {"(": ")", "[": "]", "{": "}"}
        closing = set(pairs.values())
        for character in symbol:
            if character in pairs:
                depth += 1
            elif character in closing:
                depth = max(0, depth - 1)
            elif character == "," and depth == 0:
                return True
        return False

    clauses = []
    for row in symbol_rows[:4]:
        verb = "denote" if plural_subject(row["symbol"]) else "denotes"
        meaning = _tex_escape_prose(row["meaning"])
        if meaning.startswith("rigid body's"):
            meaning = f"the {meaning}"
        clauses.append(rf"\({row['symbol']}\) {verb} {meaning}")
    return _oxford(clauses) + "."


def _physics_interpretation(spec: Any, result: Mapping[str, object]) -> str:
    interpretations = {
        "physics_center_of_mass": "Mass weights the positions, so the center moves toward components carrying a larger share of the total mass.",
        "physics_circular": "Tangential quantities describe motion along the path; radial quantities use the inward direction as their geometric reference.",
        "physics_energy": "Energy is scalar, and only changes in potential energy are independent of the chosen zero level.",
        "physics_force": "Vector signs refer to the chosen axes; a negative component points opposite the corresponding positive axis.",
        "physics_kinematics": "Position and velocity components inherit the coordinate sign convention, while elapsed time is nonnegative.",
        "physics_momentum": "All momenta must be evaluated in one inertial frame and added as vectors over the same system boundary.",
        "physics_ode": "The initial condition selects the physical solution, and the sign of the rate determines local growth or decay.",
        "physics_potential": "Where the potential exceeds total energy, the implied kinetic energy would be negative and the classical motion is forbidden.",
        "physics_recoil": "Opposite velocity signs indicate motion in opposite directions; momentum conservation concerns their mass-weighted sum.",
        "physics_rocket": "Exhaust speed is relative to the rocket, and the logarithm requires positive initial and final masses.",
        "physics_rotation": "Angular quantities depend on the chosen origin and axis; the right-hand rule fixes their signs and directions.",
        "physics_vector": "Components carry signs in the selected basis, while magnitude is nonnegative and independent of axis orientation.",
        "physics_wave": "Wavelength has units of length and frequency has units of inverse time, so their product has units of speed.",
        "physics_work": "Work and kinetic-energy change are scalars; a negative value means energy leaves the selected kinetic degree of freedom.",
    }
    base = _MODEL_PHYSICS_INTERPRETATION.get(
        spec.model_id,
        interpretations.get(
            spec.visual_kind,
            "The numerical signs and magnitudes are interpreted using the coordinates and reference choices stated with the problem.",
        ),
    )
    base = f"For {_quantity_list(list(result))}, {base[:1].lower() + base[1:]}"
    truth_rows = [
        _boolean_statement(key, value)
        for key, value in result.items()
        if isinstance(value, bool)
    ]
    if truth_rows:
        return f"{base} In this case, {_oxford(truth_rows)}."
    return base


def _economics_interpretation(model_id: str, result: Mapping[str, object]) -> str:
    outcome_names = _quantity_list(list(result))
    if model_id in _ECON_CONDITIONING_BY_MODEL:
        conditioning = _ECON_CONDITIONING_BY_MODEL[model_id]
    elif model_id in {
        "oligopoly",
        "strategic_game",
        "nash_equilibrium",
        "dominant_strategy",
    }:
        conditioning = "the available strategies and payoff matrix"
    elif model_id in {
        "consumer_preferences",
        "utility_representation",
        "budget_constraint",
        "marginal_rate_of_substitution",
        "consumer_choice",
        "income_substitution_effects",
        "own_price_elasticity",
        "income_elasticity",
        "cross_price_elasticity",
        "intertemporal_choice",
        "choice_under_uncertainty",
        "behavioral_economics",
    }:
        conditioning = "preferences, income, prices, and the specified choice environment"
    elif model_id in {
        "production_function",
        "labor_market",
        "labor_input_market",
        "capital_input_market",
        "factor_input_markets",
        "cost_curves",
        "perfect_competition",
        "competitive_shutdown",
        "monopoly",
        "marginal_revenue",
        "price_discrimination",
    }:
        conditioning = "technology, input prices, demand, and the stated market structure"
    else:
        conditioning = "the supply, demand, policy, and institutional primitives stated in the problem"
    sentences = [
        f"The values of {outcome_names} are descriptive implications conditional on {conditioning}."
    ]
    if model_id in _ECON_WELFARE_MODELS:
        sentences.append(
            "Any efficiency conclusion drawn from these outcomes uses the welfare criterion stated in the relation; it does not imply that every participant is better off."
        )
    distribution_sentence = _ECON_DISTRIBUTION_INTERPRETATION.get(model_id)
    if distribution_sentence:
        sentences.append(distribution_sentence)
    indicators = [
        (key, value)
        for key, value in result.items()
        if key.endswith("_indicator") and isinstance(value, (int, float))
    ]
    if indicators:
        descriptions = [
            f"{_humanize(key.removesuffix('_indicator'))} is {'true' if float(value) >= 0.5 else 'false'}"
            for key, value in indicators
        ]
        sentences.append(f"For the stated numbers, {_oxford(descriptions)}.")
    return " ".join(sentences)


def _structure_property(spec: Any) -> str:
    model_overrides = {
        "action_reaction": "The equal and opposite forces act on different bodies, so they belong on separate free-body diagrams and do not cancel in either body's force sum.",
        "continuous_mass_accumulation": r"For a stationary control region, \(dM_{\mathrm{cv}}/dt=\dot m_{\mathrm{in}}-\dot m_{\mathrm{out}}\); equal port rates leave stored mass unchanged.",
        "continuous_mass_transfer": "For steady flow through a fixed control volume, external force balances the signed difference between outgoing and incoming momentum flux.",
        "externality": r"The market quantity follows private marginal conditions, whereas the efficient quantity satisfies \(MSC=MSB\); the gap reflects the external effect.",
        "international_trade": "At the world price, imports equal domestic demand minus domestic supply; autarky is a separate benchmark.",
        "labor_market": r"Labor-market equilibrium requires \(L_d(w^*)=L_s(w^*)\); the common quantity is equilibrium employment at wage \(w^*\).",
        "market_equilibrium": r"With \(Q_d=a_d-b_dP\) and \(Q_s=a_s+b_sP\), the clearing price solves \(a_d-b_dP^*=a_s+b_sP^*\).",
        "moment_of_inertia": r"Each mass element contributes \(r_\perp^2\,dm\), so moving mass farther from the axis increases \(I_O\) quadratically in distance.",
        "nash_equilibrium": "A strategy profile is a Nash equilibrium only when both players' choices are best responses in the same payoff cell.",
        "own_price_elasticity": r"Demand elasticity is a dimensionless percentage ratio; its sign records the response direction and \(|E_d|\) records response magnitude.",
        "potential_energy_diagram": r"Allowed positions satisfy \(E-U(x)\geq0\), and turning points solve \(U(x)=E\).",
        "price_ceiling_shortage": r"A binding ceiling satisfies \(\bar P<P^*\); demand and supply are evaluated separately at \(\bar P\), and their horizontal gap is the shortage.",
        "price_controls": "A ceiling and a floor must each be compared with the unregulated equilibrium before their shortage or surplus is computed.",
        "price_floor_surplus": r"A binding floor satisfies \(\underline P>P^*\); supply and demand are evaluated separately at \(\underline P\), and their horizontal gap is the surplus.",
        "production_function": r"For \(q=A L^\alpha K^{1-\alpha}\), the exponents sum to one and each marginal product is the partial derivative of output with the other input fixed.",
        "rocket_equation": "The velocity increment follows from momentum balance as mass is expelled with a specified effective exhaust speed.",
        "tax_incidence": "The buyer and seller burdens add to the tax wedge, while elasticities determine how that wedge is divided.",
        "utility_representation": "Only bundle rankings are preserved: every strictly increasing transformation of a valid utility representation describes the same preferences.",
        "waves": "Amplitude scales displacement, whereas wavelength and frequency determine wave speed and period.",
        "welfare_surplus": r"Total surplus is maximized where \(MB(Q^*)=MC(Q^*)\), provided the marginal schedules define the stated competitive benchmark.",
    }
    if spec.model_id in model_overrides:
        return model_overrides[spec.model_id]
    if spec.statement_kind == "dynamical_law" and spec.visual_kind == "physics_force":
        return "The net force is the vector sum of the modeled interactions on the selected body and determines its acceleration."
    if spec.statement_kind == "dynamical_law" and spec.visual_kind == "physics_rotation":
        return "Net torque and angular acceleration must be evaluated about the same axis with one consistent sign convention."
    return _STRUCTURAL_PROPERTIES.get(
        spec.statement_kind,
        "Every term in the relation is evaluated under the hypotheses stated for the topic.",
    )


def _physics_consistency_sentence(spec: Any, result_names: Sequence[str]) -> str:
    if spec.model_id in _MODEL_CONSISTENCY:
        return _MODEL_CONSISTENCY[spec.model_id]
    outputs = _quantity_list(result_names)
    by_visual = {
        "physics_center_of_mass": f"The positions entering {outputs} use one origin, while mass supplies the weighting rather than the coordinate convention.",
        "physics_circular": f"The signs in {outputs} follow the chosen radial and tangential directions, with inward radial direction stated explicitly.",
        "physics_energy": f"The entries in {outputs} share one energy unit and one declared potential-energy reference level.",
        "physics_force": f"The force entries among {outputs} use the axes and force units shown on the free-body diagram; derived motion entries use compatible mass and time units.",
        "physics_kinematics": f"The components of {outputs} use the chosen spatial axes; elapsed time fixes evolution but does not define a positive direction.",
        "physics_momentum": f"The vectors in {outputs} are measured in one inertial frame and use a common mass-length-time unit system.",
        "physics_ode": "The state has its declared unit, its derivative has that unit per time, and the initial condition fixes the solution branch.",
        "physics_potential": f"Positions in {outputs} are measured on the declared \(x\)-axis, while the potential-energy zero and total-energy level set the vertical reference.",
        "physics_recoil": f"Opposite signs in {outputs} refer to opposite directions on one selected axis in a common inertial frame.",
        "physics_rocket": f"The mass ratio entering {outputs} is dimensionless, so the velocity increment has the same units as exhaust speed.",
        "physics_rotation": f"The angular quantities in {outputs} use one origin, rotation axis, and right-hand-rule sign convention.",
        "physics_vector": f"The components in {outputs} use the displayed basis; vector magnitude itself does not depend on a rotation of that basis.",
        "physics_wave": f"Displacement in {outputs} is measured from equilibrium, while wavelength times frequency has units of propagation speed.",
        "physics_work": f"The work and energy entries in {outputs} share one energy unit; their signs follow transfer into or out of the chosen system.",
    }
    return by_visual.get(
        spec.visual_kind,
        f"The quantities in {outputs} use the units and reference choices stated in the setup.",
    )


def _physics_property_sentence(spec: Any, focus_output: str) -> str:
    if spec.model_id in _MODEL_PHYSICS_PROPERTY:
        base = _MODEL_PHYSICS_PROPERTY[spec.model_id]
        return f"For {_quantity_name(focus_output)}, {base[:1].lower() + base[1:]}"
    by_visual = {
        "physics_center_of_mass": "Changing a component mass changes the weighted average but does not redefine the position origin.",
        "physics_circular": "Tangential velocity and inward radial acceleration are perpendicular at every point on the circular path.",
        "physics_energy": "Only energy differences affect the balance; shifting every potential value by one constant leaves the motion unchanged.",
        "physics_force": "A force arrow represents one interaction on the selected body and must not be duplicated when components are taken.",
        "physics_kinematics": "A negative component indicates direction relative to an axis, not a negative speed or elapsed time.",
        "physics_momentum": "Momentum conservation applies to the vector total of the selected system, not to each body separately.",
        "physics_ode": "The initial condition and evolution law together determine the state at later times.",
        "physics_potential": "The slope of the potential determines force, while the height difference from total energy determines available kinetic energy.",
        "physics_recoil": "The two recoil momenta need not correspond to equal speeds when the masses differ.",
        "physics_rocket": "With positive masses, increasing the mass ratio increases ideal velocity gain logarithmically rather than linearly.",
        "physics_rotation": "Signed angular velocities and accelerations use one marked rotation axis and right-hand-rule convention.",
        "physics_vector": "Component signs depend on the basis, whereas the vector relation and magnitude are geometric.",
        "physics_wave": "Changing amplitude scales displacement but leaves phase speed unchanged when wavelength and frequency are fixed.",
        "physics_work": "Only the force component parallel to displacement contributes to mechanical work.",
    }
    base = by_visual.get(
        spec.visual_kind,
        "The relation is interpreted using the physical reference choices declared in the problem.",
    )
    return f"For {_quantity_name(focus_output)}, {base[:1].lower() + base[1:]}"


def _economics_calculation_sentence(
    spec: Any,
    setup_names: Sequence[str],
    result_names: Sequence[str],
) -> str:
    primitives = _quantity_list(setup_names)
    outcomes = _quantity_list(result_names)
    by_model = {
        "budget_constraint": r"Compute expenditure \(p_xx+p_yy\), subtract it from income for budget slack, and derive the two intercepts and slope; affordability requires expenditure no greater than income and does not require a preference ranking.",
        "externality": r"Find the unregulated quantity from the private marginal condition, then include marginal external cost in \(MSC\) and solve \(MSC=MSB\) for the efficient quantity.",
        "labor_market": r"Write labor demand as \(L_d=a_d-b_dw\) and labor supply as \(L_s=a_s+b_sw\), set them equal, and substitute the clearing wage back into either schedule for \(L^*\).",
        "market_equilibrium": r"Write \(Q_d=a_d-b_dP\) and \(Q_s=a_s+b_sP\), set them equal, and solve \(P^*=(a_d-a_s)/(b_d+b_s)\) before evaluating \(Q^*\).",
        "monopoly": r"For inverse demand \(P=a_d-b_dq\), form \(MR=a_d-2b_dq\), solve \(MR=MC\) for \(q_m\), read \(P_m\) from demand, and subtract variable and fixed cost from revenue for profit.",
        "own_price_elasticity": r"Compute \(\%\Delta Q_d=(Q_1-Q_0)/Q_0\) and \(\%\Delta P=(P_1-P_0)/P_0\), then divide the first percentage change by the second.",
        "price_ceiling_shortage": r"First solve the unregulated clearing price \(P^*\). If \(\bar P<P^*\), evaluate \(Q_d(\bar P)\) and \(Q_s(\bar P)\) separately and subtract supply from demand.",
        "price_controls": "Solve the unregulated clearing price, test each legal price for whether it binds, and evaluate demand and supply at the binding ceiling or floor before taking the relevant horizontal gap.",
        "price_floor_surplus": r"First solve the unregulated clearing price \(P^*\). If \(\underline P>P^*\), evaluate \(Q_d(\underline P)\) and \(Q_s(\underline P)\) separately and subtract demand from supply.",
        "utility_representation": r"For this numerical illustration use \(U(x,y)=\sqrt{xy}\): evaluate it at both bundles and compare the two values; only their ordering determines the preferred-bundle index.",
    }
    if spec.model_id in by_model:
        return by_model[spec.model_id]
    by_kind = {
        "accounting_identity": f"Evaluate each component of {outcomes} for the same market, period, and price, then take the stated sum or difference.",
        "behavioral_relation": f"Insert {primitives} into the behavioral relation to obtain {outcomes}, keeping the listed shifters fixed.",
        "best_response_condition": f"For each rival strategy, compare the player's payoffs cell by cell; mutual best responses determine {outcomes}.",
        "budget_constraint": f"Construct the affordable set from {primitives}, then evaluate feasibility and any preference ranking needed for {outcomes}.",
        "classification_rule": f"Compute the statistic defining {outcomes} from the common baseline in {primitives}, then apply its sign or magnitude criterion.",
        "comparative_static": f"Compute the initial outcome and the outcome after the stated primitive shifts; their difference gives {outcomes}.",
        "equilibrium_condition": f"Evaluate the opposing market or choice conditions at one candidate value and impose equality to determine {outcomes}.",
        "expected_utility": f"Weight each state-contingent payoff or utility by its probability in {primitives} to obtain {outcomes}.",
        "incentive_condition": f"Compare compliance with the feasible deviation under the same information and prices to determine {outcomes}.",
        "optimality_condition": f"Check feasibility first, impose the appropriate marginal condition for an interior candidate, and compare boundary choices before reporting {outcomes}.",
        "policy_wedge": f"Impose the policy-created wedge on the underlying market relations, then read the price, quantity, and burden entries in {outcomes}.",
        "resource_constraint": f"Apply the common resource limit to {primitives} and allocate the available amount across the uses summarized by {outcomes}.",
        "welfare_measure": f"Compute the explicitly defined benefit, cost, or surplus terms at one allocation before combining them into {outcomes}.",
    }
    return by_kind.get(
        spec.statement_kind,
        f"Apply the defining relation to {primitives} to determine {outcomes}.",
    )


def _complete_worked_derivation(
    model_id: str,
    setup: Mapping[str, object],
    calculation: Mapping[str, object],
    result: Mapping[str, object],
) -> str | None:
    """Return a scenario-bound derivation for models whose mechanism needs steps."""

    if model_id == "pulley_constraint":
        m_1 = _format_number(float(setup["mass_1"]))
        m_2 = _format_number(float(setup["mass_2"]))
        gravity = _format_number(float(setup["gravity"]))
        acceleration = _math_value(calculation["shared_acceleration_magnitude"])
        tension = _math_value(result["tension"])
        return (
            rf"Choose upward for mass 1 and downward for mass 2, so the inextensible string gives "
            rf"\(a_1=a_2=a\) in those local positive directions. Newton's second law gives "
            rf"\(T-m_1g=m_1a\) and \(m_2g-T=m_2a\). Adding eliminates tension: "
            rf"\((m_2-m_1)g=(m_1+m_2)a\), hence "
            rf"\(a=({m_2}-{m_1}){gravity}/({m_1}+{m_2})={acceleration}\). "
            rf"Substitution gives \(T=m_1(g+a)={m_1}({gravity}+{acceleration})={tension}\). "
            rf"In the common coordinate convention the accelerations are \({_math_value(result['accelerations'])}\), "
            rf"and \(\Delta\ell={_math_value(result['string_length_change'])}\)."
        )
    if model_id == "perfect_competition":
        price = _format_number(float(setup["market_price"]))
        intercept = _format_number(float(setup["marginal_cost_intercept"]))
        slope = _format_number(float(setup["marginal_cost_slope"]))
        quantity = _math_value(result["chosen_output"])
        return (
            rf"The price-taking firm has \(MR=P={price}\) and "
            rf"\(MC(q)={intercept}+{slope}q\). The interior condition "
            rf"\({price}={intercept}+{slope}q\) gives \(q^*={quantity}\). "
            rf"Integrating marginal cost gives \(VC(q)={intercept}q+({slope}/2)q^2\), so "
            rf"\(VC(q^*)={_format_number(float(result['total_cost']) - float(setup['fixed_cost']))}\), "
            rf"\(TC=VC+FC={_math_value(result['total_cost'])}\), and "
            rf"\(TR=Pq^*={price}({quantity})={_math_value(result['total_revenue'])}\). "
            rf"Therefore \(\pi=TR-TC={_math_value(result['total_revenue'])}-{_math_value(result['total_cost'])}"
            rf"={_math_value(result['profit'])}\)."
        )
    if model_id == "monopoly":
        intercept = _format_number(float(setup["demand_intercept"]))
        slope = _format_number(float(setup["demand_slope"]))
        marginal_cost = _format_number(float(setup["marginal_cost"]))
        fixed = _format_number(float(setup["fixed_cost"]))
        quantity = _math_value(result["monopoly_quantity"])
        price = _math_value(result["monopoly_price"])
        return (
            rf"Inverse demand is \(P(q)={intercept}-{slope}q\), so "
            rf"\(TR(q)={intercept}q-{slope}q^2\) and "
            rf"\(MR(q)={intercept}-{_format_number(2.0 * float(setup['demand_slope']))}q\). "
            rf"Setting \(MR=MC\) gives \({intercept}-{_format_number(2.0 * float(setup['demand_slope']))}q={marginal_cost}\), "
            rf"hence \(q_m={quantity}\). Demand then gives "
            rf"\(P_m={intercept}-{slope}({quantity})={price}\). Finally, "
            rf"\(\pi=P_mq_m-MC\,q_m-FC={price}({quantity})-{marginal_cost}({quantity})-{fixed}"
            rf"={_math_value(result['profit'])}\)."
        )
    if model_id == "price_discrimination":
        a_1 = _format_number(float(setup["demand_1_intercept"]))
        b_1 = _format_number(float(setup["demand_1_slope"]))
        a_2 = _format_number(float(setup["demand_2_intercept"]))
        b_2 = _format_number(float(setup["demand_2_slope"]))
        marginal_cost = _format_number(float(setup["marginal_cost"]))
        fixed = _format_number(float(setup["fixed_cost"]))
        q_1 = _math_value(result["market_1_quantity"])
        q_2 = _math_value(result["market_2_quantity"])
        p_1 = _math_value(result["market_1_price"])
        p_2 = _math_value(result["market_2_price"])
        return (
            rf"The separated demands \(P_1={a_1}-{b_1}q_1\) and \(P_2={a_2}-{b_2}q_2\) imply "
            rf"\(MR_1={a_1}-{_format_number(2.0 * float(setup['demand_1_slope']))}q_1\) and "
            rf"\(MR_2={a_2}-{_format_number(2.0 * float(setup['demand_2_slope']))}q_2\). "
            rf"Set each marginal revenue equal to \(MC={marginal_cost}\): "
            rf"\(q_1=({a_1}-{marginal_cost})/{_format_number(2.0 * float(setup['demand_1_slope']))}={q_1}\) and "
            rf"\(q_2=({a_2}-{marginal_cost})/{_format_number(2.0 * float(setup['demand_2_slope']))}={q_2}\). "
            rf"Substitution into demand gives \(P_1={p_1}\) and \(P_2={p_2}\), while "
            rf"\(Q=q_1+q_2={_math_value(result['total_quantity'])}\). Therefore "
            rf"\(\pi=P_1q_1+P_2q_2-MC(q_1+q_2)-FC"
            rf"={p_1}({q_1})+{p_2}({q_2})-{marginal_cost}({_math_value(result['total_quantity'])})-{fixed}"
            rf"={_math_value(result['profit'])}\)."
        )
    return None


def _economics_consistency_sentence(spec: Any, result_names: Sequence[str]) -> str:
    if spec.model_id in _MODEL_CONSISTENCY:
        return _MODEL_CONSISTENCY[spec.model_id]
    outcomes = _quantity_list(result_names)
    by_visual = {
        "econ_budget": f"Quantities in {outcomes} are measured in goods units, expenditure in currency, and utility only in the ordinal representation stated for the example.",
        "econ_curve": f"Interpret {outcomes} in the units named on the two axes; any slope combines those units in the way specified by the model.",
        "econ_elasticity": f"Elasticity entries in {outcomes} are dimensionless percentage ratios, so their classification does not depend on the units of price or quantity.",
        "econ_supply_demand": f"Prices and quantities in {outcomes} use the same market definition, time period, and units on both curves.",
        "econ_tax_wedge": f"The price burdens in {outcomes} share the tax's currency-per-unit measure, and buyer plus seller burden equals the wedge.",
        "game_payoff": f"Payoffs in {outcomes} use each player's stated payoff scale; best-response comparisons are within a player, not across players.",
    }
    return by_visual.get(
        spec.visual_kind,
        f"Interpret {outcomes} in the units and market environment stated for the topic.",
    )


def _development_opening(
    spec: Any,
    setup_names: Sequence[str],
    result_names: Sequence[str],
    learner_assumptions: Sequence[str],
) -> str:
    formula = rf"\({spec.canonical_formula}\)"
    inputs = _quantity_list(setup_names)
    outputs = _quantity_list(result_names)
    maintained = "the maintained assumptions stated above"
    by_kind = {
        "accounting_identity": f"Place {inputs} on one accounting boundary and evaluate {formula}; under {maintained}, the identity fixes {outputs}.",
        "behavioral_relation": f"Treat {inputs} as the primitives in {formula}. With {maintained}, the relation predicts {outputs}.",
        "best_response_condition": f"Use {formula} to compare each feasible response while the rival choice is held fixed; the payoff data in {inputs} determine {outputs}.",
        "budget_constraint": f"Construct the feasible set from {inputs} using {formula}, then apply {maintained} to identify {outputs}.",
        "classification_rule": f"Compute the statistic in {formula} from {inputs} on one stated baseline; its sign or magnitude classifies {outputs}.",
        "comparative_static": f"Evaluate the initial and shifted states encoded by {inputs} under {formula}; their difference determines {outputs}.",
        "conservation_law": f"Choose the system boundary first, then balance the transfers in {formula}. With {maintained}, the data {inputs} determine {outputs}.",
        "constitutive_law": f"Within the maintained response regime, insert {inputs} into {formula} to obtain {outputs}.",
        "constraint": f"Require the quantities in {formula} to satisfy the constraint simultaneously. The admissible data {inputs} then determine {outputs}.",
        "definition": f"Apply the definition {formula} to {inputs}. The maintained conventions determine how to interpret {outputs}.",
        "differential_equation": f"Combine the evolution law and initial data in {formula}; with {inputs} specified, the selected solution gives {outputs}.",
        "dynamical_law": f"Specify the body or system and apply {formula} to {inputs}. Under {maintained}, the balance determines {outputs}.",
        "equilibrium_condition": f"Impose the conditions in {formula} at one common candidate state. The primitives {inputs} then jointly determine {outputs}.",
        "expected_utility": f"Use the probabilities and state outcomes in {inputs} to evaluate {formula}; the resulting risk comparison is summarized by {outputs}.",
        "geometric_relation": f"Express {inputs} in one coordinate convention and apply {formula}; the geometry yields {outputs}.",
        "incentive_condition": f"Compare compliance with the feasible deviation through {formula}. With information and payoffs in {inputs} fixed, the test yields {outputs}.",
        "interaction_law": f"Assign each interaction in {formula} to the body or agent receiving it. The data {inputs} then imply {outputs}.",
        "kinematic_relation": f"Propagate the initial geometric data {inputs} with {formula}; no additional force law is needed to obtain {outputs}.",
        "optimality_condition": f"Use {formula} after checking the feasible set defined by {inputs}. Interior and boundary comparisons determine {outputs}.",
        "policy_wedge": f"Apply the policy condition {formula} to the underlying relations specified by {inputs}; the constrained outcome is {outputs}.",
        "resource_constraint": f"Allocate the common resource in {inputs} according to {formula}; every feasible use must fit the same aggregate limit before {outputs} are evaluated.",
        "wave_relation": f"Use the spatial and temporal parameters in {inputs} within {formula}; phase and repetition then determine {outputs}.",
        "welfare_measure": f"Evaluate the benefit and cost terms in {formula} over the allocation encoded by {inputs}; the stated criterion produces {outputs}.",
    }
    return by_kind.get(
        spec.statement_kind,
        f"Evaluate {formula} with {inputs} under {maintained} to determine {outputs}.",
    )


def _worked_case_intro(spec: Any, setup: Mapping[str, object]) -> str:
    leads = {
        "accounting_identity": "For the common accounting case",
        "behavioral_relation": "For the stated behavioral case",
        "best_response_condition": "For the payoff comparison",
        "budget_constraint": "For the feasible-set calculation",
        "classification_rule": "For the classification example",
        "comparative_static": "For the two-state comparison",
        "conservation_law": "For the selected system",
        "constitutive_law": "Within the stated response regime",
        "constraint": "For the constrained state",
        "definition": "For a concrete evaluation",
        "differential_equation": "For the initial-value problem",
        "dynamical_law": "For the selected body or system",
        "equilibrium_condition": "For the equilibrium instance",
        "expected_utility": "For the state-contingent lottery",
        "geometric_relation": "In the chosen coordinates",
        "incentive_condition": "For the compliance-deviation comparison",
        "interaction_law": "For the specified interaction",
        "kinematic_relation": "For the motion data",
        "optimality_condition": "For the feasible candidate set",
        "policy_wedge": "For the policy-constrained market",
        "resource_constraint": "For the resource allocation",
        "wave_relation": "For the displayed wave state",
        "welfare_measure": "For the surplus calculation",
    }
    lead = leads.get(spec.statement_kind, "For the worked model")
    return f"{lead}, use {_assignment_list(setup)}."


def _comparison_development_intro(
    spec: Any,
    changed_key: str,
    alt_setup: Mapping[str, object],
) -> str:
    actions = {
        "accounting_identity": "Recompute the same identity after varying",
        "behavioral_relation": "Shift one primitive by varying",
        "best_response_condition": "Repeat the response comparison after varying",
        "budget_constraint": "Rebuild the feasible set after varying",
        "classification_rule": "Reapply the classification rule after varying",
        "comparative_static": "Form a second pair of static states by varying",
        "conservation_law": "Keep the system boundary fixed and vary",
        "constitutive_law": "Stay within the same response regime and vary",
        "constraint": "Resolve the constrained state after varying",
        "definition": "Evaluate the same definition after varying",
        "differential_equation": "Resolve the initial-value problem after varying",
        "dynamical_law": "Keep the selected system fixed and vary",
        "equilibrium_condition": "Solve the joint conditions again after varying",
        "expected_utility": "Recompute the probability-weighted comparison after varying",
        "geometric_relation": "Retain the coordinate convention and vary",
        "incentive_condition": "Repeat the compliance-deviation test after varying",
        "interaction_law": "Keep the interaction assignment fixed and vary",
        "kinematic_relation": "Generate a second motion state by varying",
        "optimality_condition": "Recheck feasibility and optimality after varying",
        "policy_wedge": "Reapply the policy rule after varying",
        "resource_constraint": "Reallocate the fixed resource after varying",
        "wave_relation": "Generate a second wave state by varying",
        "welfare_measure": "Recalculate the surplus criterion after varying",
    }
    action = actions.get(spec.statement_kind, "Re-evaluate the model after varying")
    return (
        f"{action} {_quantity_name(changed_key)} alone. "
        f"The comparison inputs are {_assignment_list(alt_setup)}."
    )


def _relation_heading(spec: Any) -> str:
    """Name the mathematical object instead of repeating a generic heading."""

    return _title(_STATEMENT_KIND_LABELS.get(spec.statement_kind, "model relation"))


def _comparison_heading(spec: Any, domain: str) -> str:
    by_kind = {
        "accounting_identity": "Boundary sensitivity",
        "best_response_condition": "Deviation sensitivity",
        "classification_rule": "Baseline sensitivity",
        "conservation_law": "Boundary-preserving change",
        "constraint": "Constraint response",
        "definition": "Input response",
        "differential_equation": "Initial-data sensitivity",
        "dynamical_law": "Forcing response",
        "equilibrium_condition": "Equilibrium shift",
        "expected_utility": "Risk comparison",
        "geometric_relation": "Geometric response",
        "incentive_condition": "Incentive response",
        "interaction_law": "Interaction response",
        "kinematic_relation": "Motion response",
        "optimality_condition": "Optimum shift",
        "policy_wedge": "Policy response",
        "resource_constraint": "Allocation response",
        "welfare_measure": "Welfare comparison",
    }
    if spec.statement_kind in by_kind:
        return by_kind[spec.statement_kind]
    return "Comparative-static implication" if domain == "economics" else "Parameter response"


def _labeled_development(
    spec: Any,
    opening: str,
    structural_property: str,
    worked: str,
    interpretation: str,
    comparison: str,
) -> str:
    labels = _DEVELOPMENT_LABELS.get(
        spec.statement_kind, ("Model setup", "Worked state", "Comparison")
    )
    return (
        f"\\textbf{{{labels[0]}.}} {opening} {structural_property}\n\n"
        f"\\textbf{{{labels[1]}.}} {worked}\n\n"
        f"\\textbf{{Interpretation.}} {interpretation}\n\n"
        rf"\textbf{{{labels[2]}.}} {comparison}"
    )


def _figure_state_sentence(spec: Any, result: Mapping[str, object]) -> str:
    leads = {
        "econ_budget": "Label the worked feasible bundle and constraint measures with",
        "econ_curve": "Place the worked input-output point and local measures at",
        "econ_elasticity": "Attach the two-observation percentage-change readout",
        "econ_supply_demand": "Label the relevant intersection, gap, and market quantities with",
        "econ_tax_wedge": "Mark the two prices, wedge, and traded quantity with",
        "game_payoff": "Annotate the payoff cells and response markers with",
        "physics_center_of_mass": "Label the component positions and weighted center with",
        "physics_circular": "Attach the tangential and radial readouts",
        "physics_energy": "Label the energy stores and transfers with",
        "physics_force": "Write the force components and resulting motion beside the arrows as",
        "physics_kinematics": "Mark the worked position, velocity, and acceleration state as",
        "physics_momentum": "Label the before-and-after momentum balance with",
        "physics_ode": "Mark the evaluated point and tangent rate as",
        "physics_potential": "Label the energy intersections and allowed region with",
        "physics_recoil": "Write the signed recoil values beside the two arrows as",
        "physics_rocket": "Label the mass-flow and velocity-change readouts with",
        "physics_rotation": "Attach the angular and translational readouts",
        "physics_vector": "Label the components and resultant with",
        "physics_wave": "Mark the wave profile and propagation readouts with",
        "physics_work": "Label the force projection and accumulated work with",
    }
    lead = _MODEL_FIGURE_STATE_LEADS.get(
        spec.model_id,
        leads.get(spec.visual_kind, "Label the displayed model state with"),
    )
    return f"{lead} {_assignment_list(result)}."


def _figure_comparison_sentence(
    spec: Any,
    comparison_focus: str,
    changed_key: str,
) -> str:
    actions = {
        "econ_budget": "Draw the revised feasible set and highlight",
        "econ_curve": "Add the revised curve or point to compare",
        "econ_elasticity": "Add the revised percentage-change bracket to compare",
        "econ_supply_demand": "Add the revised intersection or horizontal gap to compare",
        "econ_tax_wedge": "Add the revised price wedge and quantity marker to compare",
        "game_payoff": "Update the affected payoff cell and best-response marks to compare",
        "physics_center_of_mass": "Move the affected mass marker and weighted center to compare",
        "physics_circular": "Add the revised tangent or radial arrow to compare",
        "physics_energy": "Add a second energy level or bar to compare",
        "physics_force": "Redraw only the affected force and response arrows to compare",
        "physics_kinematics": "Add the revised motion marker and tangent arrow to compare",
        "physics_momentum": "Add the revised before-and-after vector balance to compare",
        "physics_ode": "Add the revised trajectory or evaluation marker to compare",
        "physics_potential": "Add the revised curve or intersection to compare",
        "physics_recoil": "Add the revised signed recoil arrows to compare",
        "physics_rocket": "Add the revised flow and velocity readouts to compare",
        "physics_rotation": "Add the revised rotational marker or arrow to compare",
        "physics_vector": "Add the revised component construction to compare",
        "physics_wave": "Add the revised profile or phase marker to compare",
        "physics_work": "Add the revised force projection or work area to compare",
    }
    action = _MODEL_FIGURE_COMPARISON_ACTIONS.get(
        spec.model_id,
        actions.get(spec.visual_kind, "Add a second state to compare"),
    )
    return (
        f"{action} {_quantity_name(comparison_focus)} after changing "
        f"{_quantity_name(changed_key)} alone."
    )


def _figure_elements(domain: str, spec: Any, scenario: Any) -> list[str]:
    if domain == "economics":
        return list(dict.fromkeys(_humanize(obj.label) for obj in scenario.objects))
    return list(dict.fromkeys(_humanize(token) for token in spec.required_figure_tokens))


def _figure_guidance(spec: Any) -> str:
    return _MODEL_FIGURE_GUIDANCE.get(
        spec.model_id,
        _FIGURE_GUIDANCE.get(
            spec.visual_kind,
            "Use the labels and scale to connect each displayed quantity to the governing relation.",
        ),
    )


def _generic_figure_content(
    domain: str,
    title: str,
    spec: Any,
    scenario: Any,
    result: Mapping[str, object],
    changed_key: str,
    comparison_focus: str,
    comparison_text: str,
) -> tuple[str, str]:
    elements = _figure_elements(domain, spec, scenario)
    caption = f"{title}: {_oxford(elements[:5])}."
    guidance = _figure_guidance(spec)
    if spec.model_id in _MODEL_FIGURE_AXIS:
        axis_text = _MODEL_FIGURE_AXIS[spec.model_id]
    elif domain == "economics" and scenario.axes:
        axis = scenario.axes[0]
        axis_text = (
            f"The horizontal axis measures {_humanize(axis.horizontal_label)} and the vertical axis measures "
            f"{_humanize(axis.vertical_label)}."
        )
    else:
        axis_text = _VISUAL_FIGURE_AXIS.get(
            spec.visual_kind,
            "The labels and scale specify how every displayed quantity is measured.",
        )
    visible_marks = _oxford(elements[:5])
    discussion = (
        f"{axis_text} {guidance} Visible marks are {visible_marks}. "
        f"The comparison mark tracks {_quantity_name(comparison_focus)} after changing "
        f"{_quantity_name(changed_key)}."
    )
    return caption, discussion


def _rigid_body_content(
    title: str,
    setup: Mapping[str, object],
    calculation: Mapping[str, object],
    result: Mapping[str, object],
    changed_key: str,
    old_value: object,
    new_value: object,
    alt_result: Mapping[str, object],
    comparison: str,
) -> dict[str, object]:
    v_o = setup["reference_velocity"]
    omega = setup["angular_velocity"]
    relative = setup["relative_position"]
    rotational = calculation["rotational_velocity"]
    v_p = result["material_point_velocity"]
    distance = result["body_relative_distance"]
    payload: dict[str, object] = {
        "development_title": "Velocity decomposition for two points on a rigid body",
        "development": (
            f"Choose a reference point \\(O\\) fixed in the body and a second material point \\(P\\). Rigidity means that "
            f"the length \\(|\\vec r_{{P/O}}|\\) is constant, although the direction of \\(\\vec r_{{P/O}}\\) may rotate. "
            f"Differentiating \\(\\vec r_P=\\vec r_O+\\vec r_{{P/O}}\\) in an inertial frame gives "
            f"\\(\\vec v_P=\\vec v_O+\\vec\\omega\\times\\vec r_{{P/O}}\\).\n\n"
            f"For the example, \\(\\vec v_O={_math_value(v_o)}\\), \\(\\omega={_math_value(omega)}\\), and "
            f"\\(\\vec r_{{P/O}}={_math_value(relative)}\\). In the plane, the angular velocity points along the "
            f"perpendicular axis, so \\(\\vec\\omega\\times\\vec r_{{P/O}}={_math_value(rotational)}\\). Therefore "
            f"\\(\\vec v_P={_math_value(v_o)}+{_math_value(rotational)}={_math_value(v_p)}\\). The separation is "
            f"\\(|\\vec r_{{P/O}}|={_format_number(float(distance))}\\), consistent with a fixed distance between the points.\n\n"
            "The cross-product term has units of angular speed times length, hence velocity. Its direction follows the "
            "right-hand rule; in the displayed coordinates the rotational contribution is negative in the first component "
            "and positive in the second. This is a kinematic statement: it does not determine the forces or torques needed "
            "to produce the motion.\n\n"
            f"{comparison} Translational velocity is added equally to every point, whereas the rotational contribution "
            "depends on the point's position relative to \\(O\\)."
        ),
        "properties": [
            "The distance between any two material points is constant in the rigid-body idealization.",
            r"The relative velocity satisfies \(\vec v_P-\vec v_O=\vec\omega\times\vec r_{P/O}\) and is perpendicular to \(\vec r_{P/O}\).",
            r"A point on the instantaneous rotation axis has \(\vec\omega\times\vec r_{P/O}=\vec 0\) relative to a reference point on that axis.",
            "Changing the reference point changes the translational and rotational pieces, but their sum gives the same physical velocity for \\(P\\).",
            "The formula applies instantaneously even when angular velocity varies with time; angular acceleration enters the corresponding acceleration formula, not this velocity relation.",
        ],
        "examples": [
            {
                "kind": "worked",
                "title": "Translation plus rotation",
                "setup": (
                    f"Take \\(\\vec v_O={_math_value(v_o)}\\), \\(\\omega={_math_value(omega)}\\), and "
                    f"\\(\\vec r_{{P/O}}={_math_value(relative)}\\) in a consistent length-time unit system."
                ),
                "calculation": (
                    f"The rotational contribution is \\(\\vec\\omega\\times\\vec r_{{P/O}}={_math_value(rotational)}\\). "
                    f"Thus \\(\\vec v_P=\\vec v_O+\\vec\\omega\\times\\vec r_{{P/O}}={_math_value(v_p)}\\)."
                ),
                "takeaway": (
                    "The point velocity is the vector sum of the body's translational velocity and the point's rotational velocity about \\(O\\)."
                ),
                "trusted_tex": True,
            },
            {
                "kind": "boundary",
                "title": "Changing the translational velocity",
                "setup": (
                    f"Change only {_quantity_name(changed_key)} from \\({_math_value(old_value)}\\) to "
                    f"\\({_math_value(new_value)}\\); keep \\(\\omega={_math_value(omega)}\\) and "
                    f"\\(\\vec r_{{P/O}}={_math_value(relative)}\\) fixed."
                ),
                "calculation": (
                    f"The cross-product term remains \\({_math_value(rotational)}\\), while the new point velocity is "
                    f"{_assignment('material_point_velocity', alt_result['material_point_velocity'])}."
                ),
                "takeaway": comparison,
                "trusted_tex": True,
            },
        ],
        "figure_caption": "Velocity decomposition of a rigid body into translation of \\(O\\) and rotation about \\(O\\).",
        "figure_discussion": (
            "Draw \\(\\vec r_{P/O}\\) from \\(O\\) to \\(P\\), \\(\\vec v_O\\) at the reference point, and "
            "\\(\\vec\\omega\\times\\vec r_{P/O}\\) perpendicular to the relative-position vector. Translating the "
            "rotational-velocity arrow to the tip of \\(\\vec v_O\\) constructs \\(\\vec v_P\\) by head-to-tail addition. "
            "The unchanged length of \\(\\vec r_{P/O}\\) represents rigidity; the turning direction of that vector represents rotation."
        ),
    }
    return payload


def _consumer_choice_content(
    title: str,
    setup: Mapping[str, object],
    result: Mapping[str, object],
    changed_key: str,
    old_value: object,
    new_value: object,
    alt_result: Mapping[str, object],
    comparison: str,
) -> dict[str, object]:
    income = float(setup["income"])
    price_x = float(setup["price_x"])
    price_y = float(setup["price_y"])
    alpha = float(setup["utility_share_x"])
    x_star = float(result["chosen_x"])
    y_star = float(result["chosen_y"])
    utility = float(result["utility"])
    return {
        "development_title": "Interior choice with Cobb-Douglas preferences",
        "development": (
            "The consumer first faces the feasible set \\(p_xx+p_yy\\leq I\\). With locally nonsatiated preferences, "
            "an interior optimum exhausts the budget, so \\(p_xx+p_yy=I\\). For the numerical example take "
            "\\(U(x,y)=x^\\alpha y^{1-\\alpha}\\), where \\(0<\\alpha<1\\). The tangency condition is "
            "\\(MRS=MU_x/MU_y=p_x/p_y\\). Solving the tangency and budget equations gives "
            "\\(x^*=\\alpha I/p_x\\) and \\(y^*=(1-\\alpha)I/p_y\\).\n\n"
            f"Substituting \\(I={_format_number(income)}\\), \\(p_x={_format_number(price_x)}\\), "
            f"\\(p_y={_format_number(price_y)}\\), and \\(\\alpha={_format_number(alpha)}\\) gives "
            f"\\(x^*={_format_number(alpha)}({_format_number(income)})/{_format_number(price_x)}={_format_number(x_star)}\\) "
            f"and \\(y^*={_format_number(1-alpha)}({_format_number(income)})/{_format_number(price_y)}={_format_number(y_star)}\\). "
            f"Expenditure is \\({_format_number(price_x)}({_format_number(x_star)})+{_format_number(price_y)}({_format_number(y_star)})"
            f"={_format_number(income)}\\), so the bundle is affordable and lies on the budget line. Its utility index is "
            f"\\(U={_format_number(utility)}\\).\n\n"
            "This is a positive choice result conditional on the utility representation, prices, income, and an interior "
            "solution. It does not compare welfare across consumers, and it does not imply that utility is measured in "
            "cardinal units. A corner solution must be checked when tangency fails or preferences are not strictly convex.\n\n"
            f"{comparison} With prices and \\(\\alpha\\) fixed, the Cobb-Douglas demands are proportional to income, so "
            "the budget line shifts outward in parallel and both chosen quantities rise in the same proportion."
        ),
        "properties": [
            r"A bundle is feasible exactly when \(p_xx+p_yy\leq I\); points above the budget line are unaffordable.",
            r"The budget-line intercepts are \(I/p_x\) and \(I/p_y\), and its slope is \(-p_x/p_y\).",
            r"At an interior differentiable optimum, \(MRS=p_x/p_y\); feasibility and boundary alternatives must still be checked.",
            r"For Cobb-Douglas utility \(x^\alpha y^{1-\alpha}\), expenditure shares are \(p_xx^*/I=\alpha\) and \(p_yy^*/I=1-\alpha\).",
            "The utility number represents a preference ranking; monotone transformations leave the chosen bundle unchanged.",
        ],
        "examples": [
            {
                "kind": "worked",
                "title": "An interior affordable bundle",
                "setup": (
                    f"Let \\(U=x^{{{_format_number(alpha)}}}y^{{{_format_number(1-alpha)}}}\\), "
                    f"\\(I={_format_number(income)}\\), \\(p_x={_format_number(price_x)}\\), and "
                    f"\\(p_y={_format_number(price_y)}\\)."
                ),
                "calculation": (
                    f"\\(x^*=\\alpha I/p_x={_format_number(x_star)}\\) and "
                    f"\\(y^*=(1-\\alpha)I/p_y={_format_number(y_star)}\\). The budget check is "
                    f"\\(p_xx^*+p_yy^*={_format_number(income)}\\)."
                ),
                "takeaway": (
                    "The chosen bundle is feasible, exhausts income, and satisfies the interior optimality condition."
                ),
                "trusted_tex": True,
            },
            {
                "kind": "boundary",
                "title": "An income expansion",
                "setup": (
                    f"Raise income from \\({_math_value(old_value)}\\) to \\({_math_value(new_value)}\\), holding "
                    f"\\(p_x={_format_number(price_x)}\\), \\(p_y={_format_number(price_y)}\\), and "
                    f"\\(\\alpha={_format_number(alpha)}\\) fixed."
                ),
                "calculation": (
                    f"The new demands are {_assignment('chosen_x', alt_result['chosen_x'])} and "
                    f"{_assignment('chosen_y', alt_result['chosen_y'])}; expenditure is "
                    f"{_assignment('expenditure', alt_result['expenditure'])}."
                ),
                "takeaway": (
                    "The budget line shifts outward without changing slope, and both normal-good demands expand proportionally with income."
                ),
                "trusted_tex": True,
            },
        ],
        "figure_caption": "Budget line, indifference curve, and the utility-maximizing affordable bundle.",
        "figure_discussion": (
            f"Put good \\(x\\) on the horizontal axis and good \\(y\\) on the vertical axis. The budget line has intercepts "
            f"\\(I/p_x={_format_number(income/price_x)}\\) and \\(I/p_y={_format_number(income/price_y)}\\), with slope "
            f"\\(-p_x/p_y={_format_number(-price_x/price_y)}\\). The chosen point "
            f"\\(({_format_number(x_star)},{_format_number(y_star)})\\) lies on that line and on the highest attainable "
            "indifference curve. A parallel outward shift represents the income comparison; a rotation would instead "
            "represent a change in a relative price."
        ),
    }


def _rocket_equation_content(
    setup: Mapping[str, object],
    calculation: Mapping[str, object],
    result: Mapping[str, object],
    alt_result: Mapping[str, object],
    comparison: str,
) -> dict[str, object]:
    mass_ratio = float(calculation["mass_ratio"])
    log_ratio = float(calculation["log_mass_ratio"])
    propellant = float(calculation["propellant_mass"])
    return {
        "development_title": "Momentum balance for an ideal rocket",
        "development": (
            "Treat the rocket and its exhaust as one isolated system during an infinitesimal ejection. Conservation of "
            "momentum gives \\(m\,dv=-v_e\,dm\\), where \\(v_e>0\\) is the exhaust speed relative to the rocket and "
            "\\(dm<0\\) is the rocket's mass change. Integrating from \\(m_i\\) to \\(m_f\\) yields "
            "\\(\\Delta v=v_e\\ln(m_i/m_f)\\).\n\n"
            f"Here \\(m_i={_math_value(setup['initial_mass'])}\\), \\(m_f={_math_value(setup['final_mass'])}\\), and "
            f"\\(v_e={_math_value(setup['exhaust_speed'])}\\). The mass ratio is "
            f"\\(m_i/m_f={_format_number(mass_ratio)}\\), so \\(\\ln(m_i/m_f)={_format_number(log_ratio)}\\). "
            f"Therefore \\(\\Delta v={_math_value(setup['exhaust_speed'])}({_format_number(log_ratio)})"
            f"={_math_value(result['delta_velocity'])}\\). The expelled propellant mass is "
            f"\\(m_i-m_f={_format_number(propellant)}\\).\n\n"
            "The mass ratio is dimensionless, as is its logarithm, so the velocity increment has the same units as exhaust speed. The formula "
            "requires positive masses with \\(m_i\geq m_f\\); if \\(m_i=m_f\\), no propellant is expelled and "
            "\\(\\Delta v=0\\). It is an ideal one-dimensional momentum result for the velocity increment.\n\n"
            f"{comparison} The vehicle still loses mass in both cases; the larger mass ratio increases ideal velocity gain "
            "logarithmically."
        ),
        "properties": [
            r"The mass ratio \(m_i/m_f\) is dimensionless and must be at least one for propellant expenditure.",
            r"Velocity gain is proportional to \(v_e\) but only logarithmic in \(m_i/m_f\).",
            r"When \(m_i=m_f\), the logarithm vanishes and \(\Delta v=0\).",
            "The exhaust speed is measured relative to the rocket; its direction sets the direction of the rocket's velocity increment.",
            "External gravity and drag impulses are omitted from this ideal increment and must be accounted for separately in a mission calculation.",
        ],
        "examples": [
            {
                "kind": "worked",
                "title": "Ideal velocity increment",
                "setup": f"Take {_assignment_list(setup)}.",
                "calculation": (
                    f"\\(m_i/m_f={_format_number(mass_ratio)}\\), "
                    f"\\(\\ln(m_i/m_f)={_format_number(log_ratio)}\\), and therefore "
                    f"{_assignment('delta_velocity', result['delta_velocity'])}."
                ),
                "takeaway": "The velocity increment follows from exhaust speed times the logarithm of the mass ratio.",
                "trusted_tex": True,
            },
            {
                "kind": "boundary",
                "title": "Increasing the initial mass",
                "setup": "Increase \\(m_i\\) while holding \\(m_f\\) and \\(v_e\\) fixed.",
                "calculation": f"The same logarithmic relation gives {_assignment('delta_velocity', alt_result['delta_velocity'])}.",
                "takeaway": comparison,
                "trusted_tex": True,
            },
        ],
        "figure_caption": "Rocket and exhaust momentum during propellant ejection.",
        "figure_discussion": (
            "Show the exhaust velocity relative to the rocket, the decrease from \\(m_i\\) to \\(m_f\\), and the rocket's "
            "opposite velocity increment. A mass-ratio readout should feed the logarithm before the velocity bar is drawn. "
            f"For the worked values, \\(m_i/m_f={_format_number(mass_ratio)}\\) and "
            f"{_assignment('delta_velocity', result['delta_velocity'])}. The comparison lengthens the velocity bar while "
            "leaving exhaust speed and final mass fixed."
        ),
    }


def _potential_diagram_content(
    setup: Mapping[str, object],
    calculation: Mapping[str, object],
    result: Mapping[str, object],
    alt_result: Mapping[str, object],
    comparison: str,
) -> dict[str, object]:
    center = float(setup["center"])
    curvature = float(setup["curvature"])
    floor = float(setup["floor_energy"])
    total = float(setup["total_energy"])
    samples = list(setup["position_samples"])
    allowed = list(result["allowed_samples"])
    allowed_positions = [value for value, is_allowed in zip(samples, allowed) if is_allowed]
    forbidden_positions = [value for value, is_allowed in zip(samples, allowed) if not is_allowed]
    return {
        "development_title": "Allowed motion and turning points in a potential well",
        "development": (
            f"For this example the potential is \\(U(x)={_format_number(curvature)}(x-{_format_number(center)})^2"
            f"+{_format_number(floor)}\\), and total mechanical energy is \\(E={_format_number(total)}\\). "
            "Kinetic energy is \\(K(x)=E-U(x)\\), so classical motion is allowed only where \\(K(x)\geq0\\).\n\n"
            f"At the sample positions \\(x_j={_math_value(samples)}\\), the potential values are "
            f"\\(U(x_j)={_math_value(calculation['potential_samples'])}\\), giving "
            f"\\(K(x_j)={_math_value(calculation['kinetic_energy_samples'])}\\). Thus "
            f"\\(x={_math_value(allowed_positions)}\\) is allowed in the displayed sample, whereas "
            f"\\(x={_math_value(forbidden_positions)}\\) is forbidden.\n\n"
            f"Turning points satisfy \\(U(x_t)=E\\): \\(x_t={_format_number(center)}\\pm"
            f"\\sqrt{{({ _format_number(total)}-{_format_number(floor)})/{_format_number(curvature)}}}"
            f"={_math_value(result['turning_points'])}\\). Position signs are fixed by the chosen \\(x\\)-axis and the "
            "center of the well; curvature controls steepness, not the coordinate convention.\n\n"
            f"{comparison} The sampled allowed/forbidden pattern remains unchanged, but the turning points move inward "
            "because the steeper well reaches \\(E\\) at a smaller displacement from its center."
        ),
        "properties": [
            r"Allowed positions satisfy \(U(x)\leq E\); forbidden positions would require \(K(x)<0\).",
            r"Turning points solve \(U(x_t)=E\) and have zero instantaneous kinetic energy.",
            r"Changing the potential-energy zero shifts \(U\) and \(E\) together and does not change the allowed region.",
            "The horizontal coordinate convention is set by the chosen axis and well center, not by the curvature parameter.",
            "Increasing positive curvature narrows this quadratic well at fixed total energy and floor energy.",
        ],
        "examples": [
            {
                "kind": "worked",
                "title": "Turning points of a quadratic well",
                "setup": f"Use {_assignment_list(setup)}.",
                "calculation": (
                    f"Solve \\({ _format_number(curvature)}(x-{_format_number(center)})^2+{_format_number(floor)}"
                    f"={_format_number(total)}\\) to obtain {_assignment('turning_points', result['turning_points'])}."
                ),
                "takeaway": f"The allowed sample positions are \\({_math_value(allowed_positions)}\\).",
                "trusted_tex": True,
            },
            {
                "kind": "boundary",
                "title": "Steepening the well",
                "setup": "Increase \\(\\kappa\\) while keeping the well center, floor, and total energy fixed.",
                "calculation": f"The new intersections are {_assignment('turning_points', alt_result['turning_points'])}.",
                "takeaway": comparison,
                "trusted_tex": True,
            },
        ],
        "figure_caption": "Potential curve, total-energy line, allowed region, and turning points.",
        "figure_discussion": (
            "Plot \\(U(x)\\) against the chosen position axis and draw the horizontal line \\(E\\). Shade only the region "
            "where the energy line lies on or above the potential. The two intersections are the turning points, and their "
            "horizontal coordinates carry the sign convention. When curvature increases, the potential steepens and those "
            "intersections move toward the well center while the displayed sample classification remains the same."
        ),
    }


def _waves_content(
    setup: Mapping[str, object],
    calculation: Mapping[str, object],
    result: Mapping[str, object],
    alt_result: Mapping[str, object],
    comparison: str,
) -> dict[str, object]:
    sine_phase = float(setup["phase"])
    cosine_phase = sine_phase - math.pi / 2.0
    cosine_argument = float(calculation["phase_argument"]) - math.pi / 2.0
    return {
        "development_title": "Phase, speed, period, and displacement of a traveling wave",
        "development": (
            "For a sinusoidal traveling wave, \\(k=2\\pi/\\lambda\\), \\(\\omega=2\\pi f\\), "
            "\\(v=\\omega/k=\\lambda f\\), and \\(T=1/f\\). For the numerical profile, the scenario phase "
            f"\\(\\phi_s={_format_number(sine_phase)}\\) is written in sine form. The equivalent canonical cosine phase is "
            f"\\(\\phi_c=\\phi_s-\\pi/2={_format_number(cosine_phase)}\\).\n\n"
            f"With \\(A={_math_value(setup['amplitude'])}\\), \\(\\lambda={_math_value(setup['wavelength'])}\\), and "
            f"\\(f={_math_value(setup['frequency'])}\\), the wave number is \\(k={_math_value(calculation['wave_number'])}\\) "
            f"and angular frequency is \\(\\omega={_math_value(calculation['angular_frequency'])}\\). Hence "
            f"{_assignment('wave_speed', result['wave_speed'])} and {_assignment('period', result['period'])}.\n\n"
            f"At \\(x={_math_value(setup['position'])}\\) and \\(t={_math_value(setup['time'])}\\), the sine argument is "
            f"\\({_math_value(calculation['phase_argument'])}\\); equivalently, the cosine argument is "
            f"\\({_format_number(cosine_argument)}\\). Both forms give "
            f"{_assignment('displacement', result['displacement'])}. A negative displacement means the medium is below "
            "the chosen equilibrium line at that point; it does not mean the wave travels backward.\n\n"
            f"{comparison} Speed and period remain fixed because neither wavelength nor frequency changes. Amplitude only "
            "rescales the vertical displacement."
        ),
        "properties": [
            r"Wave speed is \(v=\lambda f\), and period is \(T=1/f\).",
            r"Wave number and angular frequency are \(k=2\pi/\lambda\) and \(\omega=2\pi f\).",
            "Amplitude changes the displacement scale but not phase speed when wavelength and frequency are fixed.",
            r"The sign of displacement is measured from the equilibrium axis; propagation direction is determined by the phase \(kx-\omega t+\phi\).",
            "Sine and cosine descriptions represent the same family of waves after an appropriate phase shift.",
        ],
        "examples": [
            {
                "kind": "worked",
                "title": "Wave speed and point displacement",
                "setup": f"Take {_assignment_list(setup)}.",
                "calculation": (
                    f"{_assignment('wave_number', calculation['wave_number'])}, "
                    f"{_assignment('angular_frequency', calculation['angular_frequency'])}, "
                    f"{_assignment('wave_speed', result['wave_speed'])}, and "
                    f"{_assignment('displacement', result['displacement'])}."
                ),
                "takeaway": "Speed follows from wavelength and frequency, while the instantaneous displacement also depends on amplitude and phase.",
                "trusted_tex": True,
            },
            {
                "kind": "boundary",
                "title": "Increasing amplitude",
                "setup": "Increase \\(A\\) while holding \\(\\lambda\\), \\(f\\), phase, position, and time fixed.",
                "calculation": f"The new displacement is {_assignment('displacement', alt_result['displacement'])}.",
                "takeaway": comparison,
                "trusted_tex": True,
            },
        ],
        "figure_caption": "Wave profile with amplitude, wavelength, equilibrium line, and propagation direction.",
        "figure_discussion": (
            "Measure amplitude vertically from the equilibrium line and wavelength horizontally between equal-phase points. "
            f"The worked profile has {_assignment('displacement', result['displacement'])} at the marked point. Increasing "
            "amplitude stretches the profile vertically, so the marked displacement changes; wavelength, the horizontal "
            f"spacing, {_assignment('wave_speed', result['wave_speed'])}, and {_assignment('period', result['period'])} remain unchanged."
        ),
        "result_statement": (
            f"For \\(A={_math_value(setup['amplitude'])}\\), \\(\\lambda={_math_value(setup['wavelength'])}\\), and "
            f"\\(f={_math_value(setup['frequency'])}\\), the wave relations give "
            f"{_assignment('wave_speed', result['wave_speed'])} and {_assignment('period', result['period'])}. "
            f"Using sine phase \\(\\phi_s={_format_number(sine_phase)}\\), or equivalently cosine phase "
            f"\\(\\phi_c={_format_number(cosine_phase)}\\), gives "
            f"{_assignment('displacement', result['displacement'])} at the stated position and time."
        ),
    }


def _tax_incidence_content(
    setup: Mapping[str, object],
    result: Mapping[str, object],
    alt_result: Mapping[str, object],
    comparison: str,
) -> dict[str, object]:
    tax = float(setup["tax"])
    demand_elasticity = float(setup["absolute_demand_elasticity"])
    supply_elasticity = float(setup["supply_elasticity"])
    denominator = demand_elasticity + supply_elasticity
    return {
        "development_title": "Dividing a per-unit tax between buyers and sellers",
        "development": (
            "A per-unit tax creates the wedge \\(P_b-P_s=t\\). For local linear incidence, the buyer share of the wedge is "
            "\\(\\varepsilon_s/(|\\varepsilon_d|+\\varepsilon_s)\\), while the seller share is "
            "\\(|\\varepsilon_d|/(|\\varepsilon_d|+\\varepsilon_s)\\). The relatively less elastic side changes its "
            "net price by more.\n\n"
            f"Here \\(t={_format_number(tax)}\\), \\(|\\varepsilon_d|={_format_number(demand_elasticity)}\\), and "
            f"\\(\\varepsilon_s={_format_number(supply_elasticity)}\\). Thus the buyer burden is "
            f"\\({ _format_number(tax)}({ _format_number(supply_elasticity)})/{_format_number(denominator)}"
            f"={_math_value(result['buyer_burden'])}\\), and the seller burden is "
            f"\\({ _format_number(tax)}({ _format_number(demand_elasticity)})/{_format_number(denominator)}"
            f"={_math_value(result['seller_burden'])}\\).\n\n"
            f"Starting from \\(P_0={_math_value(setup['pre_tax_price'])}\\), buyers pay "
            f"\\(P_b=P_0+{_math_value(result['buyer_burden'])}={_math_value(result['buyer_price'])}\\), while sellers "
            f"receive \\(P_s=P_0-{_math_value(result['seller_burden'])}={_math_value(result['seller_price'])}\\). "
            f"The check \\(P_b-P_s={_math_value(result['tax_wedge'])}=t\\) closes the wedge.\n\n"
            f"{comparison} The elasticity shares are unchanged, so increasing the tax scales both burdens in the same "
            "proportions. These incidence calculations describe price burdens; quantity loss and deadweight loss require "
            "additional demand and supply information."
        ),
        "properties": [
            r"Buyer and seller burdens sum to the statutory wedge: \((P_b-P_0)+(P_0-P_s)=t\).",
            "The less elastic side of the market bears the larger price burden in the local incidence formula.",
            "Statutory remittance does not determine economic incidence.",
            "Incidence is distributional; it is distinct from tax revenue and deadweight loss.",
            "Holding elasticities fixed, both burden amounts scale linearly with the tax rate.",
        ],
        "examples": [
            {
                "kind": "worked",
                "title": "Elasticity-based tax shares",
                "setup": f"Take {_assignment_list(setup)}.",
                "calculation": (
                    f"The buyer share is \\({ _format_number(supply_elasticity)}/{_format_number(denominator)}\\) and "
                    f"the seller share is \\({ _format_number(demand_elasticity)}/{_format_number(denominator)}\\). "
                    f"Hence {_assignment('buyer_burden', result['buyer_burden'])} and "
                    f"{_assignment('seller_burden', result['seller_burden'])}."
                ),
                "takeaway": "The more inelastic supply side receives the larger adverse price change in this example.",
                "trusted_tex": True,
            },
            {
                "kind": "boundary",
                "title": "A larger tax with unchanged elasticities",
                "setup": "Increase \\(t\\) while holding the pre-tax price and both elasticities fixed.",
                "calculation": (
                    f"The new burdens are {_assignment('buyer_burden', alt_result['buyer_burden'])} and "
                    f"{_assignment('seller_burden', alt_result['seller_burden'])}."
                ),
                "takeaway": comparison,
                "trusted_tex": True,
            },
        ],
        "figure_caption": "Supply, demand, and the division of a per-unit tax wedge.",
        "figure_discussion": (
            f"Draw \\(P_b={_math_value(result['buyer_price'])}\\) above "
            f"\\(P_s={_math_value(result['seller_price'])}\\). Their vertical separation is "
            f"\\(t={_math_value(result['tax_wedge'])}\\). Split that segment at the pre-tax price "
            f"\\(P_0={_math_value(setup['pre_tax_price'])}\\): the upper segment is the buyer burden and the lower segment "
            "is the seller burden. A larger tax lengthens both segments according to the same elasticity shares."
        ),
    }


def _oligopoly_content(
    title: str,
    setup: Mapping[str, object],
    result: Mapping[str, object],
    alt_result: Mapping[str, object],
    comparison: str,
) -> dict[str, object]:
    a = _math_value(setup["demand_intercept"])
    b = _math_value(setup["demand_slope"])
    c = _math_value(setup["marginal_cost"])
    if "collusive_total_quantity" in result:
        return {
            "development_title": "Cournot competition and joint-profit-maximizing collusion",
            "development": (
                "With inverse demand \\(P=a-bQ\\) and constant marginal cost \\(c\\), two symmetric Cournot firms "
                "choose quantities independently. Their mutual best responses give "
                "\\[q_i^N=\\frac{a-c}{3b},\\qquad Q_N=\\frac{2(a-c)}{3b},\\qquad P_N=\\frac{a+2c}{3}.\\]"
                "Perfect coordination instead maximizes joint profit \\(\\Pi(Q)=[a-bQ-c]Q\\). The first-order "
                "condition \\(a-c-2bQ=0\\) gives "
                "\\[Q_C=\\frac{a-c}{2b},\\qquad P_C=\\frac{a+c}{2},\\qquad q_i^C=\\frac{a-c}{4b}.\\]"
                f"For \\(a={a}\\), \\(b={b}\\), and \\(c={c}\\), Cournot total output is "
                f"\\({_math_value(result['cournot_total_quantity'])}\\) at price "
                f"\\({_math_value(result['cournot_price'])}\\), whereas collusive total output is "
                f"\\({_math_value(result['collusive_total_quantity'])}\\) at price "
                f"\\({_math_value(result['collusive_price'])}\\). Thus the cartel restricts output by "
                f"\\({_math_value(result['output_restriction'])}\\) and raises price by "
                f"\\({_math_value(result['price_increase'])}\\). {comparison}"
            ),
            "properties": [
                "Cournot quantities are mutual best responses; collusive quantities maximize joint profit.",
                "For linear demand and constant marginal cost, collusive total output is below Cournot total output.",
                "Restricting total output moves the market up the demand curve to a higher collusive price.",
                "An equal cartel split assigns half of joint output to each firm but does not remove incentives to deviate.",
                "The comparison holds demand slope and marginal cost fixed when the demand intercept changes.",
            ],
            "examples": [
                {
                    "kind": "worked",
                    "title": "Cournot output versus collusive output",
                    "setup": f"Take inverse demand \\(P={a}-{b}Q\\) and constant marginal cost \\(c={c}\\) for two symmetric firms.",
                    "calculation": (
                        f"Cournot gives \\(Q_N=2(a-c)/(3b)={_math_value(result['cournot_total_quantity'])}\\) and "
                        f"\\(P_N={_math_value(result['cournot_price'])}\\). Joint-profit maximization gives "
                        f"\\(Q_C=(a-c)/(2b)={_math_value(result['collusive_total_quantity'])}\\) and "
                        f"\\(P_C={_math_value(result['collusive_price'])}\\)."
                    ),
                    "takeaway": "Collusion replaces mutual best-response output choices with joint-profit maximization, reducing quantity and increasing price.",
                    "trusted_tex": True,
                },
                {
                    "kind": "boundary",
                    "title": "A higher demand intercept",
                    "setup": "Raise only the demand intercept while holding demand slope and marginal cost fixed.",
                    "calculation": (
                        f"The new Cournot total is \\({_math_value(alt_result['cournot_total_quantity'])}\\), the new collusive total is "
                        f"\\({_math_value(alt_result['collusive_total_quantity'])}\\), and the output restriction is "
                        f"\\({_math_value(alt_result['output_restriction'])}\\)."
                    ),
                    "takeaway": comparison,
                    "trusted_tex": True,
                },
            ],
            "figure_caption": "Cournot reaction curves and the lower-output, higher-price collusive benchmark.",
            "figure_discussion": (
                "The reaction-curve intersection marks the Cournot equilibrium, where each firm's quantity is a best "
                "response to the other. Mark the collusive allocation at lower total quantity and project that quantity "
                "to inverse demand to show the higher collusive price; the horizontal quantity gap is output restriction."
            ),
        }
    if title.strip().lower().endswith("ii"):
        monopoly_quantity = (float(setup["demand_intercept"]) - float(setup["marginal_cost"])) / (2.0 * float(setup["demand_slope"]))
        collusive_firm_quantity = monopoly_quantity / 2.0
        monopoly_price = float(setup["demand_intercept"]) - float(setup["demand_slope"]) * monopoly_quantity
        return {
            "development_title": "Cournot competition, collusion, and the market benchmark",
            "development": (
                "The Cournot equilibrium is a noncooperative benchmark. If the two firms coordinate perfectly, they choose total output to maximize joint profit,\n"
                "\\[\\Pi(Q)=[a-bQ-c]Q.\\]\n"
                "The first-order condition is \\(a-c-2bQ=0\\), so\n"
                "\\[Q^{M}=\\frac{a-c}{2b},\\qquad P^{M}=\\frac{a+c}{2}.\\]\n"
                "With an equal output split, each colluding firm produces \\(q_i^{M}=(a-c)/(4b)\\). By contrast, Cournot competition gives "
                "\\(q_i^{C}=(a-c)/(3b)\\) and \\(Q^{C}=2(a-c)/(3b)\\). Therefore \\(Q^{M}<Q^{C}\\) and \\(P^{M}>P^{C}\\): "
                "collusion restricts output and raises price.\n\n"
                f"For \\(a={a}\\), \\(b={b}\\), and \\(c={c}\\), collusive total output is \\({ _math_value(monopoly_quantity) }\\), "
                f"each firm's equal share is \\({ _math_value(collusive_firm_quantity) }\\), and price is \\({ _math_value(monopoly_price) }\\). "
                f"The Cournot benchmark remains \\(Q^C={_math_value(result['total_quantity'])}\\) and \\(P^C={_math_value(result['market_price'])}\\)."
            ),
            "properties": [
                "Cournot equilibrium is noncooperative; collusion maximizes joint profit.",
                "A collusive industry behaves like a single monopolist when coordination is perfect.",
                "Collusive total output is below Cournot total output for linear demand and constant marginal cost.",
                "The collusive price is above the Cournot price, transferring surplus away from consumers.",
                "A collusive allocation must also specify how firms divide output and profit, and it may be unstable without enforcement.",
            ],
            "examples": [
                {
                    "kind": "worked",
                    "title": "Comparing Cournot and collusion",
                    "setup": f"Use \\(a={a}\\), \\(b={b}\\), and \\(c={c}\\).",
                    "calculation": f"Compute \\(Q^M=(a-c)/(2b)={_math_value(monopoly_quantity)}\\) and compare it with \\(Q^C={_math_value(result['total_quantity'])}\\). Prices are \\(P^M={_math_value(monopoly_price)}\\) and \\(P^C={_math_value(result['market_price'])}\\).",
                    "takeaway": "Coordination reduces industry output and raises price relative to Cournot competition.",
                    "trusted_tex": True,
                },
                {
                    "kind": "boundary",
                    "title": "Why a cartel agreement can unravel",
                    "setup": "Hold the rival at its agreed collusive quantity and consider one firm's unilateral output increase.",
                    "calculation": "The deviating firm moves along its Cournot best response and can gain at the agreed price, although simultaneous deviations destroy the cartel outcome.",
                    "takeaway": "Joint-profit maximization does not by itself make the collusive allocation a noncooperative equilibrium.",
                    "trusted_tex": True,
                },
            ],
            "figure_caption": "Cournot reaction functions locate the noncooperative benchmark used to compare collusive output.",
            "figure_discussion": "The reaction-curve intersection gives the Cournot quantities. The collusive benchmark lies at lower total output; it is chosen from joint profit rather than from the intersection of unilateral best responses.",
        }
    return {
        "development_title": "Cournot reaction functions and equilibrium",
        "development": (
            "Let inverse demand be \\(P(Q)=a-bQ\\), let \\(Q=q_1+q_2\\), and assume constant marginal cost \\(c\\). "
            "Firm 1 treats \\(q_2\\) as fixed and solves\n\\[\\pi_1(q_1,q_2)=[a-b(q_1+q_2)-c]q_1.\\]\n"
            "Differentiating with respect to its own output gives\n"
            "\\[\\frac{\\partial \\pi_1}{\\partial q_1}=a-c-2bq_1-bq_2=0,\\qquad "
            "BR_1(q_2)=\\frac{a-c-bq_2}{2b}.\\]\n"
            "By symmetry, \\(BR_2(q_1)=(a-c-bq_1)/(2b)\\). Solving the two reaction functions together yields\n"
            "\\[q_1^*=q_2^*=\\frac{a-c}{3b},\\qquad Q^*=\\frac{2(a-c)}{3b},\\qquad "
            "P^*=\\frac{a+2c}{3}.\\]\n"
            "The second derivative is \\(-2b<0\\), so each reaction-function solution maximizes that firm's profit. "
            f"For \\(a={a}\\), \\(b={b}\\), and \\(c={c}\\), this gives "
            f"\\(q_1^*=q_2^*={_math_value(result['firm_1_quantity'])}\\), "
            f"\\(Q^*={_math_value(result['total_quantity'])}\\), and \\(P^*={_math_value(result['market_price'])}\\).\n\n"
            "Analytically, \\(\\partial q_i^*/\\partial a=1/(3b)>0\\), "
            "\\(\\partial q_i^*/\\partial c=-1/(3b)<0\\), and \\(\\partial P^*/\\partial a=1/3\\). "
            f"{comparison}"
        ),
        "properties": [
            "Each Cournot firm chooses quantity while treating its rival's quantity as fixed.",
            "A reaction function slopes downward because more rival output lowers the firm's profit-maximizing output.",
            "The symmetric equilibrium is the intersection of the two reaction functions.",
            "The condition \\(-2b<0\\) verifies that the first-order condition gives a maximum when \\(b>0\\).",
            "A higher demand intercept raises equilibrium quantities and price; a higher marginal cost lowers quantities and raises price.",
        ],
        "examples": [
            {
                "kind": "worked",
                "title": "Solving a symmetric Cournot duopoly",
                "setup": f"Use \\(a={a}\\), \\(b={b}\\), and \\(c={c}\\).",
                "calculation": (
                    "Set \\(q_1=(a-c-bq_2)/(2b)\\) and \\(q_2=(a-c-bq_1)/(2b)\\). "
                    f"Symmetry gives \\(q_i=(a-c)/(3b)={_math_value(result['firm_1_quantity'])}\\), then "
                    f"\\(Q={_math_value(result['total_quantity'])}\\) and \\(P={_math_value(result['market_price'])}\\)."
                ),
                "takeaway": "The equilibrium is obtained from best-response intersection, not from a payoff-matrix cell.",
                "trusted_tex": True,
            },
            {
                "kind": "boundary",
                "title": "Demand expansion",
                "setup": "Increase only the demand intercept and keep slope and marginal cost fixed.",
                "calculation": f"The new symmetric quantity is {_assignment('firm_1_quantity', alt_result['firm_1_quantity'])} and the new price is {_assignment('market_price', alt_result['market_price'])}.",
                "takeaway": comparison,
                "trusted_tex": True,
            },
        ],
        "figure_caption": "Cournot reaction functions intersect at the symmetric quantity equilibrium.",
        "figure_discussion": (
            "Plot \\(q_1\\) horizontally and \\(q_2\\) vertically. Each downward-sloping reaction function records one firm's optimal output for every rival output. "
            "Their intersection is the Nash equilibrium. A demand expansion shifts both reaction functions outward and moves the intersection to larger quantities."
        ),
    }


def _nash_equilibrium_content(
    setup: Mapping[str, object],
    result: Mapping[str, object],
    alt_result: Mapping[str, object],
    comparison: str,
) -> dict[str, object]:
    return {
        "development_title": "Best responses and mutual best-response cells",
        "development": (
            "Write each payoff cell as \\((u_R,u_C)\\). If the column player chooses \\(A\\), the row player compares "
            f"\\(u_R(A,A)={_math_value(setup['row_aa'])}\\) with \\(u_R(B,A)={_math_value(setup['row_ba'])}\\), so row "
            "action \\(A\\) is the best response. If the column player chooses \\(B\\), the row player compares "
            f"\\(u_R(A,B)={_math_value(setup['row_ab'])}\\) with \\(u_R(B,B)={_math_value(setup['row_bb'])}\\), so row "
            "action \\(B\\) is the best response.\n\n"
            "Now hold the row action fixed. Against row \\(A\\), the column player compares "
            f"\\(u_C(A,A)={_math_value(setup['column_aa'])}\\) with \\(u_C(A,B)={_math_value(setup['column_ab'])}\\), "
            "choosing \\(A\\). Against row \\(B\\), the comparison is "
            f"\\(u_C(B,A)={_math_value(setup['column_ba'])}\\) versus \\(u_C(B,B)={_math_value(setup['column_bb'])}\\), "
            "so \\(B\\) is the best response.\n\n"
            "The mutual best-response cells are therefore \\((A,A)\\) and \\((B,B)\\). Thus "
            f"{_assignment('nash_equilibrium_count', result['nash_equilibrium_count'])}. At \\((A,A)\\), neither player "
            f"can gain from a unilateral deviation, so {_assignment('unilateral_deviation_gain_at_aa', result['unilateral_deviation_gain_at_aa'])}. "
            "The sum of payoffs is descriptive here; it is not the criterion defining Nash equilibrium.\n\n"
            f"{comparison} The best-response ordering and both equilibrium cells are unchanged; only the payoff total at "
            "\\((A,A)\\) increases."
        ),
        "properties": [
            "A Nash equilibrium requires mutual best responses in the same cell.",
            "Best responses are found by comparing one player's payoffs while holding the other player's action fixed.",
            "Nash equilibrium does not require the equilibrium to maximize the sum of payoffs.",
            "This payoff matrix has two pure-strategy Nash equilibria: \\((A,A)\\) and \\((B,B)\\).",
            "Increasing a payoff without changing any best-response ordering leaves the equilibrium set unchanged.",
        ],
        "examples": [
            {
                "kind": "worked",
                "title": "Marking mutual best responses",
                "setup": "Use the four payoff pairs \\((4,4)\\), \\((0,1)\\), \\((1,0)\\), and \\((3,3)\\).",
                "calculation": (
                    "Row best responses are \\(A\\) against \\(A\\) and \\(B\\) against \\(B\\); column best responses "
                    "are the same. Their intersections are \\((A,A)\\) and \\((B,B)\\)."
                ),
                "takeaway": "There are two mutual best-response cells, so there are two pure-strategy Nash equilibria.",
                "trusted_tex": True,
            },
            {
                "kind": "boundary",
                "title": "Increasing one equilibrium payoff",
                "setup": "Raise only the row player's payoff at \\((A,A)\\) from \\(4\\) to \\(5\\).",
                "calculation": f"The equilibrium count remains {_assignment('nash_equilibrium_count', alt_result['nash_equilibrium_count'])}.",
                "takeaway": comparison,
                "trusted_tex": True,
            },
        ],
        "figure_caption": "Payoff matrix with row best responses, column best responses, and two mutual best-response cells.",
        "figure_discussion": (
            "Mark the row player's larger payoff within each column and the column player's larger payoff within each row. "
            "Cells carrying both marks are Nash equilibria. In this matrix, both \\((A,A)\\) and \\((B,B)\\) receive two "
            "marks. Raising the row payoff at \\((A,A)\\) changes its displayed payoff sum but does not move either mark, "
            "so the two-cell equilibrium set remains unchanged."
        ),
    }


def _international_trade_content(
    setup: Mapping[str, object],
    result: Mapping[str, object],
    alt_result: Mapping[str, object],
    comparison: str,
) -> dict[str, object]:
    return {
        "development_title": "Domestic demand, domestic supply, and imports at the world price",
        "development": (
            f"Domestic demand is \\(Q_d(P)={_math_value(setup['demand_intercept'])}-"
            f"{_math_value(setup['demand_slope'])}P\\), and domestic supply is "
            f"\\(Q_s(P)={_math_value(setup['supply_intercept'])}+{_math_value(setup['supply_slope'])}P\\). "
            f"The small open economy takes \\(P_w={_math_value(setup['world_price'])}\\) as given.\n\n"
            f"At that price, \\(Q_d(P_w)={_math_value(setup['demand_intercept'])}-"
            f"{_math_value(setup['demand_slope'])}({_math_value(setup['world_price'])})"
            f"={_math_value(result['domestic_demand'])}\\), while \\(Q_s(P_w)={_math_value(setup['supply_intercept'])}+"
            f"{_math_value(setup['supply_slope'])}({_math_value(setup['world_price'])})"
            f"={_math_value(result['domestic_supply'])}\\). Imports fill the horizontal gap: "
            f"\\(M=Q_d(P_w)-Q_s(P_w)={_math_value(result['imports'])}\\).\n\n"
            f"Autarky would instead equate domestic demand and supply, giving \\(P_A={_math_value(result['autarky_price'])}\\) "
            f"and \\(Q_A={_math_value(result['autarky_quantity'])}\\). Because \\(P_w<P_A\\), the country imports; the "
            "autarky intersection is a benchmark, not the open-economy allocation mechanism. These quantity calculations "
            "alone do not establish how gains from trade are distributed.\n\n"
            f"{comparison} At the unchanged world price, domestic supply remains fixed while the outward demand shift "
            "widens the import gap."
        ),
        "properties": [
            r"At the world price, imports are \(M=Q_d(P_w)-Q_s(P_w)\) when demand exceeds supply.",
            r"If \(P_w<P_A\), the country imports; if \(P_w>P_A\), it exports in this competitive small-country model.",
            "The autarky intersection determines the no-trade benchmark, not the quantities consumed and produced under trade.",
            "The import quantity is the horizontal distance between domestic demand and domestic supply at the same world price.",
            "Trade volume alone does not determine the distribution of gains or losses across consumers and producers.",
        ],
        "examples": [
            {
                "kind": "worked",
                "title": "Imports at a fixed world price",
                "setup": f"Take {_assignment_list(setup)}.",
                "calculation": (
                    f"{_assignment('domestic_demand', result['domestic_demand'])}, "
                    f"{_assignment('domestic_supply', result['domestic_supply'])}, and therefore "
                    f"{_assignment('imports', result['imports'])}."
                ),
                "takeaway": "Domestic consumption exceeds domestic production, and imports fill the difference at the world price.",
                "trusted_tex": True,
            },
            {
                "kind": "boundary",
                "title": "An outward demand shift",
                "setup": "Increase the demand intercept while holding the world price and supply curve fixed.",
                "calculation": (
                    f"The new quantities are {_assignment('domestic_demand', alt_result['domestic_demand'])}, "
                    f"{_assignment('domestic_supply', alt_result['domestic_supply'])}, and "
                    f"{_assignment('imports', alt_result['imports'])}."
                ),
                "takeaway": comparison,
                "trusted_tex": True,
            },
        ],
        "figure_caption": "Domestic demand and supply with a horizontal world-price line and the import gap.",
        "figure_discussion": (
            f"Draw the horizontal line \\(P=P_w={_math_value(setup['world_price'])}\\). Its intersection with demand gives "
            f"\\(Q_d(P_w)={_math_value(result['domestic_demand'])}\\), and its intersection with supply gives "
            f"\\(Q_s(P_w)={_math_value(result['domestic_supply'])}\\). The horizontal segment between those two quantities "
            f"is \\(M={_math_value(result['imports'])}\\). Keep the autarky intersection visually separate as a benchmark. "
            "After the demand shift, extend the demand endpoint and the import-gap segment while leaving the world-price line "
            "and supply endpoint fixed."
        ),
    }


def _continuous_mass_accumulation_content(
    setup: Mapping[str, object],
    calculation: Mapping[str, object],
    result: Mapping[str, object],
    alt_result: Mapping[str, object],
    comparison: str,
) -> dict[str, object]:
    return {
        "development_title": "Mass storage from inlet and outlet rates",
        "development": (
            "Draw one stationary control region and count every crossing rate as positive at its port. "
            "Mass conservation assigns inlet rates a positive contribution to storage and outlet rates a negative contribution, so "
            "\(dM_{\mathrm{cv}}/dt=\dot m_{\mathrm{in}}-\dot m_{\mathrm{out}}\).\n\n"
            f"The worked rates give \(dM_{{\mathrm{{cv}}}}/dt={_math_value(calculation['net_mass_flow'])}\). "
            f"Over \(\Delta t={_math_value(setup['duration'])}\), the stored-mass change is "
            f"\(\Delta M_{{\mathrm{{cv}}}}={_math_value(calculation['mass_change'])}\), hence "
            f"\(M_{{\mathrm{{cv}},f}}={_math_value(setup['initial_mass'])}+{_math_value(calculation['mass_change'])}"
            f"={_math_value(result['final_mass'])}\).\n\n"
            "The balance concerns mass storage rather than momentum transport: velocities and external forces do not enter this relation. "
            f"{comparison} The control-volume boundary and outlet rate remain fixed, so the steeper accumulation follows entirely from the larger inlet rate."
        ),
        "properties": [
            r"The storage rate is the algebraic balance (dot M_{mathrm{cv}}=dot m_{mathrm{in}}-dot m_{mathrm{out}}).",
            r"Equal inlet and outlet rates imply constant stored mass even though material continues crossing the boundary.",
            r"For constant rates, (Delta M_{mathrm{cv}}=(dot m_{mathrm{in}}-dot m_{mathrm{out}})Delta t).",
            "A negative net rate is admissible only while the computed stored mass remains nonnegative.",
            "Changing the control-volume boundary would change which crossings count as inlet or outlet and requires a new balance.",
        ],
        "examples": [
            {
                "kind": "worked",
                "title": "Stored mass after a finite interval",
                "setup": f"Use {_assignment_list(setup)}.",
                "calculation": (
                    f"The net storage rate is {_assignment('net_mass_flow', calculation['net_mass_flow'])}; "
                    f"the resulting change is {_assignment('mass_change', calculation['mass_change'])}, giving "
                    f"{_assignment('final_mass', result['final_mass'])}."
                ),
                "takeaway": "Because inflow exceeds outflow, stored mass rises linearly over the stated interval.",
                "trusted_tex": True,
            },
            {
                "kind": "boundary",
                "title": "Increasing the inlet rate",
                "setup": "Raise only the inlet mass-flow rate while preserving the outlet rate, duration, and control-volume boundary.",
                "calculation": f"The revised balance gives {_assignment('final_mass', alt_result['final_mass'])}.",
                "takeaway": comparison,
                "trusted_tex": True,
            },
        ],
        "figure_caption": "Stationary control region with inlet and outlet flux arrows, stored-mass readout, and accumulation graph.",
        "figure_discussion": (
            "Direct the inflow marker into the boundary and the outflow marker away from it. Label the stored-mass readout inside the boundary, "
            "then plot its linear change over the stated duration; the graph slope equals inlet rate minus outlet rate."
        ),
    }


def _continuous_mass_transfer_content(
    setup: Mapping[str, object],
    calculation: Mapping[str, object],
    result: Mapping[str, object],
    alt_result: Mapping[str, object],
    comparison: str,
) -> dict[str, object]:
    rate = float(setup["mass_flow_rate"])
    inlet = float(setup["inlet_velocity"])
    outlet = float(setup["outlet_velocity"])
    duration = float(setup["duration"])
    return {
        "development_title": "Steady momentum flow through a fixed control volume",
        "development": (
            "Choose a fixed control volume and one positive flow axis before assigning signs. The general momentum balance is "
            "\\(\\sum\\vec F_{\\mathrm{ext}}=d\\vec P_{\\mathrm{cv}}/dt"
            "+\\sum_{\\mathrm{out}}\\dot m\\vec v-\\sum_{\\mathrm{in}}\\dot m\\vec v\\). "
            "The force is the net external force on the material currently inside the boundary; forces exerted by that material "
            "on its surroundings have the opposite sign.\n\n"
            "For steady one-dimensional flow, momentum stored inside the fixed control volume does not change. With one inlet "
            "and one outlet carrying the same positive mass-flow-rate magnitude, the balance reduces to "
            "\\(F_{\\mathrm{ext}}=\\dot m(v_{\\mathrm{out}}-v_{\\mathrm{in}})\\). Velocities remain signed components in the "
            "chosen inertial frame: the inlet contribution is subtracted because it enters the control volume, whereas the "
            "outlet contribution is added because it leaves.\n\n"
            f"Here \\(\\dot m={_format_number(rate)}\\), \\(v_{{\\mathrm{{in}}}}={_format_number(inlet)}\\), and "
            f"\\(v_{{\\mathrm{{out}}}}={_format_number(outlet)}\\). The incoming momentum flux is "
            f"\\(\\dot m v_{{\\mathrm{{in}}}}={_math_value(calculation['momentum_rate_in'])}\\), and the outgoing flux is "
            f"\\(\\dot m v_{{\\mathrm{{out}}}}={_math_value(calculation['momentum_rate_out'])}\\). Therefore "
            f"\\(F_{{\\mathrm{{ext}}}}={_format_number(rate)}({_format_number(outlet)}-{_format_number(inlet)})"
            f"={_math_value(result['external_force'])}\\), directed along the positive axis. Over "
            f"\\(\\Delta t={_format_number(duration)}\\), the processed mass is "
            f"\\(\\dot m\\Delta t={_math_value(calculation['mass_processed'])}\\); duration changes this mass total but not "
            "the steady force.\n\n"
            "Dimensional analysis gives \\([\\dot m v]=(\\mathrm{mass}/\\mathrm{time})(\\mathrm{length}/\\mathrm{time})"
            "=\\mathrm{force}\\); these are the dimensions of force. "
            f"{comparison} With both port velocities fixed, the momentum-flux difference and required force scale linearly "
            "with mass-flow rate."
        ),
        "properties": [
            r"At steady state \(d\vec P_{\mathrm{cv}}/dt=0\); an unsteady control volume must retain the accumulation term.",
            r"For one inlet and one outlet with equal flow rate, \(F_{\mathrm{ext}}=\dot m(v_{\mathrm{out}}-v_{\mathrm{in}})\).",
            r"The port rate \(\dot m\) is positive by convention, while each velocity carries the sign of the selected axis.",
            r"Momentum flux \(\dot m v\) and external force have dimensions of mass times length per time squared.",
            "The system boundary determines which interactions count as external and which momentum crossings appear as inlet or outlet terms.",
        ],
        "examples": [
            {
                "kind": "worked",
                "title": "Force required by a steady velocity change",
                "setup": (
                    f"Take \\(\\dot m={_format_number(rate)}\\), "
                    f"\\(v_{{\\mathrm{{in}}}}={_format_number(inlet)}\\), "
                    f"\\(v_{{\\mathrm{{out}}}}={_format_number(outlet)}\\), and "
                    f"\\(\\Delta t={_format_number(duration)}\\)."
                ),
                "calculation": (
                    f"\\(\\dot m v_{{\\mathrm{{in}}}}={_math_value(calculation['momentum_rate_in'])}\\), "
                    f"\\(\\dot m v_{{\\mathrm{{out}}}}={_math_value(calculation['momentum_rate_out'])}\\), so "
                    f"{_assignment('external_force', result['external_force'])}. The processed mass is "
                    f"\\({_math_value(calculation['mass_processed'])}\\)."
                ),
                "takeaway": "The positive force supplies the increase in downstream momentum flux across the fixed boundary.",
                "trusted_tex": True,
            },
            {
                "kind": "boundary",
                "title": "Increasing the steady mass-flow rate",
                "setup": "Increase \\(\\dot m\\) while holding both signed port velocities, duration, and the control-volume boundary fixed.",
                "calculation": (
                    f"The revised momentum-flux difference requires "
                    f"{_assignment('external_force', alt_result['external_force'])}."
                ),
                "takeaway": comparison,
                "trusted_tex": True,
            },
        ],
        "figure_caption": "Fixed control volume with inlet, outlet, momentum-flux labels, and net external force.",
        "figure_discussion": (
            "Draw a closed, fixed boundary around the device and mark one positive axis. Place an inlet arrow crossing inward "
            f"with label \\(\\dot m v_{{\\mathrm{{in}}}}={_math_value(calculation['momentum_rate_in'])}\\) and an outlet arrow "
            f"crossing outward with label \\(\\dot m v_{{\\mathrm{{out}}}}={_math_value(calculation['momentum_rate_out'])}\\). "
            f"The external-force arrow points in the positive direction with {_assignment('external_force', result['external_force'])}. "
            "For the comparison, lengthen both flux arrows in proportion to \\(\\dot m\\) and lengthen the force arrow while "
            "leaving the boundary and port velocities unchanged."
        ),
        "result_statement": (
            f"For steady one-inlet, one-outlet flow, \\(F_{{\\mathrm{{ext}}}}=\\dot m"
            f"(v_{{\\mathrm{{out}}}}-v_{{\\mathrm{{in}}}})"
            f"={_format_number(rate)}({_format_number(outlet)}-{_format_number(inlet)})"
            f"={_math_value(result['external_force'])}\\). Over \\(\\Delta t={_format_number(duration)}\\), "
            f"\\({_math_value(calculation['mass_processed'])}\\) units of mass cross the control volume, and the flow is continuous."
        ),
    }


def _production_function_content(
    setup: Mapping[str, object],
    result: Mapping[str, object],
    alt_result: Mapping[str, object],
    comparison: str,
) -> dict[str, object]:
    technology = float(setup["technology"])
    labor = float(setup["labor"])
    capital = float(setup["capital"])
    alpha = float(setup["labor_share"])
    return {
        "development_title": "Cobb-Douglas output and marginal products",
        "development": (
            "The specified technology is the Cobb-Douglas production function "
            "\\(q=A L^{\\alpha}K^{1-\\alpha}\\), where \\(A>0\\), \\(L>0\\), \\(K>0\\), and "
            "\\(0<\\alpha<1\\). Output is determined by technology and physical inputs; no product price or input price is "
            "needed to calculate the production relation itself.\n\n"
            "Holding capital fixed and differentiating with respect to labor gives "
            "\\(MP_L=\\partial q/\\partial L=\\alpha A L^{\\alpha-1}K^{1-\\alpha}=\\alpha q/L\\). "
            "Holding labor fixed instead gives "
            "\\(MP_K=\\partial q/\\partial K=(1-\\alpha)A L^{\\alpha}K^{-\\alpha}=(1-\\alpha)q/K\\). "
            "Because the exponents sum to one, doubling both inputs doubles output; because each exponent lies between zero "
            "and one, either input has a diminishing marginal product when the other is fixed.\n\n"
            f"With \\(A={_format_number(technology)}\\), \\(L={_format_number(labor)}\\), "
            f"\\(K={_format_number(capital)}\\), and \\(\\alpha={_format_number(alpha)}\\), "
            f"\\(q={_format_number(technology)}({_format_number(labor)})^{{{_format_number(alpha)}}}"
            f"({_format_number(capital)})^{{{_format_number(1.0-alpha)}}}"
            f"={_math_value(result['output'])}\\). Hence "
            f"\\(MP_L={_format_number(alpha)}({_math_value(result['output'])})/{_format_number(labor)}"
            f"={_math_value(result['marginal_product_labor'])}\\) and "
            f"\\(MP_K={_format_number(1.0-alpha)}({_math_value(result['output'])})/{_format_number(capital)}"
            f"={_math_value(result['marginal_product_capital'])}\\).\n\n"
            f"{comparison} Since \\(A\\) multiplies the whole production function, holding \\(L\\), \\(K\\), and \\(\\alpha\\) "
            "fixed raises output and both marginal products in the same proportion."
        ),
        "properties": [
            r"The production relation is \(q=A L^\alpha K^{1-\alpha}\), with \(A,L,K>0\) and \(0<\alpha<1\).",
            r"The labor marginal product is \(MP_L=\alpha q/L\), calculated with capital fixed.",
            r"The capital marginal product is \(MP_K=(1-\alpha)q/K\), calculated with labor fixed.",
            "The exponents sum to one, so this specification has constant returns to scale in labor and capital.",
            "A technology increase shifts the entire production surface upward rather than moving the firm along one unchanged input slice.",
        ],
        "examples": [
            {
                "kind": "worked",
                "title": "Output and marginal products",
                "setup": (
                    f"Use \\(A={_format_number(technology)}\\), \\(L={_format_number(labor)}\\), "
                    f"\\(K={_format_number(capital)}\\), and \\(\\alpha={_format_number(alpha)}\\)."
                ),
                "calculation": (
                    f"\\(q={_math_value(result['output'])}\\), "
                    f"\\(MP_L=\\alpha q/L={_math_value(result['marginal_product_labor'])}\\), and "
                    f"\\(MP_K=(1-\\alpha)q/K={_math_value(result['marginal_product_capital'])}\\)."
                ),
                "takeaway": "Each marginal product is the local output gain from one more unit of its input while the other input remains fixed.",
                "trusted_tex": True,
            },
            {
                "kind": "boundary",
                "title": "An increase in total factor productivity",
                "setup": "Raise \\(A\\) while holding \\(L\\), \\(K\\), and \\(\\alpha\\) fixed.",
                "calculation": (
                    f"The shifted technology gives \\(q={_math_value(alt_result['output'])}\\), "
                    f"\\(MP_L={_math_value(alt_result['marginal_product_labor'])}\\), and "
                    f"\\(MP_K={_math_value(alt_result['marginal_product_capital'])}\\)."
                ),
                "takeaway": comparison,
                "trusted_tex": True,
            },
        ],
        "figure_caption": "Cobb-Douglas output slice with a marginal-product tangent and an upward technology shift.",
        "figure_discussion": (
            f"Plot labor \\(L\\) horizontally and output \\(q\\) vertically while fixing \\(K={_format_number(capital)}\\). "
            f"Mark the point \\((L,q)=({_format_number(labor)},{_math_value(result['output'])})\\) on the "
            f"\\(A={_format_number(technology)}\\) curve and draw its tangent with slope "
            f"\\(MP_L={_math_value(result['marginal_product_labor'])}\\). Draw the comparison technology as a second curve "
            f"above the first and mark \\(q={_math_value(alt_result['output'])}\\) at the same labor input. An isoquant inset "
            "may place labor and capital on its axes, but neither axis represents price or cost."
        ),
        "result_statement": (
            f"For \\(q=A L^\\alpha K^{{1-\\alpha}}\\) with \\(A={_format_number(technology)}\\), "
            f"\\(L={_format_number(labor)}\\), \\(K={_format_number(capital)}\\), and "
            f"\\(\\alpha={_format_number(alpha)}\\), \\(q={_math_value(result['output'])}\\), "
            f"\\(MP_L={_math_value(result['marginal_product_labor'])}\\), and "
            f"\\(MP_K={_math_value(result['marginal_product_capital'])}\\)."
        ),
    }


def _welfare_surplus_content(
    setup: Mapping[str, object],
    result: Mapping[str, object],
    alt_result: Mapping[str, object],
    comparison: str,
) -> dict[str, object]:
    mb_intercept = float(setup["marginal_benefit_intercept"])
    mb_slope = float(setup["marginal_benefit_slope"])
    mc_intercept = float(setup["marginal_cost_intercept"])
    mc_slope = float(setup["marginal_cost_slope"])
    mc_expression = (
        f"{_format_number(mc_intercept)}+Q"
        if math.isclose(mc_slope, 1.0)
        else f"{_format_number(mc_intercept)}+{_format_number(mc_slope)}Q"
    )
    return {
        "development_title": "Efficient trade and the surplus integral",
        "development": (
            f"The marginal-benefit schedule is \\(MB(Q)={_format_number(mb_intercept)}"
            f"-{_format_number(mb_slope)}Q\\), and marginal cost is "
            f"\\(MC(Q)={mc_expression}\\). "
            "Total surplus from the first \\(Q\\) units is "
            "\\(TS(Q)=\\int_0^Q[MB(q)-MC(q)]\\,dq\\). The surplus-maximizing interior quantity sets the integrand to zero "
            "at the margin, so \\(MB(Q^*)=MC(Q^*)\\).\n\n"
            f"Solving \\({_format_number(mb_intercept)}-{_format_number(mb_slope)}Q"
            f"={mc_expression}\\) gives "
            f"\\(Q^*={_math_value(result['efficient_quantity'])}\\). Substitution into either schedule gives "
            f"\\(P^*={_math_value(result['equilibrium_price'])}\\). Units below \\(Q^*\\) have marginal benefit above "
            "marginal cost; units beyond it would reduce total surplus.\n\n"
            f"Consumer surplus is the area between marginal benefit and price: "
            f"\\(CS=\\tfrac12({_format_number(mb_intercept)}-{_math_value(result['equilibrium_price'])})"
            f"({_math_value(result['efficient_quantity'])})={_math_value(result['CS'])}\\). "
            f"Producer surplus is the area between price and marginal cost: "
            f"\\(PS=\\tfrac12({_math_value(result['equilibrium_price'])}-{_format_number(mc_intercept)})"
            f"({_math_value(result['efficient_quantity'])})={_math_value(result['PS'])}\\). "
            f"The integral check is \\(TS=\\int_0^{{{_math_value(result['efficient_quantity'])}}}"
            f"[{_format_number(mb_intercept-mc_intercept)}-{_format_number(mb_slope+mc_slope)}q]\,dq"
            f"={_math_value(result['TS'])}=CS+PS\\).\n\n"
            f"{comparison} The higher marginal-benefit intercept shifts the demand/benefit schedule upward while marginal "
            f"cost is unchanged, moving the efficient quantity to \\({_math_value(alt_result['efficient_quantity'])}\\) and "
            f"raising total surplus to \\({_math_value(alt_result['TS'])}\\). This is an efficiency comparison under the "
            "stated surplus criterion; it does not by itself settle distributional or equity questions."
        ),
        "properties": [
            r"An interior surplus maximum satisfies \(MB(Q^*)=MC(Q^*)\).",
            r"Consumer surplus is \(\int_0^{Q^*}[MB(q)-P^*]\,dq\), the region above price and below marginal benefit.",
            r"Producer surplus is \(\int_0^{Q^*}[P^*-MC(q)]\,dq\), the region below price and above marginal cost.",
            r"Total surplus obeys \(TS=CS+PS=\int_0^{Q^*}[MB(q)-MC(q)]\,dq\).",
            "A larger total surplus is an efficiency result for this benchmark, not a claim that every participant receives a gain.",
        ],
        "examples": [
            {
                "kind": "worked",
                "title": "Linear marginal benefit and marginal cost",
                "setup": (
                    f"Use \\(MB(Q)={_format_number(mb_intercept)}-{_format_number(mb_slope)}Q\\) and "
                    f"\\(MC(Q)={mc_expression}\\)."
                ),
                "calculation": (
                    f"\\(Q^*={_math_value(result['efficient_quantity'])}\\), "
                    f"\\(P^*={_math_value(result['equilibrium_price'])}\\), "
                    f"\\(CS={_math_value(result['CS'])}\\), \\(PS={_math_value(result['PS'])}\\), and "
                    f"\\(TS={_math_value(result['TS'])}\\)."
                ),
                "takeaway": "The two surplus triangles exactly partition the gains from the efficient trades in this linear benchmark.",
                "trusted_tex": True,
            },
            {
                "kind": "boundary",
                "title": "An upward shift in marginal benefit",
                "setup": "Raise the marginal-benefit intercept while keeping both slopes and the marginal-cost schedule fixed.",
                "calculation": (
                    f"The new intersection gives \\(Q^*={_math_value(alt_result['efficient_quantity'])}\\), "
                    f"\\(P^*={_math_value(alt_result['equilibrium_price'])}\\), "
                    f"\\(CS={_math_value(alt_result['CS'])}\\), \\(PS={_math_value(alt_result['PS'])}\\), and "
                    f"\\(TS={_math_value(alt_result['TS'])}\\)."
                ),
                "takeaway": comparison,
                "trusted_tex": True,
            },
        ],
        "figure_caption": "Marginal benefit, marginal cost, efficient quantity, and consumer and producer surplus regions.",
        "figure_discussion": (
            f"Put quantity on the horizontal axis and marginal benefit or cost on the vertical axis. Draw "
            f"\\(MB={_format_number(mb_intercept)}-{_format_number(mb_slope)}Q\\) and "
            f"\\(MC={mc_expression}\\), marking their intersection at "
            f"\\((Q^*,P^*)=({_math_value(result['efficient_quantity'])},{_math_value(result['equilibrium_price'])})\\). "
            f"Shade the triangle above \\(P^*\\) and below \\(MB\\) as \\(CS={_math_value(result['CS'])}\\); shade the triangle "
            f"below \\(P^*\\) and above \\(MC\\) as \\(PS={_math_value(result['PS'])}\\). Draw the shifted marginal-benefit "
            "schedule as a dashed line and extend the two shaded regions to the new efficient intersection."
        ),
        "result_statement": (
            f"For \\(MB={_format_number(mb_intercept)}-{_format_number(mb_slope)}Q\\) and "
            f"\\(MC={mc_expression}\\), "
            f"\\(Q^*={_math_value(result['efficient_quantity'])}\\), "
            f"\\(P^*={_math_value(result['equilibrium_price'])}\\), "
            f"\\(CS={_math_value(result['CS'])}\\), \\(PS={_math_value(result['PS'])}\\), and "
            f"\\(TS={_math_value(result['TS'])}\\)."
        ),
    }


def _learner_assumptions(domain: str, spec: Any) -> list[str]:
    """Return maintained model conditions, never prerequisite topic labels."""

    authored = getattr(spec, "learner_assumptions", ())
    if authored:
        return [str(item).strip() for item in authored if str(item).strip()]
    by_kind = {
        "conservation_law": "The system boundary is fixed and external transfers are counted with one sign convention.",
        "constitutive_law": "The state remains inside the response regime where the constitutive law applies.",
        "constraint": "All constrained quantities satisfy the same geometric or material constraint at once.",
        "definition": "Coordinates, reference levels, and units remain fixed throughout the evaluation.",
        "differential_equation": "The evolution law applies on the interval considered and the initial condition selects one solution.",
        "dynamical_law": "The selected body or system is evaluated in one inertial frame with all modeled external interactions included.",
        "geometric_relation": "All components use one coordinate basis and one orientation convention.",
        "interaction_law": "Interaction forces are assigned to the distinct bodies on which they act.",
        "kinematic_relation": "The coordinate frame and time origin are fixed, and the stated acceleration model applies over the interval.",
        "wave_relation": "The medium parameters are uniform over the displayed interval and the phase convention is fixed.",
    }
    fallback = (
        "The model's coordinate, unit, boundary, and validity conventions remain fixed during the calculation."
        if domain == "physics"
        else "The market definition, time period, and omitted shifters remain fixed during the calculation."
    )
    return [by_kind.get(spec.statement_kind, fallback)]


def build_model_note_payload(
    topic: str,
    domain: str,
    source_contexts: Sequence[str] = (),
) -> dict[str, object]:
    """Build concise lecture-note prose from an exact model and scenario."""

    canonical_domain, spec, scenario = _resolve(topic, domain)
    comparison, changed_key, old_value, new_value = _comparison_scenario(scenario)
    setup, calculation, result = _scenario_parts(canonical_domain, scenario)
    alt_setup, alt_calculation, alt_result = _scenario_parts(
        canonical_domain, comparison
    )
    if spec.model_id == "continuous_mass_accumulation":
        # The scenario retains the initial value for cross-layer audit probes,
        # but learner-facing consequences should not present an input as output.
        result.pop("initial_mass", None)
        alt_result.pop("initial_mass", None)
        result.pop("fixed_control_volume", None)
        alt_result.pop("fixed_control_volume", None)
    title = _concept_title(topic, spec.model_id)
    definition_lead = _MODEL_DEFINITIONS[spec.model_id]
    prerequisites = [_humanize(item) for item in spec.prerequisites]
    learner_assumptions = _learner_assumptions(canonical_domain, spec)
    assumption_text = " ".join(learner_assumptions)
    symbols = [row.as_dict() for row in spec.exact_symbol_rows]
    setup_names = list(setup)
    result_names = list(result)
    comparison_contract = _comparison_analysis(
        spec.model_id,
        spec.statement_kind,
        changed_key,
        old_value,
        new_value,
        result,
        alt_result,
    )
    comparison_text = str(comparison_contract["text"])
    comparison_focus = str(comparison_contract["focus_output"])
    changed_outputs = [str(key) for key in comparison_contract["changed_outputs"]]

    source_vocabulary = [
        title,
        *prerequisites,
        *(row["meaning"] for row in symbols),
        *(_humanize(token) for token in spec.required_example_tokens),
        *(_humanize(token) for token in spec.required_figure_tokens),
    ]
    source_digests, course_framing = _source_evidence(
        source_contexts,
        title=title,
        vocabulary=source_vocabulary,
    )

    if canonical_domain == "physics":
        primitive_sentence = (
            f"The initial data and parameters are {_quantity_list(setup_names)}; "
            f"the model then determines {_quantity_list(result_names)}."
        )
        interpretation = _physics_interpretation(spec, result)
        comparison_heading = _comparison_heading(spec, canonical_domain)
        consistency_sentence = _physics_consistency_sentence(spec, result_names)
        property_interpretation = _physics_property_sentence(
            spec, comparison_focus
        )
        physical_takeaway = _physics_property_sentence(spec, comparison_focus)
        worked_takeaway = (
            f"The calculation determines {_quantity_list(result_names)} from {_quantity_list(setup_names)}; "
            f"{physical_takeaway[:1].lower() + physical_takeaway[1:]}"
        )
    else:
        primitive_sentence = (
            f"The primitives {_quantity_list(setup_names)} are taken as given, while "
            f"{_quantity_list(result_names)} are the model outputs determined from them."
        )
        interpretation = _economics_interpretation(spec.model_id, result)
        comparison_heading = _comparison_heading(spec, canonical_domain)
        consistency_sentence = _economics_consistency_sentence(
            spec, result_names
        )
        if spec.model_id in _ECON_WELFARE_MODELS:
            property_interpretation = (
                "Any efficiency claim uses the stated surplus or social objective; the numerical predictions alone "
                "do not determine how gains or losses are distributed."
            )
        else:
            property_interpretation = (
                f"The values of {_quantity_list(result_names)} are conditional predictions, not interpersonal welfare comparisons."
            )
        worked_takeaway = (
            f"The calculation obtains {_quantity_list(result_names)} from {_quantity_list(setup_names)} under "
            "the maintained market conditions."
        )

    definition = (
        f"{definition_lead}\n\n"
        f"\\textbf{{{_relation_heading(spec)}.}} \\({spec.canonical_formula}\\). "
        f"{_symbol_explanation(symbols)}\n\n"
        f"\\textbf{{Maintained assumptions.}} {assumption_text} {primitive_sentence}"
    )

    consequence_heading = _SECOND_HEADING_BY_MODEL.get(
        spec.model_id,
        _SECOND_RESULT_HEADINGS.get(
            spec.statement_kind, "Mathematical consequence"
        ),
    )
    results = [
        {
            "id": f"{spec.model_id}-relation",
            "name": _relation_heading(spec),
            "statement": (
                f"Under the maintained assumptions, \\({spec.canonical_formula}\\) relates "
                f"{_quantity_list(setup_names)} to {_quantity_list(result_names)}."
            ),
        },
        {
            "id": f"{spec.model_id}-consequence",
            "name": consequence_heading,
            "statement": (
                f"For {_assignment_list(setup)}, the relation gives {_assignment_list(result)}."
            ),
        },
        {
            "id": f"{spec.model_id}-comparison",
            "name": comparison_heading,
            "statement": (
                f"Changing {_quantity_name(changed_key)} requires recomputing "
                f"{_quantity_list(changed_outputs)}; the boundary example reports that comparison."
            ),
        },
    ]

    complete_derivation = _complete_worked_derivation(
        spec.model_id, setup, calculation, result
    )
    if complete_derivation is not None:
        calculation_sentence = complete_derivation
    elif calculation:
        calculation_sentence = (
            f"Evaluating the intermediate expressions gives {_assignment_list(calculation)}."
        )
    else:
        calculation_sentence = _economics_calculation_sentence(
            spec, setup_names, result_names
        )
    structural_property = _structure_property(spec)
    development_opening = _development_opening(
        spec, setup_names, result_names, learner_assumptions
    )
    bound_consequence = (
        f"The computed consequence of the equation is {_assignment_list(result)}. "
        if spec.model_id == "total_surplus"
        else ""
    )
    worked_development = (
        f"{calculation_sentence} {consistency_sentence} "
        f"{bound_consequence}"
        f"The worked example below substitutes {_quantity_list(setup_names)} in sequence. "
        f"Verify the derivation by checking the units and reference conventions for {_quantity_list(result_names)}, "
        f"then substitute those outputs back into \\({spec.canonical_formula}\\). "
        f"A sign, feasibility, boundary, or accounting check on {_quantity_list(result_names)} should agree with "
        f"the model condition before interpretation. In the computed state, verify "
        f"{_oxford([_humanize(name) for name in result_names])} for inconsistent units or inadmissible values."
    )
    comparison_development = (
        f"Vary {_quantity_name(changed_key)} alone, rebuild the same relation, and compare "
        f"{_quantity_list(changed_outputs)} while holding the other primitives fixed."
    )
    development = _labeled_development(
        spec,
        development_opening,
        structural_property,
        worked_development,
        interpretation,
        comparison_development,
    )

    properties = [
        structural_property,
        consistency_sentence,
        property_interpretation,
        f"Treat {_quantity_list(setup_names)} as primitives and derive {_quantity_list(result_names)} without feeding those outputs back as assumptions.",
        f"A one-input sensitivity check preserves the model structure while testing {_quantity_name(comparison_focus)}.",
    ]

    worked_case_intro = _worked_case_intro(spec, setup)
    examples = [
        {
            "kind": "worked",
            "title": f"Worked example: {title}",
            "setup": worked_case_intro,
            "calculation": (
                f"Evaluate \\({spec.canonical_formula}\\) for this state. "
                f"{calculation_sentence} Check {_quantity_list(result_names)} against the reported consequence, "
                f"including the units of {_quantity_name(result_names[0])}, the sign convention for "
                f"{_quantity_name(result_names[-1])}, feasibility conditions, and relevant limiting behavior."
            ),
            "takeaway": worked_takeaway,
            "trusted_tex": True,
        },
        {
            "kind": "boundary",
            "title": f"Changing {_humanize(changed_key)}",
            "setup": (
                f"Change only {_quantity_name(changed_key)}: replace {_assignment(changed_key, old_value)} by "
                f"{_assignment(changed_key, new_value)}."
            ),
            "calculation": (
                f"Re-evaluating \\({spec.canonical_formula}\\) gives "
                + (
                    f"{_assignment_list(alt_calculation)}, followed by "
                    if alt_calculation
                    else ""
                )
                + f"{_assignment_list(alt_result)}."
            ),
            "takeaway": (
                f"The change isolates the effect of {_quantity_name(changed_key)} on "
                f"{_quantity_list(changed_outputs)} while the stated assumptions remain in force."
            ),
            "trusted_tex": True,
        },
    ]

    figure_caption, figure_discussion = _generic_figure_content(
        canonical_domain,
        title,
        spec,
        scenario,
        result,
        changed_key,
        comparison_focus,
        comparison_text,
    )

    special: dict[str, object] | None = None
    if spec.model_id == "rigid_body_motion":
        special = _rigid_body_content(
            title,
            setup,
            calculation,
            result,
            changed_key,
            old_value,
            new_value,
            alt_result,
            comparison_text,
        )
    elif spec.model_id == "consumer_choice":
        special = _consumer_choice_content(
            title,
            setup,
            result,
            changed_key,
            old_value,
            new_value,
            alt_result,
            comparison_text,
        )
    elif spec.model_id == "continuous_mass_accumulation":
        special = _continuous_mass_accumulation_content(
            setup, calculation, result, alt_result, comparison_text
        )
    elif spec.model_id == "continuous_mass_transfer":
        special = _continuous_mass_transfer_content(
            setup, calculation, result, alt_result, comparison_text
        )
    elif spec.model_id == "rocket_equation":
        special = _rocket_equation_content(
            setup, calculation, result, alt_result, comparison_text
        )
    elif spec.model_id == "potential_energy_diagram":
        special = _potential_diagram_content(
            setup, calculation, result, alt_result, comparison_text
        )
    elif spec.model_id == "waves":
        special = _waves_content(
            setup, calculation, result, alt_result, comparison_text
        )
    elif spec.model_id == "tax_incidence":
        special = _tax_incidence_content(
            setup, result, alt_result, comparison_text
        )
    elif spec.model_id in {"oligopoly", "oligopoly_collusion"}:
        special = _oligopoly_content(
            title, setup, result, alt_result, comparison_text
        )
    elif spec.model_id == "nash_equilibrium":
        special = _nash_equilibrium_content(
            setup, result, alt_result, comparison_text
        )
    elif spec.model_id == "international_trade":
        special = _international_trade_content(
            setup, result, alt_result, comparison_text
        )
    elif spec.model_id == "production_function":
        special = _production_function_content(
            setup, result, alt_result, comparison_text
        )
    elif spec.model_id == "welfare_surplus":
        special = _welfare_surplus_content(
            setup, result, alt_result, comparison_text
        )

    if special is not None:
        development_title = str(special["development_title"])
        development = str(special["development"])
        properties = list(special["properties"])
        examples = list(special["examples"])
        figure_caption = str(special["figure_caption"])
        figure_discussion = str(special.get("figure_discussion", figure_discussion))
        if "result_statement" in special:
            results[1]["statement"] = str(special["result_statement"])
    else:
        development_title = _DEVELOPMENT_TITLES.get(
            spec.statement_kind, f"Evaluating and interpreting {title}"
        )

    model_scenario = scenario.as_dict()
    comparison_scenario = comparison.as_dict()
    exported_result = model_scenario.get(
        "result", model_scenario.get("results", {})
    )
    exported_comparison_result = comparison_scenario.get(
        "result", comparison_scenario.get("results", {})
    )
    payload: dict[str, object] = {
        "topic": topic.strip(),
        "definition": definition,
        "results": results,
        "development_title": development_title,
        "development": development,
        "development_kind": spec.statement_kind.replace("_", " "),
        "properties": properties,
        "algorithms": [],
        "extensions": [],
        "examples": examples,
        "symbols": symbols,
        "canonical_formula": spec.canonical_formula,
        "prerequisites": list(spec.prerequisites),
        "learner_assumptions": learner_assumptions,
        "visual_kind": spec.visual_kind,
        "figure": True,
        "figure_caption": figure_caption,
        "figure_discussion": figure_discussion,
        "course_framing": course_framing,
        "content_basis": "source-derived-domain-scaffold",
        "trusted_tex": True,
        "model_id": spec.model_id,
        "model_scenario": model_scenario,
        "comparison_model_scenario": comparison_scenario,
        "numeric_evidence": {
            "setup": model_scenario["setup"],
            "calculation": model_scenario.get("calculation", {}),
            "result": exported_result,
            "comparison_setup": comparison_scenario["setup"],
            "comparison_calculation": comparison_scenario.get(
                "calculation", {}
            ),
            "comparison_result": exported_comparison_result,
            "changed_input": changed_key,
        },
        "comparison_contract": comparison_contract,
        "source_evidence_digests": source_digests,
    }
    if canonical_domain == "physics" and "gyroscope" in topic.casefold():
        payload.update({
            "definition": (
                "A rapidly spinning gyroscope carries angular momentum along its spin axis. "
                "A torque perpendicular to that angular momentum changes its direction and produces precession.\n\n"
                r"\textbf{Steady-precession relation.} \(\Omega_p=\tau/L=Mgr/(I\omega)\)."
            ),
            "results": [
                {
                    "id": "gyroscope-precession-law",
                    "name": "Precession law",
                    "statement": r"When \(\vec\tau\perp\vec L\), the spin axis precesses with \(\Omega_p=\tau/L\).",
                },
                {
                    "id": "gyroscope-numeric-rate",
                    "name": "Computed precession rate",
                    "statement": r"For \(L=12\,\mathrm{kg\,m^2/s}\) and \(\tau=3\,\mathrm{N\,m}\), \(\Omega_p=0.25\,\mathrm{rad/s}\).",
                },
                {
                    "id": "gyroscope-direction",
                    "name": "Direction check",
                    "statement": r"The right-hand rule for \(\vec\tau=d\vec L/dt\) fixes the direction in which the spin axis precesses.",
                },
            ],
            "development_title": "From torque to precession",
            "development": (
                r"\textbf{Vector change.} Over a short interval, \(d\vec L=\vec\tau\,dt\). "
                r"For steady precession the magnitude of \(\vec L\) is approximately fixed while its tip moves through angle \(d\phi\), so \(|d\vec L|=L\,d\phi\). "
                r"Equating magnitudes gives \(\tau\,dt=L\,d\phi\), hence \(\Omega_p=d\phi/dt=\tau/L\). "
                r"For a wheel whose center of mass is distance \(r\) from the support, gravity supplies \(\tau=Mgr\); with \(L=I\omega\), \(\Omega_p=Mgr/(I\omega)\). "
                r"Substituting \(\tau=3\,\mathrm{N\,m}\) and \(L=12\,\mathrm{kg\,m^2/s}\) gives \(0.25\,\mathrm{rad/s}\)."
            ),
            "properties": [
                r"A perpendicular torque redirects \(\vec L\) instead of changing its magnitude to first order.",
                r"Larger spin angular momentum produces slower precession for the same torque.",
                r"The torque and angular momentum must be measured about the same support point.",
                r"The steady-precession formula assumes a rapidly spinning rotor and neglects nutation in the ideal model.",
            ],
            "examples": [
                {
                    "kind": "worked",
                    "title": "Worked example: steady gyroscope precession",
                    "setup": r"A rotor has \(L=12\,\mathrm{kg\,m^2/s}\), and gravity produces \(\tau=3\,\mathrm{N\,m}\) about the support.",
                    "calculation": r"Use \(\Omega_p=\tau/L\): \(\Omega_p=3/12=0.25\,\mathrm{rad/s}\).",
                    "takeaway": r"The torque turns the spin axis sideways at \(0.25\,\mathrm{rad/s}\); it does not directly erase the spin angular momentum.",
                },
                {
                    "kind": "comparison",
                    "title": "Comparison: doubling the rotor spin",
                    "setup": r"Keep the gravitational torque fixed at \(3\,\mathrm{N\,m}\), but double the spin angular momentum from \(12\) to \(24\,\mathrm{kg\,m^2/s}\).",
                    "calculation": r"The new rate is \(\Omega_p=3/24=0.125\,\mathrm{rad/s}\), exactly half the original precession rate.",
                    "takeaway": r"At fixed torque, increasing spin angular momentum makes the axis precess more slowly because \(\Omega_p\) is inversely proportional to \(L\).",
                },
            ],
            "symbols": [
                {"symbol": r"\vec L", "meaning": "spin angular momentum about the support"},
                {"symbol": r"\vec\tau", "meaning": "external torque about the same support"},
                {"symbol": r"\Omega_p", "meaning": "precession angular speed"},
                {"symbol": r"\omega", "meaning": "rotor spin angular speed"},
            ],
            "canonical_formula": r"\Omega_p=\frac{\tau}{L}=\frac{Mgr}{I\omega}",
            "figure_caption": "Gyroscope precession: gravity supplies torque perpendicular to the spin angular momentum, so the axis turns around the vertical.",
            "figure_discussion": "Read the three vectors together: the spin axis carries angular momentum, gravity creates torque about the support, and the resulting vector change advances the precession direction.",
        })
    for key in (
        "definition", "results", "development_title", "development", "properties",
        "examples", "figure_caption", "figure_discussion", "course_framing",
    ):
        payload[key] = _diversify_learner_prose(payload[key], f"{canonical_domain}:{topic}")
    return payload


def _visible_strings(payload: Mapping[str, object]) -> list[str]:
    strings = [str(payload.get(key, "")) for key in _VISIBLE_SCALAR_FIELDS]
    for result in payload.get("results", []):
        if isinstance(result, Mapping):
            strings.extend(str(result.get(key, "")) for key in ("name", "statement"))
    for value in payload.get("properties", []):
        strings.append(str(value))
    for example in payload.get("examples", []):
        if isinstance(example, Mapping):
            strings.extend(
                str(example.get(key, ""))
                for key in ("title", "setup", "calculation", "takeaway")
            )
    for row in payload.get("symbols", []):
        if isinstance(row, Mapping):
            strings.extend(str(row.get(key, "")) for key in ("symbol", "meaning"))
    return [value for value in strings if value.strip()]


def visible_note_word_count(payload: Mapping[str, object]) -> int:
    """Count learner-visible prose while ignoring ids and machine metadata."""

    if not isinstance(payload, Mapping):
        raise TypeError("payload must be a mapping")
    text = " ".join(_visible_strings(payload))
    text = re.sub(r"\\[A-Za-z]+\*?", " ", text)
    text = text.replace("_", " ")
    return len(re.findall(r"\b[A-Za-z0-9]+(?:'[A-Za-z0-9]+)?\b", text))


__all__ = ["build_model_note_payload", "visible_note_word_count"]
