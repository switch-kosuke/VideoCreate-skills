#!/usr/bin/env python3
"""Step 3: ScriptAgent ファイルI/Oヘルパー

Claude Code が日英台本を生成・ユーザー承認を得た後にこのスクリプトで
スキーマ検証を行い data/script_{item_id}.json として保存する。

使い方:
    python scripts/step3_save_script.py --script-json '<JSON文字列>'
    python scripts/step3_save_script.py --script-file /path/to/script.json
"""

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

REQUIRED_SCRIPT_FIELDS = ["item_id", "title", "title_en", "hook", "hook_en", "scenes", "outro", "outro_en"]
REQUIRED_SCENE_FIELDS = ["id", "voiceover", "voiceover_en", "visual_note", "image_keywords", "duration_sec"]


# ---- スキーマ検証 ----

def validate_script_schema(script: dict) -> bool:
    """ScriptJSON スキーマを検証する。問題があれば ValueError を送出する"""
    # 必須フィールド確認
    for field in REQUIRED_SCRIPT_FIELDS:
        if field not in script:
            raise ValueError(f"必須フィールド '{field}' が ScriptJSON に含まれていません")

    # title 25文字以内
    if len(script["title"]) > 25:
        raise ValueError(f"'title' は 25 文字以内でなければなりません（現在 {len(script['title'])} 文字）")

    # scenes が空でないこと
    if not script["scenes"]:
        raise ValueError("'scenes' は 1 件以上必要です")

    # 各シーンの検証
    for i, scene in enumerate(script["scenes"]):
        for field in REQUIRED_SCENE_FIELDS:
            if field not in scene:
                raise ValueError(f"scenes[{i}] に必須フィールド '{field}' が含まれていません")

        kw = scene["image_keywords"]
        if not (2 <= len(kw) <= 4):
            raise ValueError(
                f"scenes[{i}] の 'image_keywords' は 2〜4 語でなければなりません（現在 {len(kw)} 語）"
            )

    return True


# ---- 合計尺計算 ----

def compute_total_duration(script: dict, hook_sec: int = 3, outro_sec: int = 5) -> int:
    """シーン合計 + hook + outro の総尺（秒）を返す"""
    scene_total = sum(s["duration_sec"] for s in script["scenes"])
    return scene_total + hook_sec + outro_sec


# ---- 台本保存 ----

def save_script_json(script: dict, output_path: Path) -> None:
    """スキーマ検証してから台本を JSON として保存する"""
    validate_script_schema(script)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(script, f, ensure_ascii=False, indent=2)


# ---- エントリポイント ----

def main() -> int:
    parser = argparse.ArgumentParser(description="ScriptAgent: 台本 JSON を検証・保存する")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--script-json", help="台本 JSON 文字列")
    group.add_argument("--script-file", help="台本 JSON ファイルパス")
    args = parser.parse_args()

    if args.script_json:
        try:
            script = json.loads(args.script_json)
        except json.JSONDecodeError as e:
            print(f"エラー: JSON パース失敗: {e}", file=sys.stderr)
            return 1
    else:
        try:
            with open(args.script_file, encoding="utf-8") as f:
                script = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"エラー: {e}", file=sys.stderr)
            return 1

    try:
        validate_script_schema(script)
    except ValueError as e:
        print(f"スキーマエラー: {e}", file=sys.stderr)
        return 1

    item_id = script["item_id"]
    output_path = PROJECT_ROOT / "data" / f"script_{item_id}.json"

    # 60秒超過チェック
    total = compute_total_duration(script, hook_sec=3, outro_sec=5)
    if total > 60:
        print(f"⚠️  合計尺 {total} 秒 > 60 秒です。シーン圧縮を検討してください。", file=sys.stderr)

    save_script_json(script, output_path)
    print(f"保存しました: {output_path}")
    print(f"  タイトル: {script['title']}")
    print(f"  シーン数: {len(script['scenes'])}")
    print(f"  合計尺: {script.get('total_duration_sec', total)} 秒")
    return 0


if __name__ == "__main__":
    sys.exit(main())
