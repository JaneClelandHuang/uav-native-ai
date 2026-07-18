#!/usr/bin/env python3
"""
Export the slide deck to a PDF handout using headless Chrome/Chromium/Edge.

Why this approach: the deck uses modern CSS (min(), aspect-ratio) that
older HTML-to-PDF tools (wkhtmltopdf, etc.) don't render correctly. A real
Chromium-family browser handles it natively, and every OS ships with one
close at hand. This script has no dependencies beyond Python's standard
library -- nothing to pip install, nothing to keep updated.

It works by shelling out to the browser's built-in --headless
--print-to-pdf flag against index.html. The actual "turn every slide into
its own page" logic lives in styles.css's @media print block, not here --
this script just triggers Chrome's print pipeline.

Usage:
    python generate_pdf.py                       # deck in current dir -> slides.pdf
    python generate_pdf.py --deck path/to/deck    # deck in a specific folder
    python generate_pdf.py --out handout.pdf      # custom output filename
    python generate_pdf.py --chrome "/path/to/chrome"   # explicit browser path,
                                                          # if auto-detection fails

Run this after every edit to the deck to regenerate the PDF.
"""

import argparse
import pathlib
import platform
import shutil
import subprocess
import sys
from typing import Optional

CANDIDATE_NAMES = [
    "google-chrome", "google-chrome-stable", "chrome",
    "chromium", "chromium-browser",
    "microsoft-edge", "microsoft-edge-stable", "msedge",
]

CANDIDATE_PATHS_MAC = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
]

CANDIDATE_PATHS_WINDOWS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]


def find_browser(explicit: Optional[str]) -> str:
    if explicit:
        path = pathlib.Path(explicit)
        if path.exists():
            return str(path)
        sys.exit(f"Specified browser not found at: {explicit}")

    for name in CANDIDATE_NAMES:
        found = shutil.which(name)
        if found:
            return found

    system = platform.system()
    candidates = (
        CANDIDATE_PATHS_MAC if system == "Darwin"
        else CANDIDATE_PATHS_WINDOWS if system == "Windows"
        else []
    )
    for path in candidates:
        if pathlib.Path(path).exists():
            return path

    sys.exit(
        "Could not find Chrome, Chromium, or Edge on this machine.\n"
        "Install one of those, or point directly at it:\n"
        '  python generate_pdf.py --chrome "/path/to/chrome"'
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--deck", default=".", help="Folder containing index.html (default: current directory)")
    parser.add_argument("--out", default="slides.pdf", help="Output PDF filename (default: slides.pdf)")
    parser.add_argument("--chrome", default=None, help="Explicit path to a Chrome/Chromium/Edge executable")
    args = parser.parse_args()

    deck_dir = pathlib.Path(args.deck).resolve()
    index_path = deck_dir / "index.html"
    if not index_path.exists():
        sys.exit(f"No index.html found in {deck_dir}")

    out_arg = pathlib.Path(args.out)
    out_path = out_arg if out_arg.is_absolute() else deck_dir / out_arg

    browser = find_browser(args.chrome)
    file_url = index_path.as_uri()

    cmd = [
        browser,
        "--headless=new",
        "--disable-gpu",
        "--no-pdf-header-footer",
        "--run-all-compositor-stages-before-draw",
        "--virtual-time-budget=8000",
        f"--print-to-pdf={out_path}",
        file_url,
    ]

    print(f"Browser: {browser}")
    print(f"Deck:    {index_path}")
    print(f"Output:  {out_path}")
    print("Rendering...")

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0 or not out_path.exists():
        sys.exit(
            "PDF generation failed.\n"
            f"--- stdout ---\n{result.stdout}\n"
            f"--- stderr ---\n{result.stderr}\n\n"
            "If your browser is older, try adding --chrome to point at a newer "
            "install, or check that Chrome supports --headless=new (Chrome 112+)."
        )

    size_kb = out_path.stat().st_size / 1024
    print(f"Done — wrote {out_path.name} ({size_kb:.0f} KB)")


if __name__ == "__main__":
    main()
