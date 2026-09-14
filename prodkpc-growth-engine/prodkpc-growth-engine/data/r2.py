"""
Cloudflare R2 video storage (S3-compatible via boto3).

Uses a single put_object request rather than multipart uploads: R2's S3
compatibility layer trips boto3's newer multipart signing/checksum path
(SignatureDoesNotMatch on CreateMultipartUpload). Single-shot puts avoid that
entirely and are fine for type-beat videos (well under R2's single-put limit).
"""


def configured(cfg):
    return bool(cfg.r2_access_key_id and cfg.r2_secret_access_key
               and cfg.r2_endpoint and cfg.r2_bucket and cfg.r2_public_base)


def _client(cfg):
    import boto3
    from botocore.config import Config as BotoConfig
    # Opt out of botocore's newer default flexible checksums, which R2 rejects.
    kwargs = dict(signature_version="s3v4")
    try:
        cfg_obj = BotoConfig(
            **kwargs,
            request_checksum_calculation="when_required",
            response_checksum_validation="when_required",
        )
    except TypeError:
        # older botocore without those options
        cfg_obj = BotoConfig(**kwargs)
    return boto3.client(
        "s3",
        endpoint_url=cfg.r2_endpoint,
        aws_access_key_id=cfg.r2_access_key_id,
        aws_secret_access_key=cfg.r2_secret_access_key,
        config=cfg_obj,
        region_name="auto",
    )


def upload_video(cfg, file_bytes, key, content_type="video/mp4"):
    """Store bytes under `key`. Returns {ok, url} or {ok: False, error}."""
    if not configured(cfg):
        return {"ok": False, "error": "R2 not configured"}
    try:
        client = _client(cfg)
        client.put_object(Bucket=cfg.r2_bucket, Key=key,
                          Body=file_bytes, ContentType=content_type)
        base = cfg.r2_public_base.rstrip("/")
        return {"ok": True, "url": f"{base}/{key}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def list_videos(cfg, prefix="", limit=100):
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
