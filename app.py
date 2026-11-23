import os
from io import BytesIO
from pathlib import Path

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from flask import Flask, abort, flash, redirect, render_template, request, send_file, url_for
from werkzeug.utils import secure_filename


BUCKET_NAME = os.environ.get("S3_BUCKET", "local-file-vault")
MAX_UPLOAD_BYTES = 16 * 1024 * 1024  # 16 MiB, an application-level limit for this demo.

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "local-development-only-change-me")
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES

# AWS_ENDPOINT_URL, credentials and the CA bundle are read from the environment.
# Keep the endpoint configuration outside the application code.
s3 = boto3.client("s3")


def format_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"


def list_bucket_objects() -> list[dict]:
    """Return the objects in the demo bucket, newest first."""
    response = s3.list_objects_v2(Bucket=BUCKET_NAME)
    objects = response.get("Contents", [])
    objects.sort(key=lambda item: item["LastModified"], reverse=True)

    for item in objects:
        item["display_size"] = format_size(item["Size"])

    return objects


@app.get("/")
def index():
    try:
        objects = list_bucket_objects()
    except (ClientError, BotoCoreError) as exc:
        app.logger.exception("Could not list objects in S3 bucket %s", BUCKET_NAME)
        flash(
            "Could not read the S3 bucket. Check that the emulator is running and "
            "that the bucket exists. See the terminal for details.",
            "error",
        )
        objects = []

    return render_template("index.html", bucket=BUCKET_NAME, objects=objects)


@app.post("/upload")
def upload():
    uploaded = request.files.get("file")
    if uploaded is None or not uploaded.filename:
        flash("Choose a file before uploading.", "error")
        return redirect(url_for("index"))

    filename = secure_filename(uploaded.filename)
    if not filename:
        flash("That filename is not valid. Rename the file and try again.", "error")
        return redirect(url_for("index"))

    try:
        # S3 object keys are unique within a bucket. Uploading the same filename
        # again replaces the existing object with that key.
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=filename,
            Body=uploaded.stream,
            ContentType=uploaded.mimetype or "application/octet-stream",
        )
        flash(f"Uploaded {filename} to s3://{BUCKET_NAME}/{filename}", "success")
    except (ClientError, BotoCoreError):
        app.logger.exception("Could not upload %s to S3", filename)
        flash("Upload failed. Check the terminal for the S3 error.", "error")

    return redirect(url_for("index"))


@app.get("/download/<path:key>")
def download(key: str):
    try:
        response = s3.get_object(Bucket=BUCKET_NAME, Key=key)
        data = response["Body"].read()
    except ClientError:
        app.logger.exception("Could not download S3 object %s", key)
        abort(404)
    except BotoCoreError:
        app.logger.exception("S3 client error downloading %s", key)
        abort(502)

    filename = Path(key).name or "download"
    return send_file(
        BytesIO(data),
        mimetype=response.get("ContentType", "application/octet-stream"),
        as_attachment=True,
        download_name=filename,
    )


@app.errorhandler(413)
def file_too_large(_error):
    flash("This demo accepts files up to 16 MiB.", "error")
    return redirect(url_for("index"))


if __name__ == "__main__":
    # Bind to loopback only. This is a local development app, not a production server.
    app.run(host="127.0.0.1", port=5000, debug=False)
