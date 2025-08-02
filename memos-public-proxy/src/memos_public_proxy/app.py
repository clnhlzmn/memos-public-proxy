import flask
import requests
import os
import json
import markdown2
import pathlib
import re

app = flask.Flask("memos-public-proxy")

MEMOS_HOST = os.environ.get("MEMOS_HOST", "http://memos:5230")
MEMOS_LOG_LEVEL = os.environ.get("MEMOS_LOG_LEVEL", "ERROR").upper()
MEMOS_CACHE_PATH = os.environ.get("MEMOS_CACHE_PATH", "/cache")
EXTRAS = [
    "tables",
    "todo_list",
    "strike",
    "fenced-code-blocks",
    "cuddled-lists",
    "header-ids",
    "latex",
    "mermaid",
]

HASHTAG_PATTERN = re.compile(r"#[^\s]+")
STYLE = "\n".join(p.read_text() for p in (pathlib.Path(__file__).parent / "style").glob("*.css"))

app.logger.setLevel(MEMOS_LOG_LEVEL)


def _handle_error(path: str, response: requests.Response):
    message = json.loads(response.content.decode())["message"]
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
    cache_path = pathlib.Path(f"{MEMOS_CACHE_PATH}/{id}/{update_time}")
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

    # Prepend the style
    content = f"""
<style type="text/css" rel="stylesheet">
{STYLE}
</style>
{content}
"""

    attachments.sort(key=lambda a: not a["type"].startswith("image"))  # Sort images first

    for attachment in attachments:

        filename = attachment["filename"]
        id = attachment["name"].split("/")[1]
        path = _file_path(id, filename)

        if attachment["type"].startswith("image"):
            image = f'<a href="{path}"><img src="{path}" alt="{filename}" width="500"/></a>'
            content = f"{content}\n\n{image}"
        else:
            link = f"[{filename}]({path})"
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
