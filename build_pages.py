#!/usr/bin/env python3
"""Build static site for GitHub Pages (play pages + base path)."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SITE = ROOT / "vectorpro-cz"
EMBEDS = SITE / "data" / "video-embeds.json"
OVERRIDES = SITE / "data" / "video-overrides.json"


def load_json(path: Path, default):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def render_play_page(slug: str, idx: int, embed: str, vids: str, base: str) -> str:
    title = slug.replace("-", " ").title()
    sep = "&" if "?" in embed else "?"
    embed_autoplay = f"{embed}{sep}autoPlay=true"
    back = f"{base}/software/{slug}/".replace("//", "/")
    vids_link = (
        f'<p><a href="{vids}" target="_blank" rel="noopener">Otevřít na původním webu</a></p>'
        if vids
        else ""
    )
    return f"""<!DOCTYPE html>
<html lang="cs"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Video – {title}</title>
<style>
  body {{ margin:0; background:#0a0a0a; color:#eee; font-family:Segoe UI,sans-serif; }}
  header {{ padding:0.75rem 1rem; background:#003d62; display:flex; gap:1rem; align-items:center; }}
  header a {{ color:#fff; text-decoration:none; }}
  main {{ display:flex; flex-direction:column; align-items:center; padding:1rem; }}
  .player {{ width:min(960px,100vw); aspect-ratio:16/9; background:#000; }}
  iframe {{ width:100%; height:100%; border:0; }}
</style>
</head>
<body>
<header>
  <a href="{back}">← Zpět</a>
  <span>{title}</span>
</header>
<main>
  <div class="player">
    <iframe src="{embed_autoplay}" allow="autoplay; fullscreen; encrypted-media; picture-in-picture" allowfullscreen></iframe>
  </div>
  {vids_link}
</main>
</body></html>"""


def rewrite_root_paths(text: str, base: str) -> str:
    if not base:
        return text
    b = base.rstrip("/")

    def repl_attr(m: re.Match) -> str:
        attr, path = m.group(1), m.group(2)
        if path.startswith(("http://", "https://", "//", "#", "mailto:")):
            return m.group(0)
        if path.startswith(b + "/") or path == b:
            return m.group(0)
        if path.startswith("/"):
            return f'{attr}="{b}{path}"'
        return m.group(0)

    text = re.sub(r'(href|src)="(/[^"]*)"', repl_attr, text)
    return text


def ensure_config_script(html: str, base: str) -> str:
    cfg = f'<script src="{base}/assets/config.js"></script>' if base else '<script src="/assets/config.js"></script>'
    if "assets/config.js" in html:
        return html
    return html.replace("<script src=", f"{cfg}\n  <script src=", 1)


def inject_base_config(html_path: Path, base: str) -> None:
    if base:
        snippet = f'<script>window.VP_BASE="{base.rstrip("/")}";</script>'
        text = html_path.read_text(encoding="utf-8")
        if snippet not in text and "window.VP_BASE" not in text:
            text = text.replace("</head>", f"  {snippet}\n</head>", 1)
            html_path.write_text(text, encoding="utf-8")


def build(out: Path, base: str) -> None:
    base = base.rstrip("/")
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(SITE, out)

    embeds = load_json(EMBEDS, {})
    overrides = load_json(OVERRIDES, {})

    for key, info in embeds.items():
        if "::" not in key:
            continue
        slug, idx_s = key.split("::", 1)
        try:
            idx = int(idx_s)
        except ValueError:
            continue
        override = overrides.get(key, {})
        if override.get("mode") == "deleted":
            continue
        embed = info.get("embed", "")
        if override.get("mode") == "embed" and override.get("url"):
            embed = override["url"]
        if not embed:
            continue
        vids = info.get("vids", "")
        play_dir = out / "play" / slug / str(idx)
        play_dir.mkdir(parents=True, exist_ok=True)
        page = render_play_page(slug, idx, embed, vids, base)
        (play_dir / "index.html").write_text(page, encoding="utf-8")

    config_template = (SITE / "assets" / "config.js").read_text(encoding="utf-8")
    if base:
        head = f'window.VP_BASE = "{base}";\n'
        config_template = head + config_template
    (out / "assets" / "config.js").write_text(config_template, encoding="utf-8")

    for html_path in out.rglob("*.html"):
        text = html_path.read_text(encoding="utf-8")
        text = ensure_config_script(text, base)
        text = rewrite_root_paths(text, base)
        html_path.write_text(text, encoding="utf-8")
        inject_base_config(html_path, base)

    print(f"Built {out} with base={base!r}, {len(list((out / 'play').rglob('index.html')))} play pages")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="_site", help="Output directory")
    ap.add_argument("--base", default="/vectorpro-cz", help="GitHub Pages base path (empty for root)")
    args = ap.parse_args()
    build(ROOT / args.out, args.base)


if __name__ == "__main__":
    main()
