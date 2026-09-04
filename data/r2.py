"""
Cloudflare R2 video storage. R2 speaks the S3 API, so we use boto3 pointed at
the R2 endpoint. Uploading a video returns its public URL (via the bucket's
r2.dev public base), which is exactly what the Instagram publishing API needs
later. All guarded: if R2 isn't configured, the app still runs and the Upload
page just skips the storage step.
"""
import io


def configured(cfg):
    return bool(cfg.r2_access_key_id and cfg.r2_secret_access_key
               and cfg.r2_endpoint and cfg.r2_bucket and cfg.r2_public_base)


def _client(cfg):
    import boto3
    from botocore.config import Config as BotoConfig
    return boto3.client(
        "s3",
        endpoint_url=cfg.r2_endpoint,
        aws_access_key_id=cfg.r2_access_key_id,
        aws_secret_access_key=cfg.r2_secret_access_key,
        config=BotoConfig(signature_version="s3v4"),
        region_name="auto",
    )


def upload_video(cfg, file_bytes, key, content_type="video/mp4"):
    """Store bytes under `key` in the bucket. Returns {ok, url} or {ok: False, error}."""
    if not configured(cfg):
        return {"ok": False, "error": "R2 not configured"}
    try:
        client = _client(cfg)
        client.upload_fileobj(
            io.BytesIO(file_bytes), cfg.r2_bucket, key,
            ExtraArgs={"ContentType": content_type},
        )
        base = cfg.r2_public_base.rstrip("/")
        return {"ok": True, "url": f"{base}/{key}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def list_videos(cfg, prefix="", limit=50):
    if not configured(cfg):
        return []
    try:
        client = _client(cfg)
        resp = client.list_objects_v2(Bucket=cfg.r2_bucket, Prefix=prefix, MaxKeys=limit)
        base = cfg.r2_public_base.rstrip("/")
        return [{"key": o["Key"], "size": o["Size"], "url": f"{base}/{o['Key']}"}
                for o in resp.get("Contents", [])]
    except Exception:
        return []
