"""shortkit: a small toolkit for 9:16 Manim explainer shorts.

Scene files start with ``from shortkit import *`` (which also re-exports Manim)
and declare their narration as a literal ``BEATS`` list:

    from shortkit import *

    BEATS = [
        ("hook", "What does multiplying a matrix by a vector actually do?"),
        ("columns", "Read A as two arrows: its columns."),
    ]

    class Short(ShortScene):
        def construct(self):
            with self.beat("hook"):
                self.title("Ax mixes columns")
                ...
            with self.beat("columns"):
                ...

What the toolkit gives a scene:

* Frame + zones: the frame is 9 x 16 scene units (x in [-4.5, 4.5], y in
  [-8, 8]). ``TITLE_ZONE``, ``STAGE`` and ``CAPTION_ZONE`` keep content clear of
  the Reels/Shorts UI and of the burned-in captions.
* ``tex()``: real LaTeX via tectonic (or pdflatex/xelatex/lualatex) -> PDF -> SVG,
  so formulas look like LaTeX even without a full TeX install.
* ``self.beat(id)``: each beat lasts at least as long as its narration clip
  (from timing.json written by voice.py), so voice and picture stay in sync.
* Layout checks at the end of every beat: text outside the safe area, text in
  the caption band, overlapping text and too-small text are written to the
  render trace and reported by render.py.

Environment variables (set by render.py):
    SHORTKIT_QUALITY  preview (540x960 @15fps) | final (1080x1920 @30fps)
    SHORTKIT_TIMING   timing.json from voice.py (optional; estimates otherwise)
    SHORTKIT_TRACE    where to write the beat/layout trace JSON
    SHORTKIT_CACHE    LaTeX SVG cache dir (default ~/.cache/shortkit)
    SHORTKIT_FONT     preferred UI font family
"""

from __future__ import annotations

import ast as _ast
import contextlib as _contextlib
import hashlib as _hashlib
import inspect as _inspect
import json as _json
import os as _os
import re as _re
import shutil as _shutil
import subprocess as _subprocess
import sys as _sys
import tempfile as _tempfile
import textwrap as _textwrap
from dataclasses import dataclass as _dataclass
from pathlib import Path as _Path

import numpy as np
from manim import *  # noqa: F401,F403 - re-exported for scene files
from manim import config

_sys.path.insert(0, str(_Path(__file__).resolve().parent))
import beatlib as _beatlib  # noqa: E402

# --------------------------------------------------------------------------
# Render settings
# --------------------------------------------------------------------------

SHORTKIT_VERSION = "2.1"
QUALITY = _os.environ.get("SHORTKIT_QUALITY", "preview")
_PRESETS = {"preview": (540, 960, 15), "final": (1080, 1920, 30)}
_PX_W, _PX_H, _FPS = _PRESETS.get(QUALITY, _PRESETS["preview"])
config.pixel_width = _PX_W
config.pixel_height = _PX_H
config.frame_rate = _FPS
config.frame_height = 16.0
config.frame_width = 9.0

# --------------------------------------------------------------------------
# Palette: dark canvas, colour carries meaning
# --------------------------------------------------------------------------

BG = "#0E1118"
INK = "#ECEFF4"        # primary text
MUTED = "#9AA4B2"      # secondary text, axes, scaffolding
GRID = "#263042"       # background grid lines
BLUE_K = "#58C4DD"     # given objects / inputs
YELLOW_K = "#F4D35E"   # the operation or rule being applied
GREEN_K = "#83C167"    # results and conclusions
RED_K = "#FC6255"      # contrast, counterexamples, errors
PURPLE_K = "#B28DFF"
ORANGE_K = "#FF9F43"
INPUT, RULE, RESULT, ALERT = BLUE_K, YELLOW_K, GREEN_K, RED_K

config.background_color = BG


def _pick_font() -> str:
    try:
        import manimpango

        available = set(manimpango.list_fonts())
    except Exception:  # pragma: no cover - depends on system fonts
        available = set()
    for name in (_os.environ.get("SHORTKIT_FONT"), "Inter", "Avenir Next", "Helvetica Neue",
                 "Helvetica", "Arial", "DejaVu Sans", "Noto Sans", "Liberation Sans"):
        if name and name in available:
            return name
    return ""


FONT = _pick_font()


class Size:
    """Font sizes tuned for a phone held at arm's length (1080x1920)."""

    TITLE = 48
    HEADLINE = 46
    BODY = 38
    LABEL = 34
    SMALL = 30


MIN_FONT_SIZE = 28

# --------------------------------------------------------------------------
# Zones
# --------------------------------------------------------------------------


@_dataclass(frozen=True)
class Zone:
    name: str
    left: float
    right: float
    bottom: float
    top: float

    @property
    def width(self) -> float:
        return self.right - self.left

    @property
    def height(self) -> float:
        return self.top - self.bottom

    @property
    def center(self) -> np.ndarray:
        return np.array([(self.left + self.right) / 2, (self.bottom + self.top) / 2, 0.0])

    def point(self, fx: float = 0.5, fy: float = 0.5) -> np.ndarray:
        """Point at fractional position (0,0)=bottom-left, (1,1)=top-right."""
        return np.array([self.left + fx * self.width, self.bottom + fy * self.height, 0.0])

    def rows(self, *weights: float, gap: float = 0.25) -> list["Zone"]:
        """Split top-to-bottom into bands with the given relative heights."""
        weights = weights or (1.0, 1.0)
        usable = self.height - gap * (len(weights) - 1)
        out, top = [], self.top
        for i, w in enumerate(weights):
            h = usable * w / sum(weights)
            out.append(Zone(f"{self.name}.row{i}", self.left, self.right, top - h, top))
            top -= h + gap
        return out

    def cols(self, *weights: float, gap: float = 0.25) -> list["Zone"]:
        """Split left-to-right into columns with the given relative widths."""
        weights = weights or (1.0, 1.0)
        usable = self.width - gap * (len(weights) - 1)
        out, left = [], self.left
        for i, w in enumerate(weights):
            wd = usable * w / sum(weights)
            out.append(Zone(f"{self.name}.col{i}", left, left + wd, self.bottom, self.top))
            left += wd + gap
        return out

    def fit(self, mob: Mobject, buff: float = 0.1, upscale: bool = True,
            max_scale: float | None = None, align: str = "center") -> Mobject:
        """Scale ``mob`` to fit inside the zone and move it there.

        ``upscale=True`` grows small diagrams so the main object dominates the
        stage; pass ``upscale=False`` for text so it never balloons.
        ``align`` is "center", "top" or "bottom".
        """
        avail_w, avail_h = self.width - 2 * buff, self.height - 2 * buff
        ratios = []
        if mob.width > 1e-6:
            ratios.append(avail_w / mob.width)
        if mob.height > 1e-6:
            ratios.append(avail_h / mob.height)
        if ratios:
            s = min(ratios)
            if not upscale:
                s = min(s, 1.0)
            if max_scale is not None:
                s = min(s, max_scale)
            if abs(s - 1.0) > 1e-3:
                mob.scale(s)
        if align == "top":
            mob.move_to(self.center).align_to(self.point(0.5, 1.0) + DOWN * buff, UP)
        elif align == "bottom":
            mob.move_to(self.center).align_to(self.point(0.5, 0.0) + UP * buff, DOWN)
        else:
            mob.move_to(self.center)
        return mob

    def contains(self, mob: Mobject, tol: float = 0.03) -> bool:
        return (mob.get_left()[0] >= self.left - tol and mob.get_right()[0] <= self.right + tol
                and mob.get_bottom()[1] >= self.bottom - tol and mob.get_top()[1] <= self.top + tol)

    def outline(self, color: str = RED_K) -> DashedVMobject:
        rect = Rectangle(width=self.width, height=self.height, stroke_color=color, stroke_width=2)
        return DashedVMobject(rect.move_to(self.center), num_dashes=60)


FRAME_ZONE = Zone("frame", -4.5, 4.5, -8.0, 8.0)
# Keep clear of the platform UI: ~240 px at the top, ~370 px at the bottom.
SAFE = Zone("safe", -4.1, 4.1, -4.9, 6.0)
TITLE_ZONE = Zone("title", -4.1, 4.1, 5.05, 6.0)
STAGE = Zone("stage", -4.1, 4.1, -2.7, 4.8)
# Burned-in narration captions live here; the right edge stays clear of the
# like/comment/share column.
CAPTION_ZONE = Zone("caption", -4.0, 3.4, -4.9, -2.9)

# --------------------------------------------------------------------------
# Text
# --------------------------------------------------------------------------


def _mark_text(mob: Mobject, font_size: float, label: str) -> Mobject:
    """Tag a text object and every glyph in it with its owner.

    Ownership lives on the glyphs because Manim may dissolve groups on screen
    (animating a slice such as ``eq[0][3:]`` splits every group containing those
    glyphs); the layout checker regroups glyphs by owner instead of trusting groups.
    """
    mob._sk_text = True
    mob._sk_font_size = float(font_size)
    mob._sk_base_height = max(mob.height, 1e-6)
    mob._sk_label = label[:48]
    for member in mob.get_family():
        member._sk_owner = mob
    return mob


def text(s: str, size: float = Size.BODY, color: str = INK, width: float | None = None,
         weight: str = NORMAL, t2c: dict | None = None, line_spacing: float = 0.8) -> Text:
    """Plain words (no maths). Wraps to ``width`` scene units when given.

    For anything containing symbols, subscripts or equations use ``tex()``.
    """
    kwargs = dict(font=FONT, font_size=size, color=color, weight=weight,
                  line_spacing=line_spacing, disable_ligatures=True)
    if t2c:
        kwargs["t2c"] = t2c
    mob = Text(s, **kwargs)
    if width is not None and mob.width > width:
        chars = max(8, int(len(s) * width / mob.width))
        for _ in range(8):
            wrapped = "\n".join(_textwrap.wrap(s, chars)) or s
            mob = Text(wrapped, **kwargs)
            if mob.width <= width:
                break
            chars = max(6, int(chars * 0.9))
    return _mark_text(mob, size, s)


# --------------------------------------------------------------------------
# LaTeX -> SVG (tectonic / pdflatex) -> SVGMobject
# --------------------------------------------------------------------------

TEX_PREAMBLE = r"""
\documentclass{article}
\usepackage[active,tightpage]{preview}
\setlength\PreviewBorder{0.5pt}
\usepackage{amsmath,amssymb,mathtools,bm,xcolor}
\definecolor{skblue}{HTML}{58C4DD}
\definecolor{skyellow}{HTML}{F4D35E}
\definecolor{skgreen}{HTML}{83C167}
\definecolor{skred}{HTML}{FC6255}
\definecolor{skpurple}{HTML}{B28DFF}
\definecolor{skorange}{HTML}{FF9F43}
\definecolor{skmuted}{HTML}{9AA4B2}
\newcommand{\cB}[1]{{\color{skblue}#1}}
\newcommand{\cY}[1]{{\color{skyellow}#1}}
\newcommand{\cG}[1]{{\color{skgreen}#1}}
\newcommand{\cR}[1]{{\color{skred}#1}}
\newcommand{\cP}[1]{{\color{skpurple}#1}}
\newcommand{\cO}[1]{{\color{skorange}#1}}
\newcommand{\cM}[1]{{\color{skmuted}#1}}
\pagestyle{empty}
\begin{document}
""".strip()
_TEX_VERSION = "sk-tex-2"
# 10pt Computer Modern cap height is 6.81pt; Text("H", font_size=48) is 0.441 units.
TEX_PT_SCALE = 0.441 / 6.81 / 48
_TEX_CACHE = _Path(_os.environ.get("SHORTKIT_CACHE", _Path.home() / ".cache" / "shortkit")) / "tex"


class TexError(RuntimeError):
    pass


def _tex_engine() -> list[str]:
    extra = ["/Library/TeX/texbin", "/opt/homebrew/bin", "/usr/local/bin"]
    path = _os.pathsep.join([_os.environ.get("PATH", "")] + extra)
    for name in ("tectonic", "pdflatex", "xelatex", "lualatex"):
        found = _shutil.which(name, path=path)
        if found:
            return [found]
    raise TexError("No LaTeX engine found. Install tectonic (brew install tectonic / "
                   "cargo install tectonic) or a TeX distribution with pdflatex.")


def _tex_body(src: str, math: bool) -> str:
    return f"$\\displaystyle {src}$" if math else src


def _tex_key(body: str) -> str:
    return _hashlib.sha1(f"{_TEX_VERSION}\n{TEX_PREAMBLE}\n{body}".encode()).hexdigest()[:20]


def _compile_tex(bodies: list[str]) -> list[_Path]:
    """Compile each body to its own cached SVG; one engine run per batch."""
    _TEX_CACHE.mkdir(parents=True, exist_ok=True)
    keys = [_tex_key(b) for b in bodies]
    todo: dict[str, str] = {}
    for key, body in zip(keys, bodies):
        if not (_TEX_CACHE / f"{key}.svg").exists():
            todo.setdefault(key, body)
    if todo:
        _run_tex(todo)
    return [_TEX_CACHE / f"{k}.svg" for k in keys]


def _run_tex(todo: dict[str, str]) -> None:
    import pymupdf

    engine = _tex_engine()
    doc = TEX_PREAMBLE + "\n" + "\n".join(
        f"\\begin{{preview}}\\color{{white}}{body}\\end{{preview}}\n" for body in todo.values()) + "\\end{document}\n"
    with _tempfile.TemporaryDirectory(prefix="shortkit-tex-") as tmp:
        src = _Path(tmp) / "expr.tex"
        src.write_text(doc, encoding="utf-8")
        if _Path(engine[0]).name == "tectonic":
            cmd = engine + ["-X", "compile", "--untrusted", "--outdir", tmp, str(src)]
        else:
            cmd = engine + ["-interaction=nonstopmode", "-halt-on-error", f"-output-directory={tmp}", str(src)]
        proc = _subprocess.run(cmd, cwd=tmp, capture_output=True, text=True, timeout=180)
        pdf = _Path(tmp) / "expr.pdf"
        if proc.returncode != 0 or not pdf.exists():
            log = (proc.stdout or "") + (proc.stderr or "")
            log_file = _Path(tmp) / "expr.log"
            if log_file.exists():
                log += log_file.read_text(errors="replace")
            errors = [ln for ln in log.splitlines() if ln.startswith("!") or "error:" in ln.lower()]
            shown = "\n".join(errors[:6]) or log[-1200:]
            exprs = "\n".join(f"  {b}" for b in todo.values())
            raise TexError(f"LaTeX failed for:\n{exprs}\n{shown}")
        with pymupdf.open(pdf) as pdf_doc:
            if pdf_doc.page_count != len(todo):
                raise TexError(f"Expected {len(todo)} pages from LaTeX, got {pdf_doc.page_count}")
            for key, page in zip(todo, pdf_doc):
                (_TEX_CACHE / f"{key}.svg").write_text(page.get_svg_image(text_as_path=True), encoding="utf-8")


class TexSVG(SVGMobject):
    """LaTeX rendered through the system TeX engine. Build with ``tex()``."""

    def __init__(self, src: str, size: float = Size.BODY, color: str | None = None,
                 math: bool = True, **kwargs):
        (svg,) = _compile_tex([_tex_body(src, math)])
        super().__init__(str(svg), height=None, should_center=True, **kwargs)
        _solidify_rules(self)
        self.scale(size * TEX_PT_SCALE)
        if color is not None:
            self.set_fill(color, opacity=1.0)
        self.tex_source = src
        _mark_text(self, size, src)


def _solidify_rules(root: Mobject) -> None:
    """TeX rules (fraction bars, sqrt and overline bars, table rules) arrive as stroked,
    zero-area paths. Replace them with filled rectangles so they scale and recolour with glyphs."""
    for parent in root.get_family():
        for i, sm in enumerate(list(parent.submobjects)):
            if not isinstance(sm, VMobject) or not len(sm.points):
                continue
            if sm.get_fill_opacity() > 0.01 or sm.get_stroke_opacity() < 0.01:
                continue
            thickness = float(sm.get_stroke_width()) or 0.4  # in points at this stage (1 unit = 1 pt)
            if sm.height < 1e-3:
                rule = Rectangle(width=max(sm.width, thickness), height=thickness)
            elif sm.width < 1e-3:
                rule = Rectangle(width=thickness, height=max(sm.height, thickness))
            else:
                continue
            rule.set_fill(sm.get_stroke_color(), opacity=1.0).set_stroke(width=0).move_to(sm.get_center())
            parent.submobjects[i] = rule


def tex(src: str, size: float = Size.BODY, color: str | None = None, math: bool = True) -> TexSVG:
    r"""Typeset LaTeX. ``math=True`` wraps ``src`` in display-style math.

    Colour pieces semantically inside the source with \cB{..} (blue/input),
    \cY{..} (yellow/rule), \cG{..} (green/result), \cR{..} (red/contrast),
    \cP{..}, \cO{..}, \cM{..} (muted). Unmarked glyphs are white unless
    ``color`` is given, which recolours the whole expression.
    Use ``math=False`` for text with inline maths: tex(r"area $=6$", math=False).
    """
    return TexSVG(src, size=size, color=color, math=math)


def matrix_tex(rows, size: float = Size.BODY, color: str | None = None, kind: str = "bmatrix") -> TexSVG:
    """A matrix/vector from nested lists, e.g. matrix_tex([[2, 1], [1, 3]])."""
    if rows and not isinstance(rows[0], (list, tuple)):
        rows = [[r] for r in rows]  # column vector
    body = r" \\ ".join(" & ".join(_fmt(v) for v in row) for row in rows)
    return tex(rf"\begin{{{kind}}}{body}\end{{{kind}}}", size=size, color=color)


class MatrixGrid(VGroup):
    """A matrix whose entries, rows and columns can be addressed and animated.

    ``m.entries[i][j]``, ``m.rows[i]``, ``m.cols[j]`` and ``m.brackets`` are mobjects, so
    "point at row 2" or "slide column 1 out" is one line. Entries are typeset with tex();
    pass strings for symbolic entries (e.g. r"\\lambda").
    """

    def __init__(self, rows, size: float = Size.BODY, color: str | None = None, col_colors=None,
                 h_buff: float = 0.55, v_buff: float = 0.32):
        super().__init__()
        rows = [[r] for r in rows] if rows and not isinstance(rows[0], (list, tuple)) else rows
        bodies = [_tex_body(_fmt(v) if not isinstance(v, str) else v, True) for row in rows for v in row]
        _compile_tex(bodies)  # one engine run for every entry
        self.entries = []
        for row in rows:
            cells = []
            for j, v in enumerate(row):
                c = (col_colors[j] if col_colors else None) or color
                cells.append(tex(_fmt(v) if not isinstance(v, str) else v, size=size, color=c))
            self.entries.append(cells)
        n_rows, n_cols = len(self.entries), max(len(r) for r in self.entries)
        cell_w = max(c.width for r in self.entries for c in r)
        cell_h = max(c.height for r in self.entries for c in r)
        for i, row in enumerate(self.entries):
            for j, cell in enumerate(row):
                cell.move_to(np.array([j * (cell_w + h_buff), -i * (cell_h + v_buff), 0.0]))
        grid = VGroup(*[c for r in self.entries for c in r])
        self.rows = [VGroup(*r) for r in self.entries]
        self.cols = [VGroup(*[r[j] for r in self.entries if j < len(r)]) for j in range(n_cols)]
        pad, tick = 0.12, 0.16
        h = grid.height + 2 * pad
        stroke = max(2.5, size / 12)
        left = VMobject(stroke_color=color or INK, stroke_width=stroke).set_points_as_corners(
            [[tick, h / 2, 0], [0, h / 2, 0], [0, -h / 2, 0], [tick, -h / 2, 0]])
        right = left.copy().flip(UP)
        left.next_to(grid, LEFT, buff=0.1)
        right.next_to(grid, RIGHT, buff=0.1)
        self.brackets = VGroup(left, right)
        self.add(self.brackets, grid)
        for cell in grid:
            _mark_text(cell, size, getattr(cell, "_sk_label", ""))


def matrix_grid(rows, size: float = Size.BODY, color: str | None = None, col_colors=None) -> MatrixGrid:
    """Addressable matrix: matrix_grid([[2, 1], [1, 2]], col_colors=[BLUE_K, ORANGE_K])."""
    return MatrixGrid(rows, size=size, color=color, col_colors=col_colors)


class LiveText(VGroup):
    """Text that re-reads a value every frame (a counter, a running total, a coordinate).

    Rebuilds only when the string changes, keeps its left/centre/right edge fixed, and keeps
    the layout checker's ownership marks correct. Uses text() (fast, no TeX run per value).
    """

    def __init__(self, fn, size: float = Size.BODY, color: str = INK, align: str = "center"):
        super().__init__()
        self._fn, self._size, self._color, self._align = fn, size, color, align
        self._last = None
        self._refresh(first=True)
        self.add_updater(lambda m: m._refresh())

    def _refresh(self, first: bool = False) -> None:
        value = str(self._fn())
        if value == self._last:
            return
        new = text(value, size=self._size, color=self._color)
        if not first and self.submobjects:
            old = self.submobjects[0]
            edge = {"left": LEFT, "right": RIGHT}.get(self._align)
            if edge is not None:
                new.move_to(old, aligned_edge=edge)
            else:
                new.move_to(old.get_center())
            new.set_opacity(old.get_fill_opacity())
        self.submobjects = [new]
        self._last = value
        _mark_text(self, self._size, f"live:{value}")


def live_text(fn, size: float = Size.BODY, color: str = INK, align: str = "center") -> LiveText:
    """e.g. live_text(lambda: f"{tracker.get_value():.0f}") next to a moving object."""
    return LiveText(fn, size=size, color=color, align=align)


def _fmt(v) -> str:
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    if isinstance(v, float):
        return f"{v:.3g}"
    return str(v)


# --------------------------------------------------------------------------
# Small building blocks
# --------------------------------------------------------------------------


def plate(mob: Mobject, buff: float = 0.12, opacity: float = 0.88, color: str = BG) -> VGroup:
    """Put a rounded backplate behind text so lines and arrows never cut through it."""
    rect = SurroundingRectangle(mob, buff=buff, corner_radius=0.08, stroke_width=0,
                                fill_color=color, fill_opacity=opacity)
    group = VGroup(rect, mob)
    marked = [m for m in mob.get_family() if getattr(m, "_sk_label", None)]
    size = getattr(mob, "_sk_font_size", marked[0]._sk_font_size if marked else Size.LABEL)
    name = " / ".join(m._sk_label[:24] for m in marked[:2]) or type(mob).__name__
    _mark_text(group, size, name)
    group._sk_inner = mob
    return group


def label(s: str, size: float = Size.LABEL, color: str = INK, math: bool = False,
          backplate: bool = True) -> Mobject:
    """A short label (words, or LaTeX when math=True), on a backplate by default."""
    mob = tex(s, size=size, color=color) if math else text(s, size=size, color=color)
    return plate(mob) if backplate else mob


def highlight(mob: Mobject, color: str = YELLOW_K, buff: float = 0.1) -> SurroundingRectangle:
    """An outline (never a filled sweep) that points at something without hiding it."""
    rect = SurroundingRectangle(mob, color=color, buff=buff, stroke_width=5, corner_radius=0.06)
    rect._sk_pointer = True  # meant to surround text; not an overlap
    return rect


def stage_plane(x_range=(-1, 5, 1), y_range=(-1, 5, 1), zone: Zone = STAGE,
                buff: float = 0.1, **kwargs) -> NumberPlane:
    """A NumberPlane with equal x/y scale, as large as fits in ``zone``."""
    xspan, yspan = x_range[1] - x_range[0], y_range[1] - y_range[0]
    unit = min((zone.width - 2 * buff) / xspan, (zone.height - 2 * buff) / yspan)
    style = dict(
        x_range=x_range, y_range=y_range, x_length=unit * xspan, y_length=unit * yspan,
        background_line_style={"stroke_color": GRID, "stroke_width": 2, "stroke_opacity": 1},
        axis_config={"stroke_color": MUTED, "stroke_width": 3},
        faded_line_ratio=1,
    )
    style.update(kwargs)
    plane = NumberPlane(**style)
    plane.move_to(zone.center)
    return plane


def vec(plane: CoordinateSystem, coords, color: str = BLUE_K, start=(0, 0), width: float = 7) -> Arrow:
    """An arrow from ``start`` to ``coords`` in plane coordinates (no buff, phone-thick)."""
    return Arrow(plane.c2p(*start), plane.c2p(*coords), buff=0, color=color, stroke_width=width,
                 max_tip_length_to_length_ratio=0.18, max_stroke_width_to_length_ratio=12)


def background(mob: Mobject) -> Mobject:
    """Mark scenery (a translucent plane, a shaded region) so the layout checker ignores it."""
    for m in mob.get_family():
        m._sk_background = True
    return mob


def clipped_line(plane: CoordinateSystem, point, direction, color: str = MUTED, width: float = 4) -> Line:
    """The full line through ``point`` along ``direction``, clipped to the plane's x/y ranges."""
    (x0, x1), (y0, y1) = plane.x_range[:2], plane.y_range[:2]
    px, py = point
    dx, dy = direction
    ts = []
    for lo, hi, p0, d in ((x0, x1, px, dx), (y0, y1, py, dy)):
        if abs(d) > 1e-12:
            ts += [(lo - p0) / d, (hi - p0) / d]
    t_lo = max(min(ts[i], ts[i + 1]) for i in range(0, len(ts), 2))
    t_hi = min(max(ts[i], ts[i + 1]) for i in range(0, len(ts), 2))
    a = plane.c2p(px + t_lo * dx, py + t_lo * dy)
    b = plane.c2p(px + t_hi * dx, py + t_hi * dy)
    return Line(a, b, color=color, stroke_width=width)


def ortho(yaw: float = -35, pitch: float = 20, scale: float = 1.0, origin=ORIGIN):
    """A 3D -> 2D orthographic projection for 9:16 scenes (ThreeDScene does not mix well with shortkit).

    ``to2d = ortho(yaw=-35, pitch=20, scale=1.2, origin=STAGE.center)``; then
    ``Polygon(*[to2d(p) for p in corners])``. Drive yaw/pitch from ValueTrackers inside
    ``always_redraw`` to turn the view; keep labels as separate 2D text that follows to2d(point).
    """
    import math

    cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
    origin = np.array(origin, dtype=float)

    def to2d(p):
        x, y, z = (list(p) + [0, 0, 0])[:3]
        xr, yr = cy * x - sy * y, sy * x + cy * y          # yaw about the vertical z axis
        return origin + scale * np.array([xr, cp * z - sp * yr, 0.0])  # tilt toward the viewer

    return to2d


_ONES = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
_TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()


def spoken(value) -> str:
    """Number -> words for narration checks: spoken(89) == "eighty-nine", spoken(0.6) == "zero point six"."""
    if isinstance(value, float) and not value.is_integer():
        whole, frac = f"{value}".split(".")
        return f"{spoken(int(whole))} point {' '.join(_ONES[int(d)] for d in frac)}"
    n = int(value)
    if n < 0:
        return "minus " + spoken(-n)
    if n < 20:
        return _ONES[n]
    if n < 100:
        return _TENS[n // 10] + ("" if n % 10 == 0 else "-" + _ONES[n % 10])
    if n < 1000:
        rest = n % 100
        return _ONES[n // 100] + " hundred" + ("" if rest == 0 else " " + spoken(rest))
    if n < 1_000_000:
        rest = n % 1000
        return spoken(n // 1000) + " thousand" + ("" if rest == 0 else " " + spoken(rest))
    return str(n)


# --------------------------------------------------------------------------
# The scene base class
# --------------------------------------------------------------------------

_TEXT_TYPES = (Text, MarkupText, Paragraph, MathTex, Tex, SingleStringMathTex, DecimalNumber, TexSVG)


class ShortScene(Scene):
    """Base class for one vertical short. See module docstring for the contract."""

    captions = True        # reserve CAPTION_ZONE for burned-in narration captions
    tail_seconds = 0.6     # calm hold on the final frame

    # ---- lifecycle -------------------------------------------------------

    def setup(self):
        super().setup()
        module = _sys.modules[type(self).__module__]
        self._beats = _beatlib.normalize_beats(getattr(module, "BEATS", None),
                                               f"{type(self).__name__}.BEATS")
        self._beat_ids = [b["id"] for b in self._beats]
        self._durations, timing_issue, self._words, self._spoken = _load_timing(self._beats)
        self._beat_start = 0.0
        self._used: list[str] = []
        self._active_beat: str | None = None
        self._title_mob: Mobject | None = None
        self._allowed_pairs: set[frozenset[int]] = set()
        self._trace = {
            "scene": type(self).__name__, "quality": QUALITY, "fps": _FPS, "shortkit": SHORTKIT_VERSION,
            "resolution": [_PX_W, _PX_H], "captions": bool(self.captions),
            "beats": [], "issues": [],
        }
        if timing_issue:
            self._issue("warning", "timing", timing_issue)
        self._check_shadowing(module)
        self._prefetch_tex(module)

    def tear_down(self):
        missing = [b for b in self._beat_ids if b not in self._used]
        if missing:
            self._issue("error", "unused-beats", f"BEATS never played: {', '.join(missing)}")
        if self.tail_seconds > 0:
            self.wait(self.tail_seconds)
        self._trace["duration"] = round(self._now(), 3)
        out = _os.environ.get("SHORTKIT_TRACE")
        if out:
            _Path(out).write_text(_json.dumps(self._trace, indent=2), encoding="utf-8")
        else:
            n = len([i for i in self._trace["issues"] if i["severity"] == "error"])
            print(f"[shortkit] duration {self._trace['duration']}s, {n} layout error(s)")
        super().tear_down()

    # ---- beats -------------------------------------------------------------

    @_contextlib.contextmanager
    def beat(self, beat_id: str, pad: float = 0.0):
        """Run the animations for one narration beat.

        The beat lasts at least as long as its narration (plus ``pad`` seconds).
        If the animations inside run longer than the narration, the overrun is
        recorded and the next beat's narration simply starts later.
        """
        if beat_id not in self._durations:
            raise KeyError(f"beat {beat_id!r} is not declared in BEATS ({', '.join(self._beat_ids)})")
        if beat_id in self._used:
            raise ValueError(f"beat {beat_id!r} was already played")
        expected = self._beat_ids[len(self._used)]
        if beat_id != expected:
            self._issue("warning", "beat-order", f"played {beat_id!r} where {expected!r} was next in BEATS")
        self._used.append(beat_id)
        self._active_beat = beat_id
        start = self._now()
        self._beat_start = start
        yield
        animated = self._now() - start
        self._check_layout(beat_id)
        target = self._durations[beat_id] + pad
        if target - animated > 1.0 / _FPS:
            self.wait(target - animated)
        end = self._now()
        self._trace["beats"].append({
            "id": beat_id, "start": round(start, 3), "end": round(end, 3),
            "narration": round(self._durations[beat_id], 3), "animated": round(animated, 3),
            "overrun": round(max(0.0, animated - target), 3),
        })
        self._active_beat = None

    def _now(self) -> float:
        return float(self.renderer.time)

    def beat_time(self) -> float:
        """Seconds since the current beat started."""
        return self._now() - self._beat_start if self._active_beat else 0.0

    def cue(self, word: str, nth: int = 0, offset: float = 0.0, prefix: bool = False) -> None:
        """Wait until the narration of the current beat reaches ``word`` (its nth occurrence).

        Uses the word timings from edge-tts when available, otherwise an even-pace estimate,
        so ``self.cue("tail"); self.play(...)`` lands the motion on the spoken word.
        """
        if not self._active_beat:
            raise RuntimeError("cue() only works inside `with self.beat(...)`")
        target = self._word_time(self._active_beat, word, nth, prefix)
        if target is None:
            self._issue("warning", "cue", f"word {word!r} not found in beat {self._active_beat!r}")
            return
        remaining = target + offset - self.beat_time()
        if remaining > 1.0 / _FPS:
            self.wait(remaining)
        elif remaining < -0.5:
            self._issue("warning", "late-cue", f"cue({word!r}) fired {-remaining:.1f}s after the word was spoken; "
                        "shorten the animations before it")

    def _word_time(self, beat_id: str, word: str, nth: int, prefix: bool = False) -> float | None:
        want = _re.sub(r"[^a-z0-9]", "", word.lower())

        def match(token: str) -> bool:
            got = _re.sub(r"[^a-z0-9]", "", str(token).lower())
            return got.startswith(want) if prefix else got == want

        timed = self._words.get(beat_id)
        if timed:
            hits = [t for t, _, w in timed if match(w)]
            return float(hits[nth]) if len(hits) > nth else None
        text_ = next(b["text"] for b in self._beats if b["id"] == beat_id)
        tokens = text_.split()
        hits = [i for i, tok in enumerate(tokens) if match(tok)]
        if len(hits) <= nth:
            return None
        spoken = self._spoken.get(beat_id, self._durations[beat_id])
        return spoken * hits[nth] / max(len(tokens), 1)

    # ---- conveniences --------------------------------------------------------

    def title(self, s: str, *also: Animation, size: float = Size.TITLE, color: str = INK,
              run_time: float = 0.6, play: bool = True) -> Mobject:
        """Set (or swap) the compact title in TITLE_ZONE.

        Extra animations in ``also`` play together with it, so the opening shot can show the
        real object at once: ``self.title("Bayes", FadeIn(grid))``. With ``play=False`` the
        title is only registered and returned; animate it yourself (e.g. inside a bigger play).
        """
        mob = text(s, size=size, color=color, weight=BOLD, width=TITLE_ZONE.width - 0.2)
        if "\n" in getattr(mob, "text", "") or mob.height > TITLE_ZONE.height:
            self._issue("warning", "long-title", f"title {s!r} wraps or shrinks; shorten it to one line")
        TITLE_ZONE.fit(mob, buff=0.05, upscale=False)
        old, self._title_mob = self._title_mob, mob
        if not play:
            return mob
        if old is None:
            anims = [FadeIn(mob, shift=DOWN * 0.15, run_time=run_time)]
        else:
            anims = [FadeOut(old, shift=UP * 0.15, run_time=run_time), FadeIn(mob, shift=UP * 0.15, run_time=run_time)]
        self.play(*anims, *also)  # each animation keeps its own run_time
        return mob

    def swap(self, old: Mobject, new: Mobject, run_time: float = 0.8, morph: bool = False) -> Mobject:
        """Replace ``old`` with ``new`` in the same place without the two ever overlapping.

        ``new`` is moved to ``old``'s position unless already placed elsewhere on purpose
        (pass it pre-positioned). ``morph=True`` uses TransformMatchingShapes for equations
        that share most glyphs; otherwise ``old`` fades out before ``new`` fades in.
        """
        if morph:
            self.play(TransformMatchingShapes(old, new), run_time=run_time)
        else:
            self.play(FadeOut(old, shift=UP * 0.1), run_time=run_time / 2)
            self.play(FadeIn(new, shift=UP * 0.1), run_time=run_time / 2)
        return new

    def clear_stage(self, *keep: Mobject, run_time: float = 0.5) -> None:
        """Fade out everything except the title and ``keep``."""
        keep_ids = {id(m) for m in keep}
        if self._title_mob is not None:
            keep_ids.add(id(self._title_mob))
        gone = [m for m in self.mobjects if id(m) not in keep_ids]
        if gone:
            self.play(*[FadeOut(m) for m in gone], run_time=run_time)

    def allow_overlap(self, a: Mobject, b: Mobject) -> None:
        """Declare an intentional overlap between two texts, or between a text and a shape."""
        keys_a = {id(getattr(a, "_sk_owner", a))} | {id(m) for m in a.get_family()}
        keys_b = {id(getattr(b, "_sk_owner", b))} | {id(m) for m in b.get_family()}
        for ka in keys_a:
            for kb in keys_b:
                self._allowed_pairs.add(frozenset((ka, kb)))

    def show_zones(self) -> None:
        """Debug aid: draw dashed zone outlines (do not leave in final renders)."""
        self.add(TITLE_ZONE.outline(MUTED), STAGE.outline(BLUE_K), CAPTION_ZONE.outline(RED_K))

    # ---- layout checks ------------------------------------------------------

    def _issue(self, severity: str, kind: str, detail: str, objects: list[str] | None = None) -> None:
        self._trace["issues"].append({
            "severity": severity, "kind": kind, "beat": self._active_beat,
            "time": round(self._now(), 2), "detail": detail, "objects": objects or [],
        })

    def _text_items(self) -> list["_TextItem"]:
        """Visible text on screen, grouped by owner (see _mark_text)."""
        groups: dict[int, _TextItem] = {}
        seen: set[int] = set()

        def visit(m: Mobject, raw_owner: Mobject | None) -> None:
            if id(m) in seen:
                return
            seen.add(id(m))
            owner = getattr(m, "_sk_owner", None)
            if owner is None and raw_owner is None and isinstance(m, _TEXT_TYPES):
                raw_owner = m  # Manim text created directly, without shortkit helpers
            own = owner if owner is not None else raw_owner
            if own is not None and len(m.points) and _self_visible(m):
                groups.setdefault(id(own), _TextItem(own)).members.append(m)
            for sub in m.submobjects:
                visit(sub, raw_owner if owner is None else None)

        for m in self.mobjects:
            visit(m, None)
        return [item for item in groups.values() if item.width > 1e-3]

    def _check_layout(self, beat_id: str) -> None:
        texts = self._text_items()
        safe = _zone_box(SAFE)
        for t in texts:
            box = t.box
            if box[0] < safe[0] - 0.05 or box[2] > safe[2] + 0.05 or box[1] < safe[1] - 0.05 or box[3] > safe[3] + 0.05:
                self._issue("error", "outside-safe-area",
                            f"text extends outside the safe area {tuple(round(v, 2) for v in box)}", [t.label])
            if self.captions and _overlap_area(box, _zone_box(CAPTION_ZONE)) > 0.02:
                self._issue("error", "in-caption-zone",
                            "text sits where burned-in captions go; move it into STAGE", [t.label])
            size = _font_size(t.owner)
            if size is not None and size < MIN_FONT_SIZE - 0.5:
                self._issue("error", "tiny-text",
                            f"effective font size {size:.0f} < {MIN_FONT_SIZE}; simplify or split instead of shrinking",
                            [t.label])
        for i, a in enumerate(texts):
            for b in texts[i + 1:]:
                if frozenset((id(a.owner), id(b.owner))) in self._allowed_pairs:
                    continue
                if _overlap_area(a.box, b.box) <= 0:
                    continue
                inter = sum(_overlap_area(x, y) for x in a.boxes for y in b.boxes)
                smaller = min(a.area, b.area)
                if smaller > 0 and inter / smaller > 0.06:
                    self._issue("error", "text-overlap",
                                f"text boxes overlap by {100 * inter / smaller:.0f}%", [a.label, b.label])
        text_ids = {id(m) for t in texts for m in t.members}
        shapes = self._geometry_leaves(text_ids)
        for t in texts:
            box = t.box
            inner = (box[0] + 0.06, box[1] + 0.06, box[2] - 0.06, box[3] - 0.06)
            hits = [g for g in shapes if frozenset((id(t.owner), id(g))) not in self._allowed_pairs
                    and _path_enters(g, inner)]
            if hits:
                verb = "hides" if getattr(t.owner, "_sk_inner", None) is not None else "is crossed by"
                self._issue("warning", "text-covers-geometry",
                            f"text {verb} a line/arrow/shape; move one of them", [t.label, _describe(hits[0])])
        if self.captions:
            for g in shapes:
                if _overlap_area(_bbox(g), _zone_box(CAPTION_ZONE)) > 0.4:
                    self._issue("warning", "geometry-in-caption-zone",
                                "a shape extends into the caption band; captions will cover it", [_describe(g)])
                    break

    def _geometry_leaves(self, text_ids: set[int]) -> list[VMobject]:
        """Visible non-text paths (arrows, lines, curves, dots), excluding grids and backgrounds."""
        leaves: list[VMobject] = []
        seen: set[int] = set()

        def visit(m: Mobject) -> None:
            if id(m) in seen or id(m) in text_ids or getattr(m, "_sk_owner", None) is not None:
                return
            seen.add(id(m))
            if (getattr(m, "_sk_background", False) or getattr(m, "_sk_pointer", False)
                    or isinstance(m, (NumberPlane, Axes, SurroundingRectangle) + _TEXT_TYPES)):
                return
            if isinstance(m, VMobject) and len(m.points) and _self_visible(m, threshold=0.3):
                leaves.append(m)
            for sub in m.submobjects:
                visit(sub)

        for m in self.mobjects:
            visit(m)
        return leaves

    def _check_shadowing(self, module) -> None:
        """Module-level names that replace Manim exports (LEFT, OUT, UP...) break Manim in odd places."""
        import manim

        try:
            tree = _ast.parse(_inspect.getsource(module))
        except (OSError, TypeError, SyntaxError):
            return
        names = set()

        def collect(target) -> None:  # bare names and tuple unpacking only, not attribute/subscript targets
            if isinstance(target, _ast.Name):
                names.add(target.id)
            elif isinstance(target, (_ast.Tuple, _ast.List)):
                for elt in target.elts:
                    collect(elt)

        for node in tree.body:
            if isinstance(node, _ast.Assign):
                for t in node.targets:
                    collect(t)
            elif isinstance(node, (_ast.AnnAssign, _ast.AugAssign)):
                collect(node.target)
        clash = sorted(n for n in names if hasattr(manim, n) and n != "BEATS")
        if clash:
            msg = f"scene.py redefines Manim names {', '.join(clash)}; rename them (e.g. LEFT_NULL)"
            print(f"[shortkit] ERROR: {msg}", file=_sys.stderr)
            self._issue("error", "shadows-manim", msg)

    # ---- LaTeX prefetch -------------------------------------------------------

    def _prefetch_tex(self, module) -> None:
        """Compile every literal tex("...") in the scene file in one engine run."""
        try:
            tree = _ast.parse(_inspect.getsource(module))
        except (OSError, TypeError, SyntaxError):
            return
        bodies = []
        for node in _ast.walk(tree):
            if not isinstance(node, _ast.Call):
                continue
            fname = node.func.id if isinstance(node.func, _ast.Name) else getattr(node.func, "attr", "")
            if fname not in {"tex", "label"} or not node.args:
                continue
            arg = node.args[0]
            if not (isinstance(arg, _ast.Constant) and isinstance(arg.value, str)):
                continue
            math = fname == "tex"
            for kw in node.keywords:
                if kw.arg == "math" and isinstance(kw.value, _ast.Constant):
                    math = bool(kw.value.value)
            if fname == "label" and not math:
                continue
            bodies.append(_tex_body(arg.value, math))
        if bodies:
            try:
                _compile_tex(bodies)
            except TexError:
                pass  # the failing call will raise with a precise message later


# --------------------------------------------------------------------------
# helpers for the checker
# --------------------------------------------------------------------------


def _load_timing(beats: list[dict[str, str]]):
    """Return (durations, issue, word timings, spoken seconds) per beat id."""
    durations = {b["id"]: _beatlib.estimate_seconds(b["text"]) for b in beats}
    words: dict[str, list] = {}
    spoken: dict[str, float] = {}
    path = _os.environ.get("SHORTKIT_TIMING")
    if not path or not _Path(path).exists():
        return durations, None, words, spoken
    data = _json.loads(_Path(path).read_text(encoding="utf-8"))
    stale = []
    by_id = {b["id"]: b for b in data.get("beats", [])}
    for b in beats:
        entry = by_id.get(b["id"])
        if entry and " ".join(str(entry.get("text", "")).split()) == b["text"]:
            durations[b["id"]] = float(entry["duration"])
            if entry.get("words"):
                words[b["id"]] = entry["words"]
            if entry.get("audio_seconds"):
                spoken[b["id"]] = float(entry["audio_seconds"])
        else:
            stale.append(b["id"])
    issue = f"timing.json is stale for beats {', '.join(stale)}; using estimates" if stale else None
    return durations, issue, words, spoken


class _TextItem:
    """One piece of on-screen text: its owner and the visible glyphs/plate that belong to it."""

    def __init__(self, owner: Mobject):
        self.owner = owner
        self.members: list[Mobject] = []

    @property
    def box(self) -> tuple[float, float, float, float]:
        boxes = [_point_box(m) for m in self.members]
        return (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))

    @property
    def boxes(self) -> list[tuple[float, float, float, float]]:
        return [_point_box(m) for m in self.members]

    @property
    def area(self) -> float:
        return sum(_area(b) for b in self.boxes)

    @property
    def width(self) -> float:
        b = self.box
        return b[2] - b[0]

    @property
    def label(self) -> str:
        return _describe(self.owner)


def _point_box(m: Mobject) -> tuple[float, float, float, float]:
    pts = m.points
    return (float(pts[:, 0].min()), float(pts[:, 1].min()), float(pts[:, 0].max()), float(pts[:, 1].max()))


def _self_visible(m: Mobject, threshold: float = 0.05) -> bool:
    if isinstance(m, VMobject):
        return m.get_fill_opacity() > threshold or (m.get_stroke_opacity() > threshold and m.get_stroke_width() > 0)
    return getattr(m, "opacity", 1) > threshold


def _visible(m: Mobject) -> bool:
    for sm in m.family_members_with_points():
        if isinstance(sm, VMobject):
            if sm.get_fill_opacity() > 0.05 or (sm.get_stroke_opacity() > 0.05 and sm.get_stroke_width() > 0):
                return True
        elif getattr(sm, "opacity", 1) > 0.05:
            return True
    return False


def _bbox(m: Mobject) -> tuple[float, float, float, float]:
    return (float(m.get_left()[0]), float(m.get_bottom()[1]), float(m.get_right()[0]), float(m.get_top()[1]))


def _zone_box(z: Zone) -> tuple[float, float, float, float]:
    return (z.left, z.bottom, z.right, z.top)


def _area(b) -> float:
    return max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])


def _overlap_area(a, b) -> float:
    w = min(a[2], b[2]) - max(a[0], b[0])
    h = min(a[3], b[3]) - max(a[1], b[1])
    return w * h if w > 0 and h > 0 else 0.0


def _path_enters(m: VMobject, box: tuple[float, float, float, float], samples: int = 48) -> bool:
    if box[2] <= box[0] or box[3] <= box[1]:
        return False
    if _overlap_area(_bbox(m), box) <= 0:
        return False
    for t in np.linspace(0, 1, samples):
        try:
            x, y, _ = m.point_from_proportion(t)
        except Exception:
            return False
        if box[0] < x < box[2] and box[1] < y < box[3]:
            return True
    return False


def _is_ancestor(a: Mobject, b: Mobject) -> bool:
    return b in a.get_family()[1:]


def _font_size(m: Mobject) -> float | None:
    inner = getattr(m, "_sk_inner", m)
    base = getattr(inner, "_sk_font_size", None)
    if base is not None:
        return base * inner.height / max(getattr(inner, "_sk_base_height", inner.height), 1e-6)
    size = getattr(m, "font_size", None)
    return float(size) if isinstance(size, (int, float)) else None


def _describe(m: Mobject) -> str:
    label_ = getattr(getattr(m, "_sk_inner", m), "_sk_label", None)
    if label_:
        return label_
    for attr in ("text", "tex_string", "original_text"):
        value = getattr(m, attr, None)
        if isinstance(value, str) and value:
            return value[:48]
    return type(m).__name__
