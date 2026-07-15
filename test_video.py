#!/usr/bin/env python3
"""Automated tests for video playback pages."""

import json
import re
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8765"
SAMPLES = [
    ("all-tests-tile", 1),
    ("play", 1),
    ("vectorpro-login-screen", 1),
]


def fetch(url: str) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "VectorProTest/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def test_server_up():
    code, _ = fetch(f"{BASE}/")
    assert code == 200, f"home returned {code}"
    print("OK server home 200")


def test_page_has_play_link(slug: str):
    code, html = fetch(f"{BASE}/software/{slug}/")
    assert code == 200, f"page {slug} returned {code}"
    href = f"/play/{slug}/1"
    assert href in html, f"missing {href} in /software/{slug}/"
    assert "video-play-link" in html, f"missing video-play-link in {slug}"
    print(f"OK page /software/{slug}/ contains {href}")


def test_player_autoplay(slug: str, idx: int):
    code, html = fetch(f"{BASE}/play/{slug}/{idx}")
    assert code == 200, f"player /play/{slug}/{idx} returned {code}"
    assert "autoPlay=true" in html, f"player page missing autoPlay param for {slug}/{idx}"
    m = re.search(r'<iframe src="(https://videos\.sproutvideo\.com/embed/[^"]+)"', html)
    assert m, f"no sproutvideo iframe in player page {slug}/{idx}"
    embed = m.group(1)
    ec, _ = fetch(embed)
    assert ec == 200, f"embed URL returned {ec}: {embed}"
    print(f"OK player /play/{slug}/{idx} autoplay iframe {embed[:70]}...")


def test_editor_js_inline_play():
    with open("vectorpro-cz/assets/editor.js", encoding="utf-8") as f:
        js = f.read()
    for fn in ("playInline", "bindPlayClicks", "playHrefFromKey"):
        assert f"function {fn}" in js, f"editor.js missing {fn}"
    print("OK editor.js has inline playback handlers")


def test_all_pages_have_play_links():
    from pathlib import Path

    root = Path("vectorpro-cz/software")
    missing = []
    for html_path in root.glob("*/index.html"):
        text = html_path.read_text(encoding="utf-8")
        if 'class="video-wrap"' not in text:
            continue
        slug = html_path.parent.name
        if f'href="/play/{slug}/' not in text:
            missing.append(slug)
    assert not missing, f"pages missing /play/ links: {missing[:5]}"
    print(f"OK all video pages contain /play/ links ({len(list(root.glob('*/index.html')))} pages checked)")


def test_embeds_json():
    with open("vectorpro-cz/data/video-embeds.json", encoding="utf-8") as f:
        data = json.load(f)
    assert len(data) > 100, "video-embeds.json too small"
    print(f"OK video-embeds.json has {len(data)} entries")


def main():
    failed = 0
    for fn in [test_server_up, test_embeds_json, test_editor_js_inline_play, test_all_pages_have_play_links]:
        try:
            fn()
        except Exception as e:
            print("FAIL", fn.__name__, e)
            failed += 1

    for slug, idx in SAMPLES:
        try:
            test_page_has_play_link(slug)
            test_player_autoplay(slug, idx)
        except Exception as e:
            print(f"FAIL {slug}/{idx}", e)
            failed += 1

    if failed:
        print(f"\n{failed} test(s) FAILED")
        sys.exit(1)
    print("\nAll video tests passed.")


if __name__ == "__main__":
    main()
