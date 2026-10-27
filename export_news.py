"""Read two allowlisted Discord channels and generate a public, credential-free feed.

Python 3.11+; standard library only. Bot token: DISCORD_BOT_TOKEN environment variable.
Nothing is sent to Discord except authenticated GET requests. No Gateway login is needed.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import sys
import time
from datetime import datetime, timezone
from urllib import request, error, parse

GUILD_ID = "990645542260445254"
CHANNELS = {"news": "997782407673544754", "changelog": "997783396468142091"}
MAX_BYTES = 2 * 1024 * 1024


class ExportError(Exception):
    pass


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Never forward the Authorization header to a redirected host.


def validate_config(config):
    if config.get("guildId") != GUILD_ID or config.get("channels") != CHANNELS:
        raise ExportError("Die Konfiguration muss genau die beiden freigegebenen OldschoolLife-Kanäle enthalten.")
    count = config.get("postsPerChannel", 20)
    if type(count) is not int or not 1 <= count <= 40:
        raise ExportError("postsPerChannel muss zwischen 1 und 40 liegen.")
    return count


def read_channel(token, channel, count, opener=None, sleep=time.sleep):
    opener = opener or request.build_opener(NoRedirect())
    url = f"https://discord.com/api/v10/channels/{channel}/messages?limit={count}"
    req = request.Request(url, headers={"Authorization": "Bot " + token,
        "User-Agent": "OldschoolLifeNews/1.0", "Accept": "application/json"}, method="GET")
    for attempt in range(3):
        try:
            with opener.open(req, timeout=25) as response:
                payload = response.read(MAX_BYTES + 1)
                if len(payload) > MAX_BYTES:
                    raise ExportError("Discord lieferte zu viele Daten.")
                messages = json.loads(payload)
                if not isinstance(messages, list):
                    raise ExportError("Discord lieferte kein gültiges Nachrichtenformat.")
                return messages
        except error.HTTPError as exc:
            if exc.code == 429:
                try:
                    details = json.loads(exc.read(8192))
                    delay = float(exc.headers.get("Retry-After") or details.get("retry_after", 5))
                except (ValueError, TypeError, json.JSONDecodeError):
                    delay = 5
                if attempt == 2 or not 0 <= delay <= 90:
                    raise ExportError("Discord begrenzt den Abruf. Später erneut ausführen.") from None
                sleep(delay + 0.25)
                continue
            if 500 <= exc.code <= 599 and attempt < 2:
                sleep(2 ** attempt)
                continue
            hints = {401: "Bot-Token in GitHub Secrets prüfen.", 403: "Bot-Rechte für den Kanal prüfen.",
                     404: "Bot zum richtigen Server hinzufügen und Kanalzugriff prüfen."}
            raise ExportError(f"Discord antwortet mit HTTP {exc.code}. " + hints.get(exc.code, "Abruf später erneut versuchen.")) from None
        except (error.URLError, TimeoutError, OSError):
            if attempt == 2:
                raise ExportError("Discord ist nicht erreichbar. Der bisher veröffentlichte Feed bleibt erhalten.") from None
            sleep(2 ** attempt)
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise ExportError("Die Discord-Antwort ist kein gültiges JSON.") from None
    raise ExportError("Der Discord-Abruf konnte nicht abgeschlossen werden.")


def clean_mentions(text, message):
    names = {}
    for user in message.get("mentions") or []:
        if isinstance(user, dict):
            names[str(user.get("id", ""))] = str(user.get("global_name") or user.get("username") or "Nutzer")
    text = re.sub(r"<@!?(\d+)>", lambda match: "@" + names.get(match[1], "Nutzer"), text)
    text = re.sub(r"<@&\d+>", "@Rolle", text)
    text = re.sub(r"<#(\d+)>", lambda match: "#" + next((k for k, v in CHANNELS.items() if v == match[1]), "Kanal"), text)
    return re.sub(r"<a?:([A-Za-z0-9_]+):\d+>", r":\1:", text).replace("\x00", "")


def post_from_message(message, kind):
    if not isinstance(message, dict) or message.get("type", 0) not in (0, 19):
        return None
    post_id = str(message.get("id", ""))
    if not re.fullmatch(r"[0-9]{1,25}", post_id) or str(message.get("channel_id")) != CHANNELS[kind]:
        raise ExportError("Discord lieferte eine Nachricht aus einem unerwarteten Kanal.")
    try:
        if not isinstance(message.get("timestamp"), str):
            raise ValueError()
        published = datetime.fromisoformat(message["timestamp"].replace("Z", "+00:00"))
        if published.tzinfo is None:
            raise ValueError()
    except (KeyError, TypeError, ValueError):
        raise ExportError("Eine Discord-Nachricht enthält kein gültiges Datum.") from None
    chunks = [str(message.get("content") or "")]
    for embed in message.get("embeds") or []:
        if not isinstance(embed, dict):
            continue
        chunks.extend(str(embed.get(key) or "") for key in ("title", "description"))
        for field in embed.get("fields") or []:
            if isinstance(field, dict):
                chunks.extend((str(field.get("name") or ""), str(field.get("value") or "")))
    attachments = [str(a.get("filename") or "Anhang") for a in message.get("attachments") or [] if isinstance(a, dict)]
    if attachments:
        chunks.append("Anhänge im Discord-Beitrag: " + ", ".join(attachments))
    text = clean_mentions("\n\n".join(part.strip() for part in chunks if part.strip()), message).strip()[:8000]
    if not text:
        return None
    title = next((line.strip().lstrip("# ").replace("**", "").replace("__", "") for line in text.splitlines() if line.strip()), "Beitrag")[:160]
    author = message.get("author") or {}
    if not isinstance(author, dict):
        author = {}
    return {"id": post_id, "kind": kind, "channelId": CHANNELS[kind], "title": title or "Beitrag",
            "text": text, "publishedAt": published.astimezone(timezone.utc).isoformat(),
            "author": str(author.get("global_name") or author.get("username") or "Serverteam")[:120],
            "url": f"https://discord.com/channels/{GUILD_ID}/{CHANNELS[kind]}/{post_id}"}


def build_feed(messages_by_kind, now=None):
    posts = []
    for kind in CHANNELS:
        messages = messages_by_kind[kind]
        converted = [post for message in messages if (post := post_from_message(message, kind)) is not None]
        readable = [m for m in messages if isinstance(m, dict) and m.get("type", 0) in (0, 19)]
        if readable and not converted:
            raise ExportError("Nachrichten sind vorhanden, aber ihr Inhalt fehlt. MESSAGE CONTENT INTENT im Discord Developer Portal aktivieren.")
        posts.extend(converted)
    posts.sort(key=lambda p: p["publishedAt"], reverse=True)
    feed = {"schemaVersion": 1, "guildId": GUILD_ID,
            "updatedAt": (now or datetime.now(timezone.utc)).isoformat(), "posts": posts}
    if len(json.dumps(feed, ensure_ascii=False).encode("utf-8")) > MAX_BYTES:
        raise ExportError("Der erzeugte Newsfeed ist zu groß. postsPerChannel verringern.")
    return feed


def export(output, config_path, token=None):
    token = (token if token is not None else os.environ.get("DISCORD_BOT_TOKEN", "")).strip()
    if not token or any(char in token for char in "\r\n"):
        raise ExportError("Das GitHub-Secret DISCORD_BOT_TOKEN fehlt oder ist ungültig.")
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    count = validate_config(config)
    # Fetch both complete snapshots before writing anything. An API failure prevents deployment.
    feed = build_feed({kind: read_channel(token, channel, count) for kind, channel in CHANNELS.items()})
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    data = json.dumps(feed, ensure_ascii=False, indent=2).encode("utf-8")
    if token.encode("utf-8") in data:
        raise ExportError("Die Ausgabe enthält unerwartet vertrauliche Daten und wird nicht veröffentlicht.")
    temporary = output / ".news.json.tmp"
    temporary.write_bytes(data)
    temporary.replace(output / "news.json")
    (output / ".nojekyll").write_text("", encoding="utf-8")
    (output / "index.html").write_text('<!doctype html><html lang="de"><meta charset="utf-8"><title>OldschoolLife News</title><h1>OldschoolLife News</h1><p>Öffentlicher Newsfeed für den Missionshelfer.</p><p><a href="news.json">news.json</a></p></html>', encoding="utf-8")
    return len(feed["posts"])


if __name__ == "__main__":
    try:
        directory = Path(__file__).resolve().parent
        count = export(sys.argv[1] if len(sys.argv) > 1 else directory / "site", directory / "channels.json")
        print(f"Newsfeed erfolgreich erzeugt: {count} Beiträge.")
    except (ExportError, OSError, ValueError) as exc:
        # Do not print request headers, raw API responses or a traceback that might expose credentials.
        print(str(exc) if isinstance(exc, ExportError) else "Konfiguration oder Ausgabeverzeichnis konnte nicht gelesen werden.", file=sys.stderr)
        sys.exit(1)
