import flask
import requests
import os
import json
import markdown2
import logging
import pathlib
import re

logger = logging.getLogger(__name__)

app = flask.Flask("memos-public-proxy")

MEMOS_PROTOCOL = os.environ.get("MEMOS_PROTOCOL", "http")
MEMOS_HOST = os.environ.get("MEMOS_HOST", "memos")
MEMOS_PORT = os.environ.get("MEMOS_PORT", "5230")
MEMOS_LOG_LEVEL = os.environ.get("MEMOS_LOG_LEVEL", "ERROR").upper()

MEMOS_CONNECTION = f"{MEMOS_PROTOCOL}://{MEMOS_HOST}:{MEMOS_PORT}"

HASHTAG_PATTERN = re.compile(r"#[^\s]+")

STYLE = "\n".join(p.read_text() for p in (pathlib.Path(__file__).parent / "style").glob("*.css"))

logger.setLevel(MEMOS_LOG_LEVEL)


def _handle_error(path: str, response: requests.Response):
    message = json.loads(response.content.decode())["message"]
    logger.error(f"Error ({path}): {message}")
    return "", 404


def _memo_path(id: str):
    return f"/memos/{id}"


def _file_path(attachment_name: str, filename: str):
    return f"/file/attachments/{attachment_name}/{filename}"


@app.route(_memo_path("<id>"))
def get_memo(id: str):
    path = _memo_path(id)
    logger.info(f"GET {path}")
    response = requests.get(f"{MEMOS_CONNECTION}/api/v1{path}")

    if response.status_code != 200:
        return _handle_error(path, response)

    body = json.loads(response.content.decode())
    content: str = body["content"]
    attachments: list = body["attachments"]

    # Escape hashtags in the first and last lines
    lines = content.split("\n")
    if lines:
        lines[0] = re.sub(HASHTAG_PATTERN, lambda m: rf"\{m.group(0)}", lines[0])
        lines[-1] = re.sub(HASHTAG_PATTERN, lambda m: rf"\{m.group(0)}", lines[-1])
    content = "\n".join(lines)

    # Prepend the style
    content = f"""
<style type="text/css" rel="stylesheet">
{STYLE}
</style>
{content}
"""

    attachments.sort(key = lambda a: not a["type"].startswith("image")) # Sort images first

    for attachment in attachments:

        filename = attachment["filename"]
        id = attachment["name"].split("/")[1]
        path = _file_path(id, filename)

        if attachment["type"].startswith("image"):
            image = f'<img src="{path}" alt="{filename}" width="500"/>'
            content = f"{content}\n\n{image}"
        else:
            link = f"[{filename}]({path})"
            content = f"{content}\n\n{link}"

    return markdown2.markdown(content)


@app.route(_file_path("<id>", "<filename>"))
def get_attachment(id: str, filename: str):
    path = _file_path(id, filename)
    logger.info(f"GET {path}")
    response = requests.get(f"{MEMOS_CONNECTION}{path}")

    if response.status_code != 200:
        return _handle_error(path, response)

    return response.content, response.status_code, response.headers.items()
