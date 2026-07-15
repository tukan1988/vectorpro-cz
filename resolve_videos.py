#!/usr/bin/env python3
"""Resolve vectorpro oembed URLs to direct SproutVideo embed URLs."""

import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCRAPE = ROOT / "vectorpro-cz" / ".cache" / "scrape.json"
OUT = ROOT / "vectorpro-cz" / "data" / "video-embeds.json"


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=45) as resp:
        return resp.read().decode("utf-8", "replace")


def vids_url_from_oembed(src: str) -> str | None:
    m = re.search(r"[?&]url=([^&\"]+)", src)
    if not m:
        return None
    return urllib.parse.unquote(m.group(1).replace("&amp;", "&"))


def sprout_embed_from_vids(vids_url: str) -> str | None:
    html = fetch(vids_url)
    m = re.search(r"https://videos\.sproutvideo\.com/embed/[a-zA-Z0-9/_-]+", html)
    if m:
        return m.group(0)
    m = re.search(r'"embedUrl":"(https://videos\.sproutvideo\.com/embed/[^"]+)"', html)
    if m:
        return m.group(1)
    return None


def resolve_src(src: str) -> dict:
    src = src.replace("&amp;", "&")
    if "sproutvideo.com/embed" in src:
        return {"embed": src, "vids": None}
    vids = vids_url_from_oembed(src)
    if not vids:
        return {"embed": src, "vids": None}
    embed = sprout_embed_from_vids(vids)
    return {"embed": embed or src, "vids": vids}


def main() -> None:
    scrape = json.loads(SCRAPE.read_text(encoding="utf-8"))
    cache = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    total = 0
    for slug, page in scrape.items():
        for i, video in enumerate(page.get("videos") or [], 1):
            src = video.get("iframe_src") or ""
            if not src:
                continue
            key = f"{slug}::{i}"
            if key in cache and cache[key].get("embed", "").startswith("https://videos.sproutvideo"):
                continue
            print(f"resolve {key}")
            try:
                cache[key] = resolve_src(src)
                cache[key]["original"] = src
                total += 1
                time.sleep(0.25)
            except Exception as exc:
                print(f"  ERR {exc}")
                cache[key] = {"embed": src, "error": str(exc), "original": src}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {len(cache)} entries ({total} new)")


if __name__ == "__main__":
    main()
