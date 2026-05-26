import flask
import requests
import os
import json
import markdown2
import pathlib
import re
import html
import urllib.parse

app = flask.Flask("memos-public-proxy")

MEMOS_HOST = os.environ.get("MEMOS_HOST", "http://memos:5230")
MEMOS_LOG_LEVEL = os.environ.get("MEMOS_LOG_LEVEL", "ERROR").upper()
MEMOS_CACHE_PATH = os.environ.get("MEMOS_CACHE_PATH", "/cache")
EXTRAS = [
    "tables",
    "task_list",
    "strike",
    "fenced-code-blocks",
    "cuddled-lists",
    "header-ids",
    "latex",
    "mermaid",
]
ICON_PATH = "/logo.webp"

HASHTAG_PATTERN = re.compile(r"#[^\s]+")
HTML = "\n".join(p.read_text() for p in (pathlib.Path(__file__).parent / "html").glob("*.html"))

app.logger.setLevel(MEMOS_LOG_LEVEL)


def _handle_error(path: str, response: requests.Response):
    try:
        message = json.loads(response.content.decode())["message"]
    except Exception as e:
        message = str(e)
    app.logger.error(f"({path}): {message}")
    return "", 404


def _memo_path(id: str):
    return f"/memos/{id}"


def _file_path(attachment_name: str, filename: str):
    return f"/file/attachments/{attachment_name}/{filename}"


@app.route(_memo_path("<id>"))
def get_memo(id: str):
    path = _memo_path(id)
    app.logger.info(f"GET {path}")
    response = requests.get(f"{MEMOS_HOST}/api/v1{path}")

    if response.status_code != 200:
        return _handle_error(path, response)

    body = json.loads(response.content.decode())
    content: str = body["content"]
    attachments: list = body["attachments"]
    update_time: str = body["updateTime"]

    # First check the cache
    update_time_slug = re.sub(r'[^a-zA-Z0-9\-]', '_', update_time)
    cache_path = pathlib.Path(f"{MEMOS_CACHE_PATH}/{id}/{update_time_slug}")
    if cache_path.exists():
        app.logger.info(f"memo {id} found in cache")
        return cache_path.read_text()

    app.logger.info(f"memo {id} not found in cache, generating html")

    # Escape hashtags in the first and last lines
    lines = content.split("\n")
    if lines:
        lines[0] = re.sub(HASHTAG_PATTERN, lambda m: rf"\{m.group(0)}", lines[0])
        lines[-1] = re.sub(HASHTAG_PATTERN, lambda m: rf"\{m.group(0)}", lines[-1])
    content = "\n".join(lines)

    # Prepend other HTML
    content = f"{HTML}\n\n{content}"

    attachments.sort(key=lambda a: not a["type"].startswith("image"))  # Sort images first

    for attachment in attachments:
        filename = attachment["filename"]
        parts = attachment["name"].split("/")
        if len(parts) < 2:
            continue
        attachment_id = parts[1]
        encoded_path = _file_path(attachment_id, urllib.parse.quote(filename))
        filename_escaped = html.escape(filename)

        if attachment["type"].startswith("image"):
            image = f'<a href="{encoded_path}"><img src="{encoded_path}" alt="{filename_escaped}" width="500"/></a>'
            content = f"{content}\n\n{image}"
        else:
            link = f"[{filename_escaped}]({encoded_path})"
            content = f"{content}\n\n{link}"

    # Update the cache
    html_content = markdown2.markdown(content, extras=EXTRAS)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(html_content)

    return html_content


@app.route(_file_path("<id>", "<filename>"))
def get_attachment(id: str, filename: str):
    path = _file_path(id, filename)
    app.logger.info(f"GET {path}")
    response = requests.get(f"{MEMOS_HOST}{path}")

    if response.status_code != 200:
        return _handle_error(path, response)

    return response.content, response.status_code, response.headers.items()


@app.route(ICON_PATH)
def get_icon():
    app.logger.info(f"GET {ICON_PATH}")
    response = requests.get(f"{MEMOS_HOST}{ICON_PATH}")

    return response.content, response.status_code, response.headers.items()
