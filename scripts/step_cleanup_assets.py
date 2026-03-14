#!/usr/bin/env python3
"""AssetCleanup: 動画生成承認後にローカルの素材ファイルを削除する。

manifest.json の original_url (元URL) はそのまま残し、
local_path のファイルを削除して local_path を "" にクリアする。
audio/ の音声ファイル、tmp/ の中間レンダリングファイルも削除する。

使い方:
    python scripts/step_cleanup_assets.py --id <item_id>
"""

import argparse
import json
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
logger = logging.getLogger(__name__)


def cleanup_assets(item_id: str, dry_run: bool = False) -> int:
    manifest_path = PROJECT_ROOT / "assets" / item_id / "manifest.json"
    if not manifest_path.exists():
        logger.error(f"manifest.json が見つかりません: {manifest_path}")
        return 1

    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)

    deleted_files = []
    skipped = []

    # --- assets/ のローカルファイルを削除 ---
    for entry in manifest.get("scenes", []):
        local_path = entry.get("local_path", "")
        if not local_path:
            continue
        abs_path = PROJECT_ROOT / local_path
        if abs_path.exists():
            if not dry_run:
                abs_path.unlink()
            deleted_files.append(local_path)
            entry["local_path"] = ""  # URLは original_url に残る
        else:
            skipped.append(local_path)

    # manifest を書き戻す（local_path をクリア済み）
    if not dry_run:
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

    # --- assets/<item_id>/ の空ディレクトリを削除 ---
    assets_dir = PROJECT_ROOT / "assets" / item_id
    if not dry_run:
        for subdir in sorted(assets_dir.glob("**/*"), reverse=True):
            if subdir.is_dir():
                try:
                    subdir.rmdir()  # 空でないと失敗するので安全
                except OSError:
                    pass

    # --- audio/ の音声ファイルを削除 ---
    for lang in ("ja", "en"):
        audio_dir = PROJECT_ROOT / "audio" / lang
        if audio_dir.exists():
            for f in audio_dir.glob("*.mp3"):
                if not dry_run:
                    f.unlink()
                deleted_files.append(str(f.relative_to(PROJECT_ROOT)))

    # --- audio_manifest.json を削除 ---
    audio_manifest = PROJECT_ROOT / "data" / "audio_manifest.json"
    if audio_manifest.exists():
        if not dry_run:
            audio_manifest.unlink()
        deleted_files.append(str(audio_manifest.relative_to(PROJECT_ROOT)))

    # --- tmp/ の中間レンダリングファイルを削除 ---
    tmp_dir = PROJECT_ROOT / "tmp"
    if tmp_dir.exists():
        for f in tmp_dir.glob(f"render_{item_id}*.mp4"):
            if not dry_run:
                f.unlink()
            deleted_files.append(str(f.relative_to(PROJECT_ROOT)))

    # --- remotion/public/ の同期済みファイルを削除 ---
    remotion_public = PROJECT_ROOT / "remotion" / "public"
    for subdir in ["assets", "audio"]:
        target = remotion_public / subdir
        if target.exists():
            import shutil
            if not dry_run:
                shutil.rmtree(target)
            deleted_files.append(str(target.relative_to(PROJECT_ROOT)))

    prefix = "[DRY RUN] " if dry_run else ""
    logger.info(f"{prefix}削除完了: {len(deleted_files)} 件")
    for f in deleted_files:
        logger.info(f"  {prefix}削除: {f}")
    if skipped:
        logger.warning(f"スキップ（既に存在しない）: {len(skipped)} 件")

    logger.info(f"manifest.json の original_url は保持されています: {manifest_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="AssetCleanup: 素材ファイルを削除しURLのみ保持する")
    parser.add_argument("--id", required=True, help="item_id")
    parser.add_argument("--dry-run", action="store_true", help="削除せずにログのみ出力")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler()],
    )

    return cleanup_assets(args.id, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
