#!/usr/bin/env python3
"""Step 4: AssetFetcher

台本 JSON の image_keywords をもとに NASA Image API → Pexels API → fallback の順で
画像を取得し assets/manifest.json を生成する。

使い方:
    python scripts/step4_fetch_assets.py --script data/script_{id}.json
"""

import argparse
import json
import logging
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import quote_plus, urlencode

import requests
from dotenv import load_dotenv
import os

PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")

logger = logging.getLogger(__name__)

NASA_SEARCH_BASE = "https://images-api.nasa.gov/search"
PEXELS_SEARCH_BASE = "https://api.pexels.com/v1/search"
RATE_LIMIT_SLEEP = 5  # X-Ratelimit-Remaining < 10 のときのスリープ秒数


# ---- NASA API ----

def build_nasa_search_url(keywords: list) -> str:
    """NASA Image and Video Library API の検索 URL を構築する"""
    query = " ".join(keywords)
    params = urlencode({"q": query, "media_type": "image"})
    return f"{NASA_SEARCH_BASE}?{params}"


def parse_nasa_search_response(data: dict) -> Optional[str]:
    """NASA 検索レスポンスから最初のアセットマニフェスト URL を返す。結果なしは None"""
    try:
        items = data["collection"]["items"]
        if not items:
            return None
        return items[0]["href"]
    except (KeyError, IndexError):
        return None


def fetch_nasa_image_url(manifest_url: str, session: requests.Session) -> Optional[str]:
    """NASA アセットマニフェストから最高解像度の画像 URL を取得する"""
    try:
        resp = session.get(manifest_url, timeout=15)
        resp.raise_for_status()
        urls = resp.json()
        # orig > large > thumb の優先順
        for suffix in ["~orig.jpg", "~large.jpg", "~medium.jpg", "~thumb.jpg"]:
            for url in urls:
                if url.endswith(suffix):
                    return url
        # どれも一致しなければ最初の .jpg
        jpg_urls = [u for u in urls if u.lower().endswith(".jpg")]
        return jpg_urls[0] if jpg_urls else (urls[0] if urls else None)
    except Exception as e:
        logger.error(f"NASA アセットマニフェスト取得失敗: {e}")
        return None


def check_nasa_rate_limit(response: requests.Response) -> None:
    """X-Ratelimit-Remaining が 10 未満なら一時停止する"""
    remaining = response.headers.get("X-Ratelimit-Remaining")
    if remaining and int(remaining) < 10:
        logger.warning(f"NASA API レート制限接近 (残り {remaining}件)。{RATE_LIMIT_SLEEP}秒スリープします")
        time.sleep(RATE_LIMIT_SLEEP)


# ---- Pexels API ----

def parse_pexels_response(data: dict) -> Optional[str]:
    """Pexels レスポンスから最高解像度の画像 URL を返す。結果なしは None"""
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


# ---- ユーティリティ ----

def generate_asset_filename(url: str, prefix: str) -> str:
    """URL からファイルシステム安全なファイル名を生成する"""
    basename = url.split("/")[-1].split("?")[0]
    # チルダを除去してアンダースコアに置換
    safe = re.sub(r"[~<>:\"/\\|?*]", "_", basename)
    if not safe:
        safe = "image.jpg"
    return f"{prefix}_{safe}"


def get_scene_asset_dir(assets_root: Path, scene_id: str) -> Path:
    """シーン ID に対応するアセットディレクトリを返す"""
    if scene_id in ("hook", "outro"):
        return assets_root / scene_id
    return assets_root / f"scene_{scene_id}"


# ---- マニフェスト ----

def build_manifest_entry(
    scene_id: str,
    source: str,
    local_path: str,
    license: str,
    original_url: str,
) -> dict:
    """AssetEntry 辞書を生成する"""
    return {
        "scene_id": scene_id,
        "source": source,
        "local_path": local_path,
        "license": license,
        "original_url": original_url,
    }


def save_manifest(entries: list, item_id: str, output_path: Path) -> None:
    """assets/manifest.json を書き出す"""
    manifest = {
        "item_id": item_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scenes": entries,
        "bgm": {},
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)


# ---- 素材取得フロー ----

def fetch_asset_for_scene(
    scene_id: str,
    keywords: list,
    assets_root: Path,
    session: requests.Session,
    pexels_api_key: Optional[str],
) -> dict:
    """1シーン分の素材を取得して AssetEntry を返す"""
    scene_dir = get_scene_asset_dir(assets_root, scene_id)
    scene_dir.mkdir(parents=True, exist_ok=True)

    # --- NASA API ---
    try:
        url = build_nasa_search_url(keywords)
        resp = session.get(url, timeout=15)
        resp.raise_for_status()
        check_nasa_rate_limit(resp)
        manifest_url = parse_nasa_search_response(resp.json())

        if manifest_url:
            image_url = fetch_nasa_image_url(manifest_url, session)
            if image_url:
                filename = generate_asset_filename(image_url, prefix="nasa")
                local_path = scene_dir / filename
                img_resp = session.get(image_url, timeout=30)
                img_resp.raise_for_status()
                local_path.write_bytes(img_resp.content)
                logger.info(f"  [NASA] {scene_id}: {filename}")
                return build_manifest_entry(
                    scene_id=scene_id,
                    source="nasa",
                    local_path=str(local_path.relative_to(PROJECT_ROOT)),
                    license="NASA Public Domain",
                    original_url=image_url,
                )
    except Exception as e:
        logger.warning(f"  NASA 取得失敗 (scene={scene_id}): {e}")

    # --- Pexels フォールバック ---
    if pexels_api_key:
        try:
            query = " ".join(keywords)
            headers = {"Authorization": pexels_api_key}
            params = {"query": query, "per_page": 5}
            resp = session.get(PEXELS_SEARCH_BASE, headers=headers, params=params, timeout=15)
            resp.raise_for_status()
            image_url = parse_pexels_response(resp.json())

            if image_url:
                filename = generate_asset_filename(image_url, prefix="pexels")
                local_path = scene_dir / filename
                img_resp = session.get(image_url, timeout=30)
                img_resp.raise_for_status()
                local_path.write_bytes(img_resp.content)
                logger.info(f"  [Pexels] {scene_id}: {filename}")
                return build_manifest_entry(
                    scene_id=scene_id,
                    source="pexels",
                    local_path=str(local_path.relative_to(PROJECT_ROOT)),
                    license="Pexels License",
                    original_url=image_url,
                )
        except Exception as e:
            logger.warning(f"  Pexels 取得失敗 (scene={scene_id}): {e}")

    # --- fallback ---
    logger.warning(f"  [fallback] {scene_id}: 素材取得不可。星フィールド背景を使用します")
    return build_manifest_entry(
        scene_id=scene_id,
        source="fallback",
        local_path="",
        license="",
        original_url="",
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

    # 全シーン（hook・scenes・outro）の収集
    scenes_to_fetch = []
    scenes_to_fetch.append(("hook", script.get("image_keywords_hook") or ["space", "nasa"]))
    for scene in script["scenes"]:
        scenes_to_fetch.append((str(scene["id"]), scene["image_keywords"]))
    scenes_to_fetch.append(("outro", script.get("image_keywords_outro") or ["space technology", "nasa"]))

    entries = []
    for scene_id, keywords in scenes_to_fetch:
        logger.info(f"取得中: scene={scene_id}, keywords={keywords}")
        entry = fetch_asset_for_scene(scene_id, keywords, assets_root, session, pexels_api_key)
        entries.append(entry)

    save_manifest(entries, item_id=item_id, output_path=manifest_path)
    logger.info(f"マニフェスト保存: {manifest_path} ({len(entries)} シーン)")

    fallback_count = sum(1 for e in entries if e["source"] == "fallback")
    if fallback_count:
        logger.warning(f"{fallback_count} シーンが fallback（星フィールド背景）になります")

    return 0


if __name__ == "__main__":
    sys.exit(main())
