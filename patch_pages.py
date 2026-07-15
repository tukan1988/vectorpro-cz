#!/usr/bin/env python3
"""Patch existing VectorPro CZ pages: relative links, editable notes, editor UI."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "vectorpro-cz"
ANNOTATIONS = OUT_DIR / "data" / "annotations.json"

EDITOR_CSS_EXTRA = """
.site-footer {
  margin-top: 2rem;
  padding: 1rem 1.25rem;
  background: #1e2a33;
  color: #cbd5dc;
  font-size: 0.9rem;
}
.edit-bar {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  flex-wrap: wrap;
  margin-top: 0.5rem;
}
.edit-bar input[type=password] {
  padding: 0.35rem 0.5rem;
  border-radius: 4px;
  border: 1px solid #4a5560;
  background: #2a3640;
  color: #fff;
}
.edit-bar button {
  padding: 0.35rem 0.75rem;
  border: 0;
  border-radius: 4px;
  background: #0066a1;
  color: #fff;
  cursor: pointer;
}
.edit-bar button:hover { background: #007cbd; }
body.edit-mode .editable-note {
  outline: 2px dashed #0066a1;
  outline-offset: 4px;
  cursor: text;
  min-height: 1.5em;
}
body.edit-mode .editable-note:focus { background: #fffde7; }
.edit-status { color: #8fd694; font-size: 0.85rem; }
.note-block { margin: 0.75rem 0; }
.note-add-btn {
  display: none;
  margin-top: 0.5rem;
  padding: 0.3rem 0.6rem;
  font-size: 0.85rem;
  border: 1px dashed var(--accent);
  background: #eef6fb;
  color: var(--accent);
  border-radius: 4px;
  cursor: pointer;
}
body.edit-mode .note-add-btn { display: inline-block; }
.custom-note {
  margin-top: 0.5rem;
  padding: 0.5rem 0.75rem;
  background: #f0f7ff;
  border-left: 3px solid var(--accent);
  border-radius: 0 4px 4px 0;
}
.custom-note-label {
  font-size: 0.75rem;
  color: var(--muted);
  margin-bottom: 0.25rem;
}
.page-hint {
  color: var(--muted);
  font-size: 0.9rem;
  margin-bottom: 1rem;
}
"""


def depth_for(path: Path) -> int:
    rel = path.relative_to(OUT_DIR)
    return len(rel.parts) - 1


def rel_to_root(path: Path, target: str) -> str:
    d = depth_for(path)
    if d == 0:
        return target.lstrip("/")
    return "/".join([".."] * d) + "/" + target.lstrip("/")


def page_href(page_path: Path, slug: str) -> str:
    d = depth_for(page_path)
    if d == 0:
        return f"software/{slug}/index.html"
    return f"../{slug}/index.html"


def fix_links(html: str, page_path: Path) -> str:
    html = re.sub(
        r'href="/software/([^/]+)/"',
        lambda m: f'href="{page_href(page_path, m.group(1))}"',
        html,
    )
    home = rel_to_root(page_path, "index.html")
    html = html.replace('href="/"', f'href="{home}"')
    css = rel_to_root(page_path, "assets/style.css")
    html = re.sub(r'href="/assets/style\.css"', f'href="{css}"', html)
    js = rel_to_root(page_path, "assets/editor.js")
    html = re.sub(r'src="/assets/editor\.js"', f'src="{js}"', html)
    html = re.sub(
        r'href="/data/([^"]+)"',
        lambda m: f'href="{rel_to_root(page_path, f"data/{m.group(1)}")}"',
        html,
    )
    return html


def wrap_video_articles(html: str, slug: str | None) -> str:
    counter = [0]

    def repl(match):
        counter[0] += 1
        body = match.group(2)
        if "note-block" in body:
            return match.group(0)

        h3 = re.search(r"<h3>(.*?)</h3>", body, re.S)
        vid_title = re.sub(r"<[^>]+>", "", h3.group(1)).strip() if h3 else f"video-{counter[0]}"
        note_id = f"{slug}::{counter[0]}"

        vm = re.search(r'(<div class="video-wrap">.*?</div>)', body, re.S)
        if not vm:
            return match.group(0)

        before = body[: vm.start()]
        video = vm.group(1)
        after = body[vm.end() :].strip()

        desc_html = ""
        en_html = ""
        dm = re.match(r"(<p>(.*?)</p>)(.*)", after, re.S)
        if dm:
            desc_html = dm.group(2)
            en_html = dm.group(3)
        else:
            en_html = after

        block = (
            f'<div class="note-block" data-note-id="{note_id}">'
            f'<p class="desc-cs editable-note" data-field="desc">{desc_html}</p>'
            f"{en_html}"
            f'<button type="button" class="note-add-btn">+ Doplnit poznámku</button>'
            f"</div>"
        )
        return match.group(1) + before + video + block + match.group(3)

    return re.sub(
        r"(<article class=\"video-item\">)(.*?)(</article>)",
        repl,
        html,
        flags=re.S,
    )


def add_footer_and_scripts(html: str, slug: str | None, page_path: Path) -> str:
    js = rel_to_root(page_path, "assets/editor.js")
    footer = """
  <footer class="site-footer">
    <div>VectorPro CZ – videa načítána z vectorpro.io | Upravit popisky: zadejte heslo níže</div>
    <div class="edit-bar" id="edit-bar">
      <input type="password" id="edit-password" placeholder="Heslo pro úpravy" autocomplete="off">
      <button type="button" id="edit-login">Přihlásit</button>
      <button type="button" id="edit-logout" hidden>Odhlásit</button>
      <span class="edit-status" id="edit-status"></span>
    </div>
  </footer>"""

    html = re.sub(r"\s*<footer class=\"site-footer\">.*?</footer>", "", html, flags=re.S)
    html = re.sub(r'\s*<script src="[^"]*editor\.js"[^>]*></script>', "", html)
    html = re.sub(r"<body(?:\s+data-page-slug=\"[^\"]*\")?>", f'<body data-page-slug="{slug or ""}">', html, count=1)

    if "</body>" in html:
        html = html.replace("</div>\n</body>", f"</div>\n{footer}\n  <script src=\"{js}\" defer></script>\n</body>")
        if "editor.js" not in html:
            html = html.replace("</body>", f"  <script src=\"{js}\" defer></script>\n</body>")

    return html


def patch_file(page_path: Path) -> None:
    html = page_path.read_text(encoding="utf-8")
    slug = None
    m = re.search(r"software[/\\]([^/\\]+)[/\\]index\.html", str(page_path).replace("\\", "/"))
    if m:
        slug = m.group(1)

    html = fix_links(html, page_path)
    if slug:
        html = wrap_video_articles(html, slug)
    html = add_footer_and_scripts(html, slug, page_path)
    page_path.write_text(html, encoding="utf-8")


def main() -> None:
    css_path = OUT_DIR / "assets" / "style.css"
    css = css_path.read_text(encoding="utf-8")
    if ".site-footer" not in css:
        css_path.write_text(css + EDITOR_CSS_EXTRA, encoding="utf-8")

    if not ANNOTATIONS.exists():
        ANNOTATIONS.write_text("{}", encoding="utf-8")

    pages = sorted(OUT_DIR.rglob("index.html"))
    for p in pages:
        patch_file(p)
        print("patched", p.relative_to(OUT_DIR))
    print(f"Done: {len(pages)} pages")


if __name__ == "__main__":
    main()
