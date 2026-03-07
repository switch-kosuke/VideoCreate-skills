"""Task 3 TopicSelector テスト（TDD: RED → GREEN）

TopicSelector の Claude Code 会話部分（スコアリング・表示）はオーケストレーション内なので
直接テストできない。ここではファイルI/Oヘルパー関数を TDD でテストする。
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from step2_save_selection import (
    save_selected_item,
    update_store_used_flag,
    validate_selected_item,
    load_store,
)


# ---- フィクスチャ ----

SAMPLE_RECORD = {
    "id": "articles-memory-foam",
    "url": "https://spinoff.nasa.gov/articles/memory-foam",
    "title": "Memory Foam",
    "summary": "NASA developed memory foam for crash protection.",
    "category": "医療",
    "fetched_at": "2026-03-07T00:00:00+00:00",
    "used": False,
    "used_at": None,
}

SAMPLE_STORE = {
    "version": "1.0",
    "records": [SAMPLE_RECORD],
}


# ---- 3.2: validate_selected_item ----

def test_validate_selected_item_valid():
    item = {
        "record": SAMPLE_RECORD,
        "viral_score": 8,
        "selected_at": "2026-03-07T10:00:00+00:00",
    }
    assert validate_selected_item(item) is True


def test_validate_selected_item_missing_record():
    item = {"viral_score": 8, "selected_at": "2026-03-07T10:00:00+00:00"}
    with pytest.raises(ValueError, match="record"):
        validate_selected_item(item)


def test_validate_selected_item_score_out_of_range_low():
    item = {"record": SAMPLE_RECORD, "viral_score": 0, "selected_at": "2026-03-07T10:00:00+00:00"}
    with pytest.raises(ValueError, match="viral_score"):
        validate_selected_item(item)


def test_validate_selected_item_score_out_of_range_high():
    item = {"record": SAMPLE_RECORD, "viral_score": 11, "selected_at": "2026-03-07T10:00:00+00:00"}
    with pytest.raises(ValueError, match="viral_score"):
        validate_selected_item(item)


def test_validate_selected_item_score_boundary_values():
    for score in [1, 10]:
        item = {"record": SAMPLE_RECORD, "viral_score": score, "selected_at": "2026-03-07T10:00:00+00:00"}
        assert validate_selected_item(item) is True


def test_validate_selected_item_missing_selected_at():
    item = {"record": SAMPLE_RECORD, "viral_score": 8}
    with pytest.raises(ValueError, match="selected_at"):
        validate_selected_item(item)


# ---- 3.2: save_selected_item ----

def test_save_selected_item_creates_file(tmp_path):
    out = tmp_path / "selected_item.json"
    save_selected_item(SAMPLE_RECORD, viral_score=9, output_path=out)
    assert out.exists()


def test_save_selected_item_json_schema(tmp_path):
    out = tmp_path / "selected_item.json"
    save_selected_item(SAMPLE_RECORD, viral_score=9, output_path=out)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert "record" in data
    assert "viral_score" in data
    assert "selected_at" in data
    assert data["viral_score"] == 9
    assert data["record"]["id"] == SAMPLE_RECORD["id"]


def test_save_selected_item_selected_at_is_iso8601(tmp_path):
    out = tmp_path / "selected_item.json"
    save_selected_item(SAMPLE_RECORD, viral_score=7, output_path=out)
    data = json.loads(out.read_text(encoding="utf-8"))
    # ISO 8601 パース確認
    datetime.fromisoformat(data["selected_at"])


def test_save_selected_item_overwrites_existing(tmp_path):
    out = tmp_path / "selected_item.json"
    save_selected_item(SAMPLE_RECORD, viral_score=5, output_path=out)
    save_selected_item(SAMPLE_RECORD, viral_score=9, output_path=out)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["viral_score"] == 9


# ---- 3.2: update_store_used_flag ----

def test_load_store_reads_existing(tmp_path):
    p = tmp_path / "store.json"
    p.write_text(json.dumps(SAMPLE_STORE), encoding="utf-8")
    store = load_store(p)
    assert len(store["records"]) == 1


def test_update_store_used_flag_sets_used_true(tmp_path):
    store_path = tmp_path / "spinoff_store.json"
    store_path.write_text(json.dumps(SAMPLE_STORE), encoding="utf-8")

    update_store_used_flag(store_path, url=SAMPLE_RECORD["url"])

    updated = json.loads(store_path.read_text(encoding="utf-8"))
    record = updated["records"][0]
    assert record["used"] is True


def test_update_store_used_flag_sets_used_at(tmp_path):
    store_path = tmp_path / "spinoff_store.json"
    store_path.write_text(json.dumps(SAMPLE_STORE), encoding="utf-8")

    update_store_used_flag(store_path, url=SAMPLE_RECORD["url"])

    updated = json.loads(store_path.read_text(encoding="utf-8"))
    used_at = updated["records"][0]["used_at"]
    assert used_at is not None
    datetime.fromisoformat(used_at)  # ISO 8601 であること


def test_update_store_used_flag_unknown_url_raises(tmp_path):
    store_path = tmp_path / "spinoff_store.json"
    store_path.write_text(json.dumps(SAMPLE_STORE), encoding="utf-8")

    with pytest.raises(ValueError, match="URL"):
        update_store_used_flag(store_path, url="https://spinoff.nasa.gov/unknown")


def test_update_store_used_flag_preserves_other_records(tmp_path):
    store = {
        "version": "1.0",
        "records": [
            SAMPLE_RECORD,
            {**SAMPLE_RECORD, "id": "other", "url": "https://spinoff.nasa.gov/other", "used": False},
        ],
    }
    store_path = tmp_path / "spinoff_store.json"
    store_path.write_text(json.dumps(store), encoding="utf-8")

    update_store_used_flag(store_path, url=SAMPLE_RECORD["url"])

    updated = json.loads(store_path.read_text(encoding="utf-8"))
    other = next(r for r in updated["records"] if r["url"] == "https://spinoff.nasa.gov/other")
    assert other["used"] is False  # 他レコードは変更されない
