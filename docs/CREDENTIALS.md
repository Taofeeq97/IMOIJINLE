# Credentials checklist for real services
#
# Fill these in `.env` (never commit secrets). Local infra:
#   docker compose -f infra/docker-compose.yml up -d

## Object storage (MinIO or AWS S3)
USE_S3=true
MINIO_ENDPOINT / MINIO_ACCESS_KEY / MINIO_SECRET_KEY / MINIO_BUCKET
# or AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_STORAGE_BUCKET_NAME / AWS_S3_REGION_NAME

## Paystack
PAYSTACK_SECRET_KEY=sk_test_... or sk_live_...
PAYSTACK_PUBLIC_KEY=pk_test_... or pk_live_...
# Webhook URL (Paystack dashboard): {API_BASE_URL}/api/v1/webhooks/paystack

## Mux
MUX_TOKEN_ID=
MUX_TOKEN_SECRET=
MUX_WEBHOOK_SECRET=   # from Mux webhook signing secret
MUX_SIGNING_KEY_ID=   # for signed playback
MUX_SIGNING_PRIVATE_KEY=  # PEM, use \n for newlines in .env
# Webhook URL: {API_BASE_URL}/api/v1/webhooks/mux
# Events: video.upload.asset_created, video.asset.ready, video.asset.errored

## Document conversion (Gotenberg)
DOCUMENT_CONVERTER_URL=http://localhost:3001
# Started via docker compose service `gotenberg`

## Optional
GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET
SENTRY_DSN
