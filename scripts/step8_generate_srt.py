"""Step 8: SRT字幕ファイル生成

render_props.json + audio_manifest.json からシーンのタイミングを計算し、
日本語・英語それぞれの .srt ファイルを生成する。

使い方:
    python scripts/step8_generate_srt.py --id <item_id> [--lang ja|en|both]
"""

import argparse
import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent


def sec_to_srt_time(sec: float) -> str:
    """秒数を SRT タイムコード形式 HH:MM:SS,mmm に変換する"""
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    ms = int(round((sec - int(sec)) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def build_srt(scenes_timing: list[dict], lang: str) -> str:
    """シーンタイミングリストから SRT 文字列を生成する

    scenes_timing の各要素:
        start_sec: シーン開始時刻（秒）
        audio_duration_sec: 音声の実測長（字幕表示時間）
        text: 字幕テキスト
    """
    lines = []
    for i, scene in enumerate(scenes_timing, start=1):
        start = scene["start_sec"]
        end = start + scene["audio_duration_sec"]
        lines.append(str(i))
        lines.append(f"{sec_to_srt_time(start)} --> {sec_to_srt_time(end)}")
        lines.append(scene["text"])
        lines.append("")
    return "\n".join(lines)


def build_scenes_timing(render_props: dict, audio_manifest: dict, lang: str) -> list[dict]:
    """render_props と audio_manifest からシーンタイミングを構築する"""
    script = render_props["script"]
    audio_by_id = {s["scene_id"]: s for s in audio_manifest["scenes"]}
    duration_key = f"{lang}_duration_sec"
    text_key = "ja_text" if lang == "ja" else "en_text"

    timing = []
    cursor = 0.0

    # hook
    hook_duration = script["hook_duration_sec"]
    if "hook" in audio_by_id:
        timing.append({
            "start_sec": cursor,
            "audio_duration_sec": audio_by_id["hook"][duration_key],
            "text": audio_by_id["hook"][text_key],
        })
    cursor += hook_duration

    # scenes
    for scene in script["scenes"]:
        scene_id = str(scene["id"])
        scene_duration = scene["duration_sec"]
        if scene_id in audio_by_id:
            timing.append({
                "start_sec": cursor,
                "audio_duration_sec": audio_by_id[scene_id][duration_key],
                "text": audio_by_id[scene_id][text_key],
            })
        cursor += scene_duration

    # outro
    outro_duration = script["outro_duration_sec"]
    if "outro" in audio_by_id:
        timing.append({
            "start_sec": cursor,
            "audio_duration_sec": audio_by_id["outro"][duration_key],
            "text": audio_by_id["outro"][text_key],
        })

    return timing


def main():
    parser = argparse.ArgumentParser(description="SRT字幕ファイルを生成する")
    parser.add_argument("--id", required=True, help="item_id")
    parser.add_argument("--lang", default="both", choices=["ja", "en", "both"], help="生成言語（デフォルト: both）")
    args = parser.parse_args()

    render_props_path = PROJECT_ROOT / "data" / "render_props.json"
    audio_manifest_path = PROJECT_ROOT / "data" / "audio_manifest.json"

    if not render_props_path.exists():
        raise FileNotFoundError(f"render_props.json が見つかりません: {render_props_path}")
    if not audio_manifest_path.exists():
        raise FileNotFoundError(f"audio_manifest.json が見つかりません: {audio_manifest_path}")

    render_props = json.loads(render_props_path.read_text(encoding="utf-8"))
    audio_manifest = json.loads(audio_manifest_path.read_text(encoding="utf-8"))

    langs = ["ja", "en"] if args.lang == "both" else [args.lang]
    outputs = []

    for lang in langs:
        timing = build_scenes_timing(render_props, audio_manifest, lang)
        srt_content = build_srt(timing, lang)
        out_path = PROJECT_ROOT / "output" / args.id / f"subtitle_{args.id}_{lang}.srt"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(srt_content, encoding="utf-8")
        logger.info(f"保存しました: {out_path} ({len(timing)} エントリ)")
        outputs.append(out_path)

    print(f"\n✅ SRT生成完了:")
    for p in outputs:
        print(f"   {p}")


if __name__ == "__main__":
    main()
