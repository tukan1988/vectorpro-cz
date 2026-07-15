#!/usr/bin/env python3
"""Upgrade layout, videos, editable titles, fix links."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "vectorpro-cz"
EMBEDS = OUT / "data" / "video-embeds.json"

LAYOUT_CSS = """
.site-shell { max-width: 1400px; margin: 0 auto; padding: 0 1rem 1rem; }
.sidebar {
  width: 100%;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 1rem;
  max-height: 42vh;
  overflow: auto;
}
.sidebar-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 0.5rem 1.25rem; }
.content-panel {
  margin-top: 1rem;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 1.25rem 1.5rem;
  min-height: 420px;
}
.content-panel .content { border: 0; padding: 0; background: transparent; min-height: 200px; }
h1 .title-cs, .video-item h3 .title-cs { display: inline; }
body.edit-mode .editable-title-cs {
  outline: 2px dashed #c77d00;
  outline-offset: 3px;
  background: #fff8e8;
}
.video-toolbar {
  display: none;
  gap: 0.4rem;
  flex-wrap: wrap;
  margin: 0.5rem 0;
}
body.edit-mode .video-toolbar { display: flex; }
.video-toolbar button, .video-toolbar label.btn-file {
  font-size: 0.8rem;
  padding: 0.25rem 0.55rem;
  border-radius: 4px;
  border: 1px solid var(--border);
  background: #f5f8fa;
  cursor: pointer;
}
.video-toolbar label.btn-file { display: inline-block; }
.video-link-btn {
  display: inline-block;
  margin-top: 0.5rem;
  padding: 0.45rem 0.8rem;
  background: var(--accent);
  color: #fff !important;
  border-radius: 4px;
  text-decoration: none;
  font-size: 0.9rem;
}
.video-link-btn:hover { background: #007cbd; }
.video-deleted-msg { color: var(--muted); font-style: italic; padding: 1rem 0; }
.layout { display: block !important; max-width: none !important; padding: 0 !important; }
"""


def load_embeds() -> dict:
    if EMBEDS.exists():
        return json.loads(EMBEDS.read_text(encoding="utf-8"))
    return {}


def fix_links(html: str) -> str:
    html = re.sub(r'href="(?:\.\./)+([^"/]+)/index\.html"', r'href="/software/\1/"', html)
    html = re.sub(r'href="software/([^"/]+)/index\.html"', r'href="/software/\1/"', html)
    html = re.sub(r'href="(?:\.\./)*index\.html"', 'href="/"', html)
    html = re.sub(r'href="/software/([^"/]+)/index\.html"', r'href="/software/\1/"', html)
    return html


def restructure_layout(html: str) -> str:
    if "site-shell" in html:
        return html
    html = re.sub(
        r'<div class="layout">\s*(<nav class="sidebar">.*?</nav>)\s*(<main class="content">.*?</main>)\s*</div>',
        r'<div class="site-shell"><div class="layout">\1</div><section class="content-panel">\2</section></div>',
        html,
        flags=re.S,
    )
    html = html.replace('<main class="content">', '<main class="content">')
    return html


def wrap_sidebar_grid(html: str) -> str:
    html = re.sub(
        r'(<nav class="sidebar"><h2>VectorPro – Index</h2>)(.*?)(</nav>)',
        lambda m: m.group(1) + '<div class="sidebar-grid">' + m.group(2) + '</div>' + m.group(3),
        html,
        flags=re.S,
        count=1,
    )
    return html


def upgrade_titles(html: str) -> str:
    html = re.sub(
        r"<h1>\s*(?:<span class=\"title-cs editable-title-cs\"[^>]*>)?([^<]+?)(?:</span>)?\s*(<span class=\"en-inline\">.*?</span>)\s*</h1>",
        r'<h1><span class="title-cs editable-title-cs" data-field="page-title">\1</span>\2</h1>',
        html,
        count=1,
        flags=re.S,
    )
    html = re.sub(
        r'(<article class="video-item"><h3>)\s*(?:<span class="title-cs editable-title-cs"[^>]*>)?([^<]+?)(?:</span>)?\s*(<span class="en-inline">.*?</span></h3>)',
        r'\1<span class="title-cs editable-title-cs" data-field="video-title">\2</span>\3',
        html,
        flags=re.S,
    )
    return html


def upgrade_videos(html: str, slug: str, embeds: dict) -> str:
    if "data-default-embed" in html:
        return html
    counter = [0]

    def repl(m):
        counter[0] += 1
        key = f"{slug}::{counter[0]}"
        info = embeds.get(key, {})
        embed = info.get("embed") or ""
        if not embed:
            return m.group(0)
        orig = info.get("original", "")
        toolbar = (
            f'<div class="video-toolbar" data-video-key="{key}">'
            f'<button type="button" data-action="delete-video">Smazat video</button>'
            f'<label class="btn-file">Nahrát vlastní video<input type="file" accept="video/*" hidden data-action="upload-video"></label>'
            f'<button type="button" data-action="set-link">Nastavit odkaz (nové okno)</button>'
            f'<button type="button" data-action="restore-video">Obnovit původní</button>'
            f"</div>"
        )
        return (
            f'<div class="video-wrap" data-video-key="{key}" data-default-embed="{embed}" data-original="{orig}">'
            f'<div class="video-display">'
            f'<iframe src="{embed}" width="630" height="354" frameborder="0" '
            f'allow="autoplay; fullscreen; picture-in-picture" allowfullscreen></iframe>'
            f"</div>"
            f"{toolbar}</div>"
        )

    html = re.sub(
        r'<div class="video-wrap"(?:[^>]*)>.*?</div>\s*(?=<div class="note-block"|</article>)',
        repl,
        html,
        flags=re.S,
    )
    return html


def ensure_scripts(html: str) -> str:
    html = re.sub(r'href="(?:\.\./)*assets/style\.css"', 'href="/assets/style.css"', html)
    if "/assets/nav.js" not in html:
        html = html.replace(
            "</body>",
            '  <script src="/assets/nav.js" defer></script>\n  <script src="/assets/editor.js" defer></script>\n</body>',
        )
    return html


def patch_file(path: Path, embeds: dict) -> None:
    html = path.read_text(encoding="utf-8")
    slug_m = re.search(r"software[/\\]([^/\\]+)[/\\]index\.html", str(path).replace("\\", "/"))
    slug = slug_m.group(1) if slug_m else ""

    html = fix_links(html)
    html = restructure_layout(html)
    html = wrap_sidebar_grid(html)
    if slug:
        html = upgrade_titles(html)
        html = upgrade_videos(html, slug, embeds)
    else:
        html = restructure_layout(html)
        html = wrap_sidebar_grid(html)
    html = ensure_scripts(html)
    path.write_text(html, encoding="utf-8")


def patch_css() -> None:
    css_path = OUT / "assets" / "style.css"
    css = css_path.read_text(encoding="utf-8")
    css = re.sub(r"\.layout \{[^}]+\}", ".layout { display: block; }", css, count=1)
    if ".site-shell" not in css:
        css += LAYOUT_CSS
    css_path.write_text(css, encoding="utf-8")


def main() -> None:
    embeds = load_embeds()
    patch_css()
    for p in sorted(OUT.rglob("index.html")):
        patch_file(p, embeds)
        print("upgraded", p.relative_to(OUT))
    print("done")


if __name__ == "__main__":
    main()
