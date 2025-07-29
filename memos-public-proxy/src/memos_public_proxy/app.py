import flask
import requests
import os
import json
import markdown
import logging

logger = logging.getLogger(__name__)

app = flask.Flask("memos-public-proxy")

MEMOS_PROTOCOL = os.environ.get("MEMOS_PROTOCOL", "http")
MEMOS_HOST = os.environ.get("MEMOS_HOST", "memos")
MEMOS_LOG_LEVEL = os.environ.get("MEMOS_LOG_LEVEL", "ERROR")

logger.setLevel(MEMOS_LOG_LEVEL)


@app.route("/memos/<slug>")
def get_memo(slug: str):
    logger.info(f"GET /memos/{slug}")
    response = requests.get(f"{MEMOS_PROTOCOL}://{MEMOS_HOST}/api/v1/memos/{slug}")

    if response.status_code != 200:
        message = json.loads(response.content.decode())["message"]
        logger.error(f"Error getting memo {slug}: {message}")
        return "", 404

    body = json.loads(response.content.decode())
    content = body["content"]
    attachments = body["attachments"]
    for attachment in attachments:
        attachment_filename = attachment["filename"]
        attachment_url = f"/file/{attachment['name']}/{attachment_filename}"
        content = f"{content}\n\n[{attachment_filename}]({attachment_url})"
    html = markdown.markdown(content)
    return html


@app.route("/file/attachments/<slug>/<filename>")
def get_attachment(slug: str, filename: str):
    logger.info(f"GET /file/attachments/{slug}/{filename}")
    memos_response = requests.get(f"{MEMOS_PROTOCOL}://{MEMOS_HOST}/file/attachments/{slug}/{filename}")

    if memos_response.status_code != 200:
        message = json.loads(memos_response.content.decode())["message"]
        logger.error(f"Error getting memo {slug}: {message}")
        return "", 404

    response = flask.make_response(memos_response.content)
    response.headers.set("Content-Type", memos_response.headers["Content-Type"])
    response.headers.set("Content-Disposition", "attachment", filename=filename)
    return response
