# Classroom Reflection Media Tool

独立工具：把通义听悟音视频转写结果转换为 `classroom-reflection-skill` 已支持的 `request.json`。

它不修改 `classroom-reflection-skill`，只负责生成输入文件。

## 1. 已有通义听悟结果时转换

```bash
python3 agent_cases/classroom-reflection-media-tool/transcribe_media.py convert \
  --tingwu-result /path/to/tingwu-transcription.json \
  --output /tmp/pan-request.json
```

然后交给原 skill：

```bash
python3 agent_cases/classroom-reflection-skill/scripts/run_reflection.py prepare /tmp/pan-request.json
```

## 2. 通过通义听悟 API 转写公网音视频 URL

先安装阿里云官方 SDK：

```bash
pip install alibabacloud-tingwu20230930 alibabacloud-tea-openapi alibabacloud-tea-util
```

执行：

```bash
python3 agent_cases/classroom-reflection-media-tool/transcribe_media.py transcribe \
  --media-url "https://example.com/lesson.mp4" \
  --wait \
  --raw-dir /tmp/tingwu-raw \
  --output /tmp/pan-request.json
```

成功后会生成两个主要文件：

- `/tmp/pan-request.json`：后处理后的 `classroom-reflection-skill` 输入文件。
- `/tmp/pan-request.tingwu-raw.json`：阿里云返回的原始转写产物，未做字段归一化、说话人映射和时间兜底。

如需指定原始产物保存位置，可加：

```bash
--raw-output /tmp/tingwu-direct.json
```

凭据默认按以下顺序读取：

1. 当前 shell 环境变量
2. `agent_cases/classroom-reflection-media-tool/.env`
3. 仓库根目录 `.env`

推荐使用 `.env`：

```bash
cp agent_cases/classroom-reflection-media-tool/.env.example \
  agent_cases/classroom-reflection-media-tool/.env
```

然后填入：

```text
TINGWU_ACCESS_KEY_ID=...
TINGWU_ACCESS_KEY_SECRET=...
TINGWU_APP_KEY=...
```

工具不会把密钥写入输出 JSON。仓库 `.gitignore` 已忽略 `.env` 和 `.env.*`。

## 3. 说话人映射

通义听悟返回的说话人通常是 `SpeakerId`，不一定知道谁是教师。工具默认用启发式推断教师/学生。

如果已知说话人编号，建议显式传入：

```bash
--teacher-speaker spk-1 --student-speaker spk-2
```

输出中会保留 `speakerRaw`，便于人工核对。

## 4. 本地文件限制

通义听悟离线任务需要公网可访问的音视频 URL。第一版工具只支持 `--media-url`。

如果用户只有本地视频，需要先上传到 OSS 或其他可访问地址，再调用本工具。

## 5. 本地视频实时推流测试

如果不想先上传 OSS，可以用实时推流模式。该模式会先调用 `ffmpeg` 从本地视频抽取 16k 单声道 PCM，再通过通义听悟实时任务的 WebSocket 推送音频流。

额外依赖：

```bash
pip install aliyun-python-sdk-core websocket-client
```

本机还需要可用的 `ffmpeg`：

```bash
ffmpeg -version
```

执行：

```bash
python3 agent_cases/classroom-reflection-media-tool/transcribe_media.py transcribe-realtime \
  --media-file /path/to/lesson.mp4 \
  --connect-timeout 60 \
  --read-timeout 180 \
  --api-retries 3 \
  --progress-interval 10 \
  --raw-dir /tmp/tingwu-realtime-raw \
  --output /tmp/tingwu-realtime-request.json
```

输出成功后继续交给原 skill：

```bash
python3 agent_cases/classroom-reflection-skill/scripts/run_reflection.py prepare \
  /tmp/tingwu-realtime-request.json
```

说明：

- 实时模式不需要公网 `media-url`。
- 默认会按 100ms 音频帧近似实时推送，长视频耗时接近视频时长。
- 实时模式也会在 `--output` 同目录生成 `.tingwu-raw.json`，内容是通义听悟 WebSocket 直接返回的事件列表；可用 `--raw-output` 改位置。
- 命令会在 stderr 输出进度，例如抽音频、创建任务、WebSocket 开始、已推送音频百分比；如需关闭可加 `--quiet`。
- 如果通义听悟没有返回说话人编号，工具默认把句子标为“教师”，避免原 skill 因全是“其他”而拒绝处理；可用 `--default-speaker 其他` 改回保守模式。
- 若已知道说话人编号，仍建议传 `--teacher-speaker ... --student-speaker ...`。
- 如果创建实时任务时报 `ConnectTimeout`，优先检查本机网络、代理、VPN 或防火墙；也可临时提高 `--connect-timeout` 和 `--api-retries`。
