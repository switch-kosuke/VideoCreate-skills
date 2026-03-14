#!/usr/bin/env python3
"""Step 6: RenderPreparer

Step 5 完了後に data/script_{id}.json・data/audio_manifest.json・
assets/manifest.json を読み込み、data/render_props.json にマージして保存する。

使い方:
    python scripts/step6_prepare_render.py --id <item_id> [--lang ja|en]
"""

import argparse
import json
import math
import shutil
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

def normalize_path(p: str) -> str:
    """絶対パスや Windows バックスラッシュを Remotion 用の相対 URL パスに正規化する"""
    path = Path(p)
    # 絶対パスの場合はプロジェクトルートからの相対パスに変換
    if path.is_absolute():
        try:
            path = path.relative_to(PROJECT_ROOT)
        except ValueError:
            pass
    return str(path).replace("\\", "/")


def normalize_assets_manifest(assets_manifest: dict) -> dict:
    """assetsManifest の local_path を正規化する"""
    import copy
    manifest = copy.deepcopy(assets_manifest)
    for scene in manifest.get("scenes", []):
        if "local_path" in scene:
            scene["local_path"] = normalize_path(scene["local_path"])
    return manifest


def normalize_audio_manifest(audio_manifest: dict) -> dict:
    """audioManifest を TypeScript AudioManifest 型に合わせて変換する。

    Python 生成形式:
      scenes: [{ scene_id, ja_path, en_path }, ...]
    TypeScript 期待形式:
      hook: { ja, en }
      scenes: [{ id: number, ja, en }, ...]
      outro: { ja, en }
    """
    result: dict = {
        "item_id": audio_manifest.get("item_id", ""),
        "generated_at": audio_manifest.get("generated_at", ""),
        "ja_voice": audio_manifest.get("ja_voice", ""),
        "en_voice": audio_manifest.get("en_voice", ""),
        "hook": {},
        "scenes": [],
        "outro": {},
    }
    for entry in audio_manifest.get("scenes", []):
        sid = entry.get("scene_id", "")
        ja = normalize_path(entry.get("ja_path", ""))
        en = normalize_path(entry.get("en_path", ""))
        if sid == "hook":
            result["hook"] = {"ja": ja, "en": en}
        elif sid == "outro":
            result["outro"] = {"ja": ja, "en": en}
        else:
            try:
                result["scenes"].append({"id": int(sid), "ja": ja, "en": en})
            except ValueError:
                result["scenes"].append({"id": sid, "ja": ja, "en": en})
    return result


def adjust_script_durations(script: dict, audio_manifest_raw: dict, lang: str) -> dict:
    """音声の実測長（ja_duration_sec / en_duration_sec）で script の duration_sec を上書きする。
    1秒のパディングを加え、hook/outro は固定秒数（3秒/5秒）で上書きしない。"""
    import copy
    script = copy.deepcopy(script)
    dur_key = f"{lang}_duration_sec"
    scene_lookup = {e["scene_id"]: e for e in audio_manifest_raw.get("scenes", [])}

    for scene in script.get("scenes", []):
        entry = scene_lookup.get(str(scene["id"]))
        if entry and dur_key in entry and entry[dur_key] > 0:
            adjusted = round(entry[dur_key] + 0.4, 1)  # 実測 + 0.4秒余白
            scene["duration_sec"] = adjusted

    # hook の実測長を反映（コンテンツシーンと同じく実測 + 1秒余白）
    hook_entry = scene_lookup.get("hook")
    if hook_entry and dur_key in hook_entry and hook_entry[dur_key] > 0:
        hook_sec = round(hook_entry[dur_key] + 0.4, 1)
    else:
        hook_sec = 3

    # total_duration_sec を再計算
    outro_sec = 5
    content_sec = sum(s["duration_sec"] for s in script.get("scenes", []))
    total_sec = hook_sec + content_sec + outro_sec

    # 最低60秒保証は廃止（アウトロ過剰膨張を防ぐ）

    script["hook_duration_sec"] = hook_sec
    script["outro_duration_sec"] = outro_sec
    script["total_duration_sec"] = total_sec
    return script


def sync_remotion_public(item_id: str) -> None:
    """assets/{item_id}/ と audio/ を remotion/public/ に同期する"""
    remotion_public = PROJECT_ROOT / "remotion" / "public"
    remotion_public.mkdir(parents=True, exist_ok=True)

    # assets/{item_id}/ → remotion/public/assets/{item_id}/
    src_assets = PROJECT_ROOT / "assets" / item_id
    dst_assets = remotion_public / "assets" / item_id
    if src_assets.exists():
        if dst_assets.exists():
            shutil.rmtree(dst_assets)
        shutil.copytree(src_assets, dst_assets)

    # audio/ → remotion/public/audio/
    src_audio = PROJECT_ROOT / "audio"
    dst_audio = remotion_public / "audio"
    if src_audio.exists():
        if dst_audio.exists():
            shutil.rmtree(dst_audio)
        shutil.copytree(src_audio, dst_audio)


def merge_render_props(
    script: dict,
    audio_manifest: dict,
    assets_manifest: dict,
    lang: str = "ja",
) -> dict:
    """3 つのマニフェストを Remotion 用 render_props に統合する"""
    adjusted_script = adjust_script_durations(script, audio_manifest, lang)
    return {
        "item_id": adjusted_script["item_id"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "lang": lang,
        "script": adjusted_script,
        "audioManifest": normalize_audio_manifest(audio_manifest),
        "assetsManifest": normalize_assets_manifest(assets_manifest),
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
    assets_path = PROJECT_ROOT / "assets" / args.id / "manifest.json"
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
    total = props["script"]["total_duration_sec"]
    print(f"  total_duration_sec: {total}秒（音声実測値に基づき調整）")

    print("  Remotion public ディレクトリに同期中...")
    sync_remotion_public(args.id)
    print("  同期完了")
    print(f"  lang: {props['lang']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
