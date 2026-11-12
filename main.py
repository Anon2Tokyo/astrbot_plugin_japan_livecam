import asyncio
import json
import re
import time
import urllib.request
from typing import Any

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.message_components import Image, Plain
from astrbot.api.star import Context, Star

LIVECAM_API_URL = "https://mini-tokyo.appspot.com/livecam"
CACHE_TTL_SECONDS = 300
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)

# Common Chinese / Japanese aliases mapping to Mini Tokyo 3D camera IDs
LOCATION_ALIASES: dict[str, str] = {
    "羽田": "Haneda-Airport-2",
    "羽田机场": "Haneda-Airport-2",
    "羽田空港": "Haneda-Airport-2",
    "成田": "Narita-Airport",
    "成田机场": "Narita-Airport",
    "成田空港": "Narita-Airport",
    "涩谷": "Shibuya-1",
    "涉谷": "Shibuya-1",
    "渋谷": "Shibuya-1",
    "新宿": "Shinjuku-1",
    "歌舞伎町": "Shinjuku-1",
    "西武新宿": "Seibu-Shinjuku",
    "秋叶原": "Akihabara-1",
    "秋葉原": "Akihabara-1",
    "东京": "Tokyo",
    "东京站": "Tokyo",
    "東京": "Tokyo",
    "東京駅": "Tokyo",
    "有乐町": "Yurakucho",
    "有楽町": "Yurakucho",
    "银座": "Yurakucho",
    "銀座": "Yurakucho",
    "新桥": "Shimbashi",
    "新橋": "Shimbashi",
    "汐留": "Shiodome-1",
    "彩虹桥": "Shijo-Mae",
    "彩虹大桥": "Shijo-Mae",
    "台场": "Odaiba-Kaihinkoen-1",
    "御台场": "Odaiba-Kaihinkoen-1",
    "お台場": "Odaiba-Kaihinkoen-1",
    "富士山": "Kawaguchiko",
    "河口湖": "Kawaguchiko",
    "江之电": "Shichirigahama-1",
    "江ノ電": "Shichirigahama-1",
    "七里滨": "Shichirigahama-1",
    "七里ヶ浜": "Shichirigahama-1",
    "镰仓": "Shichirigahama-1",
    "鎌倉": "Shichirigahama-1",
    "箱根": "Hakone-Yumoto",
    "箱根汤本": "Hakone-Yumoto",
    "神田": "Kanda",
    "两国": "Ryogoku",
    "両国": "Ryogoku",
    "日暮里": "Nippori",
    "田端": "Tabata",
    "新干线": "Tabata",
    "赤羽": "Akabane",
    "尾久": "Oku",
    "葛西": "Kasairinkaikoen",
    "葛西临海公园": "Kasairinkaikoen",
    "小田原": "Odawara",
    "二子玉川": "Futako-tamagawa",
    "武藏小杉": "Musashi-kosugi-2",
}


class JapanLiveCamPlugin(Star):
    """AstrBot plugin to fetch real-time live camera street view from Japan."""

    def __init__(self, context: Context) -> None:
        """Initialize plugin and camera cache.

        Args:
            context: AstrBot context instance.
        """
        super().__init__(context)
        self._cameras_cache: list[dict[str, Any]] = []
        self._last_fetch_time: float = 0

    async def _get_cameras(self) -> list[dict[str, Any]]:
        """Fetch live camera data from Mini Tokyo 3D API with TTL caching.

        Returns:
            List of camera dictionaries parsed from Mini Tokyo 3D API.
        """
        now = time.time()
        if self._cameras_cache and (now - self._last_fetch_time < CACHE_TTL_SECONDS):
            return self._cameras_cache

        def fetch_sync() -> list[dict[str, Any]]:
            request = urllib.request.Request(
                LIVECAM_API_URL, headers={"User-Agent": DEFAULT_USER_AGENT}
            )
            with urllib.request.urlopen(request, timeout=10) as response:
                return json.loads(response.read().decode("utf-8"))

        try:
            loop = asyncio.get_running_loop()
            data = await loop.run_in_executor(None, fetch_sync)
            self._cameras_cache = data
            self._last_fetch_time = now
            logger.info(f"[JapanLiveCam] Successfully cached {len(data)} live cameras.")
            return data
        except (
            urllib.error.URLError,
            TimeoutError,
            OSError,
            json.JSONDecodeError,
        ) as exc:
            logger.error(
                f"[JapanLiveCam] Failed to fetch cameras from {LIVECAM_API_URL}: {exc}"
            )
            return self._cameras_cache or []

    def _match_camera(
        self, query: str, cameras: list[dict[str, Any]]
    ) -> dict[str, Any] | None:
        """Match camera by user query text.

        Args:
            query: User search query string.
            cameras: List of available camera objects.

        Returns:
            Matched camera dictionary or None.
        """
        cleaned = re.sub(
            r"(想看看|看看|看下|目前|现在|的画面|画面|现场|监控|直播|视频|街景)",
            "",
            query,
        ).strip()
        if not cleaned:
            cleaned = query.strip()

        # Step 1: Check predefined aliases
        for alias_key, target_id in LOCATION_ALIASES.items():
            if alias_key in cleaned:
                for cam in cameras:
                    if cam.get("id") == target_id:
                        return cam

        # Step 2: Fuzzy match camera names across languages and keywords
        cleaned_lower = cleaned.lower()
        for cam in cameras:
            name_obj = cam.get("name", {})
            candidates = [
                name_obj.get("zh-Hans", ""),
                name_obj.get("zh-Hant", ""),
                name_obj.get("ja", ""),
                name_obj.get("en", ""),
                cam.get("keyword", ""),
                cam.get("id", ""),
            ]
            for candidate in candidates:
                candidate_str = str(candidate).lower()
                if candidate_str and (
                    cleaned_lower in candidate_str or candidate_str in cleaned_lower
                ):
                    return cam
        return None

    def _extract_video_id(self, cam: dict[str, Any]) -> str:
        """Extract YouTube video ID from iframe HTML or thumbnail URL.

        Args:
            cam: Camera dictionary.

        Returns:
            Extracted YouTube video ID string or empty string.
        """
        html = cam.get("html", "")
        match_html = re.search(r"embed/([a-zA-Z0-9_-]+)", html)
        if match_html:
            return match_html.group(1)

        thumb = cam.get("thumbnail", "")
        match_thumb = re.search(r"/vi/([a-zA-Z0-9_-]+)/", thumb)
        if match_thumb:
            return match_thumb.group(1)

        return ""

    async def _get_hd_image_url(self, cam: dict[str, Any]) -> str | None:
        """Resolve highest resolution available image URL (1080p -> 720p fallback).

        Args:
            cam: Camera dictionary.

        Returns:
            URL string of the highest resolution image available.
        """
        video_id = self._extract_video_id(cam)
        if not video_id:
            return cam.get("thumbnail")

        maxres_url = f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg"

        def check_maxres_sync() -> bool:
            try:
                request = urllib.request.Request(
                    maxres_url,
                    method="HEAD",
                    headers={"User-Agent": DEFAULT_USER_AGENT},
                )
                with urllib.request.urlopen(request, timeout=3) as resp:
                    return bool(resp.status == 200)
            except (urllib.error.URLError, TimeoutError, OSError):
                return False

        loop = asyncio.get_running_loop()
        has_maxres = await loop.run_in_executor(None, check_maxres_sync)
        if has_maxres:
            return maxres_url

        # Fallback to Mini Tokyo 3D provided 720p signed thumbnail or hq720
        return cam.get("thumbnail") or f"https://i.ytimg.com/vi/{video_id}/hq720.jpg"

    @filter.llm_tool(name="get_japan_livecam")
    async def get_japan_livecam(self, event: AstrMessageEvent, location: str) -> str:
        """Get real-time live camera street view from Japan (Tokyo, Haneda Airport, etc.).

        Args:
            location: The name of the city, airport or landmark (e.g. 羽田机场, 涩谷, 富士山).

        Returns:
            Execution summary text for the LLM.
        """
        cameras = await self._get_cameras()
        cam = self._match_camera(location, cameras)
        if not cam:
            return (
                f"未能找到与【{location}】相关的日本实时街景机位。常见地点包括："
                "羽田机场、成田机场、涩谷、新宿、秋叶原、东京站、彩虹大桥、富士山河口湖、江之电等。"
            )

        name_zh = (
            cam.get("name", {}).get("zh-Hans")
            or cam.get("name", {}).get("ja")
            or cam.get("id")
        )
        image_url = await self._get_hd_image_url(cam)
        mt3d_url = f"https://minitokyo3d.com/?selection={cam.get('id')}"

        msg_chain = [
            Plain(f"📷【{name_zh}】当前高清现场实况：\n"),
        ]
        if image_url:
            msg_chain.append(Image.fromURL(image_url))
        msg_chain.append(Plain(f"\n🌐 3D 视角查看：{mt3d_url}"))

        await event.send(event.chain_result(msg_chain))
        return f"已成功发送【{name_zh}】的高清现场画面及 3D 地图链接。"

    @filter.command("livecam")
    async def livecam_cmd(self, event: AstrMessageEvent, location: str = ""):
        """查看日本各地实时监控画面。用法: /livecam [地点]，例如 /livecam 羽田机场"""
        cameras = await self._get_cameras()
        if not location or location.strip() in ["list", "列表", "帮助", "help"]:
            categories = [
                "✈️ 机场航站：羽田机场、成田机场",
                "🏙️ 核心商圈：涩谷、新宿、秋叶原、东京站、有乐町、新桥",
                "🌉 景观胜地：彩虹大桥、御台场、葛西临海公园",
                "🗻 富士周边：富士山(河口湖)、江之电(七里滨)、箱根汤本",
            ]
            reply_text = (
                "【🇯🇵 日本实况街景 · 机位列表】\n"
                + "\n".join(categories)
                + "\n\n💡 指令用法：/livecam 羽田机场，或直接对机器人说“想看羽田机场的画面”"
            )
            yield event.plain_result(reply_text)
            return

        cam = self._match_camera(location, cameras)
        if not cam:
            yield event.plain_result(
                f"未找到与【{location}】匹配的机位，可发送 `/livecam` 查看可用地点列表。"
            )
            return

        name_zh = (
            cam.get("name", {}).get("zh-Hans")
            or cam.get("name", {}).get("ja")
            or cam.get("id")
        )
        image_url = await self._get_hd_image_url(cam)
        mt3d_url = f"https://minitokyo3d.com/?selection={cam.get('id')}"

        msg_chain = [
            Plain(f"📷【{name_zh}】当前高清现场实况：\n"),
        ]
        if image_url:
            msg_chain.append(Image.fromURL(image_url))
        msg_chain.append(Plain(f"\n🌐 3D 视角查看：{mt3d_url}"))

        yield event.chain_result(msg_chain)
