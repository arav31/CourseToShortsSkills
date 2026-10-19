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


def test_uncovered_unit_must_be_skipped_with_reason(plan_run):
    edit_plan(plan_run, lambda p: p["shorts"].pop())
    code, result = run_check(plan_run)
    assert code == 1
    assert any("u02" in e and "coverage" in e for e in result["errors"])
    edit_plan(plan_run, lambda p: p.__setitem__("skipped_units", [{"unit": "u02", "reason": "elimination is notes-only here"}]))
    code, result = run_check(plan_run)
    assert code == 0, result["errors"]


def test_skipped_unknown_unit_and_long_title_fail(plan_run):
    def bad(plan):
        plan["skipped_units"] = [{"unit": "u99", "reason": "does not exist in the outline"}]
        plan["shorts"][0]["title"] = "x" * 61
    edit_plan(plan_run, bad)
    code, result = run_check(plan_run)
    assert code == 1
    assert any("u99" in e for e in result["errors"]) and any("60" in e for e in result["errors"])


def test_step_numbers_alone_are_not_concrete(plan_run):
    def filler(plan):
        plan["shorts"][0]["worked_example"] = {"setup": "Look at the idea.",
                                               "steps": ["Step 1: think about it.", "Step 2: apply the rule."],
                                               "result": "Step 3: conclude."}
    edit_plan(plan_run, filler)
    code, result = run_check(plan_run)
    assert code == 1
    assert any("no concrete values" in e for e in result["errors"])
