"""集中管理常量与运行配置。"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

# ---- 服务端点（华北2-北京，Token Plan 专属域名）----
BASE_URL = os.environ.get(
    "TRYON_BASE_URL", "https://token-plan.cn-beijing.maas.aliyuncs.com"
)
SUBMIT_PATH = "/api/v1/services/aigc/video-generation/video-synthesis"
TASK_PATH = "/api/v1/tasks/{task_id}"

DEFAULT_MODEL = "happyhorse-1.1-r2v"

# 参考生视频参数取值范围（见官方 API 文档）
RESOLUTIONS = {"480P", "720P", "1080P"}
RATIOS = {"16:9", "9:16", "3:4", "4:3", "4:5", "5:4", "1:1", "9:21", "21:9"}
DURATION_RANGE = (3, 15)

# 项目根目录：tryon_video/config.py -> 上两级
PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = PROJECT_ROOT / "assets"
OUTPUT_DIR = PROJECT_ROOT / "output"


def _key_from_opencode_auth() -> str | None:
    """兜底：从 opencode 的 auth.json 读取 Token Plan Key（本机开发便利）。"""
    auth = (
        Path(os.path.expanduser("~"))
        / ".local"
        / "share"
        / "opencode"
        / "auth.json"
    )
    if not auth.exists():
        return None
    try:
        data = json.loads(auth.read_text(encoding="utf-8"))
        return data.get("alibaba-token-plan-cn", {}).get("key") or None
    except (ValueError, OSError):
        return None


@dataclass
class Settings:
    api_key: str
    base_url: str = BASE_URL
    model: str = DEFAULT_MODEL

    @classmethod
    def load(cls, api_key: str | None = None) -> "Settings":
        key = (
            api_key
            or os.environ.get("TRYON_API_KEY")
            or os.environ.get("ANTHROPIC_AUTH_TOKEN")
            or _key_from_opencode_auth()
        )
        if not key:
            raise RuntimeError(
                "未找到 API Key：请设置环境变量 TRYON_API_KEY，"
                "或通过 --api-key 传入以 sk-sp- 开头的套餐 Key。"
            )
        return cls(api_key=key)
