#!/usr/bin/env python3
"""Step 7: PostProcessor

Pixabay Music API から BGM を取得し、FFmpeg でナレーション音声とミックスして
最終 MP4 を output/ に書き出す。

使い方:
    python scripts/step7_postprocess.py --input tmp/render_{id}.mp4 --id {item_id}
"""

import argparse
import logging
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv
import os

PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")

logger = logging.getLogger(__name__)

JAMENDO_API = "https://api.jamendo.com/v3.0/tracks/"
BGM_TAGS = ["epic", "dramatic", "orchestral"]
BGM_MIN_DURATION = 30  # 秒


# ---- パス生成 ----

def build_output_path(item_id: str, date_str: str, output_dir: Path) -> Path:
    """出力 MP4 パスを返す: output/{item_id}/output_{item_id}_{YYYYMMDD}.mp4"""
    date_compact = date_str.replace("-", "")
    return output_dir / f"output_{item_id}_{date_compact}.mp4"


def build_bgm_path(filename: str, bgm_dir: Path) -> Path:
    """BGM ファイルパスを返す: assets/bgm/bgm_{filename}"""
    return bgm_dir / f"bgm_{filename}"


# ---- Jamendo レスポンスパース ----

def parse_jamendo_response(data: dict) -> Optional[tuple]:
    """Jamendo API レスポンスから商用利用可 (audio_url, filename) を返す。結果なしは None

    CC BY-NC / CC BY-NC-SA / CC BY-NC-ND はスキップし、
    CC BY / CC BY-SA / CC0 のみを採用する。
    """
    try:
        results = data.get("results", [])
        for track in results:
            license_url = track.get("license_ccurl", "")
            # NC（非商用）ライセンスをスキップ
            if "-nc" in license_url.lower():
                continue
            audio_url = track.get("audiodownload", "") or track.get("audio", "")
            if not audio_url:
                continue
            track_id = track.get("id", "track")
            name = track.get("name", f"bgm_{track_id}").replace(" ", "_")
            filename = f"{track_id}_{name}.mp3"
            return audio_url, filename
        return None
    except Exception:
        return None


# ---- BGM キャッシュ検索 ----

def find_cached_bgm(bgm_dir: Path) -> Optional[Path]:
    """assets/bgm/ に既存 MP3 があれば最初の 1 件を返す。なければ None"""
    if not bgm_dir.exists():
        return None
    mp3s = sorted(bgm_dir.glob("*.mp3"))
    return mp3s[0] if mp3s else None


# ---- Jamendo BGM 取得 ----

def fetch_bgm_from_jamendo(
    client_id: str,
    bgm_dir: Path,
    session: requests.Session,
) -> Optional[Path]:
    """Jamendo API で BGM を検索・ダウンロードして Path を返す"""
    for tag in BGM_TAGS:
        try:
            params = {
                "client_id": client_id,
                "format": "json",
                "limit": 20,
                "tags": tag,
                "audiodlformat": "mp32",
                "order": "popularity_total",
                "durationbetween": f"{BGM_MIN_DURATION}_300",
                "license_type": "cc_by cc_by_sa",  # 商用利用可ライセンスのみ
            }
            resp = session.get(JAMENDO_API, params=params, timeout=15)
            resp.raise_for_status()
            result = parse_jamendo_response(resp.json())
            if not result:
                continue

            audio_url, filename = result
            bgm_path = build_bgm_path(filename, bgm_dir)
            bgm_dir.mkdir(parents=True, exist_ok=True)

            audio_resp = session.get(audio_url, timeout=60)
            audio_resp.raise_for_status()
            bgm_path.write_bytes(audio_resp.content)
            logger.info(f"  [Jamendo] BGM 取得: {bgm_path.name}")
            return bgm_path

        except Exception as e:
            logger.warning(f"  Jamendo BGM 取得失敗 (tag={tag}): {e}")

    return None


# ---- FFmpeg チェック ----

def check_ffmpeg_available() -> bool:
    """システムに ffmpeg が存在するか確認する"""
    return shutil.which("ffmpeg") is not None


# ---- FFmpeg コマンド構築 ----

def build_ffmpeg_mix_command(
    input_video: Path,
    bgm_path: Path,
    output_path: Path,
    video_duration_sec: float,
) -> list:
    """FFmpeg ミックスコマンドリストを構築する

    - BGM: normalize=0 でそのまま加算（BGM素材が元々ナレーションより静かな前提）
    - BGM が動画より長い場合は duration=first でトリミング
    """
    # bgm_path が None なら AttributeError が自然に発生
    _ = bgm_path.name  # None チェック（TypeError/AttributeError）

    filter_complex = (
        "[1:a]volume=-14dB[bgm];"
        "[0:a][bgm]amix=inputs=2:duration=first:normalize=0[aout]"
    )

    return [
        "ffmpeg",
        "-y",
        "-i", str(input_video),
        "-i", str(bgm_path),
        "-t", str(video_duration_sec),
        "-filter_complex", filter_complex,
        "-map", "0:v",
        "-map", "[aout]",
        "-c:v", "copy",
        str(output_path),
    ]


# ---- エントリポイント ----

def main() -> int:
    parser = argparse.ArgumentParser(description="PostProcessor: BGMミックスして最終 MP4 を出力する")
    parser.add_argument("--input", required=True, help="Remotion 出力 MP4 パス（例: tmp/render_{id}.mp4）")
    parser.add_argument("--id", required=True, help="item_id")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler()],
    )

    input_path = Path(args.input)
    if not input_path.exists():
        logger.error(f"入力 MP4 が見つかりません: {input_path}")
        return 1

    if not check_ffmpeg_available():
        logger.error(
            "ffmpeg が見つかりません。インストールしてから再実行してください。\n"
            "  Windows: winget install FFmpeg\n"
            "  Mac:     brew install ffmpeg\n"
            "  Ubuntu:  sudo apt install ffmpeg"
        )
        return 1

    bgm_dir = PROJECT_ROOT / "assets" / args.id / "bgm"
    output_dir = PROJECT_ROOT / "output" / args.id
    output_dir.mkdir(parents=True, exist_ok=True)

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    output_path = build_output_path(args.id, date_str, output_dir)

    # BGM 取得（キャッシュ優先）
    bgm_path = find_cached_bgm(bgm_dir)
    if bgm_path:
        logger.info(f"キャッシュ BGM を使用: {bgm_path.name}")
    else:
        jamendo_client_id = os.getenv("JAMENDO_CLIENT_ID")
        if jamendo_client_id:
            session = requests.Session()
            session.headers.update({"User-Agent": "NASA-Spinoff-VideoBot/1.0"})
            bgm_path = fetch_bgm_from_jamendo(jamendo_client_id, bgm_dir, session)
        else:
            logger.warning("JAMENDO_CLIENT_ID が未設定です。.env に追加してください")
        if not bgm_path:
            logger.warning("BGM を取得できませんでした。BGM なしで続行します")

    # FFmpeg ミックス
    import subprocess
    if bgm_path:
        # 動画の長さを取得（ffprobe）
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", str(input_path)],
                capture_output=True, text=True, timeout=30,
            )
            duration = float(result.stdout.strip()) if result.returncode == 0 else 60.0
        except Exception:
            duration = 60.0

        cmd = build_ffmpeg_mix_command(input_path, bgm_path, output_path, duration)
        logger.info(f"FFmpeg 実行: {' '.join(cmd[:4])} ...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            logger.error(f"FFmpeg 失敗:\n{result.stderr}")
            return 1
    else:
        # BGM なし: そのままコピー
        import shutil as _shutil
        _shutil.copy2(str(input_path), str(output_path))
        logger.info("BGM なし: 入力 MP4 をそのままコピーしました")

    logger.info(f"完了: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
