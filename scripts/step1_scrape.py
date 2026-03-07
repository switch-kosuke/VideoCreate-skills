#!/usr/bin/env python3
"""Step 1: SpinoffScraper

spinoff.nasa.gov をスクレイピングして data/spinoff_store.json に追記保存する。

使い方:
    python scripts/step1_scrape.py --fetch   # 新規スクレイピングを実行
    python scripts/step1_scrape.py           # 既存ストアを参照のみ
"""

import argparse
import json
import logging
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, TypedDict
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

PROJECT_ROOT = Path(__file__).parent.parent

logger = logging.getLogger(__name__)


# ---- 型定義 ----

class SpinoffRecord(TypedDict):
    id: str
    url: str
    title: str
    summary: str
    category: str
    fetched_at: str
    used: bool
    used_at: Optional[str]


class SpinoffStore(TypedDict):
    version: str
    records: list


# ---- 設定 ----

def load_config(config_path: Path) -> dict:
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


# ---- スラッグ生成 ----

def generate_slug(url: str) -> str:
    """URL からファイルシステム安全なスラッグを生成する"""
    path = urlparse(url).path.strip("/")
    slug = path.replace("/", "-").replace("_", "-")
    return slug.strip("-") or "article"


# ---- HTML パース ----

def parse_list_page(html: str, base_url: str, list_selector: str) -> list:
    """一覧ページから記事 URL を抽出する（重複除去済み）"""
    soup = BeautifulSoup(html, "html.parser")
    seen: set = set()
    urls = []
    for tag in soup.select(list_selector):
        href = tag.get("href")
        if href:
            full_url = urljoin(base_url, href)
            if full_url not in seen:
                seen.add(full_url)
                urls.append(full_url)
    return urls


def map_category(raw: str, category_map: dict) -> str:
    """英語カテゴリ名を日本語にマッピングする"""
    return category_map.get(raw.strip().lower(), "その他")


def parse_detail_page(html: str, url: str, config: dict) -> Optional[SpinoffRecord]:
    """詳細ページから SpinoffRecord を生成する。タイトルが取得できない場合は None を返す"""
    soup = BeautifulSoup(html, "html.parser")

    title_el = soup.select_one(config["detail_title_selector"])
    if not title_el:
        return None

    summary_el = soup.select_one(config["detail_summary_selector"])
    category_el = soup.select_one(config["detail_category_selector"])

    title = title_el.get_text(strip=True)
    summary_raw = summary_el.get_text(strip=True) if summary_el else ""
    # ".field--name-body" のラベル "Body" プレフィックスを除去
    summary = summary_raw[4:].strip() if summary_raw.startswith("Body") else summary_raw
    category_raw = category_el.get("alt", "").strip() if category_el else ""
    category = map_category(category_raw, config.get("category_map", {}))

    return SpinoffRecord(
        id=generate_slug(url),
        url=url,
        title=title,
        summary=summary,
        category=category,
        fetched_at=datetime.now(timezone.utc).isoformat(),
        used=False,
        used_at=None,
    )


# ---- robots.txt ----

def is_allowed_by_robots(base_url: str, user_agent: str) -> bool:
    """robots.txt でスクレイピングが許可されているか確認する"""
    rp = RobotFileParser()
    rp.set_url(f"{base_url.rstrip('/')}/robots.txt")
    try:
        rp.read()
        return rp.can_fetch(user_agent, base_url)
    except Exception as e:
        logger.warning(f"robots.txt の取得に失敗しました（許可として扱います）: {e}")
        return True


# ---- ストア管理 ----

def load_store(store_path: Path) -> SpinoffStore:
    """既存ストアを読み込む。存在しない場合は空ストアを返す"""
    if not store_path.exists():
        return SpinoffStore(version="1.0", records=[])
    with open(store_path, encoding="utf-8") as f:
        return json.load(f)


def save_store(store: SpinoffStore, store_path: Path) -> None:
    """ストアを JSON として書き出す"""
    store_path.parent.mkdir(parents=True, exist_ok=True)
    with open(store_path, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=2)


def merge_records(existing: list, new_records: list) -> tuple:
    """既存レコードに新規レコードを URL 重複チェックしながら追記する"""
    existing_urls = {r["url"] for r in existing}
    merged = list(existing)
    added = 0
    for record in new_records:
        if record["url"] not in existing_urls:
            merged.append(record)
            existing_urls.add(record["url"])
            added += 1
    return merged, added


# ---- スクレイピング ----

def scrape(config: dict) -> list:
    """spinoff.nasa.gov をスクレイピングして SpinoffRecord リストを返す"""
    base_url = config["base_url"]
    user_agent = config["user_agent"]
    delay_min = config.get("request_delay_min", 1)
    delay_max = config.get("request_delay_max", 2)

    if not is_allowed_by_robots(base_url, user_agent):
        raise RuntimeError(f"{base_url} のスクレイピングは robots.txt により禁止されています")

    session = requests.Session()
    session.headers.update({"User-Agent": user_agent})

    logger.info(f"一覧ページを取得します: {base_url}")
    try:
        resp = session.get(base_url, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"一覧ページの取得に失敗しました: {e}")

    article_urls = parse_list_page(resp.text, base_url, config["list_selector"])
    logger.info(f"{len(article_urls)} 件の記事 URL を発見しました")

    records = []
    for i, url in enumerate(article_urls):
        logger.info(f"[{i + 1}/{len(article_urls)}] 詳細ページ取得: {url}")
        try:
            time.sleep(random.uniform(delay_min, delay_max))
            resp = session.get(url, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"詳細ページの取得に失敗しました ({url}): {e}")
            continue

        record = parse_detail_page(resp.text, url, config)
        if record:
            records.append(record)
            logger.info(f"  -> '{record['title']}' ({record['category']})")
        else:
            logger.warning(f"  -> 詳細ページのパースに失敗しました: {url}")

    return records


# ---- エントリポイント ----

def main() -> int:
    parser = argparse.ArgumentParser(description="NASA Spinoff スクレイパー")
    parser.add_argument("--fetch", action="store_true", help="spinoff.nasa.gov から新規スクレイピングを実行する")
    args = parser.parse_args()

    # ロギング設定
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler()],
    )

    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"step1_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logging.getLogger().addHandler(file_handler)

    config_path = PROJECT_ROOT / "config.json"
    store_path = PROJECT_ROOT / "data" / "spinoff_store.json"

    try:
        config = load_config(config_path)
    except FileNotFoundError:
        logger.error(f"設定ファイルが見つかりません: {config_path}")
        return 1

    store = load_store(store_path)

    if args.fetch:
        logger.info("スクレイピングを開始します...")
        try:
            new_records = scrape(config)
        except RuntimeError as e:
            logger.error(str(e))
            return 1

        merged, added = merge_records(store["records"], new_records)
        store["records"] = merged
        save_store(store, store_path)
        logger.info(f"完了: {added} 件追加 / 合計 {len(store['records'])} 件")
    else:
        logger.info(f"--fetch フラグなし: 既存ストアを参照のみ（{len(store['records'])} 件）")

    return 0


if __name__ == "__main__":
    sys.exit(main())
