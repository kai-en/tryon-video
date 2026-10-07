"""HappyHorse 参考生视频（r2v）异步接口封装：提交 -> 轮询 -> 下载。"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Callable, List, Optional

import requests

from .config import SUBMIT_PATH, TASK_PATH, Settings

# 轮询回调类型：用于打印 PENDING/RUNNING 进度
Progress = Optional[Callable[[str, int], None]]


class VideoGenerationError(RuntimeError):
    pass


class Client:
    def __init__(self, settings: Settings, timeout: int = 120):
        self.settings = settings
        self.timeout = timeout
        self.session = requests.Session()
        # 国内直连百炼即可；避免 Windows 下 requests 读取注册表系统代理导致 TLS 握手报错
        self.session.trust_env = False
        self.session.headers.update({"Authorization": f"Bearer {settings.api_key}"})

    # ---- 步骤1：创建任务 ----
    def submit(
        self,
        prompt: str,
        image_sources: List[str],
        *,
        resolution: str = "720P",
        ratio: str = "9:16",
        duration: int = 5,
        watermark: bool = False,
        seed: Optional[int] = None,
    ) -> str:
        from .images import to_data_uri  # 延迟导入，避免循环依赖

        media = [
            {"type": "reference_image", "url": to_data_uri(src, self.session)}
            for src in image_sources
        ]
        parameters = {
            "resolution": resolution,
            "ratio": ratio,
            "duration": duration,
            "watermark": watermark,
        }
        if seed is not None:
            parameters["seed"] = seed

        body = {
            "model": self.settings.model,
            "input": {"prompt": prompt, "media": media},
            "parameters": parameters,
        }
        url = self.settings.base_url + SUBMIT_PATH
        resp = self.session.post(
            url,
            json=body,
            headers={"X-DashScope-Async": "enable"},
            timeout=self.timeout,
        )
        data = _json_or_raise(resp)
        task_id = data.get("output", {}).get("task_id")
        if not task_id:
            raise VideoGenerationError(f"提交失败，未返回 task_id: {data}")
        return task_id

    # ---- 步骤2：轮询任务 ----
    def wait(
        self,
        task_id: str,
        *,
        interval: int = 15,
        max_wait: int = 1800,
        progress: Progress = None,
    ) -> str:
        url = self.settings.base_url + TASK_PATH.format(task_id=task_id)
        waited = 0
        while waited < max_wait:
            time.sleep(interval)
            waited += interval
            data = _json_or_raise(self.session.get(url, timeout=self.timeout))
            output = data.get("output", {})
            status = output.get("task_status", "UNKNOWN")
            if progress:
                progress(status, waited)
            if status == "SUCCEEDED":
                video_url = output.get("video_url")
                if not video_url:
                    raise VideoGenerationError(f"成功但无 video_url: {data}")
                return video_url
            if status in ("FAILED", "CANCELED", "UNKNOWN"):
                raise VideoGenerationError(
                    f"任务未成功（{status}）: {output.get('code')} {output.get('message')}"
                )
        raise VideoGenerationError(f"轮询超时（>{max_wait}s），task_id={task_id}")

    # ---- 步骤3：下载视频 ----
    def download(self, video_url: str, out_path: Path) -> Path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with self.session.get(video_url, stream=True, timeout=self.timeout) as resp:
            resp.raise_for_status()
            with open(out_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=1 << 16):
                    f.write(chunk)
        return out_path


def _json_or_raise(resp: requests.Response) -> dict:
    try:
        data = resp.json()
    except ValueError:
        raise VideoGenerationError(f"HTTP {resp.status_code} 非 JSON 响应: {resp.text[:300]}")
    if resp.status_code >= 400 or data.get("code"):
        raise VideoGenerationError(f"HTTP {resp.status_code}: {data}")
    return data
