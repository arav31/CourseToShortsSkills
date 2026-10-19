import json
import re

import pytest

from conftest import ROOT, SKILLS

SKILL_DIRS = sorted(p.parent for p in SKILLS.glob("*/SKILL.md"))


def frontmatter(path):
    match = re.match(r"^---\n(.*?)\n---\n", path.read_text(), re.S)
    assert match, f"{path} has no frontmatter"
    return dict(line.split(": ", 1) for line in match.group(1).splitlines())


def test_expected_skills_present():
    assert [d.name for d in SKILL_DIRS] == ["course-notes", "course-plan", "course-reels", "course-to-shorts", "course-video"]


@pytest.mark.parametrize("skill", SKILL_DIRS, ids=lambda d: d.name)
def test_skill_metadata_and_links(skill):
    text = (skill / "SKILL.md").read_text()
    fm = frontmatter(skill / "SKILL.md")
    assert fm["name"] == skill.name
    assert 80 < len(fm["description"]) <= 1024
    assert len(text.splitlines()) < 500, "keep SKILL.md short; move detail into references/"
    for ref in re.findall(r"\]\(((?:references|assets|scripts)/[^)]+)\)", text):
        assert (skill / ref).exists(), f"{skill.name}: broken link {ref}"
    for script in re.findall(r"\$SKILL_DIR/scripts/([\w.]+)", text):
        assert (skill / "scripts" / script).exists(), f"{skill.name}: missing script {script}"
    assert (skill / "agents" / "openai.yaml").exists()


@pytest.mark.parametrize("manifest", [".claude-plugin/plugin.json", ".claude-plugin/marketplace.json",
                                      ".codex-plugin/plugin.json", ".agents/plugins/marketplace.json"])
def test_plugin_manifests_parse(manifest):
    data = json.loads((ROOT / manifest).read_text())
    assert data["name"] == "course-to-shorts"
