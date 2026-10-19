#!/usr/bin/env python3
"""Check (and optionally set up) everything the course-shorts skills need.

    python3 doctor.py            # report what is present / missing
    python3 doctor.py --install  # create ~/.course-shorts/venv and pip-install the Python deps

It looks for a ready interpreter in $COURSE_SHORTS_PYTHON, then ~/.course-shorts/venv
($COURSE_SHORTS_VENV), then a .venv at the repository root, then the current python3.

Prints a final line `PY=<interpreter>`; use that interpreter for every script in
the course-* skills. System tools (ffmpeg, a TeX engine, cairo/pango) are
reported with the install command for this platform but never installed
automatically.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

VENV = Path(os.environ.get("COURSE_SHORTS_VENV", Path.home() / ".course-shorts" / "venv"))
REQUIREMENTS = ["manim>=0.18", "pymupdf>=1.24", "edge-tts>=7.0", "Pillow>=10"]
OPTIONAL = ["piper-tts>=1.2"]
EXTRA_PATHS = ["/Library/TeX/texbin", "/opt/homebrew/bin", "/usr/local/bin"]


def venv_python() -> Path:
    return VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def which(name: str) -> str | None:
    return shutil.which(name, path=os.pathsep.join([os.environ.get("PATH", "")] + EXTRA_PATHS))


def python_ok(exe: str) -> bool:
    try:
        out = subprocess.run([exe, "-c", "import sys; print(sys.version_info >= (3, 10))"],
                             capture_output=True, text=True, timeout=20)
        return out.stdout.strip() == "True"
    except (OSError, subprocess.TimeoutExpired):
        return False


def find_base_python() -> str | None:
    for name in ("python3.13", "python3.12", "python3.11", "python3.10", "python3"):
        exe = which(name)
        if exe and python_ok(exe):
            return exe
    return None


def module_report(exe: str) -> dict[str, str | None]:
    code = (
        "import importlib, json\n"
        "out = {}\n"
        "for m in ['manim', 'pymupdf', 'PIL', 'numpy', 'edge_tts', 'piper']:\n"
        "    try:\n"
        "        mod = importlib.import_module(m)\n"
        "        out[m] = getattr(mod, '__version__', 'ok')\n"
        "    except Exception:\n"
        "        out[m] = None\n"
        "try:\n"
        "    import manimpango\n"
        "    fonts = set(manimpango.list_fonts())\n"
        "    out['font'] = next((f for f in ['Inter', 'Avenir Next', 'Helvetica Neue', 'Arial', 'DejaVu Sans'] if f in fonts), None)\n"
        "except Exception:\n"
        "    out['font'] = None\n"
        "print(json.dumps(out))\n"
    )
    try:
        proc = subprocess.run([exe, "-c", code], capture_output=True, text=True, timeout=120)
        return json.loads(proc.stdout.strip().splitlines()[-1])
    except Exception:
        return {}


def system_hints() -> dict[str, str]:
    if platform.system() == "Darwin":
        return {"ffmpeg": "brew install ffmpeg", "tex": "brew install tectonic",
                "cairo": "brew install cairo pango pkg-config"}
    return {"ffmpeg": "sudo apt install ffmpeg  (or your package manager)",
            "tex": "install tectonic (https://tectonic-typesetting.github.io) or: sudo apt install texlive-latex-extra texlive-pictures",
            "cairo": "sudo apt install libcairo2-dev libpango1.0-dev pkg-config"}


def install() -> int:
    base = find_base_python()
    if not base:
        print("error: need Python 3.10+ on PATH to create the venv", file=sys.stderr)
        return 1
    if not venv_python().exists():
        print(f"creating {VENV} with {base}")
        VENV.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([base, "-m", "venv", str(VENV)], check=True)
    py = str(venv_python())
    subprocess.run([py, "-m", "pip", "install", "-q", "--upgrade", "pip"], check=True)
    print("installing " + " ".join(REQUIREMENTS))
    proc = subprocess.run([py, "-m", "pip", "install", "-q", *REQUIREMENTS])
    if proc.returncode != 0:
        hint = system_hints()["cairo"]
        print(f"error: pip install failed. Manim needs cairo/pango headers: {hint}", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--install", action="store_true", help=f"create/update the venv at {VENV}")
    ap.add_argument("--with-piper", action="store_true", help="also install the offline Piper voice engine")
    args = ap.parse_args(argv)
    if args.install:
        if install() != 0:
            return 1
        if args.with_piper:
            subprocess.run([str(venv_python()), "-m", "pip", "install", "-q", *OPTIONAL], check=False)

    repo_venv = Path(__file__).resolve().parents[3] / ".venv" / "bin" / "python"
    candidates = [c for c in (os.environ.get("COURSE_SHORTS_PYTHON"), str(venv_python()), str(repo_venv))
                  if c and Path(c).exists()]
    candidates.append(sys.executable)
    py = next((c for c in candidates if module_report(c).get("manim")), candidates[0])
    mods = module_report(py)
    hints = system_hints()
    rows: list[tuple[str, bool, str, bool]] = []  # name, ok, detail, required
    rows.append(("python>=3.10", python_ok(py), py, True))
    for mod, label in (("manim", "manim"), ("pymupdf", "pymupdf"), ("PIL", "Pillow"), ("numpy", "numpy")):
        rows.append((label, bool(mods.get(mod)), str(mods.get(mod) or f"run: python3 {Path(__file__).name} --install"), True))
    rows.append(("edge-tts (default voice)", bool(mods.get("edge_tts")), str(mods.get("edge_tts") or "pip install edge-tts"), False))
    rows.append(("piper (offline voice)", bool(mods.get("piper")), str(mods.get("piper") or "doctor.py --install --with-piper"), False))
    ffmpeg = which("ffmpeg")
    has_ass = False
    if ffmpeg:
        filters = subprocess.run([ffmpeg, "-hide_banner", "-filters"], capture_output=True, text=True).stdout
        has_ass = " ass " in filters
    rows.append(("ffmpeg + ffprobe", bool(ffmpeg and which("ffprobe")), ffmpeg or hints["ffmpeg"], True))
    rows.append(("ffmpeg libass (burned captions)", has_ass, "ok" if has_ass else "rebuild/install ffmpeg with libass", False))
    tex = next((which(n) for n in ("tectonic", "latexmk", "pdflatex") if which(n)), None)
    rows.append(("TeX engine (notes + video maths)", bool(tex), tex or hints["tex"], True))
    rows.append(("UI font", bool(mods.get("font")), str(mods.get("font") or "install Inter or DejaVu Sans"), False))

    missing_required = False
    for name, ok, detail, required in rows:
        mark = "ok " if ok else ("MISSING" if required else "optional")
        print(f"  [{mark:^8}] {name:<34} {detail}")
        missing_required |= required and not ok
    if missing_required:
        print("\nSome required pieces are missing; fix them before rendering.")
    print(f"PY={py}")
    return 1 if missing_required else 0


if __name__ == "__main__":
    sys.exit(main())
