#!/usr/bin/env python3
"""Remove footer info text, add lang.js, strip password mentions from HTML."""

from pathlib import Path
import re

SITE = Path(__file__).resolve().parent / "vectorpro-cz"
FOOTER_OLD = re.compile(
    r'\s*<div>VectorPro CZ – videa načítána z vectorpro\.io \| Úpravy: heslo titanic – editovat lze české nadpisy, popisky a videa</div>\s*',
    re.MULTILINE,
)
LANG_TAG = '  <script src="/assets/lang.js" defer></script>\n'


def main():
    html_n = footer_n = lang_n = 0
    for html in SITE.rglob("*.html"):
        text = html.read_text(encoding="utf-8")
        orig = text
        text = FOOTER_OLD.sub("\n", text)
        if text != orig:
            footer_n += 1
        if "assets/lang.js" not in text and "assets/nav.js" in text:
            text = text.replace(
                '  <script src="/assets/nav.js" defer></script>',
                LANG_TAG + '  <script src="/assets/nav.js" defer></script>',
                1,
            )
            lang_n += 1
        if text != orig or lang_n:
            html.write_text(text, encoding="utf-8")
            html_n += 1
    print(f"Updated {html_n} files, removed footer from {footer_n}, added lang.js to {lang_n}")


if __name__ == "__main__":
    main()
