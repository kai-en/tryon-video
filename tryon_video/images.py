"""图片输入：本地文件 / http URL -> data URI（base64）。

参考生视频接口要求图像为公网 URL 或 base64 数据。素材常来自国外 CDN
（如 Pexels），国内服务端拉取未必稳定，因此默认统一转 base64 传入。
"""
from __future__ import annotations

import base64
from pathlib import Path

import requests

# 接口支持的格式：JPEG / JPG / PNG / WEBP
MIME_BY_SUFFIX = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}

MAX_BYTES = 20 * 1024 * 1024  # 单图不超过 20MB


def to_data_uri(source: str, session: requests.Session | None = None) -> str:
    """把图片来源（本地路径或 URL）转换为 data:image/...;base64,xxx。"""
    if source.startswith(("http://", "https://")):
        resp = (session or requests).get(
            source, timeout=60, headers={"User-Agent": "Mozilla/5.0"}
        )
        resp.raise_for_status()
        content = resp.content
        mime = (resp.headers.get("Content-Type") or "").split(";")[0]
        if mime not in MIME_BY_SUFFIX.values():
            mime = _guess_mime_from_url(source)
    else:
        path = Path(source).expanduser()
        if not path.is_file():
            raise FileNotFoundError(f"图片不存在: {path}")
        content = path.read_bytes()
        mime = MIME_BY_SUFFIX.get(path.suffix.lower())
        if not mime:
            raise ValueError(f"不支持的图片格式: {path.suffix}（仅 jpg/png/webp）")

    if len(content) > MAX_BYTES:
        raise ValueError(f"图片超过 20MB: {len(content)} bytes")
    return f"data:{mime};base64,{base64.b64encode(content).decode('ascii')}"


def _guess_mime_from_url(url: str) -> str:
    suffix = Path(url.split("?")[0]).suffix.lower()
    return MIME_BY_SUFFIX.get(suffix, "image/jpeg")
