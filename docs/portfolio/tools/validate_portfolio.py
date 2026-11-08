"""Read-only portfolio checks; writes a small report, never contacts an LLM."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import urllib.request
import zipfile
from collections import Counter
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pymupdf
from PIL import Image
from pptx import Presentation

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "docs/portfolio"
CHECKS = []


def check(name, passed, detail=None):
    CHECKS.append({"name": name, "passed": bool(passed), "detail": detail})


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-public", action="store_true")
    args = parser.parse_args()
    docs = [
        ROOT / "README.md",
        ROOT / "docs/README.md",
        *BASE.rglob("*.md"),
        *(ROOT / "docs/ml/en").glob("*.md"),
    ]
    external = set()
    missing = []
    relative_count = 0
    for path in docs:
        if path.name == "CASE_STUDY_original.md":
            continue
        content = re.sub(r"```.*?```", "", path.read_text(encoding="utf-8-sig"), flags=re.S)
        for raw in re.findall(r"\[[^\]]*\]\(([^\s)]+)(?:[^)]*)\)", content):
            raw = raw.strip("<>")
            parts = urlsplit(raw)
            if parts.scheme in ["http", "https"]:
                external.add(raw)
                continue
            if parts.scheme or not parts.path:
                continue
            target = (path.parent / unquote(parts.path)).resolve()
            relative_count += 1
            if not target.exists():
                missing.append({"file": path.relative_to(ROOT).as_posix(), "target": raw})
            elif parts.fragment and target.suffix == ".md":
                headings = re.findall(
                    r"^#{1,6}\s+(.+)$", target.read_text(encoding="utf-8-sig"), flags=re.M
                )
                anchors = {re.sub(r"[^\w\- ]", "", h.lower()).replace(" ", "-") for h in headings}
                if unquote(parts.fragment) not in anchors:
                    missing.append(
                        {
                            "file": path.relative_to(ROOT).as_posix(),
                            "target": raw,
                            "reason": "anchor",
                        }
                    )
    check("local_markdown_links", not missing, {"checked": relative_count, "missing": missing})
    verified_images = []
    for p in (BASE / "assets").rglob("*"):
        if p.suffix.lower() in [".jpg", ".png"]:
            with Image.open(p) as im:
                im.verify()
            verified_images.append(p.relative_to(ROOT).as_posix())
    check("image_integrity", len(verified_images) > 20, {"count": len(verified_images)})
    for language, name in [
        ("en", "anac-flight-intelligence-presentation-en"),
        ("pt", "anac-flight-intelligence-apresentacao"),
    ]:
        ppt = BASE / f"presentation/{name}.pptx"
        pdf = BASE / f"presentation/{name}.pdf"
        with zipfile.ZipFile(ppt) as archive:
            check(f"{language}_pptx_zip_integrity", archive.testzip() is None)
        pres = Presentation(ppt)
        document = pymupdf.open(pdf)
        check(f"{language}_slide_count", len(pres.slides) == len(document) == 10)
        all_text = []
        parity = []
        outside = []
        for i, (slide, page) in enumerate(zip(pres.slides, document, strict=True)):
            ptext = " ".join(shape.text for shape in slide.shapes if shape.has_text_frame)
            pdftext = page.get_text()
            all_text.append(pdftext)
            parity.append(Counter(ptext.split()) == Counter(pdftext.split()))
            for block in page.get_text("dict")["blocks"]:
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        box = span["bbox"]
                        if (
                            box[0] < -0.1
                            or box[1] < -0.1
                            or box[2] > page.rect.width + 0.1
                            or box[3] > page.rect.height + 0.1
                        ):
                            outside.append({"slide": i + 1, "text": span["text"]})
        check(f"{language}_pdf_pptx_text_parity", all(parity), {"slides": parity})
        check(f"{language}_pdf_text_inside_page", not outside, outside)
        text = " ".join(all_text).lower()
        terms = ["368", "91", "10.10%", "6.06 pp", "22.24%", "22.40%"]
        check(f"{language}_required_numbers", all(t in text for t in terms))
        if language == "en":
            caveats = [
                "partially exposed",
                "not been retrained",
                "inconclusive",
                "not trained",
                "not future forecasts",
                "11 skipped",
            ]
            check("english_required_disclosures", all(t in text for t in caveats), caveats)
        check(f"{language}_pdf_has_hyperlinks", any(page.get_links() for page in document))
    for ext in ["pdf", "pptx"]:
        check(
            f"english_{ext}_compatibility_alias",
            sha(BASE / f"presentation/anac-flight-intelligence-presentation-en.{ext}")
            == sha(BASE / f"presentation/anac-flight-intelligence-summary-en.{ext}"),
        )
    original = json.loads(
        (ROOT / "docs/ml/visualization-inventory.json").read_text(encoding="utf-8")
    )
    english = json.loads(
        (ROOT / "docs/ml/en/visualization-inventory.json").read_text(encoding="utf-8")
    )
    check(
        "english_inventory_exact_ids",
        {e["id"] for e in original["items"]} == {e["id"] for e in english["items"]},
    )
    check(
        "english_inventory_counts",
        all(
            english[k] == original[k]
            for k in ["web_charts", "web_tables", "web_kpis", "registry_panels", "report_figures"]
        ),
    )
    public = json.loads((ROOT / "web/public/ml/showcase.json").read_text(encoding="utf-8"))
    for key, expected in [("a", 10.10), ("b", 6.06), ("d_pax", 22.24), ("d_seats", 22.40)]:
        check(
            f"historical_metric_{key}",
            round(public["tasks"][key]["lightgbm"]["value"] * 100, 2) == expected,
        )
    protected = ["src", "tests", "configs", "web", "reports", "research/ml-showcase"]
    changes = subprocess.check_output(
        ["git", "diff", "--name-only", "100e509", "--", *protected], cwd=ROOT, text=True
    ).splitlines()
    check("production_and_audit_files_unchanged", not changes, changes)
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
    patterns = [
        rb"gsk_[A-Za-z0-9]{20,}",
        rb"gh[pousr]_[A-Za-z0-9]{30,}",
        rb"github_pat_[A-Za-z0-9_]{30,}",
        rb"AKIA[0-9A-Z]{16}",
        rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    ]
    candidates = set(n for n in tracked if n)
    candidates.update(
        str(p.relative_to(ROOT))
        for p in [ROOT / "README.md", *BASE.rglob("*"), *(ROOT / "docs/ml/en").rglob("*")]
        if p.is_file()
    )
    hits = []
    for name in sorted(candidates):
        p = ROOT / name
        if p.is_file() and any(re.search(pattern, p.read_bytes()) for pattern in patterns):
            hits.append(name)
    check(
        "credential_pattern_scan",
        not hits,
        {
            "file_count": len(candidates),
            "paths": hits,
            "scope": "Current tracked/candidate files and token/private-key patterns; not complete history or a security certification.",
        },
    )
    if args.check_public:
        # Only README HTTP GET links; never provider chat/status endpoints.
        links = {u for u in external if u.startswith("https://anac-flight-intelligence-")}
        for url in sorted(links):
            if "/analyst/status" in url or "/analyst/chat" in url:
                raise ValueError("Provider calls prohibited")
            try:
                with urllib.request.urlopen(url, timeout=90) as response:
                    status = response.status
            except Exception as exc:
                status = type(exc).__name__
            check("public_get_link", status == 200, {"url": url, "status": status})
        for route, local in [
            ("/ml/showcase.json", "web/public/ml/showcase.json"),
            ("/ml/report.pdf", "web/public/ml/report.pdf"),
        ]:
            with urllib.request.urlopen(
                "https://anac-flight-intelligence-api-main.vercel.app" + route, timeout=90
            ) as response:
                body = response.read()
            check(
                "published_audited_file_" + route,
                hashlib.sha256(body).hexdigest() == sha(ROOT / local),
            )
    assets = {
        p.relative_to(ROOT).as_posix(): sha(p)
        for p in (BASE / "presentation").glob("*")
        if p.suffix in [".pdf", ".pptx"]
    }
    result = {
        "status": "passed" if all(c["passed"] for c in CHECKS) else "failed",
        "date": "2026-11-08",
        "source_base": "100e5093b8d574603c784306d5920de779a66241",
        "check_count": len(CHECKS),
        "checks": CHECKS,
        "presentation_sha256": assets,
        "public_links_checked": args.check_public,
        "provider_calls": False,
        "models_retrained": False,
    }
    (BASE / "validation.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": result["status"],
                "checks": len(CHECKS),
                "failures": [c for c in CHECKS if not c["passed"]],
            }
        )
    )
    if result["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
