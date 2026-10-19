import json

import check_plan


def run_check(run, *extra):
    code = check_plan.main([str(run), *extra])
    return code, json.loads((run / "plan_check.json").read_text())


def edit_plan(run, fn):
    path = run / "short_plan.json"
    plan = json.loads(path.read_text())
    fn(plan)
    path.write_text(json.dumps(plan))


def test_valid_plan_passes(plan_run):
    code, result = run_check(plan_run)
    assert code == 0, result["errors"]
    assert result["status"] == "pass"
    assert result["shorts"] == 2 and result["units"] == 2


def test_forward_prerequisite_fails(plan_run):
    edit_plan(plan_run, lambda p: p["shorts"][0].__setitem__("prerequisites", ["s02"]))
    code, result = run_check(plan_run)
    assert code == 1
    assert any("prerequisite s02" in e for e in result["errors"])


def test_reused_example_fails(plan_run):
    def reuse(plan):
        plan["shorts"][1]["worked_example"] = dict(plan["shorts"][0]["worked_example"])
    edit_plan(plan_run, reuse)
    code, result = run_check(plan_run)
    assert code == 1
    assert any("identical to s01" in e for e in result["errors"])


def test_placeholder_example_fails(plan_run):
    def vague(plan):
        plan["shorts"][0]["worked_example"] = {"setup": "Choose a small example.",
                                               "steps": ["Work through the definition.", "TBD"],
                                               "result": "It works."}
    edit_plan(plan_run, vague)
    code, result = run_check(plan_run)
    assert code == 1
    assert any("placeholder" in e for e in result["errors"])


def test_missing_source_file_fails(plan_run):
    outline = json.loads((plan_run / "outline.json").read_text())
    outline["units"][0]["sources"] = ["sources/999-missing.txt"]
    (plan_run / "outline.json").write_text(json.dumps(outline))
    code, result = run_check(plan_run)
    assert code == 1
    assert any("does not exist" in e for e in result["errors"])


def test_uncovered_unit_is_a_warning_then_strict_error(plan_run):
    edit_plan(plan_run, lambda p: p["shorts"].pop())
    code, result = run_check(plan_run)
    assert code == 0
    assert any("unit u02" in w for w in result["warnings"])
    code, _ = run_check(plan_run, "--strict")
    assert code == 1
