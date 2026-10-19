#!/usr/bin/env python3
"""Render one Manim scene class and report failures in terms of the scene file.

    python run_scene.py <scene.py> <ClassName> --media-dir <dir> --output <name>

Used by render.py instead of the Manim CLI so that a crash prints the failing
line of scene.py and the exception, not a page of framework traceback.
Quality/resolution comes from shortkit (SHORTKIT_QUALITY).
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
import traceback
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("scene", type=Path)
    ap.add_argument("cls")
    ap.add_argument("--media-dir", type=Path, required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    scene_path = args.scene.resolve()
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.path.insert(0, str(scene_path.parent))

    from manim import config

    config.media_dir = str(args.media_dir)
    config.input_file = str(scene_path)
    config.output_file = args.output
    config.progress_bar = "none"
    config.verbosity = "WARNING"
    config.write_to_movie = True
    config.format = "mp4"
    # Manim's partial-movie cache advances the scene clock by exact run times but replays whole
    # frames, so a cached re-render drifts from the narration. Always render fresh.
    config.disable_caching = True
    try:
        spec = importlib.util.spec_from_file_location(scene_path.stem, scene_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[scene_path.stem] = module
        spec.loader.exec_module(module)
        scene_cls = getattr(module, args.cls)
        scene_cls().render()
    except Exception as exc:  # report in scene terms
        frames = traceback.extract_tb(exc.__traceback__)
        mine = [f for f in frames if Path(f.filename).resolve() == scene_path]
        print("".join(traceback.format_exception(exc)), file=sys.stderr)  # full detail for the log
        print("\n=== scene error ===", file=sys.stderr)
        for f in mine[-3:]:
            print(f"{scene_path.name} line {f.lineno}, in {f.name}: {f.line}", file=sys.stderr)
        if not mine:
            last = frames[-1] if frames else None
            if last:
                print(f"{Path(last.filename).name} line {last.lineno}, in {last.name}: {last.line}", file=sys.stderr)
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
