#!/usr/bin/env python3
"""Check two figure-label collisions in exported MEMS PDFs.

Run from the MEMS repository root:
    python qa/check_figure_overlaps.py

The script checks the two vector figure PDFs embedded by LaTeX. Poppler's
pdftotext and pdftocairo are required; no Python PDF package is needed. Use
--figure3 and --figure4 to override their paths, or --help for details.
"""

from __future__ import annotations

import argparse
import math
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


SVG_NS = "{http://www.w3.org/2000/svg}"
NUMBER = re.compile(r"[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?")
TOKEN = re.compile(r"[A-Za-z]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?")


@dataclass(frozen=True)
class Rect:
    x0: float
    y0: float
    x1: float
    y1: float

    def expanded(self, amount: float) -> "Rect":
        return Rect(self.x0 - amount, self.y0 - amount,
                    self.x1 + amount, self.y1 + amount)

    def intersects(self, other: "Rect") -> bool:
        return not (self.x1 < other.x0 or other.x1 < self.x0 or
                    self.y1 < other.y0 or other.y1 < self.y0)


@dataclass(frozen=True)
class Word:
    text: str
    box: Rect


@dataclass(frozen=True)
class Finding:
    label: str
    page: int
    text_box: Rect
    object_kind: str
    color: str


def run_poppler(command: str, args: list[str], *, output: Path | None = None) -> str:
    exe = shutil.which(command)
    if not exe:
        raise RuntimeError(f"Required Poppler command not found: {command}")
    result = subprocess.run([exe, *args], text=True, capture_output=True)
    # Some Windows Poppler builds report a cairo cleanup assertion after writing
    # a valid SVG. Accept that case only when the requested output exists.
    if result.returncode and (output is None or not output.is_file()):
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"{command} failed: {detail or result.returncode}")
    return result.stdout


def extract_words(pdf: Path, temp: Path) -> list[list[Word]]:
    html = temp / "text-bboxes.html"
    run_poppler("pdftotext", ["-bbox", str(pdf), str(html)])
    root = ET.parse(html).getroot()
    pages: list[list[Word]] = []
    for page in (element for element in root.iter()
                 if element.tag.rsplit("}", 1)[-1] == "page"):
        words: list[Word] = []
        for element in (child for child in page
                        if child.tag.rsplit("}", 1)[-1] == "word"):
            try:
                box = Rect(*(float(element.attrib[key]) for key in
                             ("xMin", "yMin", "xMax", "yMax")))
            except (KeyError, ValueError):
                continue
            words.append(Word(" ".join((element.text or "").split()), box))
        pages.append(words)
    if not pages:
        raise RuntimeError(f"No text pages found in {pdf}")
    return pages


def target_boxes(words: list[Word], label: str) -> list[Rect]:
    if label == "67,4 kHz":
        found = []
        for left in words:
            if left.text != "67,4":
                continue
            for right in words:
                gap = right.box.x0 - left.box.x1
                if (right.text.lower() == "khz" and -1.0 <= gap <= 4.0 and
                        abs(right.box.y0 - left.box.y0) <= 2.0):
                    found.append(Rect(min(left.box.x0, right.box.x0),
                                      min(left.box.y0, right.box.y0),
                                      max(left.box.x1, right.box.x1),
                                      max(left.box.y1, right.box.y1)))
        return found
    return [word.box for word in words if word.text == label]


def parse_style(style: str) -> dict[str, str]:
    return {key.strip(): value.strip() for part in style.split(";")
            if ":" in part for key, value in [part.split(":", 1)]}


def parse_color(value: str | None) -> tuple[float, float, float] | None:
    if not value or value == "none":
        return None
    if value.startswith("#") and len(value) == 7:
        return tuple(int(value[index:index + 2], 16) / 255 for index in (1, 3, 5))
    match = re.fullmatch(r"rgb\(([^)]+)\)", value)
    if match:
        parts = [part.strip() for part in match.group(1).split(",")]
        if len(parts) == 3:
            return tuple(float(part.rstrip("%")) / (100 if part.endswith("%") else 255)
                         for part in parts)
    return None


def chromatic(color: tuple[float, float, float] | None) -> bool:
    if color is None:
        return False
    high, low = max(color), min(color)
    return high >= 0.22 and (high - low) / max(high, 1e-9) >= 0.18


def parse_transform(value: str | None) -> tuple[float, float, float, float, float, float]:
    if not value:
        return (1, 0, 0, 1, 0, 0)
    match = re.search(r"matrix\(([^)]+)\)", value)
    if match:
        numbers = [float(part) for part in re.split(r"[ ,]+", match.group(1).strip())]
        if len(numbers) == 6:
            return tuple(numbers)  # type: ignore[return-value]
    match = re.search(r"translate\(([^)]+)\)", value)
    if match:
        numbers = [float(part) for part in re.split(r"[ ,]+", match.group(1).strip())]
        return (1, 0, 0, 1, numbers[0], numbers[1] if len(numbers) > 1 else 0)
    match = re.search(r"scale\(([^)]+)\)", value)
    if match:
        numbers = [float(part) for part in re.split(r"[ ,]+", match.group(1).strip())]
        return (numbers[0], 0, 0, numbers[1] if len(numbers) > 1 else numbers[0], 0, 0)
    return (1, 0, 0, 1, 0, 0)


def combine(a: tuple[float, float, float, float, float, float],
            b: tuple[float, float, float, float, float, float]
            ) -> tuple[float, float, float, float, float, float]:
    aa, ab, ac, ad, ae, af = a
    ba, bb, bc, bd, be, bf = b
    return (aa * ba + ac * bb, ab * ba + ad * bb,
            aa * bc + ac * bd, ab * bc + ad * bd,
            aa * be + ac * bf + ae, ab * be + ad * bf + af)


def transformed(point: tuple[float, float], matrix: tuple[float, float, float,
                                                            float, float, float]
                ) -> tuple[float, float]:
    a, b, c, d, e, f = matrix
    x, y = point
    return (a * x + c * y + e, b * x + d * y + f)


def path_subpaths(data: str) -> list[list[tuple[float, float]]]:
    """Flatten SVG M/L/H/V/C/S/Q/T/Z paths for intersection checks."""
    tokens = TOKEN.findall(data)
    result: list[list[tuple[float, float]]] = []
    points: list[tuple[float, float]] = []
    i, command = 0, ""
    current = (0.0, 0.0)
    start = current

    def num() -> float:
        nonlocal i
        value = float(tokens[i]); i += 1
        return value

    def point(x: float, y: float) -> tuple[float, float]:
        return (current[0] + x, current[1] + y) if command.islower() else (x, y)

    def cubic(p0, p1, p2, p3, steps=8):
        out = []
        for step in range(1, steps + 1):
            t = step / steps; u = 1 - t
            out.append((u**3*p0[0] + 3*u*u*t*p1[0] + 3*u*t*t*p2[0] + t**3*p3[0],
                        u**3*p0[1] + 3*u*u*t*p1[1] + 3*u*t*t*p2[1] + t**3*p3[1]))
        return out

    def quad(p0, p1, p2, steps=8):
        out = []
        for step in range(1, steps + 1):
            t = step / steps; u = 1 - t
            out.append((u*u*p0[0] + 2*u*t*p1[0] + t*t*p2[0],
                        u*u*p0[1] + 2*u*t*p1[1] + t*t*p2[1]))
        return out

    previous_control = current
    while i < len(tokens):
        if tokens[i].isalpha():
            command = tokens[i]; i += 1
            if command in "Zz":
                if points and points[-1] != start:
                    points.append(start)
                current = start
                continue
        if not command:
            break
        upper = command.upper()
        if upper == "M":
            if points:
                result.append(points)
            p = point(num(), num()); current = p; start = p; points = [p]
            command = "l" if command.islower() else "L"
        elif upper == "L":
            p = point(num(), num()); points.append(p); current = p
        elif upper == "H":
            x = num() + (current[0] if command.islower() else 0)
            p = (x, current[1]); points.append(p); current = p
        elif upper == "V":
            y = num() + (current[1] if command.islower() else 0)
            p = (current[0], y); points.append(p); current = p
        elif upper == "C":
            p0 = current
            p1, p2, p3 = point(num(), num()), point(num(), num()), point(num(), num())
            points.extend(cubic(p0, p1, p2, p3)); current = p3; previous_control = p2
        elif upper == "S":
            p0 = current; p1 = (2*current[0]-previous_control[0], 2*current[1]-previous_control[1])
            p2, p3 = point(num(), num()), point(num(), num())
            points.extend(cubic(p0, p1, p2, p3)); current = p3; previous_control = p2
        elif upper == "Q":
            p0 = current; p1, p2 = point(num(), num()), point(num(), num())
            points.extend(quad(p0, p1, p2)); current = p2; previous_control = p1
        elif upper == "T":
            p0 = current; p1 = (2*current[0]-previous_control[0], 2*current[1]-previous_control[1])
            p2 = point(num(), num()); points.extend(quad(p0, p1, p2)); current = p2; previous_control = p1
        elif upper == "A":
            # Arc markers are rare in Matplotlib output. Consume their endpoint;
            # a conservative endpoint segment still catches close collisions.
            values = [num() for _ in range(7)]; p = point(values[5], values[6])
            points.append(p); current = p
        else:
            break
    if points:
        result.append(points)
    return result


def segment_intersects_rect(a: tuple[float, float], b: tuple[float, float], rect: Rect) -> bool:
    dx, dy = b[0] - a[0], b[1] - a[1]
    low, high = 0.0, 1.0
    for p, q in ((-dx, a[0] - rect.x0), (dx, rect.x1 - a[0]),
                 (-dy, a[1] - rect.y0), (dy, rect.y1 - a[1])):
        if abs(p) < 1e-12:
            if q < 0:
                return False
            continue
        ratio = q / p
        if p < 0:
            low = max(low, ratio)
        else:
            high = min(high, ratio)
        if low > high:
            return False
    return True


def point_segment_distance(point: tuple[float, float], a: tuple[float, float],
                           b: tuple[float, float]) -> float:
    dx, dy = b[0] - a[0], b[1] - a[1]
    length2 = dx * dx + dy * dy
    if length2 <= 1e-12:
        return math.hypot(point[0] - a[0], point[1] - a[1])
    t = max(0.0, min(1.0, ((point[0] - a[0]) * dx + (point[1] - a[1]) * dy) / length2))
    return math.hypot(point[0] - (a[0] + t * dx), point[1] - (a[1] + t * dy))


def point_rect_distance(point: tuple[float, float], rect: Rect) -> float:
    dx = max(rect.x0 - point[0], 0.0, point[0] - rect.x1)
    dy = max(rect.y0 - point[1], 0.0, point[1] - rect.y1)
    return math.hypot(dx, dy)


def segment_rect_distance(a: tuple[float, float], b: tuple[float, float], rect: Rect) -> float:
    if segment_intersects_rect(a, b, rect):
        return 0.0
    corners = ((rect.x0, rect.y0), (rect.x0, rect.y1),
               (rect.x1, rect.y0), (rect.x1, rect.y1))
    return min(min(point_rect_distance(a, rect), point_rect_distance(b, rect)),
               *(point_segment_distance(corner, a, b) for corner in corners))


def point_in_polygon(point: tuple[float, float], polygon: list[tuple[float, float]]) -> bool:
    inside = False
    x, y = point
    for a, b in zip(polygon, polygon[1:] + polygon[:1]):
        if (a[1] > y) != (b[1] > y):
            crossing = (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]
            if x < crossing:
                inside = not inside
    return inside


def marker_intersects_rect(points: list[tuple[float, float]], rect: Rect) -> bool:
    if any(rect.x0 <= x <= rect.x1 and rect.y0 <= y <= rect.y1 for x, y in points):
        return True
    corners = ((rect.x0, rect.y0), (rect.x0, rect.y1),
               (rect.x1, rect.y0), (rect.x1, rect.y1))
    if any(point_in_polygon(corner, points) for corner in corners):
        return True
    return any(segment_intersects_rect(a, b, rect) for a, b in zip(points, points[1:]))


def walk_paths(element: ET.Element, inherited, output):
    matrix = combine(inherited, parse_transform(element.get("transform")))
    if element.tag == SVG_NS + "path":
        style = parse_style(element.get("style", ""))
        stroke = parse_color(style.get("stroke"))
        fill = parse_color(style.get("fill"))
        opacity = float(style.get("stroke-opacity", "1"))
        width = float(style.get("stroke-width", "0"))
        subs = [[transformed(p, matrix) for p in sub]
                for sub in path_subpaths(element.get("d", ""))]
        output.append((style, stroke, fill, opacity, width, subs))
    for child in element:
        walk_paths(child, matrix, output)


def geometry_hit(svg: Path, box: Rect, *, include_fills: bool) -> tuple[str, str] | None:
    root = ET.parse(svg).getroot()
    paths = []
    walk_paths(root, (1, 0, 0, 1, 0, 0), paths)
    for style, stroke, fill, opacity, width, subpaths in paths:
        candidates = []
        if opacity >= 0.65 and chromatic(stroke) and width >= 0.4:
            candidates.append(("stroke", stroke, width / 2 + 0.25))
        if include_fills and chromatic(fill):
            candidates.append(("marker", fill, 0.25))
        for kind, color, clearance in candidates:
            for sub in subpaths:
                if len(sub) < 2:
                    continue
                if kind == "marker":
                    if marker_intersects_rect(sub, box):
                        return kind, "#%02x%02x%02x" % tuple(round(c * 255) for c in color)
                elif any(segment_rect_distance(a, b, box) <= clearance
                         for a, b in zip(sub, sub[1:])):
                    return kind, "#%02x%02x%02x" % tuple(round(c * 255) for c in color)
    return None


def svg_for_page(pdf: Path, page: int, temp: Path) -> Path:
    prefix = temp / f"page-{page}"
    run_poppler("pdftocairo", ["-svg", "-f", str(page), "-l", str(page),
                               str(pdf), str(prefix)], output=prefix)
    return prefix


def check_target(pdf: Path, label: str, *, include_fills: bool) -> list[Finding]:
    hits = []
    found_boxes = 0
    with tempfile.TemporaryDirectory(prefix="mems-figure-qa-") as tmp_name:
        temp = Path(tmp_name)
        pages = extract_words(pdf, temp)
        for page_no, words in enumerate(pages, start=1):
            boxes = target_boxes(words, label)
            if not boxes:
                continue
            found_boxes += len(boxes)
            svg = svg_for_page(pdf, page_no, temp)
            for box in boxes:
                result = geometry_hit(svg, box, include_fills=include_fills)
                if result:
                    kind, color = result
                    hits.append(Finding(label, page_no, box, kind, color))
    if found_boxes != 1:
        raise RuntimeError(f"Expected exactly one '{label}' label in {pdf}; found {found_boxes}")
    return hits


def check_pdf(pdf: Path, *, figure3: bool = True, figure4: bool = True) -> list[Finding]:
    findings = []
    if figure3:
        findings.extend(check_target(pdf, "67,4 kHz", include_fills=True))
    if figure4:
        findings.extend(check_target(pdf, "Ida", include_fills=False))
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--figure3", type=Path,
                        help="override the Fig. 3 amplitude-sweep PDF")
    parser.add_argument("--figure4", type=Path,
                        help="override the Fig. 4(a,b) composite PDF")
    args = parser.parse_args(argv)

    findings = []
    try:
        targets = ((args.figure3 or Path("Figuras_paper/figure_1_amplitude_sweeps.pdf"),
                    "67,4 kHz", True),
                   (args.figure4 or Path("Figuras_paper/figure_2_lorentzian_hysteresis.pdf"),
                    "Ida", False))
        for path, label, include_fills in targets:
            if not path.is_file():
                raise RuntimeError(f"PDF not found: {path}")
            findings.extend(check_target(path, label, include_fills=include_fills))
    except (RuntimeError, ET.ParseError, OSError, ValueError) as exc:
        print(f"QA could not complete: {exc}", file=sys.stderr)
        return 2

    if findings:
        for finding in findings:
            print(f"FAIL {finding.label}: colored {finding.object_kind} "
                  f"{finding.color} intersects text bbox on page {finding.page} "
                  f"of target PDF")
        return 1
    print("PASS: no colored curve or marker intersects either target label.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
