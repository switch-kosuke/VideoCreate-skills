#!/usr/bin/env python3
"""Step 6: RenderPreparer

Step 5 完了後に data/script_{id}.json・data/audio_manifest.json・
assets/manifest.json を読み込み、data/render_props.json にマージして保存する。

使い方:
    python scripts/step6_prepare_render.py --id <item_id> [--lang ja|en]
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


# ---- I/O ヘルパー ----

def load_json(path: Path) -> dict:
    """JSON ファイルを読み込んで dict を返す。

    Raises:
        FileNotFoundError: ファイルが存在しない場合
        ValueError: JSON パースに失敗した場合
    """
    if not path.exists():
        raise FileNotFoundError(f"ファイルが見つかりません: {path}")
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON パース失敗 ({path}): {e}") from e


def check_required_files(script_path: Path, audio_path: Path, assets_path: Path) -> None:
    """3つの入力ファイルが存在するか確認する。

    Raises:
        FileNotFoundError: いずれかのファイルが存在しない場合（パスを明示）
    """
    if not script_path.exists():
        raise FileNotFoundError(f"script ファイルが見つかりません: {script_path}")
    if not audio_path.exists():
        raise FileNotFoundError(f"audio_manifest ファイルが見つかりません: {audio_path}")
    if not assets_path.exists():
        raise FileNotFoundError(f"assets manifest ファイルが見つかりません: {assets_path}")


# ---- マージ ----

def merge_render_props(
    script: dict,
    audio_manifest: dict,
    assets_manifest: dict,
    lang: str = "ja",
) -> dict:
    """3 つのマニフェストを Remotion 用 render_props に統合する"""
    return {
        "item_id": script["item_id"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "lang": lang,
        "script": script,
        "audioManifest": audio_manifest,
        "assetsManifest": assets_manifest,
    }


# ---- 保存 ----

def save_render_props(props: dict, output_path: Path) -> None:
    """render_props.json を書き出す"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(props, f, ensure_ascii=False, indent=2)


# ---- エントリポイント ----

def main() -> int:
    parser = argparse.ArgumentParser(
        description="RenderPreparer: 3 マニフェストを render_props.json にマージする"
    )
    parser.add_argument("--id", required=True, help="item_id（例: memory-foam）")
    parser.add_argument(
        "--lang", default="ja", choices=["ja", "en"], help="使用音声言語（デフォルト: ja）"
    )
    args = parser.parse_args()

    script_path = PROJECT_ROOT / "data" / f"script_{args.id}.json"
    audio_path = PROJECT_ROOT / "data" / "audio_manifest.json"
    assets_path = PROJECT_ROOT / "assets" / "manifest.json"
    output_path = PROJECT_ROOT / "data" / "render_props.json"

    try:
        check_required_files(script_path, audio_path, assets_path)
    except FileNotFoundError as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1

    try:
        script = load_json(script_path)
        audio_manifest = load_json(audio_path)
        assets_manifest = load_json(assets_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1

    props = merge_render_props(script, audio_manifest, assets_manifest, lang=args.lang)
    save_render_props(props, output_path)

    print(f"保存しました: {output_path}")
    print(f"  item_id: {props['item_id']}")
    print(f"  lang: {props['lang']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
