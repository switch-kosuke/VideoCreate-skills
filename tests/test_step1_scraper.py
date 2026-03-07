"""Task 2 SpinoffScraper テスト（TDD: RED → GREEN）"""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from step1_scrape import (
    generate_slug,
    load_store,
    map_category,
    merge_records,
    parse_detail_page,
    parse_list_page,
    save_store,
)

# ---- HTML フィクスチャ ----

LIST_PAGE_HTML = """
<html><body>
  <a class="feature" href="/articles/memory-foam">Memory Foam</a>
  <a class="feature" href="/articles/scratch-resistant-lenses">Scratch Resistant Lenses</a>
  <a class="other" href="/not-an-article">Not an article</a>
</body></html>
"""

DETAIL_PAGE_HTML = """
<html><body>
  <h1 class="page-title">Memory Foam</h1>
  <div class="field--name-body"><p>NASA developed memory foam to improve crash protection for aircraft seats.</p></div>
  <div class="field--name-field-category">Medical</div>
</body></html>
"""

DETAIL_CONFIG = {
    "detail_title_selector": "h1.page-title",
    "detail_summary_selector": ".field--name-body",
    "detail_category_selector": ".field--name-field-category",
    "category_map": {
        "medical": "医療",
        "food": "食品",
        "environment": "環境",
        "consumer/home/recreation": "日用品",
    },
}


# ---- Task 2.1: スクレイピングロジック ----

def test_generate_slug_simple_path():
    assert generate_slug("https://spinoff.nasa.gov/articles/memory-foam") == "articles-memory-foam"


def test_generate_slug_with_underscores():
    assert generate_slug("https://spinoff.nasa.gov/articles/scratch_resistant") == "articles-scratch-resistant"


def test_generate_slug_root_path_not_empty():
    result = generate_slug("https://spinoff.nasa.gov/")
    assert len(result) > 0


def test_parse_list_page_extracts_feature_urls():
    urls = parse_list_page(LIST_PAGE_HTML, "https://spinoff.nasa.gov", "a.feature")
    assert len(urls) == 2
    assert "https://spinoff.nasa.gov/articles/memory-foam" in urls
    assert "https://spinoff.nasa.gov/articles/scratch-resistant-lenses" in urls


def test_parse_list_page_ignores_non_feature_links():
    urls = parse_list_page(LIST_PAGE_HTML, "https://spinoff.nasa.gov", "a.feature")
    assert not any("not-an-article" in u for u in urls)


def test_parse_list_page_deduplicates():
    html = '<a class="feature" href="/a">A</a><a class="feature" href="/a">A dup</a>'
    urls = parse_list_page(html, "https://spinoff.nasa.gov", "a.feature")
    assert len(urls) == 1


def test_parse_detail_page_extracts_title():
    record = parse_detail_page(DETAIL_PAGE_HTML, "https://spinoff.nasa.gov/articles/memory-foam", DETAIL_CONFIG)
    assert record is not None
    assert record["title"] == "Memory Foam"


def test_parse_detail_page_extracts_summary():
    record = parse_detail_page(DETAIL_PAGE_HTML, "https://spinoff.nasa.gov/articles/memory-foam", DETAIL_CONFIG)
    assert record is not None
    assert "crash protection" in record["summary"]


def test_parse_detail_page_maps_category_to_japanese():
    record = parse_detail_page(DETAIL_PAGE_HTML, "https://spinoff.nasa.gov/articles/memory-foam", DETAIL_CONFIG)
    assert record is not None
    assert record["category"] == "医療"


def test_parse_detail_page_sets_used_false_and_used_at_none():
    record = parse_detail_page(DETAIL_PAGE_HTML, "https://spinoff.nasa.gov/articles/memory-foam", DETAIL_CONFIG)
    assert record is not None
    assert record["used"] is False
    assert record["used_at"] is None


def test_parse_detail_page_returns_none_when_title_missing():
    html = "<html><body><p>No title here</p></body></html>"
    record = parse_detail_page(html, "https://example.com/x", DETAIL_CONFIG)
    assert record is None


def test_parse_detail_page_record_has_all_required_fields():
    record = parse_detail_page(DETAIL_PAGE_HTML, "https://spinoff.nasa.gov/articles/memory-foam", DETAIL_CONFIG)
    assert record is not None
    for field in ["id", "url", "title", "summary", "category", "fetched_at", "used", "used_at"]:
        assert field in record, f"フィールド '{field}' が SpinoffRecord に含まれていません"


def test_map_category_known_value():
    assert map_category("Medical", {"medical": "医療"}) == "医療"


def test_map_category_case_insensitive():
    assert map_category("MEDICAL", {"medical": "医療"}) == "医療"


def test_map_category_unknown_defaults_to_other():
    assert map_category("Quantum Computing", {}) == "その他"


# ---- Task 2.2: 永続ストア管理 ----

def test_load_store_returns_empty_when_not_exists(tmp_path):
    store = load_store(tmp_path / "nonexistent.json")
    assert store["version"] == "1.0"
    assert store["records"] == []


def test_load_store_reads_existing_json(tmp_path):
    data = {
        "version": "1.0",
        "records": [
            {
                "id": "test", "url": "https://example.com", "title": "Test",
                "summary": "", "category": "その他",
                "fetched_at": "2024-01-01T00:00:00+00:00",
                "used": False, "used_at": None,
            }
        ],
    }
    path = tmp_path / "store.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    store = load_store(path)
    assert len(store["records"]) == 1
    assert store["records"][0]["id"] == "test"


def test_save_store_writes_valid_json(tmp_path):
    store = {"version": "1.0", "records": []}
    path = tmp_path / "store.json"
    save_store(store, path)
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["version"] == "1.0"
    assert loaded["records"] == []


def test_save_store_creates_parent_directory(tmp_path):
    store = {"version": "1.0", "records": []}
    path = tmp_path / "nested" / "deep" / "store.json"
    save_store(store, path)
    assert path.exists()


def test_merge_records_adds_new_record():
    existing = [
        {"url": "https://example.com/a", "id": "a", "title": "A",
         "summary": "", "category": "その他", "fetched_at": "", "used": False, "used_at": None},
    ]
    new = [
        {"url": "https://example.com/b", "id": "b", "title": "B",
         "summary": "", "category": "その他", "fetched_at": "", "used": False, "used_at": None},
    ]
    merged, added = merge_records(existing, new)
    assert added == 1
    assert len(merged) == 2


def test_merge_records_skips_duplicate_url():
    record = {
        "url": "https://example.com/a", "id": "a", "title": "A",
        "summary": "", "category": "その他", "fetched_at": "", "used": False, "used_at": None,
    }
    merged, added = merge_records([record], [record])
    assert added == 0
    assert len(merged) == 1


def test_merge_records_preserves_existing_used_flag():
    existing = [
        {"url": "https://example.com/a", "id": "a", "title": "A",
         "summary": "", "category": "その他", "fetched_at": "", "used": True, "used_at": "2024-01-01"},
    ]
    new = [
        {"url": "https://example.com/a", "id": "a", "title": "A",
         "summary": "", "category": "その他", "fetched_at": "", "used": False, "used_at": None},
    ]
    merged, _ = merge_records(existing, new)
    assert merged[0]["used"] is True  # 既存レコードが保持される


def test_merge_records_multiple_new_deduped():
    existing = []
    new = [
        {"url": "https://example.com/a", "id": "a", "title": "A",
         "summary": "", "category": "その他", "fetched_at": "", "used": False, "used_at": None},
        {"url": "https://example.com/a", "id": "a", "title": "A dup",
         "summary": "", "category": "その他", "fetched_at": "", "used": False, "used_at": None},
    ]
    merged, added = merge_records(existing, new)
    assert added == 1
    assert len(merged) == 1
