# Local S3 File Vault: Flask + Boto3 + AWS Emulator

A small local web app for uploading files to an S3 bucket on AWS Emulator, listing objects in a browser, and downloading them.

## Prerequisites

- AWS Emulator installed and running on `https://127.0.0.1:9297`
- AWS CLI v2 (for creating the bucket and independently inspecting its contents)
- Python 3.11+
- uv

## 1. Start AWS Emulator

In terminal 1:

```bash
aws-emulator --telemetry off
```

## 2. Configure the emulator endpoint

In terminal 2, from the project directory or any shell used to run the app and AWS CLI:

```bash
export AWS_ENDPOINT_URL=https://127.0.0.1:9297
export AWS_SHARED_CREDENTIALS_FILE=$HOME/.aws/emulator/9297/emulator_credentials
export AWS_CONFIG_FILE=$HOME/.aws/emulator/9297/config
export AWS_CA_BUNDLE=$HOME/.aws/emulator/9297/ca.pem
export AWS_EC2_METADATA_DISABLED=true
export AWS_DISABLE_HOST_PREFIX_INJECTION=true
export AWS_REGION=us-east-1
export AWS_DEFAULT_REGION=us-east-1

unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN AWS_PROFILE
```

Health check:

```bash
curl --cacert "$HOME/.aws/emulator/9297/ca.pem" https://127.0.0.1:9297/__admin/health
```

Expected output: `ok`.

## 3. Create the S3 bucket using AWS CLI

```bash
export S3_BUCKET=local-file-vault
aws s3api create-bucket --bucket "$S3_BUCKET"
```

The bucket is created inside the emulator, not in an AWS account.

## 4. Install dependencies and run the web app

```bash
uv sync
uv run python app.py
```

Open <http://127.0.0.1:5000> in your browser. Upload a file. It should appear in the bucket contents table. Use the Download link to retrieve it.

## 5. Verify the same object with AWS CLI

In terminal 2, using the same exported environment variables:

```bash
aws s3 ls "s3://$S3_BUCKET/"

aws s3api list-objects-v2 \
  --bucket "$S3_BUCKET" \
  --query 'Contents[].{Key:Key,Size:Size,LastModified:LastModified}'
```

Download an object through the CLI:

```bash
aws s3 cp "s3://$S3_BUCKET/your-file-name.txt" ./cli-copy.txt
```

Replace the object name with one shown in the web UI.

## Notes

- The browser talks to Flask. Flask uses Boto3 to call AWS Emulator. The browser does not need AWS credentials or direct S3 access.
- The app accepts files up to 16 MiB. This is a demo application limit, not an S3 limit.
- Uploading a file with the same filename overwrites the existing object with that key.
- The list view uses one `ListObjectsV2` request. It is intentionally kept simple for a small demo.
- AWS Emulator keeps resource state in memory. Stopping the emulator deletes the bucket and its objects.
- Do not use this demo as a production file-sharing service. It has no user authentication, malware scanning, or production-grade upload controls.
- Keep the emulator bound to localhost. Do not expose its port to your network or the internet.
