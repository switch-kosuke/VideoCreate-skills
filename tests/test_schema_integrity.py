"""Task 11.2 スキーマ整合性テスト

Step 1→2→3→4→5→6 間の JSON スキーマ整合性を検証する。
各ステップの出力フォーマットが次ステップの入力として有効であることを確認する。
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from step3_save_script import validate_script_schema, compute_total_duration
from step6_prepare_render import merge_render_props


# ---- フィクスチャ ----

VALID_SCRIPT = {
    "item_id": "test-001",
    "title": "テストタイトル",
    "title_en": "Test Title",
    "hook": "フック",
    "hook_en": "Hook",
    "scenes": [
        {
            "id": 1,
            "voiceover": "ナレーション1",
            "voiceover_en": "Narration 1",
            "visual_note": "ビジュアル",
            "image_keywords": ["space", "nasa"],
            "duration_sec": 10,
        },
        {
            "id": 2,
            "voiceover": "ナレーション2",
            "voiceover_en": "Narration 2",
            "visual_note": "ビジュアル2",
            "image_keywords": ["technology", "innovation"],
            "duration_sec": 10,
        },
    ],
    "outro": "アウトロ",
    "outro_en": "Outro",
    "total_duration_sec": 28,
}

VALID_STORE = {
    "version": "1.0",
    "records": [
        {
            "id": "memory-foam",
            "url": "https://spinoff.nasa.gov/Spinoff2024/hm_1.html",
            "title": "Memory Foam",
            "summary": "NASA developed memory foam...",
            "category": "医療",
            "fetched_at": "2026-01-01T00:00:00+00:00",
            "used": False,
            "used_at": None,
        }
    ],
}

VALID_AUDIO_MANIFEST = {
    "item_id": "test-001",
    "generated_at": "2026-01-01T00:00:00Z",
    "ja_voice": "ja-JP-NanamiNeural",
    "en_voice": "en-US-JennyNeural",
    "scenes": [
        {"scene_id": "hook", "ja_text": "フック", "en_text": "Hook",
         "ja_path": "audio/ja/scene_hook.mp3", "en_path": "audio/en/scene_hook.mp3"},
        {"scene_id": "1", "ja_text": "ナレーション1", "en_text": "Narration 1",
         "ja_path": "audio/ja/scene_1.mp3", "en_path": "audio/en/scene_1.mp3"},
        {"scene_id": "2", "ja_text": "ナレーション2", "en_text": "Narration 2",
         "ja_path": "audio/ja/scene_2.mp3", "en_path": "audio/en/scene_2.mp3"},
        {"scene_id": "outro", "ja_text": "アウトロ", "en_text": "Outro",
         "ja_path": "audio/ja/scene_outro.mp3", "en_path": "audio/en/scene_outro.mp3"},
    ],
}

VALID_ASSETS_MANIFEST = {
    "item_id": "test-001",
    "generated_at": "2026-01-01T00:00:00Z",
    "scenes": [
        {"scene_id": "hook", "source": "nasa", "local_path": "assets/hook/img.jpg",
         "license": "NASA Public Domain", "original_url": "https://x.com/img.jpg"},
        {"scene_id": "1", "source": "pexels", "local_path": "assets/scene_1/img.jpg",
         "license": "Pexels License", "original_url": "https://p.com/img.jpg"},
        {"scene_id": "2", "source": "fallback", "local_path": "", "license": "", "original_url": ""},
        {"scene_id": "outro", "source": "nasa", "local_path": "assets/outro/img.jpg",
         "license": "NASA Public Domain", "original_url": "https://x.com/img2.jpg"},
    ],
    "bgm": {},
}


# ---- 11.2a: 台本 JSON スキーマ検証 ----

def test_script_schema_valid_passes():
    assert validate_script_schema(VALID_SCRIPT) is True


def test_script_total_duration_le_60():
    total = compute_total_duration(VALID_SCRIPT)
    assert total <= 60, f"total_duration_sec={total} は 60秒以内でなければなりません"


def test_script_title_le_25_chars():
    assert len(VALID_SCRIPT["title"]) <= 25


def test_script_all_required_fields_present():
    required = ["item_id", "title", "title_en", "hook", "hook_en", "scenes", "outro", "outro_en"]
    for field in required:
        assert field in VALID_SCRIPT, f"必須フィールド '{field}' が不足しています"


def test_script_scenes_image_keywords_2_to_4():
    for scene in VALID_SCRIPT["scenes"]:
        kw = scene["image_keywords"]
        assert 2 <= len(kw) <= 4, f"scene[{scene['id']}] の image_keywords が {len(kw)} 語"


def test_script_schema_rejects_long_title():
    bad_script = {**VALID_SCRIPT, "title": "あ" * 26}
    with pytest.raises(ValueError, match="title"):
        validate_script_schema(bad_script)


def test_script_schema_rejects_empty_scenes():
    bad_script = {**VALID_SCRIPT, "scenes": []}
    with pytest.raises(ValueError, match="scenes"):
        validate_script_schema(bad_script)


def test_script_schema_rejects_too_few_keywords():
    bad_scene = {**VALID_SCRIPT["scenes"][0], "image_keywords": ["only_one"]}
    bad_script = {**VALID_SCRIPT, "scenes": [bad_scene]}
    with pytest.raises(ValueError, match="image_keywords"):
        validate_script_schema(bad_script)


# ---- 11.2b: Step 1→2 間スキーマ整合性（spinoff_store.json → TopicSelector） ----

def test_store_has_version_field():
    assert "version" in VALID_STORE


def test_store_has_records_field():
    assert "records" in VALID_STORE
    assert isinstance(VALID_STORE["records"], list)


def test_store_record_has_required_fields():
    required = ["id", "url", "title", "summary", "category", "fetched_at", "used", "used_at"]
    for field in required:
        assert field in VALID_STORE["records"][0], f"record に '{field}' が不足"


def test_store_record_used_is_bool():
    assert isinstance(VALID_STORE["records"][0]["used"], bool)


def test_store_unused_records_selectable():
    unused = [r for r in VALID_STORE["records"] if not r["used"]]
    assert len(unused) >= 1


# ---- 11.2c: Step 3→4 間スキーマ整合性（script → AssetFetcher/VoiceGenerator） ----

def test_script_scenes_have_image_keywords():
    for scene in VALID_SCRIPT["scenes"]:
        assert "image_keywords" in scene
        assert len(scene["image_keywords"]) >= 2


def test_script_scenes_have_voiceover():
    for scene in VALID_SCRIPT["scenes"]:
        assert "voiceover" in scene
        assert "voiceover_en" in scene
        assert len(scene["voiceover"]) > 0
        assert len(scene["voiceover_en"]) > 0


def test_script_has_hook_and_outro_text():
    assert len(VALID_SCRIPT["hook"]) > 0
    assert len(VALID_SCRIPT["hook_en"]) > 0
    assert len(VALID_SCRIPT["outro"]) > 0
    assert len(VALID_SCRIPT["outro_en"]) > 0


# ---- 11.2d: Step 5→6 間マニフェスト整合性（audio_manifest → render_props） ----

def test_audio_manifest_scenes_cover_all_script_scenes():
    script_scene_ids = {"hook", "outro"} | {str(s["id"]) for s in VALID_SCRIPT["scenes"]}
    manifest_scene_ids = {s["scene_id"] for s in VALID_AUDIO_MANIFEST["scenes"]}
    assert script_scene_ids == manifest_scene_ids


def test_audio_manifest_has_ja_en_paths():
    for scene in VALID_AUDIO_MANIFEST["scenes"]:
        assert "ja_path" in scene
        assert "en_path" in scene
        assert scene["ja_path"].endswith(".mp3")
        assert scene["en_path"].endswith(".mp3")


def test_render_props_merges_all_three_manifests():
    props = merge_render_props(VALID_SCRIPT, VALID_AUDIO_MANIFEST, VALID_ASSETS_MANIFEST)
    assert "script" in props
    assert "audioManifest" in props
    assert "assetsManifest" in props
    assert props["script"]["item_id"] == props["audioManifest"]["item_id"]
    assert props["script"]["item_id"] == props["assetsManifest"]["item_id"]


def test_render_props_item_ids_consistent():
    props = merge_render_props(VALID_SCRIPT, VALID_AUDIO_MANIFEST, VALID_ASSETS_MANIFEST)
    assert props["item_id"] == "test-001"


def test_render_props_default_lang_is_ja():
    props = merge_render_props(VALID_SCRIPT, VALID_AUDIO_MANIFEST, VALID_ASSETS_MANIFEST)
    assert props["lang"] == "ja"
