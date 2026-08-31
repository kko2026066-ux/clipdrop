from __future__ import annotations

import threading
import uuid
import os
from pathlib import Path
from shutil import which
from typing import Any

from flask import Flask, Response, jsonify, render_template, request, send_from_directory

try:
    from yt_dlp import YoutubeDL
except ImportError:  # pragma: no cover - gives a useful message when setup is incomplete
    YoutubeDL = None


BASE_DIR = Path(__file__).resolve().parent
DOWNLOAD_DIR = BASE_DIR / "downloads"
LOCAL_FFMPEG_DIR = BASE_DIR / "tools" / "ffmpeg" / "ffmpeg-9.0.1-essentials_build" / "bin"
DOWNLOAD_DIR.mkdir(exist_ok=True)

app = Flask(__name__)
JOBS: dict[str, dict[str, Any]] = {}
JOBS_LOCK = threading.Lock()


def update_job(job_id: str, **changes: Any) -> None:
    with JOBS_LOCK:
        JOBS[job_id].update(changes)


def download_media(job_id: str, url: str, audio_only: bool) -> None:
    if YoutubeDL is None:
        update_job(job_id, status="error", message="yt-dlp가 설치되지 않았습니다. requirements.txt를 설치해주세요.")
        return

    def progress_hook(data: dict[str, Any]) -> None:
        status = data.get("status")
        if status == "downloading":
            downloaded = data.get("downloaded_bytes", 0)
            total = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
            percent = round(downloaded / total * 100, 1) if total else 0
            update_job(
                job_id,
                status="downloading",
                progress=percent,
                message="파일을 다운로드하고 있습니다…",
            )
        elif status == "finished":
            update_job(job_id, status="processing", progress=100, message="파일을 변환하고 있습니다…")

    options: dict[str, Any] = {
        "outtmpl": str(DOWNLOAD_DIR / "%(title)s.%(ext)s"),
        "noplaylist": True,
        "progress_hooks": [progress_hook],
        "quiet": True,
        "no_warnings": True,
    }
    ffmpeg_executable = which("ffmpeg")
    if LOCAL_FFMPEG_DIR.exists():
        options["ffmpeg_location"] = str(LOCAL_FFMPEG_DIR)
    elif ffmpeg_executable:
        options["ffmpeg_location"] = str(Path(ffmpeg_executable).parent)
    # Newer YouTube responses may need a JavaScript runtime. Use Node when it
    # exists, while keeping the app usable on machines that only have FFmpeg.
    if which("node"):
        options["js_runtimes"] = {"node": {}}

    if audio_only:
        options["format"] = "bestaudio/best"
        options["postprocessors"] = [
            {"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}
        ]
    else:
        options["format"] = "bv*+ba/b"
        options["merge_output_format"] = "mp4"

    try:
        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)
            prepared = ydl.prepare_filename(info)
            output_path = Path(prepared)
            if audio_only:
                output_path = output_path.with_suffix(".mp3")
            elif output_path.suffix.lower() != ".mp4":
                output_path = output_path.with_suffix(".mp4")

        if not output_path.exists():
            # yt-dlp may return a post-processed filename that differs slightly.
            candidates = sorted(DOWNLOAD_DIR.glob(f"{Path(prepared).stem}.*"), key=lambda p: p.stat().st_mtime, reverse=True)
            output_path = candidates[0] if candidates else output_path

        update_job(
            job_id,
            status="complete",
            progress=100,
            message="다운로드가 완료되었습니다.",
            filename=output_path.name,
            title=info.get("title", output_path.stem),
        )
    except Exception as error:  # yt-dlp raises different errors for different providers
        update_job(job_id, status="error", message=f"다운로드에 실패했습니다: {error}")


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/robots.txt")
def robots():
    return Response("User-agent: *\nAllow: /\n", mimetype="text/plain")


@app.post("/api/download")
def create_download():
    payload = request.get_json(silent=True) or {}
    url = str(payload.get("url", "")).strip()
    audio_only = bool(payload.get("audio_only", False))

    if not url:
        return jsonify({"error": "YouTube URL을 입력해주세요."}), 400
    if not url.startswith(("https://", "http://")):
        return jsonify({"error": "올바른 URL을 입력해주세요."}), 400

    job_id = uuid.uuid4().hex
    with JOBS_LOCK:
        JOBS[job_id] = {"status": "queued", "progress": 0, "message": "다운로드를 준비하고 있습니다…"}
    thread = threading.Thread(target=download_media, args=(job_id, url, audio_only), daemon=True)
    thread.start()
    return jsonify({"job_id": job_id})


@app.get("/api/download/<job_id>")
def download_status(job_id: str):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
    if job is None:
        return jsonify({"error": "작업을 찾을 수 없습니다."}), 404
    response = dict(job)
    if response.get("filename"):
        response["download_url"] = f"/downloads/{response['filename']}"
    return jsonify(response)


@app.get("/downloads/<path:filename>")
def serve_download(filename: str):
    return send_from_directory(DOWNLOAD_DIR, filename, as_attachment=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
