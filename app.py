from __future__ import annotations

import atexit
import ipaddress
import mimetypes
import secrets
import shutil
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

import yt_dlp
from flask import Flask, jsonify, request, send_file, send_from_directory
from yt_dlp.utils import DownloadError


APP_DIR = Path(__file__).resolve().parent
ALLOWED_DOMAINS = (
    "youtube.com",
    "youtu.be",
    "instagram.com",
    "tiktok.com",
    "twitter.com",
    "x.com",
)
QUALITY_HEIGHTS = {
    "480p": 480,
    "720p": 720,
    "1080p": 1080,
    "2160p": 2160,
}
VALID_FORMATS = {"mp4", "mkv", "mp3"}
MP3_BITRATE_KBPS = 192
TICKET_LIFETIME_SECONDS = 60 * 60

app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024


@dataclass
class DownloadTicket:
    folder: Path
    file_path: Path
    expires_at: float


_tickets: dict[str, DownloadTicket] = {}
_tickets_lock = threading.Lock()


def validate_media_url(raw_url: object) -> str:
    if not isinstance(raw_url, str) or not raw_url.strip():
        raise ValueError("Paste a media link first.")
    raw_url = raw_url.strip()
    if len(raw_url) > 4096:
        raise ValueError("That link is too long.")

    parsed = urlsplit(raw_url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Use a link that starts with https:// or http://.")
    if parsed.username or parsed.password:
        raise ValueError("Links containing a username or password aren’t supported.")
    if not parsed.hostname:
        raise ValueError("That doesn’t look like a valid media link.")
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("That doesn’t look like a valid media link.") from exc
    if port not in {None, 80, 443}:
        raise ValueError("Links with a custom port aren’t supported.")

    host = parsed.hostname.rstrip(".").lower()
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise ValueError("Paste a link from a supported media platform.")

    if not any(host == domain or host.endswith("." + domain) for domain in ALLOWED_DOMAINS):
        raise ValueError("Supported links are from YouTube, Instagram, TikTok, X, or Twitter.")
    return raw_url


def read_options(payload: dict) -> tuple[str, str, str]:
    url = validate_media_url(payload.get("url"))
    media_format = str(payload.get("format", "mp4")).lower()
    quality = str(payload.get("quality", "480p")).lower()
    if media_format not in VALID_FORMATS:
        raise ValueError("Choose MP4, MKV, or MP3.")
    if quality not in QUALITY_HEIGHTS:
        raise ValueError("Choose a supported video quality.")
    return url, media_format, quality


def yt_dlp_options(media_format: str, quality: str) -> dict:
    base = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "socket_timeout": 25,
        "retries": 2,
        "fragment_retries": 2,
        "extractor_retries": 2,
        "restrictfilenames": True,
    }
    height = QUALITY_HEIGHTS[quality]

    if media_format == "mp3":
        base.update({
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": str(MP3_BITRATE_KBPS),
            }],
        })
    elif media_format == "mp4":
        base.update({
            "format": (
                "bestvideo[height<=" + str(height) + "][ext=mp4]+bestaudio[ext=m4a]"
                "/best[height<=" + str(height) + "][ext=mp4]"
            ),
            "merge_output_format": "mp4",
            "postprocessors": [{
                "key": "FFmpegVideoRemuxer",
                "preferedformat": "mp4",
            }],
        })
    else:
        base.update({
            "format": (
                "bestvideo[height<=" + str(height) + "]+bestaudio"
                "/best[height<=" + str(height) + "]"
            ),
            "merge_output_format": "mkv",
            "postprocessors": [{
                "key": "FFmpegVideoRemuxer",
                "preferedformat": "mkv",
            }],
        })
    return base


def _part_size(part: dict, fallback_duration: float | None) -> tuple[int | None, bool]:
    exact = part.get("filesize")
    if isinstance(exact, (int, float)) and exact >= 0:
        return int(exact), False
    approximate = part.get("filesize_approx")
    if isinstance(approximate, (int, float)) and approximate >= 0:
        return int(approximate), True
    bitrate = part.get("tbr")
    duration = part.get("duration") or fallback_duration
    if isinstance(bitrate, (int, float)) and isinstance(duration, (int, float)):
        return int(float(duration) * float(bitrate) * 1000 / 8), True
    return None, True


def estimate_size(info: dict, media_format: str) -> tuple[int | None, bool]:
    duration = info.get("duration")
    if media_format == "mp3":
        if isinstance(duration, (int, float)) and duration >= 0:
            return int(float(duration) * MP3_BITRATE_KBPS * 1000 / 8), True
        return None, True

    requested = info.get("requested_formats")
    parts = requested if isinstance(requested, list) and requested else [info]
    sizes: list[int] = []
    approximate = True
    for part in parts:
        size, is_approximate = _part_size(part, duration if isinstance(duration, (int, float)) else None)
        if size is None:
            return None, True
        sizes.append(size)
        approximate = approximate or is_approximate
    if not sizes:
        return None, True
    return sum(sizes), approximate


def _extract_info(url: str, media_format: str, quality: str) -> dict:
    with yt_dlp.YoutubeDL(yt_dlp_options(media_format, quality)) as ydl:
        info = ydl.extract_info(url, download=False)
    if not isinstance(info, dict) or info.get("_type") == "playlist":
        raise ValueError("Use a link to one video or media item, not a playlist.")
    return info


def _friendly_error(exc: Exception) -> str:
    message = str(exc).lower()
    if "ffmpeg" in message or "ffprobe" in message:
        return "FFmpeg and ffprobe are needed for MP3 conversion and video merging. Install FFmpeg, then restart OmniFetch."
    if "requested format" in message or "no video formats" in message or "no suitable formats" in message:
        return "That format or quality isn’t available for this media. Try a lower quality or another format."
    if "unsupported url" in message or "no suitable extractor" in message:
        return "This link type isn’t supported. Try a public YouTube, Instagram, TikTok, X, or Twitter link."
    return "Couldn’t read or prepare this media. It may be private, unavailable, or blocked by its source."


def _cleanup_ticket(token: str, ticket: DownloadTicket | None = None) -> None:
    with _tickets_lock:
        current = _tickets.get(token)
        if current is None or (ticket is not None and current is not ticket):
            return
        _tickets.pop(token, None)
    shutil.rmtree(current.folder, ignore_errors=True)


def _cleanup_expired_tickets() -> None:
    now = time.time()
    with _tickets_lock:
        expired = [(token, ticket) for token, ticket in _tickets.items() if ticket.expires_at <= now]
    for token, ticket in expired:
        _cleanup_ticket(token, ticket)


def _ticket_cleanup_loop() -> None:
    while True:
        time.sleep(5 * 60)
        _cleanup_expired_tickets()


def _cleanup_all_tickets() -> None:
    with _tickets_lock:
        outstanding = list(_tickets.items())
    for token, ticket in outstanding:
        _cleanup_ticket(token, ticket)


threading.Thread(target=_ticket_cleanup_loop, name="omnifetch-temp-cleanup", daemon=True).start()
atexit.register(_cleanup_all_tickets)


@app.get("/")
def index():
    return send_from_directory(APP_DIR, "index.html")


@app.post("/api/info")
def media_info():
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        payload = {}
    try:
        url, media_format, quality = read_options(payload)
        info = _extract_info(url, media_format, quality)
        size_bytes, _ = estimate_size(info, media_format)
        requested = info.get("requested_formats") or [info]
        heights = [
            part.get("height")
            for part in requested
            if isinstance(part.get("height"), (int, float))
        ]
        duration = info.get("duration")
        return jsonify({
            "title": str(info.get("title") or "Media item")[:300],
            "thumbnail": info.get("thumbnail") if isinstance(info.get("thumbnail"), str) else None,
            "duration_seconds": duration if isinstance(duration, (int, float)) else None,
            "selected_height": max(heights) if heights else None,
            "estimated_size_bytes": size_bytes,
        })
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": _friendly_error(exc)}), 422


@app.post("/api/prepare")
def prepare_download():
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        payload = {}
    folder: Path | None = None
    try:
        url, media_format, quality = read_options(payload)
        _cleanup_expired_tickets()
        folder = Path(tempfile.mkdtemp(prefix="omnifetch-"))
        options = yt_dlp_options(media_format, quality)
        options["outtmpl"] = str(folder / "%(title).120B [%(id)s].%(ext)s")
        with yt_dlp.YoutubeDL(options) as ydl:
            ydl.download([url])

        output_files = [
            path for path in folder.rglob("*")
            if path.is_file() and path.suffix.lower() not in {".part", ".ytdl", ".tmp"}
        ]
        if not output_files:
            raise RuntimeError("No media file was produced.")
        file_path = max(output_files, key=lambda path: path.stat().st_size)
        token = secrets.token_urlsafe(32)
        ticket = DownloadTicket(
            folder=folder,
            file_path=file_path,
            expires_at=time.time() + TICKET_LIFETIME_SECONDS,
        )
        with _tickets_lock:
            _tickets[token] = ticket
        return jsonify({
            "token": token,
            "filename": file_path.name,
            "size_bytes": file_path.stat().st_size,
        })
    except ValueError as exc:
        if folder:
            shutil.rmtree(folder, ignore_errors=True)
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        if folder:
            shutil.rmtree(folder, ignore_errors=True)
        return jsonify({"error": _friendly_error(exc)}), 422


@app.get("/api/file/<token>")
def download_file(token: str):
    _cleanup_expired_tickets()
    with _tickets_lock:
        ticket = _tickets.get(token)
    if ticket is None or not ticket.file_path.is_file():
        return jsonify({"error": "This prepared file expired. Prepare it again."}), 404

    mimetype = mimetypes.guess_type(ticket.file_path.name)[0] or "application/octet-stream"
    response = send_file(
        ticket.file_path,
        mimetype=mimetype,
        as_attachment=True,
        download_name=ticket.file_path.name,
        conditional=True,
        max_age=0,
    )
    response.call_on_close(lambda: _cleanup_ticket(token, ticket))
    return response


@app.after_request
def add_local_app_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Cache-Control", "no-store")
    return response


if __name__ == "__main__":
    print("OmniFetch is available at http://127.0.0.1:8765")
    print("This server is bound to this computer only.")
    app.run(host="127.0.0.1", port=8765, debug=False, threaded=True)
