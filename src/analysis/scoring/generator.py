"""
Report Generator
----------------
Renders SASReport to:
  1. JSON file (always)
  2. HTML file (Jinja2 template)
  3. PDF file (WeasyPrint from HTML)

Radar chart is built as inline SVG using pure math.
No external chart libraries needed at render time.
"""
import os
import math
import json
from pathlib import Path
from typing import Optional
from jinja2 import Environment, FileSystemLoader
from src.analysis.scoring.report_builder import SASReport, report_to_dict, save_json_report
from src.core.config import settings
from src.core.logger import logger


# ─────────────────────────────────────────────
# Radar Chart (Pure SVG - no dependencies)
# ─────────────────────────────────────────────

def _build_radar_svg(dimensions: dict, size: int = 400) -> str:
    """
    Build a radar/spider chart as pure inline SVG.
    No Plotly, no Kaleido needed - pure math.

    Args:
        dimensions: dict of {key: {name, score, ...}}
        size: SVG canvas size in pixels

    Returns:
        SVG string ready to embed in HTML
    """
    dim_items = list(dimensions.items())
    n = len(dim_items)
    cx, cy = size // 2, size // 2
    r_max = (size // 2) - 60    # max radius leaving room for labels

    # Colors
    grid_color = "#e2e8f0"
    fill_color = "rgba(43, 108, 176, 0.25)"
    stroke_color = "#2b6cb0"
    label_color = "#4a5568"
    score_color = "#1a365d"

    svg_parts = [
        f'<svg viewBox="0 0 {size} {size}" xmlns="http://www.w3.org/2000/svg" '
        f'style="font-family: Arial, sans-serif;">',
    ]

    # Draw grid rings (5 levels = scores 1-5)
    for level in range(1, 6):
        r = r_max * level / 5
        points = []
        for i in range(n):
            angle = math.pi / 2 + 2 * math.pi * i / n
            x = cx + r * math.cos(angle)
            y = cy - r * math.sin(angle)
            points.append(f"{x:.1f},{y:.1f}")
        pts_str = " ".join(points)
        svg_parts.append(
            f'<polygon points="{pts_str}" fill="none" '
            f'stroke="{grid_color}" stroke-width="1"/>'
        )
        # Level label (score number)
        lx = cx + 6
        ly = cy - r + 4
        svg_parts.append(
            f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="9" '
            f'fill="{grid_color}" text-anchor="start">{level}</text>'
        )

    # Draw axis lines from center to each vertex
    for i in range(n):
        angle = math.pi / 2 + 2 * math.pi * i / n
        x = cx + r_max * math.cos(angle)
        y = cy - r_max * math.sin(angle)
        svg_parts.append(
            f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" '
            f'stroke="{grid_color}" stroke-width="1"/>'
        )

    # Draw data polygon
    data_points = []
    for i, (key, dim) in enumerate(dim_items):
        score = dim.get("score", 1) if isinstance(dim, dict) else dim.raw_score
        r = r_max * score / 5
        angle = math.pi / 2 + 2 * math.pi * i / n
        x = cx + r * math.cos(angle)
        y = cy - r * math.sin(angle)
        data_points.append((x, y, score))

    pts_str = " ".join(f"{x:.1f},{y:.1f}" for x, y, _ in data_points)
    svg_parts.append(
        f'<polygon points="{pts_str}" fill="{fill_color}" '
        f'stroke="{stroke_color}" stroke-width="2.5"/>'
    )

    # Draw data point dots
    for x, y, score in data_points:
        svg_parts.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" '
            f'fill="{stroke_color}" stroke="white" stroke-width="1.5"/>'
        )

    # Draw dimension labels
    for i, (key, dim) in enumerate(dim_items):
        angle = math.pi / 2 + 2 * math.pi * i / n
        lx = cx + (r_max + 38) * math.cos(angle)
        ly = cy - (r_max + 38) * math.sin(angle)
        name = dim.get("name", key) if isinstance(dim, dict) else dim.name
        score = dim.get("score", 1) if isinstance(dim, dict) else dim.raw_score

        # Text anchor based on position
        if lx < cx - 10:
            anchor = "end"
        elif lx > cx + 10:
            anchor = "start"
        else:
            anchor = "middle"

        # Shorten long names
        short_name = name.replace(" Quality", "").replace(" Words", "").replace(" Patterns", "")
        short_name = short_name.replace(" Use", "").replace(" / Demeanor", "")

        svg_parts.append(
            f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="11" '
            f'fill="{label_color}" text-anchor="{anchor}" '
            f'dominant-baseline="middle">{short_name}</text>'
        )
        # Score below label
        svg_parts.append(
            f'<text x="{lx:.1f}" y="{ly + 13:.1f}" font-size="10" '
            f'fill="{score_color}" text-anchor="{anchor}" '
            f'font-weight="bold">{score}/5</text>'
        )

    svg_parts.append("</svg>")
    return "\n".join(svg_parts)


# ─────────────────────────────────────────────
# Grade Color Helper
# ─────────────────────────────────────────────

def _grade_color(grade: str) -> str:
    return {
        "A": "#38a169",
        "B": "#3182ce",
        "C": "#d69e2e",
        "D": "#e53e3e",
        "F": "#742a2a",
    }.get(grade, "#718096")


# ─────────────────────────────────────────────
# HTML Report
# ─────────────────────────────────────────────

def generate_html_report(
    report: SASReport,
    output_dir: Optional[str] = None,
) -> str:
    """
    Render the Jinja2 HTML template with report data.
    Returns path to generated HTML file.
    """
    output_dir = output_dir or str(settings.reports_dir)
    os.makedirs(output_dir, exist_ok=True)

    # Build radar SVG
    radar_svg = _build_radar_svg(report.dimensions)

    # Set up Jinja2
    template_dir = str(Path(__file__).resolve().parent.parent.parent.parent / "templates")
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("report.html")

    html_content = template.render(
        report=report,
        radar_svg=radar_svg,
        grade_color=_grade_color(report.grade),
    )

    output_path = os.path.join(output_dir, f"{report.metadata.job_id}_report.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    logger.info(f"HTML report saved: {output_path}")
    return output_path


# ─────────────────────────────────────────────
# PDF Report
# ─────────────────────────────────────────────

def generate_pdf_report(
    report: SASReport,
    output_dir: Optional[str] = None,
) -> str:
    """
    Convert HTML report to PDF using WeasyPrint.
    Returns path to generated PDF file.
    """
    output_dir = output_dir or str(settings.reports_dir)
    os.makedirs(output_dir, exist_ok=True)

    # First generate HTML
    html_path = generate_html_report(report, output_dir)
    pdf_path = html_path.replace(".html", ".pdf")

    try:
        from weasyprint import HTML
        HTML(filename=html_path).write_pdf(pdf_path)
        logger.info(f"PDF report saved: {pdf_path}")
        return pdf_path
    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
        logger.info(f"HTML report still available: {html_path}")
        return html_path   # return HTML path as fallback


# ─────────────────────────────────────────────
# Main Entry Point
# ─────────────────────────────────────────────

def generate_all_reports(
    report: SASReport,
    output_dir: Optional[str] = None,
) -> dict:
    """
    Generate all report formats: JSON + HTML + PDF.
    Returns dict with paths to all generated files.
    """
    output_dir = output_dir or str(settings.reports_dir)

    paths = {}

    # 1. JSON
    paths["json"] = save_json_report(report, output_dir)

    # 2. HTML
    paths["html"] = generate_html_report(report, output_dir)

    # 3. PDF
    paths["pdf"] = generate_pdf_report(report, output_dir)

    logger.success(
        f"All reports generated for job {report.metadata.job_id}: "
        f"JSON + HTML + PDF"
    )
    return paths
