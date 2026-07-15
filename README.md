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

Lokální server podporuje režim úprav včetně ukládání do souborů.
Heslo nastavte proměnnou `VP_EDIT_PASSWORD` nebo souborem `.edit-password` (viz `.edit-password.example`).

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

Na veřejné GitHub Pages verzi funguje prohlížení, přehrávání videí a **editace**.
Po zadání hesla dole na stránce se změny ukládají do GitHubu (`annotations.json`, `video-overrides.json`).
Lokálně (`server.py`) se ukládá do souborů na disku.

Pro obnovení GitHub tokenu použitého k uložení z webu:

```bash
# Fine-grained PAT (Contents: Write) uložte do .edit-github-token
python setup_gh_edit.py
python deploy_github.py
```

