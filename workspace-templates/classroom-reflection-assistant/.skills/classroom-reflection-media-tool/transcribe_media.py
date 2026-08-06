#!/usr/bin/env python3
"""把音视频转写结果转换成 classroom-reflection-skill 可读取的输入。

这个工具独立于 classroom-reflection-skill。
它负责调用通义听悟完成音视频转写，然后写出 scripts/run_reflection.py 已经支持的 request JSON。

实时模式的流程是：

1. 从环境变量或 .env 读取本地凭据。
2. 用 ffmpeg 从本地视频抽取 16k 单声道 PCM 音频。
3. 创建通义听悟实时任务，拿到 MeetingJoinUrl。
4. 连接 MeetingJoinUrl 对应的 WebSocket。
5. 发送 StartTranscription 控制消息。
6. 把 PCM 音频按小块推送给 WebSocket。
7. 接收通义听悟返回的句子事件。
8. 发送 StopTranscription 控制消息，并停止实时任务。
9. 把收到的事件转换成 classroom-reflection-skill 的 request JSON。
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from uuid import uuid4


# 通义听悟文档示例中常用的默认值。这里仍允许命令行覆盖，因为不同网络、
# 代理、区域部署可能需要不同 endpoint 或 timeout。
DEFAULT_ENDPOINT = "tingwu.cn-beijing.aliyuncs.com"
DEFAULT_REGION = "cn-beijing"
DEFAULT_LANGUAGE = "cn"
DEFAULT_POLL_INTERVAL = 10
DEFAULT_TIMEOUT = 7200

# 实时模式推送的是原始 PCM 音频。16 kHz 单声道 16 位 PCM 表示：
# 每秒 16000 个采样点 * 每个采样点 2 字节 = 每秒 32000 字节。
DEFAULT_SAMPLE_RATE = 16000
DEFAULT_AUDIO_FORMAT = "pcm"
DEFAULT_CHUNK_MS = 100
DEFAULT_CONNECT_TIMEOUT = 30
DEFAULT_READ_TIMEOUT = 120
DEFAULT_API_RETRIES = 3
DEFAULT_RETRY_SLEEP = 5
DEFAULT_PROGRESS_INTERVAL = 10
TOOL_ROOT = Path(__file__).resolve().parent
REPO_ROOT = TOOL_ROOT.parents[1]
DEFAULT_ENV_PATHS = [TOOL_ROOT / ".env", REPO_ROOT / ".env"]


@dataclass(frozen=True)
class Credentials:
    """通义听悟调用所需的最小凭据集合。

    access_key_id / access_key_secret 用来通过阿里云 OpenAPI 鉴权；
    app_key 是通义听悟应用本身的标识。三者缺一不可。
    """

    access_key_id: str
    access_key_secret: str
    app_key: str


def resolve_credentials() -> Credentials:
    """自动查找凭据，避免用户每次都在命令行传密钥。

    查找顺序：
    1. 当前 shell 环境变量。
    2. 工具目录 .env。
    3. 仓库根目录 .env。

    工具不会打印密钥，也不会把密钥写入输出 JSON。
    """
    env_values = load_env_values(DEFAULT_ENV_PATHS)
    env_credentials = credentials_from_mapping(env_values)
    if env_credentials:
        return env_credentials

    raise ValueError(
        "No Tingwu credentials found. Set TINGWU_ACCESS_KEY_ID, TINGWU_ACCESS_KEY_SECRET, "
        "and TINGWU_APP_KEY in environment, tool .env, or repository .env."
    )


def load_env_values(paths: list[Path]) -> dict[str, str]:
    """合并 shell 环境变量和可选的 .env 文件。

    已存在的 shell 环境变量优先级高于 .env。这样可以在终端里临时覆盖
    凭据，而不需要修改文件。
    """
    values = dict(os.environ)
    for path in paths:
        if not path.exists():
            continue
        for key, value in parse_env_file(path).items():
            values.setdefault(key, value)
    return values


def parse_env_file(path: Path) -> dict[str, str]:
    """解析简单的 KEY=VALUE 形式 .env 文件。"""
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


def credentials_from_mapping(values: dict[str, str]) -> Credentials | None:
    """从环境变量字典中提取通义听悟凭据。

    values 通常来自 load_env_values()，也就是“当前 shell 环境变量 +
    工具目录 .env + 仓库根目录 .env”的合并结果。

    这里保留 ALIBABA_CLOUD_ACCESS_KEY_ID / SECRET，是为了兼容阿里云
    SDK 文档中常见的环境变量命名；AppKey 没有通用阿里云变量名，所以
    只读取本工具明确约定的 TINGWU_APP_KEY。
    """
    access_key_id = first_present(values, ["TINGWU_ACCESS_KEY_ID", "ALIBABA_CLOUD_ACCESS_KEY_ID"])
    access_key_secret = first_present(
        values,
        ["TINGWU_ACCESS_KEY_SECRET", "ALIBABA_CLOUD_ACCESS_KEY_SECRET"],
    )
    app_key = first_present(values, ["TINGWU_APP_KEY"])
    if access_key_id and access_key_secret and app_key:
        return Credentials(access_key_id=access_key_id, access_key_secret=access_key_secret, app_key=app_key)
    return None


def first_present(row: dict[str, str], names: list[str]) -> str:
    """按候选 key 顺序返回第一个非空字符串。

    这个小函数用于表达“优先读取 A，缺失时再读取 B”的配置兼容规则。
    返回空字符串表示所有候选 key 都不存在或值为空白。
    """
    for name in names:
        value = (row.get(name) or "").strip()
        if value:
            return value
    return ""


def load_json(path: Path) -> Any:
    """读取 UTF-8 JSON 文件。

    通义听悟原始响应和本工具输出都固定使用 UTF-8，避免中文逐字稿在不同
    系统默认编码下出现乱码。
    """
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    """写出 UTF-8 JSON 文件，并自动创建父目录。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def default_raw_output_path(output: Path) -> Path:
    """根据最终 request 路径推导阿里云原始产物保存路径。

    例如 /tmp/pan-request.json 会生成 /tmp/pan-request.tingwu-raw.json。
    这样用户只需要指定 --output，也能在同一目录拿到“未后处理”的原始产物。
    """
    suffix = output.suffix or ".json"
    stem = output.stem if output.suffix else output.name
    return output.with_name(f"{stem}.tingwu-raw{suffix}")


def log_progress(message: str, *, quiet: bool = False) -> None:
    """向 stderr 输出进度日志，避免污染 stdout 的机器可读结果。"""
    if not quiet:
        print(f"[transcribe-media] {message}", file=sys.stderr, flush=True)


def download_json(url: str) -> Any:
    """下载通义听悟返回的远程 JSON 结果文件。"""
    with urllib.request.urlopen(url, timeout=60) as response:  # nosec: caller provides trusted Tingwu result URL
        return json.loads(response.read().decode("utf-8"))


def submit_tingwu_task(
    *,
    media_url: str,
    credentials: Credentials,
    endpoint: str,
    language: str,
    task_key: str,
    speaker_count: int | None,
) -> dict[str, Any]:
    """创建通义听悟离线转写任务。

    离线模式适用于已经有公网可访问音视频 URL 的场景。这个函数只负责
    提交任务并返回创建任务响应；是否等待任务完成由 command_transcribe()
    根据 --wait 决定。
    """
    try:
        from alibabacloud_tea_openapi import models as open_api_models
        from alibabacloud_tea_util import models as util_models
        from alibabacloud_tingwu20230930 import models as tingwu_models
        from alibabacloud_tingwu20230930.client import Client as TingwuClient
    except ImportError as exc:
        raise RuntimeError(
            "Tongyi Tingwu SDK is not installed. Install official SDK packages first: "
            "pip install alibabacloud-tingwu20230930 alibabacloud-tea-openapi alibabacloud-tea-util"
        ) from exc

    # 官方 SDK 通过 Config 注入 AccessKey，再由具体 request 携带 AppKey。
    # AccessKey 证明“谁在调用阿里云”，AppKey 证明“调用哪个听悟应用”。
    config = open_api_models.Config(
        access_key_id=credentials.access_key_id,
        access_key_secret=credentials.access_key_secret,
    )
    config.endpoint = endpoint
    client = TingwuClient(config)

    # Diarization 是说话人分离。课堂反思后续需要区分教师/学生，所以默认开启。
    diarization = make_model(tingwu_models, "CreateTaskRequestParametersTranscriptionDiarization", speaker_count=speaker_count)
    transcription = make_model(
        tingwu_models,
        "CreateTaskRequestParametersTranscription",
        diarization_enabled=True,
        diarization=diarization,
    )
    parameters = make_model(tingwu_models, "CreateTaskRequestParameters", transcription=transcription)
    input_payload = make_model(
        tingwu_models,
        "CreateTaskRequestInput",
        source_language=language,
        file_url=media_url,
        task_key=task_key,
    )
    request = make_model(
        tingwu_models,
        "CreateTaskRequest",
        app_key=credentials.app_key,
        type="offline",
        input=input_payload,
        parameters=parameters,
    )
    runtime = util_models.RuntimeOptions()

    # 不同版本的阿里云 SDK 方法名有差异；优先使用带 RuntimeOptions 的形式，
    # 如果旧版本没有这个方法，再回退到 create_task。
    try:
        response = client.create_task_with_options(request, {}, runtime)
    except (AttributeError, TypeError):
        try:
            response = client.create_task_with_options(request, runtime)
        except (AttributeError, TypeError):
            response = client.create_task(request)
    return tea_to_plain(response)


def create_realtime_task(
    *,
    credentials: Credentials,
    endpoint: str,
    region: str,
    language: str,
    task_key: str,
    audio_format: str,
    sample_rate: int,
    speaker_count: int | None,
    connect_timeout: int,
    read_timeout: int,
    api_retries: int,
    retry_sleep: int,
) -> dict[str, Any]:
    """创建通义听悟实时任务。

    这一步只是在服务端创建任务，还没有开始发送音频。这个接口返回值里
    最重要的是 MeetingJoinUrl，它就是后面 stream_pcm_realtime() 要连接
    的 WebSocket 地址。
    """
    body = {
        "AppKey": credentials.app_key,
        "Input": {
            "SourceLanguage": language,
            "Format": audio_format,
            "SampleRate": sample_rate,
            "TaskKey": task_key,
        },
        "Parameters": {
            "Transcription": {
                "DiarizationEnabled": True,
                "Diarization": {"SpeakerCount": speaker_count},
            }
        },
    }
    return call_realtime_task_api(
        credentials=credentials,
        endpoint=endpoint,
        region=region,
        body=body,
        connect_timeout=connect_timeout,
        read_timeout=read_timeout,
        api_retries=api_retries,
        retry_sleep=retry_sleep,
    )


def stop_realtime_task(
    *,
    credentials: Credentials,
    endpoint: str,
    region: str,
    task_id: str,
    connect_timeout: int,
    read_timeout: int,
    api_retries: int,
    retry_sleep: int,
) -> dict[str, Any]:
    """通知通义听悟实时任务已经结束。

    只关闭 WebSocket 不够。实时任务还需要通过 OpenAPI 的 operation=stop
    接口主动停止，避免任务在服务端继续保持活跃。
    """
    body = {
        "AppKey": credentials.app_key,
        "Input": {
            "TaskId": task_id,
        },
    }
    return call_realtime_task_api(
        credentials=credentials,
        endpoint=endpoint,
        region=region,
        body=body,
        operation="stop",
        connect_timeout=connect_timeout,
        read_timeout=read_timeout,
        api_retries=api_retries,
        retry_sleep=retry_sleep,
    )


def call_realtime_task_api(
    *,
    credentials: Credentials,
    endpoint: str,
    region: str,
    body: dict[str, Any],
    operation: str | None = None,
    connect_timeout: int = DEFAULT_CONNECT_TIMEOUT,
    read_timeout: int = DEFAULT_READ_TIMEOUT,
    api_retries: int = DEFAULT_API_RETRIES,
    retry_sleep: int = DEFAULT_RETRY_SLEEP,
) -> dict[str, Any]:
    """调用通义听悟实时任务 OpenAPI，并带上重试和较长超时。

    官方 SDK 默认连接超时可能偏短。这里把连接超时和读取超时做成可配置，
    并对创建/停止任务请求做重试，方便应对和诊断临时网络问题。
    """
    try:
        from aliyunsdkcore.auth.credentials import AccessKeyCredential
        from aliyunsdkcore.client import AcsClient
        from aliyunsdkcore.request import CommonRequest
    except ImportError as exc:
        raise RuntimeError(
            "Aliyun core SDK is not installed. Install it first: pip install aliyun-python-sdk-core"
        ) from exc

    aliyun_credentials = AccessKeyCredential(credentials.access_key_id, credentials.access_key_secret)
    client = AcsClient(region_id=region, credential=aliyun_credentials)
    request = CommonRequest()
    request.set_accept_format("json")
    request.set_domain(endpoint)
    request.set_version("2023-09-30")
    request.set_protocol_type("https")
    request.set_method("PUT")
    request.set_uri_pattern("/openapi/tingwu/v2/tasks")
    request.add_header("Content-Type", "application/json")
    request.add_query_param("type", "realtime")
    set_request_timeout(request, connect_timeout=connect_timeout, read_timeout=read_timeout)
    if operation:
        request.add_query_param("operation", operation)
    request.set_content(json.dumps(body, ensure_ascii=False).encode("utf-8"))
    last_error: Exception | None = None
    for attempt in range(1, max(api_retries, 1) + 1):
        try:
            response = client.do_action_with_exception(request)
            return json.loads(response.decode("utf-8") if isinstance(response, bytes) else response)
        except Exception as exc:  # noqa: BLE001 - SDK wraps connectivity errors in its own exception type.
            last_error = exc
            if attempt >= max(api_retries, 1):
                break
            time.sleep(retry_sleep)
    raise RuntimeError(
        "Tingwu realtime task API request failed after "
        f"{max(api_retries, 1)} attempt(s). endpoint={endpoint}, region={region}, "
        f"connect_timeout={connect_timeout}, read_timeout={read_timeout}. "
        "If this is a ConnectTimeout, check local network/proxy/VPN/firewall and try a longer "
        "--connect-timeout. Original error: "
        f"{last_error}"
    )


def set_request_timeout(request: Any, *, connect_timeout: int, read_timeout: int) -> None:
    """当 SDK 请求对象支持超时方法时，设置连接超时和读取超时。"""
    for method_name, value in [
        ("set_connect_timeout", connect_timeout),
        ("set_read_timeout", read_timeout),
    ]:
        method = getattr(request, method_name, None)
        if callable(method):
            method(value)


def get_tingwu_task_info(*, task_id: str, credentials: Credentials, endpoint: str) -> dict[str, Any]:
    """查询通义听悟离线任务状态和结果入口。

    轮询阶段会反复调用这个函数。任务完成后，transcribe 流程会从
    Body/body.Data.Result.Transcription 读取转写产物。
    """
    try:
        from alibabacloud_tea_openapi import models as open_api_models
        from alibabacloud_tea_util import models as util_models
        from alibabacloud_tingwu20230930 import models as tingwu_models
        from alibabacloud_tingwu20230930.client import Client as TingwuClient
    except ImportError as exc:
        raise RuntimeError(
            "Tongyi Tingwu SDK is not installed. Install official SDK packages first: "
            "pip install alibabacloud-tingwu20230930 alibabacloud-tea-openapi alibabacloud-tea-util"
        ) from exc

    config = open_api_models.Config(
        access_key_id=credentials.access_key_id,
        access_key_secret=credentials.access_key_secret,
    )
    config.endpoint = endpoint
    client = TingwuClient(config)
    runtime = util_models.RuntimeOptions()

    # 和创建任务一样，兼容新旧 SDK 的方法名差异。
    try:
        response = client.get_task_info_with_options(task_id, {}, runtime)
    except (AttributeError, TypeError):
        try:
            response = client.get_task_info_with_options(task_id, runtime)
        except (AttributeError, TypeError):
            request = make_model(tingwu_models, "GetTaskInfoRequest", task_id=task_id)
            response = client.get_task_info(request)
    return tea_to_plain(response)


def make_model(models_module: Any, class_name: str, **kwargs: Any) -> Any:
    """安全构造阿里云 SDK 的 model 对象。

    阿里云 Python SDK 的 request/model 类名较长，而且不同版本对可选字段
    的处理不完全一致。这里集中做两件事：
    1. 找不到 SDK 类时给出明确错误。
    2. 过滤 None，避免把没有设置的可选参数传进 SDK。
    """
    cls = getattr(models_module, class_name, None)
    if cls is None:
        raise RuntimeError(f"Tongyi Tingwu SDK model not found: {class_name}.")
    clean_kwargs = {key: value for key, value in kwargs.items() if value is not None}
    return cls(**clean_kwargs)


def tea_to_plain(value: Any) -> Any:
    """把 Tea SDK 对象递归转换成普通 Python dict/list。

    阿里云 Tea SDK 返回值通常不是原生 dict，而是带 to_map()/to_dict()
    方法的对象。后续保存 raw-dir、搜索 TaskId、提取结果都需要普通结构。
    """
    if hasattr(value, "to_map"):
        return value.to_map()
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, dict):
        return {key: tea_to_plain(item) for key, item in value.items()}
    if isinstance(value, list):
        return [tea_to_plain(item) for item in value]
    if hasattr(value, "__dict__"):
        return {key: tea_to_plain(item) for key, item in vars(value).items() if not key.startswith("_")}
    return value


def poll_until_complete(
    *,
    task_id: str,
    credentials: Credentials,
    endpoint: str,
    interval: int,
    timeout: int,
) -> dict[str, Any]:
    """轮询离线任务直到完成、失败或超时。

    --wait 模式才会走到这里。未完成时按 interval 睡眠；失败状态立即抛错；
    超过 timeout 后抛 TimeoutError，并带上最后一次任务信息方便排查。
    """
    deadline = time.time() + timeout
    last_info: dict[str, Any] = {}
    while time.time() < deadline:
        last_info = get_tingwu_task_info(task_id=task_id, credentials=credentials, endpoint=endpoint)
        status = find_first_value(last_info, ["TaskStatus", "taskStatus", "Status", "status"])
        # 听悟不同接口/版本可能返回不同状态字段名和状态值，所以这里做宽松匹配。
        if str(status).upper() in {"COMPLETED", "SUCCESS", "SUCCEEDED"}:
            return last_info
        if str(status).upper() in {"FAILED", "ERROR"}:
            raise RuntimeError(f"Tongyi Tingwu task failed: {json.dumps(last_info, ensure_ascii=False)}")
        time.sleep(interval)
    raise TimeoutError(f"Tongyi Tingwu task did not complete in {timeout} seconds. Last info: {last_info}")


def task_id_from_create_response(response: dict[str, Any]) -> str:
    """从创建任务响应中提取 TaskId。

    后续查询、停止任务都依赖 TaskId；如果响应结构异常，尽早失败比继续
    传空值更容易定位问题。
    """
    task_id = find_first_value(response, ["TaskId", "TaskID", "taskId", "task_id"])
    if not task_id:
        raise ValueError(f"Could not find TaskId in CreateTask response: {json.dumps(response, ensure_ascii=False)}")
    return str(task_id)


def transcription_result_from_task_info(info: dict[str, Any]) -> Any:
    """从 GetTaskInfo 响应中按官方固定结构取出转写结果。

    Tea SDK 的响应外壳可能是 Body，也可能经 to_map() 转成 body；内部
    Data.Result.Transcription 仍按通义听悟 GetTaskInfo 结构读取。
    """
    result = first_path(
        info,
        [
            ["Body", "Data", "Result", "Transcription"],
            ["body", "Data", "Result", "Transcription"],
        ],
    )
    if isinstance(result, str) and result.startswith(("http://", "https://")):
        return download_json(result)
    if result:
        return result
    raise ValueError("Could not find Body/body.Data.Result.Transcription in GetTaskInfo response.")


def first_path(payload: Any, paths: list[list[str]]) -> Any:
    """按候选路径读取嵌套 dict，返回第一个非空值。"""
    for path in paths:
        value = get_path(payload, path)
        if value not in (None, ""):
            return value
    return None


def get_path(payload: Any, path: list[str]) -> Any:
    """按路径读取嵌套 dict，路径不存在时返回 None。"""
    current = payload
    for part in path:
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def find_first_value(payload: Any, keys: list[str]) -> Any:
    """在任意嵌套 dict/list 中递归查找第一个非空字段值。

    用在 TaskId、状态字段、MeetingJoinUrl 等位置。这样可以减少对听悟
    响应具体嵌套层级的依赖。
    """
    if isinstance(payload, dict):
        for key in keys:
            if key in payload and payload[key] not in (None, ""):
                return payload[key]
        for value in payload.values():
            found = find_first_value(value, keys)
            if found not in (None, ""):
                return found
    elif isinstance(payload, list):
        for item in payload:
            found = find_first_value(item, keys)
            if found not in (None, ""):
                return found
    return None


def convert_tingwu_to_request(
    raw: Any,
    *,
    teacher_speaker: str | None,
    student_speaker: str | None,
    time_unit: str,
    media_url: str | None = None,
    media_file: str | None = None,
    default_speaker: str = "教师",
) -> dict[str, Any]:
    """把通义听悟结果转换成 classroom-reflection-skill 的 request JSON。

    这里不再写入 topic/subject/grade。媒体工具只负责“媒体转写 -> 标准
    transcription[]”，课题和学科信息如果需要，应由后续课堂反思流程补充
    或推断。
    """
    transcription_payload = unwrap_transcription_payload(raw)
    sentence_items = find_sentences(transcription_payload)
    if not sentence_items:
        raise ValueError("No sentence list found in Tingwu transcription result.")

    # 先建立“通义听悟原始说话人编号 -> 教师/学生”的映射。
    # 用户显式传 --teacher-speaker / --student-speaker 时会优先使用显式映射；
    # 否则使用 build_speaker_map() 的启发式规则。
    mapped_speakers = build_speaker_map(sentence_items, teacher_speaker, student_speaker, time_unit)
    rows: list[dict[str, Any]] = []
    for index, item in enumerate(sentence_items, start=1):
        # 兼容离线/实时/不同 SDK 版本可能出现的字段命名差异。
        content = sentence_text(item)
        if not content:
            continue
        raw_speaker = str(
            first_field(item, ["SpeakerId", "speakerId", "speaker_id", "Speaker", "speaker", "ChannelId", "channelId"])
            or ""
        )
        start = sentence_start_time(item, time_unit)
        end = sentence_end_time(item, time_unit)
        if end <= start:
            # 有些实时事件可能缺少结束时间，或者结束时间等于开始时间。
            # 后续 reflection skill 需要合法时间段，所以按文本长度估一个保守值。
            end = start + max(len(content) / 6.0, 1.0)
        speaker = mapped_speakers.get(raw_speaker)
        if not speaker:
            speaker = infer_speaker_from_content(content, default_speaker)
        rows.append(
            {
                "id": len(rows) + 1,
                "speaker": speaker,
                "speakerRaw": raw_speaker or None,
                "start": round(start, 3),
                "end": round(end, 3),
                "content": content,
            }
        )

    if not rows:
        sample_keys = sorted({key for item in sentence_items[:5] for key in item.keys()})
        raise ValueError(
            "Tingwu transcription result contained sentence-like items, but none had readable text. "
            f"Sample item keys: {sample_keys}"
        )

    request: dict[str, Any] = {
        "transcriptionProvider": "tongyi-tingwu",
        "mediaUrl": media_url,
        "mediaFile": media_file,
        "transcription": rows,
    }
    # 去掉空的 mediaUrl/mediaFile，保持输出 JSON 简洁。
    return {key: value for key, value in request.items() if value not in (None, "")}


def unwrap_transcription_payload(raw: Any) -> Any:
    """剥离听悟响应外层包装，尽量定位到 Transcription 对象本身。

    convert 命令可能收到完整 GetTaskInfo 响应，也可能收到已经抽取好的
    Transcription JSON。这个函数负责把这些输入统一到后续 find_sentences()
    能继续处理的结构。
    """
    if isinstance(raw, str):
        raw = json.loads(raw)
    for path in [
        ["Data", "Result", "Transcription"],
        ["data", "result", "transcription"],
        ["Result", "Transcription"],
        ["result", "transcription"],
        ["Transcription"],
        ["transcription"],
    ]:
        value = get_path(raw, path)
        if value:
            return value
    return raw


def find_sentences(payload: Any) -> list[dict[str, Any]]:
    """从任意嵌套结构中寻找句子列表。

    通义听悟不同模式下句子字段可能叫 Sentences、sentences、
    SentenceList 等。这里递归查找，降低对单一响应格式的依赖。
    """
    if isinstance(payload, dict):
        for key in ["Sentences", "sentences", "SentenceList", "sentenceList", "SentenceResults", "sentenceResults"]:
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        for value in payload.values():
            sentences = find_sentences(value)
            if sentences:
                return sentences
    if isinstance(payload, list):
        if all(isinstance(item, dict) for item in payload):
            return payload
        for item in payload:
            sentences = find_sentences(item)
            if sentences:
                return sentences
    return []


def first_field(item: dict[str, Any], names: list[str]) -> Any:
    """从一句转写结果中按候选字段名取第一个存在的值。"""
    for name in names:
        if name in item:
            return item[name]
    return None


def sentence_text(item: dict[str, Any]) -> str:
    """提取句子/段落文本，兼容 Text 字段和 Words 词级列表。"""
    direct = first_field(
        item,
        [
            "Text",
            "text",
            "Content",
            "content",
            "Sentence",
            "sentence",
            "SentenceText",
            "sentenceText",
            "Transcript",
            "transcript",
        ],
    )
    if direct not in (None, ""):
        return str(direct).strip()

    words = first_field(item, ["Words", "words", "WordList", "wordList"])
    if not isinstance(words, list):
        return ""
    pieces: list[str] = []
    for word in words:
        if isinstance(word, dict):
            text = first_field(word, ["Text", "text", "Word", "word", "Content", "content"])
        else:
            text = word
        if text not in (None, ""):
            pieces.append(str(text).strip())
    return "".join(pieces).strip()


def sentence_start_time(item: dict[str, Any], time_unit: str) -> float:
    direct = first_field(item, ["BeginTime", "beginTime", "StartTime", "startTime", "Start", "start"])
    if direct not in (None, ""):
        return parse_time(direct, time_unit)
    words = first_field(item, ["Words", "words", "WordList", "wordList"])
    if isinstance(words, list):
        for word in words:
            if isinstance(word, dict):
                value = first_field(word, ["BeginTime", "beginTime", "StartTime", "startTime", "Start", "start"])
                if value not in (None, ""):
                    return parse_time(value, time_unit)
    return 0.0


def sentence_end_time(item: dict[str, Any], time_unit: str) -> float:
    direct = first_field(item, ["EndTime", "endTime", "End", "end"])
    if direct not in (None, ""):
        return parse_time(direct, time_unit)
    words = first_field(item, ["Words", "words", "WordList", "wordList"])
    if isinstance(words, list):
        for word in reversed(words):
            if isinstance(word, dict):
                value = first_field(word, ["EndTime", "endTime", "End", "end"])
                if value not in (None, ""):
                    return parse_time(value, time_unit)
    return 0.0


def parse_time(value: Any, time_unit: str) -> float:
    """把听悟时间戳统一转换成秒。

    支持三类输入：
    - 空值：返回 0。
    - 形如 00:01:23.4 的时间字符串。
    - 数字时间戳，根据 --time-unit 判断是毫秒还是秒。
    """
    if value is None or value == "":
        return 0.0
    if isinstance(value, str) and ":" in value:
        parts = [float(part) for part in value.split(":")]
        total = 0.0
        for part in parts:
            total = total * 60 + part
        return total
    number = float(value)
    if time_unit == "ms":
        return number / 1000.0
    return number


def build_speaker_map(
    sentence_items: list[dict[str, Any]],
    teacher_speaker: str | None,
    student_speaker: str | None,
    time_unit: str,
) -> dict[str, str]:
    """建立听悟原始说话人到“教师/学生”的映射。

    优先级：
    1. 用户显式传入 teacher_speaker / student_speaker。
    2. 如果没有显式映射，就按启发式给每个说话人打分。

    启发式假设：教师通常发言更长、问题更多、课堂指令词更多。因此用
    发言时长 + 问号加分 + 指令词加分排序，最高者标为教师，第二名标为学生。
    """
    mapping: dict[str, str] = {}
    if teacher_speaker:
        mapping[str(teacher_speaker)] = "教师"
    if student_speaker:
        mapping[str(student_speaker)] = "学生"
    if teacher_speaker or student_speaker:
        return mapping

    scores: dict[str, float] = {}
    for item in sentence_items:
        speaker = str(first_field(item, ["SpeakerId", "speakerId", "Speaker", "speaker", "ChannelId", "channelId"]) or "")
        if not speaker:
            continue
        text = sentence_text(item)
        start = sentence_start_time(item, time_unit)
        end = sentence_end_time(item, time_unit)
        duration = max(end - start, 0.0)
        # 问句和课堂指令词不一定完全可靠，只作为辅助加分，不直接覆盖显式映射。
        question_bonus = 8.0 if any(mark in text for mark in ["？", "?"]) else 0.0
        instruction_bonus = 4.0 if any(word in text for word in ["同学", "请", "观察", "思考", "回答", "讨论"]) else 0.0
        scores[speaker] = scores.get(speaker, 0.0) + duration + question_bonus + instruction_bonus

    if not scores:
        return mapping
    ranked = sorted(scores, key=scores.get, reverse=True)
    mapping[ranked[0]] = "教师"
    if len(ranked) > 1:
        mapping[ranked[1]] = "学生"
    return mapping


def infer_speaker_from_content(content: str, default_speaker: str) -> str:
    """通义听悟没有返回说话人编号时，用这个函数兜底标注 speaker。

    课堂分析脚本会拒绝所有行都是 speaker=其他 的输入。为了快速跑通流程，
    默认标为“教师”可以让后续 skill 至少拿到可分析文本。用户如果想更保守，
    可以传 --default-speaker 其他。
    """
    if default_speaker != "其他":
        return default_speaker
    if any(mark in content for mark in ["？", "?"]):
        return "教师"
    if any(word in content for word in ["同学", "请", "观察", "思考", "回答", "讨论", "我们来看", "谁来说"]):
        return "教师"
    if len(content) <= 18 and any(word in content for word in ["我", "是", "不是", "因为", "发现", "觉得"]):
        return "学生"
    return "其他"


def extract_pcm_audio(media_file: Path, pcm_path: Path, *, sample_rate: int, ffmpeg_bin: str) -> None:
    """把本地视频/音频抽取成实时 API 需要的原始 PCM 音频。

    - -vn 表示去掉视频，只保留音频。
    - -ac 1 表示转成单声道。
    - -ar 16000 表示重采样到 16 kHz。
    - -f s16le 表示输出 16 位小端原始 PCM 字节。

    原始 PCM 没有文件头，文件里只有音频字节。因此后面发送
    StartTranscription 时，必须额外告诉通义听悟音频格式和采样率。
    """
    pcm_path.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [
            ffmpeg_bin,
            "-y",
            "-i",
            str(media_file),
            "-vn",
            "-ac",
            "1",
            "-ar",
            str(sample_rate),
            "-f",
            "s16le",
            str(pcm_path),
        ],
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        detail = proc.stderr.strip().splitlines()[-5:]
        raise RuntimeError("ffmpeg failed to extract PCM audio: " + "\n".join(detail))


def stream_pcm_realtime(
    *,
    meeting_join_url: str,
    task_id: str,
    app_key: str,
    pcm_path: Path,
    audio_format: str,
    sample_rate: int,
    chunk_ms: int,
    realtime_pace: bool,
    receive_timeout: int,
    progress_interval: int,
    quiet: bool,
) -> list[dict[str, Any]]:
    """通过 WebSocket 向通义听悟推送 PCM 字节，并收集返回事件。

    这个 WebSocket 里会传两类数据：
    - JSON 控制消息，例如 StartTranscription 和 StopTranscription。
    - 从 PCM 文件读取出来的二进制音频块。

    返回的 events 是通义听悟的 JSON 消息，后面会交给
    realtime_events_to_transcription() 统一整理。
    """
    try:
        import websocket
        from websocket import WebSocketTimeoutException
    except ImportError as exc:
        raise RuntimeError("websocket-client is not installed. Install it first: pip install websocket-client") from exc

    events: list[dict[str, Any]] = []

    # chunk_ms 控制每个 WebSocket 二进制帧里放多少音频。
    # 对 16 kHz 16 位单声道 PCM 来说，100ms 音频就是 16000 * 2 * 0.1 = 3200 字节。
    chunk_bytes = max(int(sample_rate * 2 * chunk_ms / 1000), 2)
    total_bytes = pcm_path.stat().st_size
    total_seconds = total_bytes / max(sample_rate * 2, 1)
    sent_bytes = 0
    last_progress = 0.0
    log_progress("connecting websocket and starting transcription", quiet=quiet)
    ws = websocket.create_connection(meeting_join_url, timeout=10)
    try:
        start_message = transcription_control_message(
            app_key=app_key,
            task_id=task_id,
            name="StartTranscription",
            payload={
                "format": audio_format,
                "sample_rate": sample_rate,
                "enable_intermediate_result": False,
                "enable_punctuation_prediction": True,
                "enable_inverse_text_normalization": True,
            },
        )

        # 先告诉通义听悟：后面的二进制帧是要转写的音频。
        # 如果没有这条 JSON 控制消息，服务端不会把二进制 WebSocket 帧当语音处理。
        ws.send(json.dumps(start_message, ensure_ascii=False))
        drain_websocket_events(ws, events, until_names={"TranscriptionStarted"}, timeout=receive_timeout)
        log_progress("websocket transcription started", quiet=quiet)

        with pcm_path.open("rb") as handle:
            while True:
                chunk = handle.read(chunk_bytes)
                if not chunk:
                    break

                # 真正上传音频发生在这里。每个 chunk 都是原始 PCM 字节，
                # 不是 JSON，也不是 base64。
                ws.send_binary(chunk)
                sent_bytes += len(chunk)
                drain_websocket_events(ws, events, timeout=0.05)
                now = time.time()
                if now - last_progress >= progress_interval or sent_bytes >= total_bytes:
                    sent_seconds = sent_bytes / max(sample_rate * 2, 1)
                    percent = sent_bytes / total_bytes * 100 if total_bytes else 100.0
                    event_count = len(events)
                    log_progress(
                        f"streamed {sent_seconds:.1f}s / {total_seconds:.1f}s audio ({percent:.1f}%), "
                        f"events={event_count}",
                        quiet=quiet,
                    )
                    last_progress = now
                if realtime_pace:
                    # 实时 API 本来面向现场采集音频。这里 sleep 是为了让本地文件
                    # 推送速度接近真实播放速度。
                    time.sleep(chunk_ms / 1000.0)

        log_progress("audio stream sent; waiting for transcription completion", quiet=quiet)
        stop_message = transcription_control_message(app_key=app_key, task_id=task_id, name="StopTranscription")

        # StopTranscription 用来结束 WebSocket 内部的语音流。
        # 后面仍会调用 stop_realtime_task()，关闭服务端实时任务本身。
        ws.send(json.dumps(stop_message, ensure_ascii=False))
        drain_websocket_events(ws, events, until_names={"TranscriptionCompleted", "TaskFailed"}, timeout=receive_timeout)
        log_progress(f"transcription completed; events={len(events)}", quiet=quiet)
    except WebSocketTimeoutException:
        raise RuntimeError("Timed out while waiting for Tingwu realtime transcription events.")
    finally:
        ws.close()
    return events


def transcription_control_message(
    *,
    app_key: str,
    task_id: str,
    name: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """构造通义听悟 WebSocket 需要的 JSON 控制消息。"""
    message: dict[str, Any] = {
        "header": {
            "message_id": uuid4().hex,
            "task_id": task_id,
            "namespace": "SpeechTranscriber",
            "name": name,
            "appkey": app_key,
        }
    }
    if payload is not None:
        message["payload"] = payload
    return message


def drain_websocket_events(
    ws: Any,
    events: list[dict[str, Any]],
    *,
    until_names: set[str] | None = None,
    timeout: float,
) -> None:
    """读取 WebSocket 当前可用消息，并把 JSON 事件追加到 events。

    如果传入 until_names，就会最多等待 timeout 秒，直到收到指定事件名，
    例如 TranscriptionStarted 或 TranscriptionCompleted。
    如果没有传 until_names，这个函数只做一次短暂的非阻塞读取，避免音频
    上传期间因为等待消息而卡住进度输出。
    """
    import websocket

    deadline = time.time() + timeout
    ws.settimeout(min(max(timeout, 0.01), 1.0))
    while time.time() < deadline:
        try:
            message = ws.recv()
        except websocket.WebSocketTimeoutException:
            if until_names:
                continue
            return
        if isinstance(message, bytes):
            continue
        try:
            event = json.loads(message)
        except json.JSONDecodeError:
            continue
        events.append(event)
        name = str(get_path(event, ["header", "name"]) or "")
        status = get_path(event, ["header", "status"])
        if name == "TaskFailed" or (isinstance(status, int) and status >= 40000000):
            raise RuntimeError(f"Tingwu realtime task failed: {json.dumps(event, ensure_ascii=False)}")
        if until_names and name in until_names:
            return


def realtime_events_to_transcription(events: list[dict[str, Any]]) -> dict[str, Any]:
    """把实时 WebSocket 事件转换成类似离线结果的 Sentences 列表。

    通义听悟实时消息是一条条事件，例如 SentenceBegin、SentenceEnd、
    TranscriptionResultChanged。后续转换函数已经能处理 Sentences 列表，
    所以这里先把实时事件整理成这个更简单的结构。
    """
    sentences: dict[int, dict[str, Any]] = {}
    for event in events:
        name = str(get_path(event, ["header", "name"]) or "")
        payload = get_path(event, ["payload"]) or {}
        if not isinstance(payload, dict):
            continue
        index = payload.get("index")
        if index is None:
            continue
        try:
            sentence_index = int(index)
        except (TypeError, ValueError):
            continue
        sentence = sentences.setdefault(sentence_index, {"Index": sentence_index})
        if name == "SentenceBegin":
            sentence["BeginTime"] = payload.get("time", sentence.get("BeginTime", 0))
        elif name in {"TranscriptionResultChanged", "SentenceEnd"}:
            text = payload.get("result")
            if text:
                sentence["Text"] = text
            if "begin_time" in payload:
                sentence["BeginTime"] = payload["begin_time"]
            elif "beginTime" in payload:
                sentence["BeginTime"] = payload["beginTime"]
            if "time" in payload:
                sentence["EndTime"] = payload["time"]
            elif "currentTime" in payload:
                sentence["EndTime"] = payload["currentTime"]
            speaker = payload.get("speaker_id") or payload.get("speakerId") or payload.get("SpeakerId")
            if speaker:
                sentence["SpeakerId"] = speaker

    ordered = []
    for sentence in sorted(sentences.values(), key=lambda item: int(item.get("Index", 0))):
        if sentence.get("Text"):
            sentence.setdefault("BeginTime", 0)
            sentence.setdefault("EndTime", sentence["BeginTime"])
            ordered.append(sentence)
    return {"Sentences": ordered}


def command_convert(args: argparse.Namespace) -> None:
    """convert 子命令入口：只做本地 JSON 格式转换，不调用通义听悟 API。"""
    raw = load_json(args.tingwu_result)
    request = convert_tingwu_to_request(
        raw,
        teacher_speaker=args.teacher_speaker,
        student_speaker=args.student_speaker,
        time_unit=args.time_unit,
        media_url=args.media_url,
        default_speaker=args.default_speaker,
    )
    write_json(args.output, request)
    print(str(args.output))


def command_transcribe(args: argparse.Namespace) -> None:
    """transcribe 子命令入口：提交公网 URL 的离线转写任务。"""
    credentials = resolve_credentials()
    task_key = args.task_key or f"classroom-reflection-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    create_response = submit_tingwu_task(
        media_url=args.media_url,
        credentials=credentials,
        endpoint=args.endpoint,
        language=args.language,
        task_key=task_key,
        speaker_count=args.speaker_count,
    )
    raw_dir = args.raw_dir
    if raw_dir:
        write_json(raw_dir / "tingwu-create-task.json", create_response)
    task_id = task_id_from_create_response(create_response)
    if not args.wait:
        # 不加 --wait 时只打印 task_id，调用方可以稍后自己查询任务。
        # 这种模式适合长视频或不希望当前命令阻塞的场景。
        print(task_id)
        return

    # 加 --wait 时，命令会一直等到听悟任务完成，再生成下游 request JSON。
    task_info = poll_until_complete(
        task_id=task_id,
        credentials=credentials,
        endpoint=args.endpoint,
        interval=args.poll_interval,
        timeout=args.timeout,
    )
    if raw_dir:
        write_json(raw_dir / "tingwu-task-info.json", task_info)
    transcription = transcription_result_from_task_info(task_info)
    if raw_dir:
        write_json(raw_dir / "tingwu-transcription-raw.json", transcription)
    raw_output = args.raw_output or default_raw_output_path(args.output)
    write_json(raw_output, transcription)
    request = convert_tingwu_to_request(
        transcription,
        teacher_speaker=args.teacher_speaker,
        student_speaker=args.student_speaker,
        time_unit=args.time_unit,
        media_url=args.media_url,
        default_speaker=args.default_speaker,
    )
    write_json(args.output, request)
    print(str(args.output))


def command_transcribe_realtime(args: argparse.Namespace) -> None:
    """本地视频/音频实时转写命令的入口函数。"""
    log_progress("resolving credentials", quiet=args.quiet)
    credentials = resolve_credentials()
    task_key = args.task_key or f"classroom-reflection-realtime-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    raw_dir = args.raw_dir
    if raw_dir:
        raw_dir.mkdir(parents=True, exist_ok=True)

    with TemporaryDirectory() as tmp:
        # 默认把 PCM 写进临时目录，命令结束后自动删除。
        # 只有用户传 --keep-pcm + --raw-dir 或显式 --pcm-output 时才保留。
        pcm_path = args.pcm_output or (raw_dir / "audio-16k.pcm" if raw_dir and args.keep_pcm else Path(tmp) / "audio-16k.pcm")
        log_progress(f"extracting audio with ffmpeg: {args.media_file}", quiet=args.quiet)
        extract_pcm_audio(args.media_file, pcm_path, sample_rate=args.sample_rate, ffmpeg_bin=args.ffmpeg_bin)
        pcm_size = pcm_path.stat().st_size
        pcm_seconds = pcm_size / max(args.sample_rate * 2, 1)
        log_progress(f"audio extracted: {pcm_seconds:.1f}s pcm, {pcm_size} bytes", quiet=args.quiet)
        log_progress("creating Tingwu realtime task", quiet=args.quiet)
        create_response = create_realtime_task(
            credentials=credentials,
            endpoint=args.endpoint,
            region=args.region,
            language=args.language,
            task_key=task_key,
            audio_format=args.audio_format,
            sample_rate=args.sample_rate,
            speaker_count=args.speaker_count,
            connect_timeout=args.connect_timeout,
            read_timeout=args.read_timeout,
            api_retries=args.api_retries,
            retry_sleep=args.retry_sleep,
        )
        if raw_dir:
            write_json(raw_dir / "tingwu-realtime-create-task.json", create_response)
        task_id = task_id_from_create_response(create_response)
        log_progress(f"Tingwu realtime task created: task_id={task_id}", quiet=args.quiet)
        meeting_join_url = find_first_value(create_response, ["MeetingJoinUrl", "meetingJoinUrl"])
        if not meeting_join_url:
            raise ValueError(f"Could not find MeetingJoinUrl in response: {json.dumps(create_response, ensure_ascii=False)}")

        stop_response: dict[str, Any] | None = None
        try:
            events = stream_pcm_realtime(
                meeting_join_url=str(meeting_join_url),
                task_id=task_id,
                app_key=credentials.app_key,
                pcm_path=pcm_path,
                audio_format=args.audio_format,
                sample_rate=args.sample_rate,
                chunk_ms=args.chunk_ms,
                realtime_pace=not args.fast,
                receive_timeout=args.receive_timeout,
                progress_interval=args.progress_interval,
                quiet=args.quiet,
            )
        finally:
            # 无论 WebSocket 推流是否抛错，都尽量通知服务端停止实时任务。
            # 这样可以减少服务端残留任务，也能把 stop 响应保存到 raw-dir 供排查。
            try:
                log_progress("stopping Tingwu realtime task", quiet=args.quiet)
                stop_response = stop_realtime_task(
                    credentials=credentials,
                    endpoint=args.endpoint,
                    region=args.region,
                    task_id=task_id,
                    connect_timeout=args.connect_timeout,
                    read_timeout=args.read_timeout,
                    api_retries=args.api_retries,
                    retry_sleep=args.retry_sleep,
                )
            except Exception as exc:  # noqa: BLE001 - preserve transcription output when stream succeeded.
                stop_response = {"warning": f"failed to stop realtime task cleanly: {exc}"}
                log_progress(stop_response["warning"], quiet=args.quiet)

        if raw_dir:
            write_json(raw_dir / "tingwu-realtime-events.json", events)
            write_json(raw_dir / "tingwu-realtime-stop-task.json", stop_response)
        raw_output = args.raw_output or default_raw_output_path(args.output)
        write_json(raw_output, events)
        transcription = realtime_events_to_transcription(events)
        log_progress(f"normalized realtime events into {len(transcription.get('Sentences', []))} sentence(s)", quiet=args.quiet)
        if raw_dir:
            write_json(raw_dir / "tingwu-realtime-transcription-normalized.json", transcription)
        request = convert_tingwu_to_request(
            transcription,
            teacher_speaker=args.teacher_speaker,
            student_speaker=args.student_speaker,
            time_unit="ms",
            media_file=str(args.media_file),
            default_speaker=args.default_speaker,
        )
        write_json(args.output, request)
        log_progress(f"wrote request JSON: {args.output}", quiet=args.quiet)
        print(str(args.output))


def build_parser() -> argparse.ArgumentParser:
    """定义命令行接口。

    三个子命令的职责保持分离：
    - convert：已有听悟 JSON -> request JSON。
    - transcribe：公网 URL -> 离线听悟任务 -> request JSON。
    - transcribe-realtime：本地媒体文件 -> PCM 推流 -> request JSON。
    """
    parser = argparse.ArgumentParser(description="Transcribe classroom media with Tongyi Tingwu and emit reflection request JSON.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    convert_parser = subparsers.add_parser("convert", help="Convert a saved Tingwu transcription JSON to reflection request JSON.")
    convert_parser.add_argument("--tingwu-result", required=True, type=Path, help="Tingwu transcription JSON or GetTaskInfo JSON.")
    add_common_output_args(convert_parser, include_media_url=True)
    convert_parser.set_defaults(func=command_convert)

    transcribe_parser = subparsers.add_parser("transcribe", help="Create and optionally wait for a Tongyi Tingwu offline transcription task.")
    transcribe_parser.add_argument("--media-url", required=True, help="Publicly reachable audio/video URL for Tingwu offline transcription.")
    transcribe_parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT, help=f"Tingwu OpenAPI endpoint. Default: {DEFAULT_ENDPOINT}.")
    transcribe_parser.add_argument("--language", default=DEFAULT_LANGUAGE, help=f"Source language. Default: {DEFAULT_LANGUAGE}.")
    transcribe_parser.add_argument("--task-key", help="Optional idempotency/business task key.")
    transcribe_parser.add_argument("--speaker-count", type=int, default=2, help="Expected speaker count for diarization. Default: 2.")
    transcribe_parser.add_argument("--wait", action="store_true", help="Poll GetTaskInfo and write output JSON when completed.")
    transcribe_parser.add_argument("--poll-interval", type=int, default=DEFAULT_POLL_INTERVAL, help="Polling interval in seconds.")
    transcribe_parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="Polling timeout in seconds.")
    transcribe_parser.add_argument("--raw-dir", type=Path, help="Optional directory for raw Tingwu responses.")
    transcribe_parser.add_argument(
        "--raw-output",
        type=Path,
        help="Path for the direct Tingwu transcription artifact before postprocessing. Defaults to <output-stem>.tingwu-raw.json.",
    )
    add_common_output_args(transcribe_parser, include_media_url=False)
    transcribe_parser.set_defaults(func=command_transcribe)

    realtime_parser = subparsers.add_parser("transcribe-realtime", help="Transcribe a local media file by streaming PCM audio to Tingwu realtime API.")
    realtime_parser.add_argument("--media-file", required=True, type=Path, help="Local audio/video file to stream after ffmpeg PCM extraction.")
    realtime_parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT, help=f"Tingwu OpenAPI endpoint. Default: {DEFAULT_ENDPOINT}.")
    realtime_parser.add_argument("--region", default=DEFAULT_REGION, help=f"Aliyun region for realtime task API. Default: {DEFAULT_REGION}.")
    realtime_parser.add_argument("--language", default=DEFAULT_LANGUAGE, help=f"Source language. Default: {DEFAULT_LANGUAGE}.")
    realtime_parser.add_argument("--task-key", help="Optional idempotency/business task key.")
    realtime_parser.add_argument("--speaker-count", type=int, default=2, help="Expected speaker count for diarization. Default: 2.")
    realtime_parser.add_argument("--audio-format", default=DEFAULT_AUDIO_FORMAT, choices=["pcm"], help="Realtime stream audio format. Default: pcm.")
    realtime_parser.add_argument("--sample-rate", type=int, default=DEFAULT_SAMPLE_RATE, choices=[8000, 16000], help="PCM sample rate. Default: 16000.")
    realtime_parser.add_argument("--chunk-ms", type=int, default=DEFAULT_CHUNK_MS, help="Audio frame duration in milliseconds. Default: 100.")
    realtime_parser.add_argument("--fast", action="store_true", help="Do not sleep between audio chunks. Useful only for quick experiments.")
    realtime_parser.add_argument("--receive-timeout", type=int, default=30, help="Seconds to wait for websocket start/complete events.")
    realtime_parser.add_argument("--progress-interval", type=int, default=DEFAULT_PROGRESS_INTERVAL, help=f"Seconds between realtime stream progress logs. Default: {DEFAULT_PROGRESS_INTERVAL}.")
    realtime_parser.add_argument("--quiet", action="store_true", help="Suppress progress logs on stderr.")
    realtime_parser.add_argument("--connect-timeout", type=int, default=DEFAULT_CONNECT_TIMEOUT, help=f"Realtime task API connect timeout in seconds. Default: {DEFAULT_CONNECT_TIMEOUT}.")
    realtime_parser.add_argument("--read-timeout", type=int, default=DEFAULT_READ_TIMEOUT, help=f"Realtime task API read timeout in seconds. Default: {DEFAULT_READ_TIMEOUT}.")
    realtime_parser.add_argument("--api-retries", type=int, default=DEFAULT_API_RETRIES, help=f"Realtime task API retry attempts. Default: {DEFAULT_API_RETRIES}.")
    realtime_parser.add_argument("--retry-sleep", type=int, default=DEFAULT_RETRY_SLEEP, help=f"Sleep seconds between API retries. Default: {DEFAULT_RETRY_SLEEP}.")
    realtime_parser.add_argument("--ffmpeg-bin", default="ffmpeg", help="ffmpeg executable path. Default: ffmpeg.")
    realtime_parser.add_argument("--raw-dir", type=Path, help="Optional directory for raw realtime responses and events.")
    realtime_parser.add_argument(
        "--raw-output",
        type=Path,
        help="Path for the direct Tingwu realtime events before postprocessing. Defaults to <output-stem>.tingwu-raw.json.",
    )
    realtime_parser.add_argument("--keep-pcm", action="store_true", help="Keep extracted PCM under --raw-dir.")
    realtime_parser.add_argument("--pcm-output", type=Path, help="Optional path for extracted PCM audio.")
    add_common_output_args(realtime_parser, include_media_url=False)
    realtime_parser.set_defaults(func=command_transcribe_realtime)

    return parser


def add_common_output_args(parser: argparse.ArgumentParser, *, include_media_url: bool) -> None:
    """给多个子命令添加共享输出和说话人映射参数。"""
    parser.add_argument("--output", required=True, type=Path, help="Output request JSON for classroom-reflection-skill.")
    if include_media_url:
        # convert 子命令允许用户额外记录原始媒体 URL，但不要求它存在。
        parser.add_argument("--media-url", help=argparse.SUPPRESS)
    parser.add_argument("--teacher-speaker", help="Raw Tingwu speaker id that should be mapped to 教师.")
    parser.add_argument("--student-speaker", help="Raw Tingwu speaker id that should be mapped to 学生.")
    parser.add_argument("--default-speaker", choices=["教师", "学生", "其他"], default="教师", help="Speaker label used when Tingwu result has no speaker id. Default: 教师.")
    parser.add_argument("--time-unit", choices=["ms", "s"], default="ms", help="Time unit in Tingwu sentence timestamps. Default: ms.")


def main(argv: list[str] | None = None) -> int:
    """CLI 总入口，返回 Unix 风格退出码。"""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except Exception as exc:  # noqa: BLE001 - CLI should return a concise actionable failure.
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
