"""Render REPORT.md to REPORT.html and REPORT.pdf (headless Chrome or Edge, no network).

.venv\\Scripts\\python research\\ml-showcase\\build_pdf.py
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

import markdown

HERE = Path(__file__).resolve().parent
BROWSERS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "google-chrome",
    "chromium",
]

CSS = """
@page { size: A4; margin: 16mm 15mm 18mm 15mm; }
:root { --ink:#0b1d38; --muted:#4b5a70; --line:#d9e1ec; --accent:#1d5fd1; --soft:#f3f6fb; }
* { box-sizing: border-box; }
body { font: 10.4pt/1.5 "Segoe UI", "Helvetica Neue", Arial, sans-serif; color: var(--ink); margin: 0; }
main { max-width: 180mm; margin: 0 auto; }
h1 { font-size: 23pt; line-height: 1.15; margin: 0 0 4pt; letter-spacing: -0.02em; }
h1 + h3 { font-size: 13pt; font-weight: 500; color: var(--muted); margin: 0 0 10pt; }
h2 { font-size: 14.5pt; margin: 20pt 0 6pt; padding-bottom: 3pt; border-bottom: 2px solid var(--accent); break-after: avoid; }
h3 { font-size: 11.5pt; margin: 14pt 0 4pt; break-after: avoid; }
p, li { orphans: 3; widows: 3; }
blockquote { margin: 8pt 0; padding: 7pt 11pt; background: var(--soft); border-left: 3px solid var(--accent); color: var(--ink); }
blockquote p { margin: 0; }
table { width: 100%; border-collapse: collapse; margin: 6pt 0 10pt; font-size: 8.9pt; break-inside: avoid; }
th { background: var(--soft); text-align: left; font-weight: 600; }
th, td { border-bottom: 1px solid var(--line); padding: 3.5pt 5pt; vertical-align: top; }
img { display: block; max-width: 100%; max-height: 118mm; margin: 6pt auto 2pt; break-inside: avoid; }
p em { color: var(--muted); font-size: 9pt; }
code { font-family: Consolas, "Cascadia Mono", monospace; font-size: 8.8pt; background: var(--soft); padding: 0 2pt; border-radius: 2px; }
pre { background: var(--soft); padding: 7pt 9pt; border-radius: 4px; font-size: 8.4pt; white-space: pre-wrap; break-inside: avoid; }
pre code { background: none; padding: 0; }
hr { border: 0; border-top: 1px solid var(--line); margin: 12pt 0; }
a { color: var(--accent); text-decoration: none; }
"""


def find_browser() -> str:
    for candidate in BROWSERS:
        if Path(candidate).exists() or shutil.which(candidate):
            return candidate
    raise SystemExit("No Chrome or Edge found to print the PDF.")


LIST_ITEM = re.compile(r"^(\s*)([-*]|\d+\.)\s")


def github_lists(text: str) -> str:
    """Python-Markdown needs a blank line before a list and 4-space nesting; GitHub does not."""
    out: list[str] = []
    for line in text.splitlines():
        match = LIST_ITEM.match(line)
        if match:
            indent = len(match.group(1))
            if indent:
                line = " " * (indent * 2) + line.lstrip()
            previous = out[-1] if out else ""
            if previous.strip() and not LIST_ITEM.match(previous) and not previous.startswith(" "):
                out.append("")
        out.append(line)
    return "\n".join(out)


def main() -> None:
    source = (HERE / "REPORT.md").read_text(encoding="utf-8")
    body_md = github_lists(re.sub(r"\A---\n.*?\n---\n", "", source, flags=re.S))
    body = markdown.markdown(
        body_md, extensions=["tables", "fenced_code", "sane_lists", "attr_list"]
    )
    title = "How Predictable Is Brazilian Aviation? — ANAC Flight Intelligence"
    html = f"<!doctype html><html lang='en'><head><meta charset='utf-8'><title>{title}</title><style>{CSS}</style></head><body><main>{body}</main></body></html>"
    html_path = HERE / "REPORT.html"
    html_path.write_text(html, encoding="utf-8")
    pdf_path = HERE / "REPORT.pdf"
    subprocess.run(
        [
            find_browser(),
            "--headless=new",
            "--disable-gpu",
            "--no-pdf-header-footer",
            f"--print-to-pdf={pdf_path}",
            html_path.as_uri(),
        ],
        check=True,
        capture_output=True,
        timeout=180,
    )
    published = HERE.parents[1] / "web" / "public" / "ml" / "report.pdf"
    published.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(pdf_path, published)
    print(f"wrote {html_path}, {pdf_path} ({pdf_path.stat().st_size // 1024} KB) and {published}")


if __name__ == "__main__":
    sys.exit(main())
