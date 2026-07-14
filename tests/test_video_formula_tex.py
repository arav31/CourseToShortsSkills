from __future__ import annotations

import ast
import json
import re
import textwrap
import unittest

from tools import stem_course


class _FakeMobject:
    def __init__(self) -> None:
        self.width = 1.0
        self.height = 0.3

    def add_background_rectangle(self, **_kwargs: object) -> None:
        return None

    def scale(self, factor: float) -> "_FakeMobject":
        self.width *= factor
        self.height *= factor
        return self


class _RecordingMathTex(_FakeMobject):
    calls: list[str] = []

    def __init__(self, tex: str, **_kwargs: object) -> None:
        super().__init__()
        self.tex = tex
        type(self).calls.append(tex)


class _FailingMathTex(_RecordingMathTex):
    def __init__(self, tex: str, **kwargs: object) -> None:
        super().__init__(tex, **kwargs)
        raise RuntimeError("controlled TeX compiler failure")


class _RecordingText(_FakeMobject):
    calls: list[str] = []

    def __init__(self, text: str, **_kwargs: object) -> None:
        super().__init__()
        self.text = text
        type(self).calls.append(text)


def _formula_harness(mathtex: type[_FakeMobject] = _RecordingMathTex):
    namespace: dict[str, object] = {
        "json": json,
        "re": re,
        "MathTex": mathtex,
        "Text": _RecordingText,
    }
    source = "class FormulaHarness:\n" + textwrap.indent(stem_course.MANIM_SCENE_HELPERS, "    ")
    exec(compile(source, "<formula-harness>", "exec"), namespace)
    harness = namespace["FormulaHarness"]()
    harness.ensure_semantic_tex_backend = lambda: "test-semantic-tex"
    return harness


class VideoFormulaTexTests(unittest.TestCase):
    def setUp(self) -> None:
        _RecordingMathTex.calls.clear()
        _FailingMathTex.calls.clear()
        _RecordingText.calls.clear()

    def assert_mathtex(self, source: str, expected: str) -> None:
        harness = _formula_harness()
        rendered = harness.formula_block(source, "flattened plain fallback")

        self.assertEqual(_RecordingMathTex.calls, [expected])
        self.assertEqual(_RecordingText.calls, [])
        self.assertEqual(rendered._formula_render_mode, "mathtex")
        self.assertEqual(rendered._formula_tex_source, expected)

    def test_homomorphism_preserves_varphi_and_factor_spacing(self) -> None:
        formula = r"\varphi(ab)=\varphi(a)\varphi(b)"
        expected = r"\varphi(ab) = \varphi(a)\,\varphi(b)"

        self.assertEqual(stem_course.sanitize_formula_latex(formula), expected)
        self.assert_mathtex(expected, expected)

    def test_coset_preserves_set_builder_braces_and_membership(self) -> None:
        formula = "gH={gh:h\u2208H}"
        expected = r"gH = \{gh \mid h \in H\}"

        self.assertEqual(stem_course.sanitize_formula_latex(formula), expected)
        self.assert_mathtex(expected, expected)

    def test_subgroup_relation_uses_semantic_relation_symbol(self) -> None:
        expected = r"H \leq G"

        self.assertEqual(stem_course.sanitize_formula_latex("H\u2264G"), expected)
        self.assert_mathtex(expected, expected)

    def test_bmatrix_multiplication_keeps_rows_columns_and_subscripts(self) -> None:
        formula = (
            r"A\vec{x}="
            r"\begin{bmatrix}1&2\\3&4\end{bmatrix}"
            r"\begin{bmatrix}x_1\\x_2\end{bmatrix}"
        )
        expected = (
            r"A\vec{x} = "
            r"\begin{bmatrix}1&2\\3&4\end{bmatrix}\,"
            r"\begin{bmatrix}x_1\\x_2\end{bmatrix}"
        )

        self.assertEqual(stem_course.sanitize_formula_latex(formula), expected)
        self.assert_mathtex(expected, expected)

    def test_vector_coordinate_regression_uses_mathtex_subscripts(self) -> None:
        formula = "x = (x_1, x_2, ..., x_n)"
        expected = r"x = (x_1, x_2, \cdots, x_n)"

        self.assert_mathtex(formula, expected)

    def test_radical_regression_uses_mathtex_sqrt(self) -> None:
        formula = "sqrt(3^2 + 4^2) = 5"
        expected = r"\sqrt{3^2 + 4^2} = 5"

        self.assertEqual(stem_course.sanitize_formula_latex(formula), expected)
        self.assert_mathtex(formula, expected)

    def test_economics_and_physics_notation_remain_semantic(self) -> None:
        economics = r"\frac{\partial Q_d}{\partial P}=-b"
        physics = r"\Delta p=F\Delta t"

        self.assertEqual(
            stem_course.sanitize_formula_latex(economics),
            r"\frac{\partial Q_d}{\partial P} = -b",
        )
        self.assertEqual(
            stem_course.sanitize_formula_latex(physics),
            r"\Delta p = F\Delta t",
        )
        self.assert_mathtex(economics, economics)
        _RecordingMathTex.calls.clear()
        self.assert_mathtex(physics, physics)

    def test_required_newton_semantic_equation_uses_structured_vector_fallback(self) -> None:
        harness = _formula_harness(_FailingMathTex)
        source = r"\frac{\lvert a_A\rvert}{\lvert a_B\rvert}=\frac{m_B}{m_A}=1.5"
        structured = _FakeMobject()
        structured._formula_render_mode = "structured_vector_math"
        structured._formula_tex_source = source
        structured._formula_tex_backend = "manim-structured-math"
        harness.physics_structured_math_mob = lambda *_args, **_kwargs: structured

        rendered = harness.physics_math_mob(source, "plain fallback must not render", require_mathtex=True)

        self.assertEqual(_FailingMathTex.calls, [source])
        self.assertEqual(_RecordingText.calls, [])
        self.assertIs(rendered, structured)
        self.assertEqual(rendered._formula_render_mode, "structured_vector_math")
        self.assertEqual(rendered._formula_tex_source, source)
        self.assertEqual(rendered._formula_tex_backend, "manim-structured-math")

    def test_paired_scalar_kinematics_uses_readable_structured_fallback_without_latex(self) -> None:
        try:
            import manim
        except ImportError as exc:  # pragma: no cover - the production renderer requires Manim
            self.skipTest(str(exc))

        namespace = dict(vars(manim))
        namespace.update({"json": json, "re": re, "MathTex": _FailingMathTex})
        source = "class FormulaHarness:\n" + textwrap.indent(stem_course.MANIM_SCENE_HELPERS, "    ")
        exec(compile(source, "<structured-formula-harness>", "exec"), namespace)
        harness = namespace["FormulaHarness"]()
        formula = r"x(t) = x_0+v_0t+\frac{1}{2}at^2,\quad v(t) = v_0+at"

        rendered = harness.physics_math_mob(
            formula,
            "plain fallback must not render",
            font_size=58,
            max_width=7.35,
            max_height=1.45,
            min_height=0.72,
            require_mathtex=True,
        )

        self.assertEqual(_FailingMathTex.calls, [formula])
        self.assertEqual(rendered._formula_render_mode, "structured_vector_math")
        self.assertEqual(rendered._formula_tex_source, formula)
        self.assertEqual(rendered._formula_tex_backend, "manim-structured-math")
        self.assertIn("equation_list", rendered._structured_math_features)
        self.assertIn("fraction", rendered._structured_math_features)
        self.assertIn("subscript", rendered._structured_math_features)
        self.assertIn("superscript", rendered._structured_math_features)
        self.assertLessEqual(rendered.width, 7.35 + 1e-6)
        self.assertLessEqual(rendered.height, 1.45 + 1e-6)

        comma_formula = r"y(t)=y_0+u_0t+\frac{1}{2}gt^2, u(t)=u_0+gt"
        comma_rendered = harness.physics_math_mob(
            comma_formula,
            "plain fallback must not render",
            font_size=58,
            max_width=7.35,
            max_height=1.45,
            require_mathtex=True,
        )
        self.assertEqual(_FailingMathTex.calls, [formula, comma_formula])
        self.assertEqual(comma_rendered._formula_tex_source, comma_formula)
        self.assertIn("equation_list", comma_rendered._structured_math_features)
        self.assertIn("fraction", comma_rendered._structured_math_features)
        self.assertIn("subscript", comma_rendered._structured_math_features)
        self.assertIn("superscript", comma_rendered._structured_math_features)

        circular_formula = r"v=\omega R,\quad T=\frac{2\pi}{\omega}"
        circular_rendered = harness.physics_math_mob(
            circular_formula,
            "plain fallback must not render",
            font_size=58,
            max_width=7.35,
            max_height=1.45,
            require_mathtex=True,
        )
        self.assertEqual(circular_rendered._formula_tex_source, circular_formula)
        self.assertIn("equation_list", circular_rendered._structured_math_features)
        self.assertIn("fraction", circular_rendered._structured_math_features)
        self.assertLessEqual(circular_rendered.width, 7.35 + 1e-6)

    def test_vector_decomposition_and_normalization_use_structured_offline_math(self) -> None:
        try:
            import manim
        except ImportError as exc:  # pragma: no cover - the production renderer requires Manim
            self.skipTest(str(exc))

        namespace = dict(vars(manim))
        namespace.update({"json": json, "re": re, "MathTex": _FailingMathTex})
        source = "class FormulaHarness:\n" + textwrap.indent(stem_course.MANIM_SCENE_HELPERS, "    ")
        exec(compile(source, "<structured-vector-formula-harness>", "exec"), namespace)
        harness = namespace["FormulaHarness"]()
        formula = (
            r"\vec u = u_x\hat i+u_y\hat j,\quad"
            r"\hat u = \frac{\vec u}{\lVert\vec u\rVert}"
        )

        rendered = harness.physics_math_mob(
            formula,
            "raw vector formula must not render",
            font_size=58,
            max_width=7.35,
            max_height=1.55,
            require_mathtex=True,
        )

        self.assertEqual(_FailingMathTex.calls, [formula])
        self.assertEqual(_RecordingText.calls, [])
        self.assertEqual(rendered._formula_render_mode, "structured_vector_math")
        self.assertEqual(rendered._formula_tex_source, formula)
        self.assertEqual(rendered._formula_tex_backend, "manim-structured-math")
        for feature in (
            "equation_list",
            "component_decomposition",
            "unit_vector_normalization",
            "vector_arrow",
            "hat",
            "subscript",
            "fraction",
            "norm",
        ):
            self.assertIn(feature, rendered._structured_math_features)
        self.assertLessEqual(rendered.width, 7.35 + 1e-6)
        self.assertLessEqual(rendered.height, 1.55 + 1e-6)

    def test_newton_runtime_formula_sources_are_canonical_mathtex(self) -> None:
        harness = _formula_harness()
        sources = (
            r"\vec{F}_{B\to A}=-6\,\mathrm{N}\,\hat{\mathbf{x}}",
            r"\vec{a}_{A}=\frac{\vec{F}_{B\to A}}{m_A}",
            r"\vec{a}_{A}=-3\,\mathrm{m\,s^{-2}}",
            r"\frac{\lvert a_A\rvert}{\lvert a_B\rvert}=\frac{m_B}{m_A}=1.5",
        )

        for source in sources:
            with self.subTest(source=source):
                rendered = harness.physics_math_mob(source, "must not fall back", require_mathtex=True)
                self.assertEqual(rendered._formula_tex_source, source)
                self.assertEqual(rendered._formula_render_mode, "mathtex")

        self.assertEqual(_RecordingMathTex.calls, list(sources))
        self.assertEqual(_RecordingText.calls, [])

    def test_newton_mathtex_succeeds_when_tectonic_preflight_fails(self) -> None:
        harness = _formula_harness()
        preflight_calls: list[bool] = []

        def failing_preflight() -> str:
            preflight_calls.append(True)
            raise RuntimeError("tectonic network initialization panic")

        harness.ensure_semantic_tex_backend = failing_preflight
        source = r"\vec{a}_{A}=\frac{\vec{F}_{B\to A}}{m_A}"
        rendered = harness.physics_math_mob(source, "must not fall back", require_mathtex=True)

        self.assertEqual(preflight_calls, [])
        self.assertEqual(_RecordingMathTex.calls, [source])
        self.assertEqual(_RecordingText.calls, [])
        self.assertEqual(rendered._formula_tex_source, source)
        self.assertEqual(rendered._formula_render_mode, "mathtex")
        self.assertEqual(rendered._formula_tex_backend, "manim-mathtex")

    def test_cases_and_aligned_environments_are_not_flattened(self) -> None:
        cases = r"f(x)=\begin{cases}x^2&x\geq0\\-x&x<0\end{cases}"
        aligned = r"\begin{aligned}a&=b+c\\&=d\end{aligned}"

        self.assertIn(r"\begin{cases}", stem_course.sanitize_formula_latex(cases))
        self.assertIn(r"\\", stem_course.sanitize_formula_latex(cases))
        self.assertEqual(stem_course.sanitize_formula_latex(aligned), aligned.replace("=", " = "))

    def test_compile_failure_uses_one_semantic_attempt_then_unicode_fallback(self) -> None:
        harness = _formula_harness(_FailingMathTex)
        semantic = r"\varphi(ab) = \varphi(a)\,\varphi(b)"
        rendered = harness.formula_block(semantic, "varphi(ab)=varphi(a)varphi(b)")

        self.assertEqual(_FailingMathTex.calls, [semantic])
        self.assertEqual(len(_RecordingText.calls), 1)
        self.assertIn("\u03c6(ab) = \u03c6(a) \u03c6(b)", _RecordingText.calls[0])
        self.assertNotIn("varphi", _RecordingText.calls[0])
        self.assertEqual(rendered._formula_render_mode, "text_fallback")
        self.assertIn("controlled TeX compiler failure", rendered._formula_tex_error)

    def test_compile_failure_fallback_keeps_sets_and_physics_tokens_separate(self) -> None:
        harness = _formula_harness(_FailingMathTex)

        coset = harness.formula_block(r"gH = \{gh \mid h \in H\}", "gH = gh:h in H")
        impulse = harness.formula_block(r"\Delta p = F\Delta t", "Delta p = F Delta t")

        self.assertEqual(coset.text, "gH = {gh | h ∈ H}")
        self.assertEqual(impulse.text, "Δ p = F Δ t")

    def test_heap_floor_notation_remains_readable_after_tex_failure(self) -> None:
        harness = _formula_harness(_FailingMathTex)
        formula = r"parent(i) = \lfloor(i - 1)/2\rfloor"

        rendered = harness.formula_block(formula, "parent index")

        self.assertEqual(rendered.text, "parent(i) = ⌊(i - 1) / 2⌋")
        self.assertNotIn("lfloor", rendered.text)
        self.assertNotIn("rfloor", rendered.text)
        self.assertEqual(stem_course.formula_unicode_text(formula), rendered.text)

    def test_hash_modulo_and_declared_operators_survive_tex_failure(self) -> None:
        harness = _formula_harness(_FailingMathTex)
        examples = {
            r"h(k)=k\bmod 5": "h(k) = k mod 5",
            r"a\equiv b\pmod{7}": "a ≡ b (mod 7)",
            r"\gcd(18,12)=6": "gcd(18, 12) = 6",
            r"\det(A)=0": "det(A) = 0",
        }

        for source, expected in examples.items():
            with self.subTest(source=source):
                rendered = harness.formula_block(source, expected)
                self.assertEqual(rendered.text, expected)
                self.assertNotRegex(rendered.text, r"\\[A-Za-z]+")

        self.assertFalse(stem_course.formula_has_unknown_macros(r"h(k)=k\bmod m"))

    def test_nested_modulus_argument_survives_tex_failure(self) -> None:
        harness = _formula_harness(_FailingMathTex)
        formula = r"(X+a)^{31}\equiv X^{31}+a\pmod{31,\,X^{29}-1}"
        expected = "(X + a)³¹ ≡ X³¹ + a (mod 31, X²⁹ - 1)"

        rendered = harness.formula_block(formula, expected)

        self.assertEqual(rendered.text, expected)
        self.assertEqual(stem_course.formula_unicode_text(formula), expected)
        self.assertNotRegex(rendered.text, r"\\[A-Za-z]+")

    def test_complexity_fallback_preserves_log_operator_and_approximation(self) -> None:
        harness = _formula_harness(_FailingMathTex)
        formula = r"n\log_2 n \approx 10{,}000"

        rendered = harness.formula_block(formula, "n log base 2 n is about 10,000")

        self.assertEqual(rendered.text, "n log₂ n ≈ 10,000")
        self.assertNotIn("approx", rendered.text)
        self.assertEqual(stem_course.formula_unicode_text(formula), rendered.text)

        theta = harness.formula_block(r"T(n,k)=\Theta(n+k)", "T(n,k) = Theta(n+k)")
        self.assertEqual(theta.text, "T(n, k) = \u0398(n + k)")
        self.assertNotIn(r"\Theta", stem_course.plain_math(r"T(n,k)=\Theta(n+k)"))

        relaxation = harness.formula_block(
            r"d[v]\leftarrow\min(d[v],d[u]+w(u,v))",
            "update the distance label",
        )
        self.assertEqual(relaxation.text, "d[v] \u2190 min(d[v], d[u] + w(u, v))")
        self.assertNotIn("arrow", relaxation.text)

    def test_group_fallbacks_have_no_raw_tex_command_residue(self) -> None:
        harness = _formula_harness(_FailingMathTex)
        examples = (
            r"S_n",
            r"\tau\;\text{first}",
            r"(\sigma\circ\tau)(1)=2",
            r"G/\ker\varphi\cong\operatorname{im}\varphi",
            r"\operatorname{Rot}(\square)\cong\mathbb{Z}/4\mathbb{Z}",
            r"90^{\circ}",
        )

        for source in examples:
            rendered = harness.formula_fallback_text(source, source)
            self.assertIsNone(harness.group_math_residue(rendered), rendered)

    def test_economics_fallback_commands_have_unicode_or_plain_renderings(self) -> None:
        harness = _formula_harness(_FailingMathTex)
        examples = (
            r"x \Longleftrightarrow y",
            r"\bar{P}=4",
            r"\bar P=4",
            r"\sum_i MB_i=MC",
            r"\underline{P}=6",
            r"x \succeq y",
        )

        for source in examples:
            rendered = harness.formula_fallback_text(source, source)
            self.assertNotRegex(rendered, r"\\[A-Za-z]+")

    def test_text_fallback_uses_font_safe_alphabetic_scripts(self) -> None:
        harness = _formula_harness(_FailingMathTex)

        rendered = harness.formula_fallback_text(
            r"C_{i,j}=\min_k(C_{i,k}+C_{k+1,j})",
            "C(i,j) = min(left + right)",
        )

        self.assertIn("C₍i, j₎", rendered)
        self.assertIn("min₍k₎", rendered)
        self.assertNotIn(chr(0x2096), rendered)
        self.assertNotIn(chr(0x2C7C), rendered)

    def test_group_math_gate_blocks_fused_command_fragments(self) -> None:
        harness = _formula_harness()
        malformed = ("tautext first", "ocirc", "mathrm", "Gcong H", "90^circ", "phicong")
        valid = (r"S_n", r"\tau\;\text{first}", r"\sigma\circ\tau", r"G\cong H", r"90^{\circ}")

        for source in malformed:
            self.assertIsNotNone(harness.group_raw_math_source_residue(source), source)
        for source in valid:
            self.assertIsNone(harness.group_raw_math_source_residue(source), source)

    def test_generated_scene_fixture_passes_semantic_tex_to_formula_block(self) -> None:
        short = {
            "index": 1,
            "concept": "Homomorphisms",
            "hook": "A homomorphism preserves the group operation.",
            "intuition": "Map first or combine first; the result agrees.",
            "formula": r"\varphi(ab)=\varphi(a)\varphi(b)",
            "plain_formula": "phi(ab) = phi(a) phi(b)",
            "prerequisites": ["groups"],
            "misconception": "It need not be injective.",
            "worked_example": {
                "setup": "Map integers to parity.",
                "calculation": "phi(3+5)=phi(3)+phi(5).",
                "takeaway": "The operation is preserved.",
            },
            "question_prompt": {
                "question": "What must the map preserve?",
                "answer": "The group operation.",
            },
            "visual_type": "group_homomorphism",
        }
        scene_source = stem_course.manim_scene(short, "FormulaTexFixture", stem_course.build_animation_plan(short))
        tree = ast.parse(scene_source)
        constants = [
            node.args[0].value
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "formula_block"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ]

        self.assertIn(r"\varphi(ab) = \varphi(a)\,\varphi(b)", constants)
        self.assertIn("import json", scene_source)
        self.assertIn("tectonic-fitz", scene_source)


if __name__ == "__main__":
    unittest.main()
