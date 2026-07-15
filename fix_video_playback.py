#!/usr/bin/env python3
"""Fix broken video-wrap HTML and replace iframes with click-to-open launcher."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "vectorpro-cz"
EMBEDS = OUT / "data" / "video-embeds.json"

embeds = json.loads(EMBEDS.read_text(encoding="utf-8"))


def poster_url(embed: str) -> str:
    m = re.search(r"embed/([^/]+)/([^/?\"]+)", embed or "")
    if not m:
        return ""
    return f"https://cdn-thumbnails.sproutvideo.com/{m.group(1)}/{m.group(2)}/0/btn_true,btnbg_2f3437/poster.jpg"


def build_launcher(key: str, vids: str, embed: str) -> str:
    href = vids or embed or "#"
    poster = poster_url(embed)
    img = (
        f'<img class="video-poster" src="{poster}" alt="Náhled videa" loading="lazy">'
        if poster
        else '<div class="video-poster-fallback"></div>'
    )
    return (
        f'<div class="video-display video-launcher">'
        f'<a class="video-play-link" href="{href}" target="_blank" rel="noopener" '
        f'title="Přehrát video v novém okně">'
        f"{img}"
        f'<span class="video-play-btn" aria-hidden="true">▶</span>'
        f'<span class="video-play-label">Přehrát video</span>'
        f"</a>"
        f'<p class="video-open-hint">Kliknutím se video otevře v novém okně.</p>'
        f"</div>"
    )


def fix_notes(html: str) -> str:
    # Ensure note-block exists after each video-wrap close before </article>
    def ensure_note(m):
        block = m.group(0)
        if "note-block" in block:
            # add empty desc placeholder if missing editable-note
            if "editable-note" not in block:
                block = block.replace(
                    "</div></article>",
                    '<div class="note-block" data-note-id="unknown"><p class="desc-cs editable-note desc-empty" data-field="desc" data-placeholder="Klikněte pro přidání popisku…"></p><button type="button" class="note-add-desc-btn">+ Přidat popisek</button></div></article>',
                )
            return block
        key_m = re.search(r'data-video-key="([^"]+)"', block)
        nid = key_m.group(1) if key_m else "note"
        return block.replace(
            "</article>",
            f'<div class="note-block" data-note-id="{nid}">'
            f'<p class="desc-cs editable-note desc-empty" data-field="desc" data-placeholder="Klikněte pro přidání popisku…"></p>'
            f'<button type="button" class="note-add-desc-btn">+ Přidat popisek</button>'
            f"</div></article>",
        )

    # Mark empty descriptions
    html = re.sub(
        r'(<p class="desc-cs editable-note" data-field="desc">)\s*(</p>)',
        r'\1\2',
        html,
    )
    html = re.sub(
        r'<p class="desc-cs editable-note" data-field="desc"></p>',
        '<p class="desc-cs editable-note desc-empty" data-field="desc" data-placeholder="Klikněte pro přidání popisku…"></p>',
        html,
    )
    return html


def fix_page(html: str, slug: str) -> str:
    # Fix missing > before video-display (main bug)
    html = re.sub(
        r'(data-original="[^"]*)"\s*<div class="video-display">',
        r'\1"><div class="video-display">',
        html,
    )
    html = re.sub(
        r'(data-default-embed="[^"]*)"\s*<div class="video-display">',
        r'\1"><div class="video-display">',
        html,
    )
    html = re.sub(
        r'(data-vids-url="[^"]*)"\s*data-default-embed',
        r'\1" data-default-embed',
        html,
    )

    counter = [0]

    def replace_video_section(m):
        counter[0] += 1
        key = m.group(1)
        attrs = m.group(2)
        info = embeds.get(key, {})
        vids = info.get("vids", "")
        embed = info.get("embed", "")
        vids_m = re.search(r'data-vids-url="([^"]*)"', attrs)
        embed_m = re.search(r'data-default-embed="([^"]*)"', attrs)
        vids = (vids_m.group(1) if vids_m else "") or vids
        embed = (embed_m.group(1) if embed_m else "") or embed
        toolbar_m = re.search(r'<div class="video-toolbar"[^>]*>.*?</div>', m.group(0), re.S)
        toolbar = toolbar_m.group(0) if toolbar_m else (
            f'<div class="video-toolbar" data-video-key="{key}">'
            f'<button type="button" data-action="delete-video">Smazat video</button>'
            f'<label class="btn-file">Nahrát vlastní<input type="file" accept="video/*" hidden data-action="upload-video"></label>'
            f'<button type="button" data-action="set-link">Vlastní odkaz</button>'
            f'<button type="button" data-action="restore-video">Obnovit původní</button>'
            f"</div>"
        )
        clean_attrs = re.sub(r'\s*data-vids-url="[^"]*"', "", attrs)
        clean_attrs = re.sub(r'\s*data-default-embed="[^"]*"', "", clean_attrs)
        clean_attrs = re.sub(r'\s*data-original="[^"]*"', "", clean_attrs)
        return (
            f'<div class="video-wrap" data-video-key="{key}" '
            f'data-vids-url="{vids}" data-default-embed="{embed}"{clean_attrs}>'
            f"{build_launcher(key, vids, embed)}"
            f"{toolbar}</div>"
        )

    html = re.sub(
        r'<div class="video-wrap" data-video-key="([^"]+)"([^>]*)>.*?<div class="video-toolbar"[^>]*>.*?</div>\s*</div>',
        replace_video_section,
        html,
        flags=re.S,
    )

    html = fix_notes(html)
    return html


def main():
    count = 0
    for p in OUT.rglob("software/*/index.html"):
        slug_m = re.search(r"software[/\\]([^/\\]+)", str(p))
        slug = slug_m.group(1) if slug_m else ""
        html = p.read_text(encoding="utf-8")
        new = fix_page(html, slug)
        if new != html:
            p.write_text(new, encoding="utf-8")
            count += 1
            print("fixed", p.relative_to(OUT))
    print(f"done: {count} pages")


if __name__ == "__main__":
    main()
