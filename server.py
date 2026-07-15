#!/usr/bin/env python3
"""Serve VectorPro CZ site with editable annotations and video overrides."""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory, session
from werkzeug.utils import secure_filename

ROOT = Path(__file__).resolve().parent
SITE = ROOT / "vectorpro-cz"
ANNOTATIONS = SITE / "data" / "annotations.json"
VIDEOS = SITE / "data" / "video-overrides.json"
EMBEDS = SITE / "data" / "video-embeds.json"
UPLOADS = SITE / "uploads"
PASSWORD = "titanic"
PORT = 8765

app = Flask(__name__, static_folder=None)
app.secret_key = "vectorpro-cz-local-edit-key"


def load_json(path: Path, default):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


@app.route("/api/auth", methods=["POST"])
def api_auth():
    body = request.get_json(silent=True) or {}
    if body.get("password") == PASSWORD:
        session["edit_auth"] = True
        return jsonify({"ok": True})
    return jsonify({"ok": False, "error": "invalid password"}), 401


@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.pop("edit_auth", None)
    return jsonify({"ok": True})


@app.route("/api/annotations", methods=["GET"])
def api_get_annotations():
    return jsonify(load_json(ANNOTATIONS, {}))


@app.route("/api/annotations", methods=["POST"])
def api_save_annotation():
    body = request.get_json(silent=True) or {}
    note_id = body.get("id")
    text = body.get("text", "")
    if not note_id:
        return jsonify({"error": "missing id"}), 400
    data = load_json(ANNOTATIONS, {})
    if text:
        data[note_id] = text
    else:
        data.pop(note_id, None)
    save_json(ANNOTATIONS, data)
    return jsonify({"ok": True})


@app.route("/api/videos", methods=["GET"])
def api_get_videos():
    return jsonify(load_json(VIDEOS, {}))


@app.route("/api/videos", methods=["POST"])
def api_save_video():
    body = request.get_json(silent=True) or {}
    key = body.get("key")
    if not key:
        return jsonify({"error": "missing key"}), 400
    data = load_json(VIDEOS, {})
    entry = {k: v for k, v in body.items() if k != "key"}
    if entry:
        data[key] = entry
    else:
        data.pop(key, None)
    save_json(VIDEOS, data)
    return jsonify({"ok": True})


@app.route("/api/upload-video", methods=["POST"])
def api_upload_video():
    if "file" not in request.files:
        return jsonify({"error": "no file"}), 400
    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "empty filename"}), 400
    UPLOADS.mkdir(parents=True, exist_ok=True)
    ext = Path(f.filename).suffix.lower() or ".mp4"
    if ext not in {".mp4", ".webm", ".ogg", ".mov"}:
        return jsonify({"error": "unsupported format"}), 400
    name = secure_filename(request.form.get("key", "video")) + "-" + uuid.uuid4().hex[:8] + ext
    dest = UPLOADS / name
    f.save(dest)
    return jsonify({"ok": True, "url": f"/uploads/{name}"})


def play_url(slug: str, idx: int) -> str:
    return f"/play/{slug}/{idx}"


@app.route("/play/<slug>/<int:idx>")
def play_video(slug: str, idx: int):
    embeds = load_json(EMBEDS, {})
    overrides = load_json(VIDEOS, {})
    key = f"{slug}::{idx}"
    override = overrides.get(key, {})
    if override.get("mode") == "deleted":
        return "Video bylo skryto.", 404
    if override.get("mode") == "upload" and override.get("url"):
        upload_url = override["url"]
        return f"""<!DOCTYPE html>
<html lang="cs"><head><meta charset="utf-8"><title>Video – {slug}</title>
<style>body{{margin:0;background:#111;color:#fff;font-family:sans-serif;text-align:center;padding:1rem;}}
video{{max-width:100%;width:min(960px,100vw);margin:1rem auto;display:block;}}
a{{color:#7ec8ff;}}</style></head><body>
<h1>Přehrávač videa</h1>
<video src="{upload_url}" controls autoplay playsinline></video>
<p><a href="/software/{slug}/">← Zpět na stránku</a></p>
</body></html>"""
    if override.get("mode") == "link" and override.get("url"):
        from flask import redirect
        return redirect(override["url"])

    info = embeds.get(key, {})
    embed = override.get("url") if override.get("mode") == "embed" else info.get("embed", "")
    vids = info.get("vids", "")
    title = slug.replace("-", " ").title()
    if not embed:
        return f"Video nenalezeno ({key})", 404
    sep = "&" if "?" in embed else "?"
    embed_autoplay = f"{embed}{sep}autoPlay=true"
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
  <a href="/software/{slug}/">← Zpět</a>
  <span>{title}</span>
</header>
<main>
  <div class="player">
    <iframe src="{embed_autoplay}" allow="autoplay; fullscreen; encrypted-media; picture-in-picture" allowfullscreen></iframe>
  </div>
  {"<p><a href='" + vids + "' target='_blank' rel='noopener'>Otevřít na původním webu</a></p>" if vids else ""}
</main>
</body></html>"""


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve(path: str):
    if not path:
        return send_from_directory(SITE, "index.html")

    target = SITE / path
    if target.is_dir():
        index = target / "index.html"
        if index.exists():
            return send_from_directory(target, "index.html")

    if target.is_file():
        return send_from_directory(SITE, path)

    index = target / "index.html"
    if index.exists():
        return send_from_directory(target, "index.html")

    return "Not Found", 404


if __name__ == "__main__":
    UPLOADS.mkdir(parents=True, exist_ok=True)
    print(f"VectorPro CZ: http://127.0.0.1:{PORT}/")
    print(f"Edit password: {PASSWORD}")
    app.run(host="127.0.0.1", port=PORT, debug=False)
