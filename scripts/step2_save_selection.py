#!/usr/bin/env python3
"""Step 2: TopicSelector ファイルI/Oヘルパー

Claude Code がバイラルスコアリング・ユーザー選択を完了した後に
このスクリプトを呼び出して selected_item.json と spinoff_store.json を更新する。

使い方:
    python scripts/step2_save_selection.py --url <URL> --score <1-10>

例:
    python scripts/step2_save_selection.py \
        --url "https://spinoff.nasa.gov/articles/memory-foam" \
        --score 9
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).parent.parent


# ---- ストア読み込み ----

def load_store(store_path: Path) -> dict:
    """spinoff_store.json を読み込む"""
    with open(store_path, encoding="utf-8") as f:
        return json.load(f)


# ---- バリデーション ----

def validate_selected_item(item: dict) -> bool:
    """SelectedItem スキーマを検証する。問題があれば ValueError を送出する"""
    if "record" not in item:
        raise ValueError("'record' フィールドが SelectedItem に含まれていません")
    if "viral_score" not in item:
        raise ValueError("'viral_score' フィールドが SelectedItem に含まれていません")
    if "selected_at" not in item:
        raise ValueError("'selected_at' フィールドが SelectedItem に含まれていません")

    score = item["viral_score"]
    if not isinstance(score, int) or score < 1 or score > 10:
        raise ValueError(f"'viral_score' は 1〜10 の整数でなければなりません: {score}")

    return True


# ---- selected_item.json 保存 ----

def save_selected_item(
    record: dict,
    viral_score: int,
    output_path: Path,
) -> None:
    """selected_item.json を保存する"""
    item = {
        "record": record,
        "viral_score": viral_score,
        "selected_at": datetime.now(timezone.utc).isoformat(),
    }
    validate_selected_item(item)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(item, f, ensure_ascii=False, indent=2)


# ---- spinoff_store.json の used フラグ更新 ----

def update_store_used_flag(store_path: Path, url: str) -> None:
    """指定 URL のレコードを used=True に更新して store を上書き保存する"""
    store = load_store(store_path)
    matched = False
    for record in store["records"]:
        if record["url"] == url:
            record["used"] = True
            record["used_at"] = datetime.now(timezone.utc).isoformat()
            matched = True
            break

    if not matched:
        raise ValueError(f"URL が spinoff_store.json に見つかりません: {url}")

    with open(store_path, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=2)


# ---- エントリポイント ----

def main() -> int:
    parser = argparse.ArgumentParser(description="TopicSelector: 選択結果を保存する")
    parser.add_argument("--url", required=True, help="選択した記事の URL")
    parser.add_argument("--score", type=int, required=True, help="バイラルスコア (1-10)")
    args = parser.parse_args()

    store_path = PROJECT_ROOT / "data" / "spinoff_store.json"
    selected_path = PROJECT_ROOT / "data" / "selected_item.json"

    if not store_path.exists():
        print(f"エラー: {store_path} が見つかりません。先に step1_scrape.py を実行してください。", file=sys.stderr)
        return 1

    store = load_store(store_path)
    record = next((r for r in store["records"] if r["url"] == args.url), None)
    if record is None:
        print(f"エラー: URL が spinoff_store.json に見つかりません: {args.url}", file=sys.stderr)
        return 1

    try:
        save_selected_item(record, viral_score=args.score, output_path=selected_path)
        update_store_used_flag(store_path, url=args.url)
    except ValueError as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1

    print(f"保存しました: {selected_path}")
    print(f"  記事: {record['title']}")
    print(f"  スコア: {args.score}/10")
    return 0


if __name__ == "__main__":
    sys.exit(main())
