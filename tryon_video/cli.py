"""命令行入口。

示例：
    python -m tryon_video --model-image assets/model.jpg --cloth-image assets/dress.jpg
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from .api import Client
from .config import (
    DEFAULT_MODEL,
    DURATION_RANGE,
    OUTPUT_DIR,
    RATIOS,
    RESOLUTIONS,
    Settings,
)

DEFAULT_PROMPT = (
    "[Image 1]中的模特换上[Image 2]中的服装，站在明亮简约的摄影棚中，"
    "镜头由正面全身缓缓环绕至侧面，展示服装的版型、面料与垂坠感，"
    "模特自然转身、轻微走动并微笑，商业服装展示风格，柔和打光，真实质感。"
)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tryon_video",
        description="人物照 + 衣服照 -> 服装展示视频（百炼 Token Plan / HappyHorse r2v）",
    )
    p.add_argument("--model-image", required=True, help="人物照：本地路径或 URL")
    p.add_argument("--cloth-image", required=True, help="衣服照：本地路径或 URL")
    p.add_argument("--prompt", default=DEFAULT_PROMPT, help="文本提示词，用 [Image 1]/[Image 2] 指代两张图")
    p.add_argument("--model-name", default=DEFAULT_MODEL, help="视频模型 ID（默认 %(default)s）")
    p.add_argument("--resolution", default="720P", choices=sorted(RESOLUTIONS))
    p.add_argument("--ratio", default="9:16", choices=sorted(RATIOS))
    p.add_argument("--duration", type=int, default=10, help=f"视频秒数 {DURATION_RANGE[0]}~{DURATION_RANGE[1]}")
    p.add_argument("--seed", type=int, default=None, help="随机种子（提升可复现性）")
    p.add_argument("--watermark", action="store_true", help="添加水印（默认不加）")
    p.add_argument("--out", default=None, help="输出 mp4 路径（默认 output/tryon_<时间戳>.mp4）")
    p.add_argument("--api-key", default=None, help="Token Plan Key（sk-sp-...），默认读环境变量 TRYON_API_KEY")
    p.add_argument("--dry-run", action="store_true", help="只构建并校验请求，不真正提交")
    p.add_argument("--task-id", default=None, help="跳过提交，直接轮询并下载已有任务")
    return p


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):  # Windows 控制台中文/emoji 兜底
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = build_parser().parse_args(argv)

    if not DURATION_RANGE[0] <= args.duration <= DURATION_RANGE[1]:
        print(f"duration 需在 {DURATION_RANGE} 秒之间", file=sys.stderr)
        return 2

    settings = Settings.load(args.api_key)
    settings.model = args.model_name
    client = Client(settings)

    if args.dry_run:
        from .images import to_data_uri

        sizes = []
        for src in (args.model_image, args.cloth_image):
            uri = to_data_uri(src, client.session)
            sizes.append(len(uri) // 1024)
        print(f"[dry-run] 模型={args.model_name} 分辨率={args.resolution} 比例={args.ratio} 时长={args.duration}s")
        print(f"[dry-run] 两张参考图 base64 大小: {sizes[0]} KB + {sizes[1]} KB（接口上限 20MB/张）")
        print("[dry-run] 校验通过，未提交任务")
        return 0

    if args.task_id:
        task_id = args.task_id
        print(f"续查已有任务: {task_id}")
    else:
        print("提交任务中 ...")
        task_id = client.submit(
            args.prompt,
            [args.model_image, args.cloth_image],
            resolution=args.resolution,
            ratio=args.ratio,
            duration=args.duration,
            watermark=args.watermark,
            seed=args.seed,
        )
        print(f"task_id: {task_id}")

    def on_progress(status: str, waited: int) -> None:
        print(f"  [{waited:>4}s] {status}")

    video_url = client.wait(task_id, progress=on_progress)
    out = Path(args.out) if args.out else OUTPUT_DIR / f"tryon_{time.strftime('%Y%m%d_%H%M%S')}.mp4"
    client.download(video_url, out)
    size_mb = out.stat().st_size / 1024 / 1024
    print(f"完成: {out.resolve()}  ({size_mb:.2f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
