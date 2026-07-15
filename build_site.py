#!/usr/bin/env python3
"""Build Czech mirror of VectorPro documentation site."""

from __future__ import annotations

import html
import json
import re
import time
import urllib.error
import urllib.request
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path

from deep_translator import GoogleTranslator

ROOT = Path(__file__).resolve().parent
LINKS_FILE = ROOT / "links.json"
OUT_DIR = ROOT / "vectorpro-cz"
DATA_DIR = OUT_DIR / "data"
CACHE_DIR = OUT_DIR / ".cache"
SCRAPE_CACHE = CACHE_DIR / "scrape.json"
TRANS_CACHE = CACHE_DIR / "translations.json"

BASE_ORIGIN = "https://vectorpro.io"

CATEGORY_CS = {
    "Requirements": "Požadavky",
    "Install/Upgrade": "Instalace/Aktualizace",
    "Login Screen": "Přihlašovací obrazovka",
    "Connect": "Připojení",
    "Stand Configuration": "Konfigurace stojanu",
    "Workspace": "Pracovní prostor",
    "Permissions": "Oprávnění",
    "Language": "Jazyk",
    "Event Log": "Protokol událostí",
    "System Deflection Compensation (SDC)": "Kompenzace systémové deflekce (SDC)",
    "Attributes": "Atributy",
    "All Tests": "Všechny testy",
    "Results": "Výsledky",
    "Batch Sets": "Dávkové sady",
    "Trash": "Koš",
    "New Test": "Nový test",
    "Attributes Tab": "Záložka Atributy",
    "Specimen Tab": "Záložka Vzorek",
    "Operations Tab": "Záložka Operace",
    "Operations": "Operace",
    "Results/Export": "Výsledky/Export",
    "Sample Results": "Výsledky vzorku",
    "Attribute Results": "Výsledky atributů",
    "Common Calculation Editing": "Úprava běžných výpočtů",
    "Calculations": "Výpočty",
    "Report Templates": "Šablony reportů",
    "Batch Report Templates": "Šablony dávkových reportů",
    "Test Permissions": "Oprávnění testu",
    "Vector Cloud": "Vector Cloud",
    "Tests": "Testy",
    "Graphs": "Grafy",
    "Graph Results": "Výsledky grafu",
    "Create a Batch Set": "Vytvoření dávkové sady",
    "Batch Set Workspace": "Pracovní prostor dávkové sady",
    "Batch Testing": "Dávkové testování",
}


def slug_from_url(url: str) -> str:
    return url.rstrip("/").split("/software/")[-1]


def load_json(path: Path, default):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


class Translator:
    def __init__(self) -> None:
        self.cache: dict[str, str] = load_json(TRANS_CACHE, {})
        self.api = GoogleTranslator(source="en", target="cs")

    def translate(self, text: str) -> str:
        text = (text or "").strip()
        if not text:
            return ""
        if text in self.cache:
            return self.cache[text]
        # Keep short all-caps tokens stable
        if re.fullmatch(r"[A-Z0-9 /\-]+", text) and len(text) <= 20:
            self.cache[text] = text
            return text
        try:
            chunks = []
            chunk_size = 4500
            for i in range(0, len(text), chunk_size):
                part = text[i : i + chunk_size]
                chunks.append(self.api.translate(part))
                time.sleep(0.15)
            result = "".join(chunks)
        except Exception:
            result = text
        self.cache[text] = result
        if len(self.cache) % 25 == 0:
            save_json(TRANS_CACHE, self.cache)
        return result


def fetch_html(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 VectorProCZ/1.0"})
    with urllib.request.urlopen(req, timeout=45) as resp:
        return resp.read().decode("utf-8", "replace")


def parse_page(html_text: str) -> dict:
    title_m = re.search(r'field--name-name.*?field--item">([^<]+)', html_text, re.S)
    title = title_m.group(1).strip() if title_m else ""

    videos = []
    for block in re.findall(r'<div class="row media tutorial">(.*?)</div>\s*</li>', html_text, re.S):
        label_m = re.search(r'field--name-field-label.*?field--item">([^<]+)', block, re.S)
        iframe_m = re.search(r'<iframe[^>]+src="([^"]+)"[^>]*title="([^"]*)"', block, re.S)
        desc_m = re.search(r'field--name-field-description.*?field--item">(.*?)</div>', block, re.S)
        desc = ""
        if desc_m:
            desc = re.sub(r"<[^>]+>", " ", desc_m.group(1))
            desc = re.sub(r"\s+", " ", desc).strip()
        src = iframe_m.group(1) if iframe_m else ""
        src = src.replace("&amp;", "&")
        if src.startswith("/"):
            src = BASE_ORIGIN + src
        videos.append(
            {
                "label": label_m.group(1).strip() if label_m else "",
                "iframe_src": src,
                "iframe_title": iframe_m.group(2).strip() if iframe_m else "",
                "description": desc,
            }
        )

    body_parts = []
    for p in re.findall(r'field--name-body.*?field--item">(.*?)</div>', html_text, re.S):
        if "contactus" in p or "followus" in p:
            continue
        clean = re.sub(r"<[^>]+>", " ", p)
        clean = re.sub(r"\s+", " ", clean).strip()
        if clean and len(clean) > 20:
            body_parts.append(clean)

    return {"title": title, "videos": videos, "body": body_parts}


def bilingual_block(cs: str, en: str, tag: str = "span") -> str:
    cs = html.escape(cs)
    en = html.escape(en)
    if not en or cs == en:
        return cs
    return f'{cs} <{tag} class="en-inline">({en})</{tag}>'


def bilingual_para(cs: str, en: str) -> str:
    cs = html.escape(cs)
    if not en or cs == html.escape(en):
        return f"<p>{cs}</p>"
    en = html.escape(en)
    return f'<p>{cs}</p><p class="en-sub">{en}</p>'


def build_index(links: list[dict]) -> tuple[list[dict], OrderedDict]:
    enriched = []
    categories: OrderedDict[str, list] = OrderedDict()
    for item in links:
        slug = slug_from_url(item["url"])
        cat_en = item["category"]
        cat_cs = CATEGORY_CS.get(cat_en, cat_en)
        entry = {
            "category_en": cat_en,
            "category_cs": cat_cs,
            "title_en": item["title"],
            "slug": slug,
            "url_original": item["url"],
            "url_local": f"/software/{slug}/",
        }
        enriched.append(entry)
        categories.setdefault(cat_en, []).append(entry)
    return enriched, categories


def render_sidebar(categories: OrderedDict, active_slug: str | None, tr: Translator, title_map: dict) -> str:
    parts = ['<nav class="sidebar"><h2>VectorPro – Index</h2>']
    for cat_en, items in categories.items():
        cat_cs = CATEGORY_CS.get(cat_en, cat_en)
        parts.append(f'<section class="cat"><h3>{bilingual_block(cat_cs, cat_en)}</h3><ol>')
        for item in items:
            slug = item["slug"]
            title_en = item["title_en"]
            title_cs = title_map.get(slug, tr.translate(title_en))
            label = bilingual_block(title_cs, title_en, "span")
            cls = ' class="active"' if slug == active_slug else ""
            parts.append(f'<li{cls}><a href="/software/{slug}/">{label}</a></li>')
        parts.append("</ol></section>")
    parts.append("</nav>")
    return "\n".join(parts)


def render_page(
    entry: dict,
    page_data: dict,
    categories: OrderedDict,
    tr: Translator,
    title_map: dict,
    desc_map: dict,
) -> str:
    slug = entry["slug"]
    title_en = page_data.get("title") or entry["title_en"]
    title_cs = title_map.get(slug, tr.translate(title_en))

    video_html = []
    for i, video in enumerate(page_data.get("videos") or [], 1):
        label_en = video.get("label") or title_en
        label_cs = tr.translate(label_en) if label_en else title_cs
        desc_en = video.get("description") or ""
        desc_cs = desc_map.get(f"{slug}::{i}", tr.translate(desc_en) if desc_en else "")
        if desc_en:
            desc_map[f"{slug}::{i}"] = desc_cs

        iframe = ""
        if video.get("iframe_src"):
            iframe = (
                f'<div class="video-wrap">'
                f'<iframe src="{html.escape(video["iframe_src"])}" '
                f'width="630" height="354" frameborder="0" allowfullscreen '
                f'title="{html.escape(label_en)}"></iframe></div>'
            )
        video_html.append(
            f'<article class="video-item">'
            f'<h3>{bilingual_block(label_cs, label_en)}</h3>'
            f"{iframe}"
            f"{bilingual_para(desc_cs, desc_en) if desc_en else ''}"
            f"</article>"
        )

    body_html = []
    for j, para_en in enumerate(page_data.get("body") or [], 1):
        para_cs = desc_map.get(f"{slug}::body::{j}", tr.translate(para_en))
        desc_map[f"{slug}::body::{j}"] = para_cs
        body_html.append(bilingual_para(para_cs, para_en))

    if not video_html and not body_html:
        body_html.append(
            '<p class="no-video">Na této stránce není video tutoriál. '
            '<span class="en-sub">(No video tutorial on this page.)</span></p>'
        )

    sidebar = render_sidebar(categories, slug, tr, title_map)
    content = "\n".join(video_html + body_html)

    return f"""<!DOCTYPE html>
<html lang="cs">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title_cs)} ({html.escape(title_en)}) – VectorPro CZ</title>
  <link rel="stylesheet" href="/assets/style.css">
</head>
<body>
  <header class="site-header">
    <a href="/" class="logo">VectorPro – Průvodce (CZ)</a>
    <a class="orig-link" href="{html.escape(entry['url_original'])}" target="_blank" rel="noopener">Původní stránka</a>
  </header>
  <div class="layout">
    {sidebar}
    <main class="content">
      <h1>{bilingual_block(title_cs, title_en, "span")}</h1>
      {content}
    </main>
  </div>
</body>
</html>"""


def render_home(categories: OrderedDict, tr: Translator, title_map: dict) -> str:
    sidebar = render_sidebar(categories, None, tr, title_map)
    intro = (
        "<p>Česká verze dokumentace VectorPro se videi načítanými z původního webu.</p>"
        '<p class="en-sub">Czech version of VectorPro documentation with videos loaded from the original site.</p>'
        f'<p><a href="/data/vectorpro-index.json">Stáhnout JSON index</a></p>'
    )
    return f"""<!DOCTYPE html>
<html lang="cs">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>VectorPro – Index (CZ)</title>
  <link rel="stylesheet" href="/assets/style.css">
</head>
<body>
  <header class="site-header">
    <a href="/" class="logo">VectorPro – Průvodce (CZ)</a>
  </header>
  <div class="layout">
    {sidebar}
    <main class="content">
      <h1>VectorPro – Index <span class="en-inline">(VectorPro – Index)</span></h1>
      {intro}
    </main>
  </div>
</body>
</html>"""


CSS = """
:root {
  --bg: #f4f6f8;
  --card: #fff;
  --text: #1a1a1a;
  --muted: #5a6570;
  --accent: #0066a1;
  --border: #d8dee6;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: "Segoe UI", Tahoma, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.5;
}
.site-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1.25rem;
  background: #003d62;
  color: #fff;
}
.site-header a { color: #fff; text-decoration: none; }
.logo { font-weight: 700; font-size: 1.1rem; }
.orig-link { font-size: 0.9rem; opacity: 0.9; }
.layout {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 1rem;
  max-width: 1400px;
  margin: 0 auto;
  padding: 1rem;
}
.sidebar {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 1rem;
  max-height: calc(100vh - 5rem);
  overflow: auto;
  position: sticky;
  top: 1rem;
}
.sidebar h2 { margin: 0 0 1rem; font-size: 1.1rem; }
.cat { margin-bottom: 1rem; }
.cat h3 {
  margin: 0 0 0.35rem;
  font-size: 0.95rem;
  color: var(--accent);
}
.sidebar ol { margin: 0; padding-left: 1.2rem; }
.sidebar li { margin: 0.2rem 0; font-size: 0.82rem; }
.sidebar li.active a { font-weight: 700; color: var(--accent); }
.sidebar a { color: var(--text); text-decoration: none; }
.sidebar a:hover { text-decoration: underline; }
.content {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 1.25rem 1.5rem;
}
.content h1 { margin-top: 0; font-size: 1.6rem; }
.video-item {
  border-top: 1px solid var(--border);
  padding-top: 1rem;
  margin-top: 1rem;
}
.video-item:first-of-type { border-top: 0; padding-top: 0; margin-top: 0; }
.video-wrap {
  margin: 0.75rem 0;
  max-width: 100%;
}
.video-wrap iframe {
  width: 100%;
  max-width: 630px;
  aspect-ratio: 630 / 354;
  height: auto;
  border: 0;
  border-radius: 6px;
  background: #000;
}
.en-inline, .en-sub {
  color: var(--muted);
  font-size: 0.85em;
  font-weight: 400;
}
.en-sub { display: block; margin-top: 0.25rem; }
.no-video { color: var(--muted); }
@media (max-width: 900px) {
  .layout { grid-template-columns: 1fr; }
  .sidebar { position: static; max-height: none; }
}
"""


def scrape_all(enriched: list[dict]) -> dict:
    cache = load_json(SCRAPE_CACHE, {})
    for i, entry in enumerate(enriched, 1):
        slug = entry["slug"]
        if slug in cache:
            continue
        url = entry["url_original"]
        print(f"[scrape {i}/{len(enriched)}] {slug}")
        try:
            html_text = fetch_html(url)
            cache[slug] = parse_page(html_text)
        except Exception as exc:
            print(f"  ERROR: {exc}")
            cache[slug] = {"title": entry["title_en"], "videos": [], "body": [], "error": str(exc)}
        time.sleep(0.2)
        if i % 10 == 0:
            save_json(SCRAPE_CACHE, cache)
    save_json(SCRAPE_CACHE, cache)
    return cache


def main() -> None:
    links = json.loads(LINKS_FILE.read_text(encoding="utf-8"))
    enriched, categories = build_index(links)

    index_export = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": BASE_ORIGIN,
        "total_pages": len(enriched),
        "total_categories": len(categories),
        "pages": enriched,
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    save_json(DATA_DIR / "vectorpro-index.json", index_export)
    save_json(ROOT / "vectorpro-index.json", index_export)

    scrape = scrape_all(enriched)
    tr = Translator()
    title_map: dict[str, str] = {}
    desc_map: dict[str, str] = {}

    # Pre-translate titles
    print("[translate] titles...")
    for entry in enriched:
        slug = entry["slug"]
        title_en = scrape.get(slug, {}).get("title") or entry["title_en"]
        title_map[slug] = tr.translate(title_en)
        entry["title_cs"] = title_map[slug]

    save_json(TRANS_CACHE, tr.cache)

    # Generate pages
    (OUT_DIR / "assets").mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "assets" / "style.css").write_text(CSS, encoding="utf-8")
    (OUT_DIR / "index.html").write_text(render_home(categories, tr, title_map), encoding="utf-8")

    for i, entry in enumerate(enriched, 1):
        slug = entry["slug"]
        page_data = scrape.get(slug, {"title": entry["title_en"], "videos": [], "body": []})
        out_path = OUT_DIR / "software" / slug / "index.html"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            render_page(entry, page_data, categories, tr, title_map, desc_map),
            encoding="utf-8",
        )
        if i % 20 == 0:
            print(f"[build {i}/{len(enriched)}] pages done")
            save_json(TRANS_CACHE, tr.cache)

    save_json(TRANS_CACHE, tr.cache)
    save_json(DATA_DIR / "vectorpro-index.json", index_export)
    print(f"Done: {len(enriched)} pages -> {OUT_DIR}")


if __name__ == "__main__":
    main()
