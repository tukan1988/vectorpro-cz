#!/usr/bin/env python3
"""Fix navigation: absolute URLs + nav.js on all pages."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "vectorpro-cz"

NAV_SCRIPT = '  <script src="/assets/nav.js" defer></script>\n  <script src="/assets/editor.js" defer></script>'


def fix_file(path: Path) -> None:
    html = path.read_text(encoding="utf-8")

    # Absolute asset paths
    html = re.sub(r'href="(?:\.\./)*assets/style\.css"', 'href="/assets/style.css"', html)
    html = re.sub(r'src="(?:\.\./)*assets/editor\.js"', 'src="/assets/editor.js"', html)
    html = re.sub(r'src="(?:\.\./)*assets/nav\.js"', 'src="/assets/nav.js"', html)

    # Home / logo links
    html = re.sub(r'href="(?:\.\./)*index\.html"', 'href="/"', html)

    # Sidebar + internal software links -> absolute
    def soft_link(m):
        slug = m.group(1)
        return f'href="/software/{slug}/"'

    html = re.sub(r'href="(?:\.\./)*software/([^/]+)/index\.html"', soft_link, html)
    html = re.sub(r'href="/software/([^/]+)/index\.html"', soft_link, html)

    # Data links
    html = re.sub(r'href="(?:\.\./)*data/([^"]+)"', r'href="/data/\1"', html)

    # Inject nav.js before editor.js
    html = re.sub(
        r'\s*<script src="/assets/editor\.js" defer></script>',
        "\n" + NAV_SCRIPT,
        html,
    )
    if "/assets/nav.js" not in html and "</body>" in html:
        html = html.replace("</body>", f"\n{NAV_SCRIPT}\n</body>")

    path.write_text(html, encoding="utf-8")


def main():
    for p in sorted(OUT.rglob("index.html")):
        fix_file(p)
        print("fixed", p.relative_to(OUT))
    print("done")


if __name__ == "__main__":
    main()
