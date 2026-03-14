#!/usr/bin/env python3
"""Step 4: AssetFetcher

台本 JSON の image_keywords をもとに素材を取得し assets/manifest.json を生成する。

prefer_video=True のシーン:
  1. NASA 動画 (duration_sec <=4 → mobile サイズ / >=5 → 中画質)
  2. Pexels 動画
  3. NASA 静止画 (動画が取れなかった場合のフォールバック)
  4. Pexels 静止画

prefer_video=False のシーン:
  1. NASA 静止画
  2. 元記事画像 (source_url 指定時)
  3. Pexels 静止画

共通 fallback: StarField 背景

使い方:
    python scripts/step4_fetch_assets.py --script data/script_{id}.json
"""

import argparse
import json
import logging
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode, urljoin

import requests
from dotenv import load_dotenv
import os

PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")

logger = logging.getLogger(__name__)

NASA_SEARCH_BASE = "https://images-api.nasa.gov/search"
PEXELS_IMAGE_BASE = "https://api.pexels.com/v1/search"
PEXELS_VIDEO_BASE = "https://api.pexels.com/videos/search"
RATE_LIMIT_SLEEP = 5

_article_image_cache: dict[str, list[str]] = {}


# ---- NASA API ----

def build_nasa_search_url(keywords: list, media_type: str = "image", page: int = 1) -> str:
    query = " ".join(keywords)
    params = urlencode({"q": query, "media_type": media_type, "page": page})
    return f"{NASA_SEARCH_BASE}?{params}"


def parse_nasa_search_response(data: dict, pick_index: int = 0) -> Optional[str]:
    try:
        items = data["collection"]["items"]
        if not items:
            return None
        idx = min(pick_index, len(items) - 1)
        return items[idx]["href"]
    except (KeyError, IndexError):
        return None


def fetch_nasa_image_url(manifest_url: str, session: requests.Session) -> Optional[str]:
    try:
        resp = session.get(manifest_url, timeout=15)
        resp.raise_for_status()
        urls = resp.json()
        for suffix in ["~orig.jpg", "~large.jpg", "~medium.jpg", "~thumb.jpg"]:
            for url in urls:
                if url.endswith(suffix):
                    return url
        jpg_urls = [u for u in urls if u.lower().endswith(".jpg")]
        return jpg_urls[0] if jpg_urls else (urls[0] if urls else None)
    except Exception as e:
        logger.error(f"NASA 静止画マニフェスト取得失敗: {e}")
        return None


def fetch_nasa_video_url(manifest_url: str, session: requests.Session, duration_sec: int = 4) -> Optional[str]:
    """NASA アセットマニフェストから最適な動画 URL を取得する。

    サイズ選択ポリシー:
      duration_sec <= 4 → mobile サイズ優先（軽量・高速）
      duration_sec >= 5 → mobile を避け中画質を優先（品質重視）
    """
    try:
        resp = session.get(manifest_url, timeout=15)
        resp.raise_for_status()
        urls = resp.json()
        mp4_urls = [u for u in urls if u.lower().endswith(".mp4")]
        if not mp4_urls:
            return None

        use_mobile = duration_sec <= 4

        if use_mobile:
            # 短いシーン: mobile → orig 以外の mp4 → 先頭
            for url in mp4_urls:
                if "mobile" in url.lower():
                    return url
            for url in mp4_urls:
                if "orig" not in url.lower():
                    return url
        else:
            # 長いシーン: mobile でも orig でもない中画質 → mobile → 先頭
            middle = [u for u in mp4_urls if "mobile" not in u.lower() and "orig" not in u.lower()]
            if middle:
                return middle[0]
            for url in mp4_urls:
                if "mobile" not in url.lower():
                    return url

        return mp4_urls[0]
    except Exception as e:
        logger.error(f"NASA 動画マニフェスト取得失敗: {e}")
        return None


def check_nasa_rate_limit(response: requests.Response) -> None:
    remaining = response.headers.get("X-Ratelimit-Remaining")
    if remaining and int(remaining) < 10:
        logger.warning(f"NASA API レート制限接近 (残り {remaining}件)。{RATE_LIMIT_SLEEP}秒スリープします")
        time.sleep(RATE_LIMIT_SLEEP)


# ---- Pexels API ----

def parse_pexels_image_response(data: dict) -> Optional[str]:
    try:
        photos = data.get("photos", [])
        if not photos:
            return None
        src = photos[0].get("src", {})
        for key in ["original", "large2x", "large"]:
            if key in src:
                return src[key]
        return None
    except Exception:
        return None


def parse_pexels_video_response(data: dict, duration_sec: int = 4) -> Optional[str]:
    """Pexels Video API レスポンスから適切なサイズの動画 URL を返す。

    duration_sec <= 4 → 幅 720 前後（軽量）
    duration_sec >= 5 → 幅 1280 前後（HD）
    """
    try:
        videos = data.get("videos", [])
        if not videos:
            return None
        video_files = videos[0].get("video_files", [])
        if not video_files:
            return None

        target_width = 720 if duration_sec <= 4 else 1280
        mp4_files = [vf for vf in video_files if (vf.get("link", "").endswith(".mp4"))]
        if not mp4_files:
            return video_files[0].get("link")

        best = min(mp4_files, key=lambda x: abs((x.get("width") or 0) - target_width))
        return best.get("link")
    except Exception:
        return None


# ---- 元記事スクレイピング ----

def scrape_article_images(article_url: str, session: requests.Session) -> list[str]:
    if article_url in _article_image_cache:
        return _article_image_cache[article_url]

    try:
        from bs4 import BeautifulSoup
        resp = session.get(article_url, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        image_urls = []
        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src") or ""
            if not src:
                continue
            abs_url = urljoin(article_url, src)
            if any(x in abs_url.lower() for x in ["logo", "icon", "favicon", "avatar", "spinner", "banner", "-bg.", "_bg.", "background"]):
                continue
            ext = abs_url.split("?")[0].rsplit(".", 1)[-1].lower()
            if ext in ("jpg", "jpeg", "png", "webp"):
                image_urls.append(abs_url)

        logger.info(f"  [article] {article_url} から {len(image_urls)} 件の画像を発見")
        _article_image_cache[article_url] = image_urls
        return image_urls
    except ImportError:
        logger.warning("  BeautifulSoup4 未インストール。`pip install beautifulsoup4` で有効化できます")
        _article_image_cache[article_url] = []
        return []
    except Exception as e:
        logger.warning(f"  記事スクレイピング失敗 ({article_url}): {e}")
        _article_image_cache[article_url] = []
        return []


def fetch_article_image(
    scene_id: str,
    article_url: str,
    image_index: int,
    scene_dir: Path,
    session: requests.Session,
) -> Optional[dict]:
    images = scrape_article_images(article_url, session)
    if not images:
        return None

    idx = min(image_index, len(images) - 1)
    image_url = images[idx]

    try:
        filename = generate_asset_filename(image_url, prefix="article")
        local_path = scene_dir / filename
        img_resp = session.get(image_url, timeout=30)
        img_resp.raise_for_status()
        local_path.write_bytes(img_resp.content)
        logger.info(f"  [article] {scene_id}: {filename} (index={idx})")
        return build_manifest_entry(
            scene_id=scene_id,
            source="article",
            media_type="image",
            local_path=str(local_path.relative_to(PROJECT_ROOT)),
            license="NASA Public Domain",
            original_url=image_url,
        )
    except Exception as e:
        logger.warning(f"  記事画像ダウンロード失敗 (scene={scene_id}): {e}")
        return None


# ---- ユーティリティ ----

def generate_asset_filename(url: str, prefix: str) -> str:
    basename = url.split("/")[-1].split("?")[0]
    safe = re.sub(r"[~<>:\"/\\|?*]", "_", basename)
    if not safe:
        safe = "asset"
    return f"{prefix}_{safe}"


def get_scene_asset_dir(assets_root: Path, scene_id: str) -> Path:
    if scene_id in ("hook", "outro"):
        return assets_root / scene_id
    return assets_root / f"scene_{scene_id}"


def build_manifest_entry(
    scene_id: str,
    source: str,
    media_type: str,
    local_path: str,
    license: str,
    original_url: str,
) -> dict:
    return {
        "scene_id": scene_id,
        "source": source,
        "media_type": media_type,
        "local_path": local_path,
        "license": license,
        "original_url": original_url,
    }


def save_manifest(entries: list, item_id: str, output_path: Path) -> None:
    manifest = {
        "item_id": item_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scenes": entries,
        "bgm": {},
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)


def _asset_credit(entry: dict) -> dict:
    """manifest エントリから著作権情報の辞書を生成する。"""
    return {
        "url": entry["original_url"],
        "source": entry["source"],
        "license": entry["license"],
    }


def write_back_attribution(script: dict, entries: list, script_path: Path) -> None:
    """取得済みアセットの元URLと著作権情報をスクリプトJSONに書き戻す。

    各シーンに fetched_assets フィールドを追加（複数URL対応の配列）。
    hook / outro は hook_fetched_assets / outro_fetched_assets として保存。
    fallback（StarField）はURLなしのためスキップ。
    """
    entry_map: dict[str, list[dict]] = {}
    for e in entries:
        if e["source"] == "fallback" or not e.get("original_url"):
            continue
        sid = e["scene_id"]
        entry_map.setdefault(sid, []).append(_asset_credit(e))

    for scene in script["scenes"]:
        sid = str(scene["id"])
        if sid in entry_map:
            existing = scene.get("fetched_assets", [])
            for credit in entry_map[sid]:
                if credit not in existing:
                    existing.append(credit)
            scene["fetched_assets"] = existing

    for special in ("hook", "outro"):
        if special in entry_map:
            key = f"{special}_fetched_assets"
            existing = script.get(key, [])
            for credit in entry_map[special]:
                if credit not in existing:
                    existing.append(credit)
            script[key] = existing

    with open(script_path, "w", encoding="utf-8") as f:
        json.dump(script, f, ensure_ascii=False, indent=2)
    logger.info(f"帰属情報をスクリプトに書き戻しました: {script_path}")


# ---- 素材取得フロー ----

def _try_nasa_video(scene_id: str, keywords: list, scene_dir: Path, session: requests.Session, duration_sec: int, randomize: bool = False) -> Optional[dict]:
    try:
        page = random.randint(1, 5) if randomize else 1
        pick = random.randint(0, 4) if randomize else 0
        url = build_nasa_search_url(keywords, media_type="video", page=page)
        resp = session.get(url, timeout=15)
        resp.raise_for_status()
        check_nasa_rate_limit(resp)
        manifest_url = parse_nasa_search_response(resp.json(), pick_index=pick)
        if not manifest_url:
            return None
        video_url = fetch_nasa_video_url(manifest_url, session, duration_sec=duration_sec)
        if not video_url:
            return None
        filename = generate_asset_filename(video_url, prefix="nasa_video")
        if not filename.lower().endswith(".mp4"):
            filename += ".mp4"
        local_path = scene_dir / filename
        vid_resp = session.get(video_url, timeout=60)
        vid_resp.raise_for_status()
        local_path.write_bytes(vid_resp.content)
        size_mb = local_path.stat().st_size / 1024 / 1024
        size_hint = "mobile" if duration_sec <= 4 else "medium"
        logger.info(f"  [NASA video/{size_hint}] {scene_id}: {filename} ({size_mb:.1f} MB)")
        return build_manifest_entry(
            scene_id=scene_id, source="nasa", media_type="video",
            local_path=str(local_path.relative_to(PROJECT_ROOT)),
            license="NASA Public Domain", original_url=video_url,
        )
    except Exception as e:
        logger.warning(f"  NASA 動画取得失敗 (scene={scene_id}): {e}")
        return None


def _try_nasa_image(scene_id: str, keywords: list, scene_dir: Path, session: requests.Session, randomize: bool = False) -> Optional[dict]:
    try:
        page = random.randint(1, 5) if randomize else 1
        pick = random.randint(0, 4) if randomize else 0
        url = build_nasa_search_url(keywords, media_type="image", page=page)
        resp = session.get(url, timeout=15)
        resp.raise_for_status()
        check_nasa_rate_limit(resp)
        manifest_url = parse_nasa_search_response(resp.json(), pick_index=pick)
        if not manifest_url:
            return None
        image_url = fetch_nasa_image_url(manifest_url, session)
        if not image_url:
            return None
        filename = generate_asset_filename(image_url, prefix="nasa")
        local_path = scene_dir / filename
        img_resp = session.get(image_url, timeout=30)
        img_resp.raise_for_status()
        local_path.write_bytes(img_resp.content)
        logger.info(f"  [NASA image] {scene_id}: {filename}")
        return build_manifest_entry(
            scene_id=scene_id, source="nasa", media_type="image",
            local_path=str(local_path.relative_to(PROJECT_ROOT)),
            license="NASA Public Domain", original_url=image_url,
        )
    except Exception as e:
        logger.warning(f"  NASA 静止画取得失敗 (scene={scene_id}): {e}")
        return None


def _try_pexels_video(scene_id: str, keywords: list, scene_dir: Path, session: requests.Session, pexels_api_key: str, duration_sec: int) -> Optional[dict]:
    try:
        query = " ".join(keywords)
        headers = {"Authorization": pexels_api_key}
        params = {"query": query, "per_page": 5, "orientation": "landscape"}
        resp = session.get(PEXELS_VIDEO_BASE, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        video_url = parse_pexels_video_response(resp.json(), duration_sec=duration_sec)
        if not video_url:
            return None
        filename = generate_asset_filename(video_url, prefix="pexels_video")
        if not filename.lower().endswith(".mp4"):
            filename += ".mp4"
        local_path = scene_dir / filename
        vid_resp = session.get(video_url, timeout=60)
        vid_resp.raise_for_status()
        local_path.write_bytes(vid_resp.content)
        size_mb = local_path.stat().st_size / 1024 / 1024
        size_hint = "720p" if duration_sec <= 4 else "HD"
        logger.info(f"  [Pexels video/{size_hint}] {scene_id}: {filename} ({size_mb:.1f} MB)")
        return build_manifest_entry(
            scene_id=scene_id, source="pexels", media_type="video",
            local_path=str(local_path.relative_to(PROJECT_ROOT)),
            license="Pexels License", original_url=video_url,
        )
    except Exception as e:
        logger.warning(f"  Pexels 動画取得失敗 (scene={scene_id}): {e}")
        return None


def _try_pexels_image(scene_id: str, keywords: list, scene_dir: Path, session: requests.Session, pexels_api_key: str) -> Optional[dict]:
    try:
        query = " ".join(keywords)
        headers = {"Authorization": pexels_api_key}
        params = {"query": query, "per_page": 5}
        resp = session.get(PEXELS_IMAGE_BASE, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        image_url = parse_pexels_image_response(resp.json())
        if not image_url:
            return None
        filename = generate_asset_filename(image_url, prefix="pexels")
        local_path = scene_dir / filename
        img_resp = session.get(image_url, timeout=30)
        img_resp.raise_for_status()
        local_path.write_bytes(img_resp.content)
        logger.info(f"  [Pexels image] {scene_id}: {filename}")
        return build_manifest_entry(
            scene_id=scene_id, source="pexels", media_type="image",
            local_path=str(local_path.relative_to(PROJECT_ROOT)),
            license="Pexels License", original_url=image_url,
        )
    except Exception as e:
        logger.warning(f"  Pexels 静止画取得失敗 (scene={scene_id}): {e}")
        return None


def fetch_asset_for_scene(
    scene_id: str,
    keywords: list,
    assets_root: Path,
    session: requests.Session,
    pexels_api_key: Optional[str],
    source_url: Optional[str] = None,
    article_image_index: int = 0,
    prefer_video: bool = False,
    duration_sec: int = 4,
    randomize: bool = False,
) -> dict:
    scene_dir = get_scene_asset_dir(assets_root, scene_id)
    # hook は毎回新鮮な素材を使うため既存ファイルを削除する
    if randomize and scene_dir.exists():
        import shutil
        shutil.rmtree(scene_dir)
    scene_dir.mkdir(parents=True, exist_ok=True)

    if prefer_video:
        # 動画優先: NASA動画 → Pexels動画 → NASA静止画 → Pexels静止画
        for fn in [
            lambda: _try_nasa_video(scene_id, keywords, scene_dir, session, duration_sec, randomize=randomize),
            lambda: _try_pexels_video(scene_id, keywords, scene_dir, session, pexels_api_key, duration_sec) if pexels_api_key else None,
            lambda: _try_nasa_image(scene_id, keywords, scene_dir, session, randomize=randomize),
            lambda: _try_pexels_image(scene_id, keywords, scene_dir, session, pexels_api_key) if pexels_api_key else None,
        ]:
            result = fn()
            if result:
                return result
    else:
        # 静止画優先: NASA静止画 → 元記事 → Pexels静止画
        result = _try_nasa_image(scene_id, keywords, scene_dir, session, randomize=randomize)
        if result:
            return result

        if source_url:
            result = fetch_article_image(scene_id, source_url, article_image_index, scene_dir, session)
            if result:
                return result

        if pexels_api_key:
            result = _try_pexels_image(scene_id, keywords, scene_dir, session, pexels_api_key)
            if result:
                return result

    logger.warning(f"  [fallback] {scene_id}: 素材取得不可。星フィールド背景を使用します")
    return build_manifest_entry(
        scene_id=scene_id, source="fallback", media_type="image",
        local_path="", license="", original_url="",
    )


# ---- エントリポイント ----

def main() -> int:
    parser = argparse.ArgumentParser(description="AssetFetcher: 台本の image_keywords で素材を取得する")
    parser.add_argument("--script", required=True, help="台本 JSON ファイルパス")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler()],
    )

    script_path = Path(args.script)
    if not script_path.exists():
        logger.error(f"台本ファイルが見つかりません: {script_path}")
        return 1

    with open(script_path, encoding="utf-8") as f:
        script = json.load(f)

    item_id = script["item_id"]
    pexels_api_key = os.getenv("PEXELS_API_KEY")
    if not pexels_api_key:
        logger.warning("PEXELS_API_KEY が未設定です。Pexels フォールバックは無効になります")

    assets_root = PROJECT_ROOT / "assets" / item_id
    manifest_path = assets_root / "manifest.json"

    session = requests.Session()
    session.headers.update({"User-Agent": "NASA-Spinoff-VideoBot/1.0"})

    # (scene_id, keywords, source_url, article_image_index, prefer_video, duration_sec, randomize)
    scenes_to_fetch = []
    scenes_to_fetch.append(("hook", script.get("image_keywords_hook") or ["space", "nasa"], None, 0, False, 3, True))

    article_index_counter: dict[str, int] = {}
    for scene in script["scenes"]:
        src_url = scene.get("source_url")
        idx = 0
        if src_url:
            idx = scene.get("article_image_index", article_index_counter.get(src_url, 0))
            article_index_counter[src_url] = idx + 1
        scenes_to_fetch.append((
            str(scene["id"]),
            scene["image_keywords"],
            src_url,
            idx,
            scene.get("prefer_video", False),
            scene.get("duration_sec", 4),
            False,
        ))

    scenes_to_fetch.append(("outro", script.get("image_keywords_outro") or ["space technology", "nasa"], None, 0, False, 5, False))

    entries = []
    for scene_id, keywords, source_url, article_idx, prefer_video, duration_sec, randomize in scenes_to_fetch:
        label = "動画優先" if prefer_video else "静止画優先"
        logger.info(f"取得中: scene={scene_id} [{label}] keywords={keywords}")
        entry = fetch_asset_for_scene(
            scene_id, keywords, assets_root, session, pexels_api_key,
            source_url, article_idx, prefer_video, duration_sec, randomize=randomize,
        )
        entries.append(entry)

    save_manifest(entries, item_id=item_id, output_path=manifest_path)
    write_back_attribution(script, entries, script_path)

    video_count = sum(1 for e in entries if e["media_type"] == "video")
    image_count = sum(1 for e in entries if e["media_type"] == "image" and e["source"] != "fallback")
    fallback_count = sum(1 for e in entries if e["source"] == "fallback")

    logger.info(f"マニフェスト保存: {manifest_path}")
    logger.info(f"  動画: {video_count}件 / 静止画: {image_count}件 / fallback: {fallback_count}件")
    if fallback_count:
        logger.warning(f"{fallback_count} シーンが fallback（星フィールド背景）になります")

    return 0


if __name__ == "__main__":
    sys.exit(main())
