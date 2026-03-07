"""Task 4 ScriptAgent テスト（TDD: RED → GREEN）

Claude Code の台本生成・承認ループはオーケストレーション内なので直接テストできない。
ここではスキーマ検証・ファイルI/Oヘルパーを TDD でテストする。
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from step3_save_script import (
    validate_script_schema,
    save_script_json,
    compute_total_duration,
)


# ---- フィクスチャ ----

SAMPLE_SCENE = {
    "id": 1,
    "voiceover": "NASAが開発したこの技術は...",
    "voiceover_en": "This technology developed by NASA...",
    "visual_note": "宇宙ステーション映像",
    "image_keywords": ["space station", "NASA technology"],
    "duration_sec": 10,
}

SAMPLE_SCRIPT = {
    "item_id": "articles-memory-foam",
    "title": "宇宙から来た低反発の秘密",
    "title_en": "The Space-Born Secret of Memory Foam",
    "hook": "実はあの枕、宇宙技術から生まれていた。",
    "hook_en": "That pillow? Born in space.",
    "scenes": [
        SAMPLE_SCENE,
        {**SAMPLE_SCENE, "id": 2, "duration_sec": 12},
        {**SAMPLE_SCENE, "id": 3, "duration_sec": 10},
    ],
    "outro": "チャンネル登録で最新情報をお届けします！",
    "outro_en": "Subscribe for the latest!",
    "total_duration_sec": 35,
}


# ---- 4.1: validate_script_schema ----

def test_validate_script_schema_valid():
    assert validate_script_schema(SAMPLE_SCRIPT) is True


def test_validate_script_schema_title_too_long():
    script = {**SAMPLE_SCRIPT, "title": "あ" * 26}
    with pytest.raises(ValueError, match="title"):
        validate_script_schema(script)


def test_validate_script_schema_title_exactly_25_chars():
    script = {**SAMPLE_SCRIPT, "title": "あ" * 25}
    assert validate_script_schema(script) is True


def test_validate_script_schema_missing_required_field():
    for field in ["item_id", "title", "title_en", "hook", "hook_en", "scenes", "outro", "outro_en"]:
        script = {k: v for k, v in SAMPLE_SCRIPT.items() if k != field}
        with pytest.raises(ValueError, match=field):
            validate_script_schema(script)


def test_validate_script_schema_image_keywords_too_few():
    bad_scene = {**SAMPLE_SCENE, "image_keywords": ["space"]}
    script = {**SAMPLE_SCRIPT, "scenes": [bad_scene]}
    with pytest.raises(ValueError, match="image_keywords"):
        validate_script_schema(script)


def test_validate_script_schema_image_keywords_too_many():
    bad_scene = {**SAMPLE_SCENE, "image_keywords": ["a", "b", "c", "d", "e"]}
    script = {**SAMPLE_SCRIPT, "scenes": [bad_scene]}
    with pytest.raises(ValueError, match="image_keywords"):
        validate_script_schema(script)


def test_validate_script_schema_image_keywords_boundary_2():
    scene = {**SAMPLE_SCENE, "image_keywords": ["space", "nasa"]}
    script = {**SAMPLE_SCRIPT, "scenes": [scene]}
    assert validate_script_schema(script) is True


def test_validate_script_schema_image_keywords_boundary_4():
    scene = {**SAMPLE_SCENE, "image_keywords": ["a", "b", "c", "d"]}
    script = {**SAMPLE_SCRIPT, "scenes": [scene]}
    assert validate_script_schema(script) is True


def test_validate_script_schema_scene_missing_fields():
    bad_scene = {"id": 1, "voiceover": "test"}  # 必須フィールド不足
    script = {**SAMPLE_SCRIPT, "scenes": [bad_scene]}
    with pytest.raises(ValueError):
        validate_script_schema(script)


def test_validate_script_schema_empty_scenes():
    script = {**SAMPLE_SCRIPT, "scenes": []}
    with pytest.raises(ValueError, match="scenes"):
        validate_script_schema(script)


# ---- 4.1: compute_total_duration ----

def test_compute_total_duration_sums_scenes():
    # scenes: 10+12+10=32, hook=3, outro=5 assumed defaults
    total = compute_total_duration(SAMPLE_SCRIPT, hook_sec=3, outro_sec=5)
    assert total == 32 + 3 + 5


def test_compute_total_duration_no_extras():
    total = compute_total_duration(SAMPLE_SCRIPT, hook_sec=0, outro_sec=0)
    assert total == 10 + 12 + 10


def test_compute_total_duration_exceeds_60():
    long_scenes = [{**SAMPLE_SCENE, "id": i, "duration_sec": 15} for i in range(5)]
    script = {**SAMPLE_SCRIPT, "scenes": long_scenes}
    total = compute_total_duration(script, hook_sec=3, outro_sec=5)
    assert total > 60


# ---- 4.2: save_script_json ----

def test_save_script_json_creates_file(tmp_path):
    out = tmp_path / "script_test.json"
    save_script_json(SAMPLE_SCRIPT, output_path=out)
    assert out.exists()


def test_save_script_json_valid_content(tmp_path):
    out = tmp_path / "script_test.json"
    save_script_json(SAMPLE_SCRIPT, output_path=out)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["item_id"] == SAMPLE_SCRIPT["item_id"]
    assert data["title"] == SAMPLE_SCRIPT["title"]
    assert len(data["scenes"]) == len(SAMPLE_SCRIPT["scenes"])


def test_save_script_json_uses_item_id_in_filename(tmp_path):
    save_script_json(SAMPLE_SCRIPT, output_path=tmp_path / f"script_{SAMPLE_SCRIPT['item_id']}.json")
    expected = tmp_path / f"script_{SAMPLE_SCRIPT['item_id']}.json"
    assert expected.exists()


def test_save_script_json_rejects_invalid_schema(tmp_path):
    bad = {**SAMPLE_SCRIPT, "title": "あ" * 30}
    out = tmp_path / "bad.json"
    with pytest.raises(ValueError, match="title"):
        save_script_json(bad, output_path=out)
    assert not out.exists()
