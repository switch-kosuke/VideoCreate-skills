#!/usr/bin/env python3
"""Step 5: VoiceGenerator

台本 JSON の全テキスト（hook・scenes・outro）に対して edge-tts で
JA・EN の MP3 を非同期生成し data/audio_manifest.json を書き出す。

使い方:
    python scripts/step5_voice.py --script data/script_{id}.json
    python scripts/step5_voice.py --script data/script_{id}.json \\
        --ja-voice ja-JP-KeitaNeural --en-voice en-US-GuyNeural
"""

import argparse
import asyncio
import json
import logging
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import edge_tts

PROJECT_ROOT = Path(__file__).parent.parent

logger = logging.getLogger(__name__)

DEFAULT_JA_VOICE = "ja-JP-NanamiNeural"
DEFAULT_EN_VOICE = "en-US-JennyNeural"
DEFAULT_RATE = "+25%"  # TTS読み上げ速度（デフォルト25%速く）

SCENE_SLEEP_SEC = 0.5  # シーン間スリープ（レート制限対策）


# ---- バリデーション ----

def validate_voices(ja_voice: str, en_voice: str) -> None:
    """ボイス名が空でないことを確認する。空の場合は ValueError を送出する"""
    if not ja_voice:
        raise ValueError("JA ボイス名が空です")
    if not en_voice:
        raise ValueError("EN ボイス名が空です")


# ---- パス生成 ----

def build_audio_path(scene_id: str, lang: str, audio_root: Path) -> Path:
    """シーン ID と言語から音声ファイルパスを返す

    - 数字 ID → audio/{lang}/scene_{id}.mp3
    - hook    → audio/{lang}/scene_hook.mp3
    - outro   → audio/{lang}/scene_outro.mp3
    """
    filename = f"scene_{scene_id}.mp3"
    return audio_root / lang / filename


# ---- マニフェスト生成 ----

def build_audio_manifest(
    script: dict,
    ja_voice: str,
    en_voice: str,
    audio_root: Path,
) -> dict:
    """全シーンの音声パス一覧を含む audio_manifest を生成して返す"""
    scenes_info = []

    # hook
    scenes_info.append({
        "scene_id": "hook",
        "ja_text": script["hook"],
        "en_text": script["hook_en"],
        "ja_path": str(build_audio_path("hook", "ja", audio_root)),
        "en_path": str(build_audio_path("hook", "en", audio_root)),
    })

    # 各シーン
    for scene in script["scenes"]:
        sid = str(scene["id"])
        scenes_info.append({
            "scene_id": sid,
            "ja_text": scene["voiceover"],
            "en_text": scene["voiceover_en"],
            "ja_path": str(build_audio_path(sid, "ja", audio_root)),
            "en_path": str(build_audio_path(sid, "en", audio_root)),
        })

    # outro
    scenes_info.append({
        "scene_id": "outro",
        "ja_text": script["outro"],
        "en_text": script["outro_en"],
        "ja_path": str(build_audio_path("outro", "ja", audio_root)),
        "en_path": str(build_audio_path("outro", "en", audio_root)),
    })

    return {
        "item_id": script["item_id"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ja_voice": ja_voice,
        "en_voice": en_voice,
        "scenes": scenes_info,
    }


# ---- マニフェスト保存 ----

def save_audio_manifest(manifest: dict, output_path: Path) -> None:
    """data/audio_manifest.json を書き出す"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)


# ---- 音声生成 ----

def get_audio_duration(path: Path) -> float:
    """ffprobe で MP3 の実際の再生時間（秒）を返す。失敗時は 0.0"""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(path)],
            capture_output=True, text=True, timeout=10,
        )
        data = json.loads(result.stdout)
        return float(data["format"]["duration"])
    except Exception:
        return 0.0


async def generate_audio(text: str, voice: str, output_path: Path, rate: str = DEFAULT_RATE) -> None:
    """edge-tts で text を voice を使って output_path に MP3 として保存する"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(str(output_path))


async def generate_all_audio(
    manifest: dict,
    ja_voice: str,
    en_voice: str,
    rate: str = DEFAULT_RATE,
) -> None:
    """全シーンの JA・EN 音声を順次生成し、実測 duration_sec を manifest に記録する"""
    for i, scene in enumerate(manifest["scenes"]):
        scene_id = scene["scene_id"]

        logger.info(f"  [JA] scene={scene_id}")
        try:
            await generate_audio(scene["ja_text"], ja_voice, Path(scene["ja_path"]), rate)
        except Exception as e:
            logger.error(f"JA 音声生成失敗 (scene={scene_id}): {e}")
            raise

        logger.info(f"  [EN] scene={scene_id}")
        try:
            await generate_audio(scene["en_text"], en_voice, Path(scene["en_path"]), rate)
        except Exception as e:
            logger.error(f"EN 音声生成失敗 (scene={scene_id}): {e}")
            raise

        # 実際の音声長を計測して記録（JA/EN の長い方をシーン尺として採用）
        ja_dur = get_audio_duration(Path(scene["ja_path"]))
        en_dur = get_audio_duration(Path(scene["en_path"]))
        scene["ja_duration_sec"] = round(ja_dur, 2)
        scene["en_duration_sec"] = round(en_dur, 2)

        if i < len(manifest["scenes"]) - 1:
            await asyncio.sleep(SCENE_SLEEP_SEC)


# ---- エントリポイント ----

def main() -> int:
    parser = argparse.ArgumentParser(description="VoiceGenerator: 台本の全テキストを edge-tts で MP3 生成する")
    parser.add_argument("--script", required=True, help="台本 JSON ファイルパス")
    parser.add_argument("--ja-voice", default=DEFAULT_JA_VOICE, help=f"JA ボイス名（デフォルト: {DEFAULT_JA_VOICE}）")
    parser.add_argument("--en-voice", default=DEFAULT_EN_VOICE, help=f"EN ボイス名（デフォルト: {DEFAULT_EN_VOICE}）")
    parser.add_argument("--rate", default=DEFAULT_RATE, help="読み上げ速度 (例: +40%% / -10%%, デフォルト: +25%%)")
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

    try:
        validate_voices(args.ja_voice, args.en_voice)
    except ValueError as e:
        logger.error(f"ボイス設定エラー: {e}")
        return 1

    audio_root = PROJECT_ROOT / "audio"
    manifest = build_audio_manifest(script, args.ja_voice, args.en_voice, audio_root)

    logger.info(f"音声生成開始: {len(manifest['scenes'])} シーン × 2言語 (rate={args.rate})")
    try:
        asyncio.run(generate_all_audio(manifest, args.ja_voice, args.en_voice, args.rate))
    except Exception as e:
        logger.error(f"音声生成中断: {e}")
        return 1

    manifest_path = PROJECT_ROOT / "data" / "audio_manifest.json"
    save_audio_manifest(manifest, manifest_path)
    logger.info(f"音声マニフェスト保存: {manifest_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
