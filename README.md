# VectorPro CZ – český průvodce

Česká verze dokumentace VectorPro s videi z původního webu.

## Online verze (zdarma)

Po push na GitHub se automaticky publikuje na:

**https://tukan1988.github.io/vectorpro-cz/**

## Lokální spuštění

```bat
start_vectorpro.bat
```

Nebo:

```bash
python server.py
```

Otevřete http://127.0.0.1:8765/

Lokální server podporuje režim úprav (heslo `titanic`) včetně ukládání do souborů.

## Aktualizace webu na internetu

1. Upravte soubory v `vectorpro-cz/` (nebo spusťte generátory)
2. Commit + push zdrojového kódu na `main`:

```bash
git add .
git commit -m "Aktualizace obsahu"
git push
```

3. Nasazení na web:

```bash
python deploy_github.py
```

Skript sestaví statickou verzi a nahraje ji na větev `gh-pages` (~1 minuta).

Repozitář: https://github.com/tukan1988/vectorpro-cz

## Build pro GitHub Pages (lokálně)

```bash
python build_pages.py --out _site --base /vectorpro-cz
```

## Testy videí

```bash
python server.py
python test_video.py
```

## Struktura

| Složka / soubor | Popis |
|-----------------|-------|
| `vectorpro-cz/` | Statický web (HTML, CSS, JS, data) |
| `server.py` | Lokální Flask server + API pro úpravy |
| `build_pages.py` | Build pro GitHub Pages (play stránky + base path) |
| `vectorpro-cz/data/video-embeds.json` | URL videí (SproutVideo) |

## Poznámka k úpravám online

Na veřejné GitHub Pages verzi funguje prohlížení a přehrávání videí.
Úpravy textů/videí se ukládají do localStorage prohlížeče (ne na server).
Pro trvalé úpravy použijte lokální server a pak push na GitHub.
