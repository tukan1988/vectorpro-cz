#!/usr/bin/env python3
"""Point all video-play-link hrefs to local /play/slug/n player."""

import re
from pathlib import Path

OUT = Path(__file__).resolve().parent / "vectorpro-cz"


def play_href(key: str) -> str:
    slug, _, idx = key.partition("::")
    return f"/play/{slug}/{idx}"


def fix(html: str) -> str:
    def repl(m):
        key = m.group(1)
        rest = m.group(2)
        href = play_href(key)
        return f'<a class="video-play-link" href="{href}" target="_blank" rel="noopener"{rest}'

    html = re.sub(
        r'<a class="video-play-link" href="[^"]*"([^>]*?)>',
        lambda m: repl(re.search(r'data-video-key="([^"]+)"', html[m.start() - 200 : m.start() + 50] or "") or type("", (), {"group": lambda s, x: "unknown::1"})()),
        html,
    )
    # simpler: replace per video-wrap block
    def fix_wrap(m):
        block = m.group(0)
        key_m = re.search(r'data-video-key="([^"]+)"', block)
        if not key_m:
            return block
        href = play_href(key_m.group(1))
        block = re.sub(
            r'(<a class="video-play-link" href=")[^"]*(")',
            rf"\1{href}\2",
            block,
            count=1,
        )
        return block

    html = re.sub(
        r'<div class="video-wrap" data-video-key="[^"]+"[^>]*>.*?</div>\s*(?=<div class="video-toolbar"|</div><div class="note-block")',
        fix_wrap,
        html,
        flags=re.S,
    )
    return html


def main():
    n = 0
    for p in OUT.rglob("software/*/index.html"):
        html = p.read_text(encoding="utf-8")
        new = html
        for key_m in re.finditer(r'data-video-key="([^"]+)"', html):
            key = key_m.group(1)
            if "::" not in key:
                continue
            href = play_href(key)
            # fix play link in following 800 chars
            start = key_m.start()
            chunk = new[start : start + 1200]
            chunk_new = re.sub(
                r'(<a class="video-play-link" href=")[^"]*(")',
                rf"\1{href}\2",
                chunk,
                count=1,
            )
            if chunk_new != chunk:
                new = new[:start] + chunk_new + new[start + 1200 :]
        if new != html:
            p.write_text(new, encoding="utf-8")
            n += 1
            print("fixed", p.relative_to(OUT))
    print(f"done: {n}")


if __name__ == "__main__":
    main()
