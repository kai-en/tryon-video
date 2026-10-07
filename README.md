# tryon-video

输入 **人物照 + 衣服照 + 提示词**，调用阿里云百炼 **Token Plan** 的 HappyHorse 参考生视频模型（`happyhorse-1.1-r2v`），产出一段 3~15 秒的服装展示视频。

## 项目结构

```
tryon-video/
├── tryon_video/          # Python 包
│   ├── config.py         # 端点/取值范围/API Key 加载
│   ├── images.py         # 本地或 URL 图片 -> base64 data URI
│   ├── api.py            # 提交任务 -> 轮询 -> 下载 三步封装
│   ├── cli.py            # 命令行入口与参数校验
│   └── __main__.py       # python -m tryon_video
├── assets/               # 示例输入图（Pexels 免费素材）
│   ├── model.jpg         # 人物照
│   └── dress.jpg         # 衣服照
├── output/               # 生成的 mp4（已 gitignore）
├── requirements.txt
├── .env.example
└── README.md
```

## 安装

```powershell
pip install -r requirements.txt
```

## 配置 API Key

按以下任一方式提供以 `sk-sp-` 开头的 Token Plan 套餐 Key：

```powershell
$env:TRYON_API_KEY = "sk-sp-xxxx"      # 推荐
```

或运行时 `--api-key sk-sp-xxxx`。本机若已配置 opencode，会自动兜底读取其 auth.json（见 `config.py`）。

## 使用

```powershell
# 先干跑校验（不提交、不消耗额度）
python -m tryon_video --model-image assets\model.jpg --cloth-image assets\dress.jpg --dry-run

# 正式生成：10 秒、720P、竖屏 9:16
python -m tryon_video --model-image assets\model.jpg --cloth-image assets\dress.jpg --duration 10
```

输出文件默认落在 `output\tryon_<时间戳>.mp4`。

常用参数：

| 参数 | 说明 | 默认 |
|---|---|---|
| `--model-image` / `--cloth-image` | 人物照 / 衣服照（本地路径或 URL） | 必填 |
| `--prompt` | 提示词，用 `[Image 1]`/`[Image 2]` 指代两图 | 内置服装展示模板 |
| `--duration` | 秒数，3~15 | 10 |
| `--resolution` | 480P / 720P / 1080P | 720P |
| `--ratio` | 16:9 / 9:16 / 1:1 ... | 9:16 |
| `--seed` | 固定种子提升复现 | 随机 |
| `--task-id` | 跳过提交，续查已提交任务 | — |

## 工作流程

1. **读取素材**：两张图本地或 URL 统一转 base64（国内服务端拉取国外 CDN 不稳定，故不走公网 URL）。
2. **提交任务**：`POST /api/v1/services/aigc/video-generation/video-synthesis`，带 `X-DashScope-Async: enable`，返回 `task_id`。
3. **轮询**：`GET /api/v1/tasks/{task_id}`，状态 `PENDING → RUNNING → SUCCEEDED/FAILED`，每 15s 一次。
4. **下载**：成功后取 `video_url`（24h 有效）流式下载到 `output/`。

## 注意事项

- 模型、Endpoint、API Key 须**同地域**（本项目默认华北2-北京）。
- 单张参考图 ≤ 20MB，短边建议 ≥ 400px。
- 生成一段 10s/720P 视频实测约 2 分钟，消耗 Token Plan Credits。
- 换装贴合度要求高时，可先用图像编辑做"虚拟试穿"合成图，再走单图首帧生视频（两步法），成功率更高。
