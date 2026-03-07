"""Task 8 RenderPreparer テスト（TDD: RED → GREEN）

step6_prepare_render.py の純粋ロジック（マニフェストマージ・パス検証）を TDD でテストする。
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from step6_prepare_render import (
    load_json,
    check_required_files,
    merge_render_props,
    save_render_props,
)


# ---- フィクスチャ ----

SAMPLE_SCRIPT = {
    "item_id": "test-001",
    "title": "テストタイトル",
    "title_en": "Test Title",
    "hook": "フック",
    "hook_en": "Hook",
    "scenes": [
        {
            "id": 1,
            "voiceover": "ナレーション",
            "voiceover_en": "Narration",
            "visual_note": "ビジュアル",
            "image_keywords": ["space", "nasa"],
            "duration_sec": 10,
        }
    ],
    "outro": "アウトロ",
    "outro_en": "Outro",
    "total_duration_sec": 18,
}

SAMPLE_AUDIO_MANIFEST = {
    "item_id": "test-001",
    "generated_at": "2026-01-01T00:00:00Z",
    "ja_voice": "ja-JP-NanamiNeural",
    "en_voice": "en-US-JennyNeural",
    "scenes": [
        {
            "scene_id": "hook",
            "ja_text": "フック",
            "en_text": "Hook",
            "ja_path": "audio/ja/scene_hook.mp3",
            "en_path": "audio/en/scene_hook.mp3",
        },
        {
            "scene_id": "1",
            "ja_text": "ナレーション",
            "en_text": "Narration",
            "ja_path": "audio/ja/scene_1.mp3",
            "en_path": "audio/en/scene_1.mp3",
        },
        {
            "scene_id": "outro",
            "ja_text": "アウトロ",
            "en_text": "Outro",
            "ja_path": "audio/ja/scene_outro.mp3",
            "en_path": "audio/en/scene_outro.mp3",
        },
    ],
}

SAMPLE_ASSETS_MANIFEST = {
    "item_id": "test-001",
    "generated_at": "2026-01-01T00:00:00Z",
    "scenes": [
        {
            "scene_id": "hook",
            "source": "nasa",
            "local_path": "assets/hook/nasa_img.jpg",
            "license": "NASA Public Domain",
            "original_url": "https://example.com/img.jpg",
        },
        {
            "scene_id": "1",
            "source": "pexels",
            "local_path": "assets/scene_1/pexels_img.jpg",
            "license": "Pexels License",
            "original_url": "https://pexels.com/img.jpg",
        },
        {
            "scene_id": "outro",
            "source": "fallback",
            "local_path": "",
            "license": "",
            "original_url": "",
        },
    ],
    "bgm": {},
}


# ---- load_json ----

def test_load_json_returns_dict(tmp_path):
    f = tmp_path / "test.json"
    f.write_text(json.dumps({"key": "value"}), encoding="utf-8")
    data = load_json(f)
    assert data == {"key": "value"}


def test_load_json_raises_for_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_json(tmp_path / "nonexistent.json")


def test_load_json_raises_for_invalid_json(tmp_path):
    f = tmp_path / "bad.json"
    f.write_text("not json", encoding="utf-8")
    with pytest.raises(ValueError):
        load_json(f)


# ---- check_required_files ----

def test_check_required_files_all_exist(tmp_path):
    script = tmp_path / "script.json"
    audio = tmp_path / "audio.json"
    assets = tmp_path / "assets.json"
    for f in [script, audio, assets]:
        f.write_text("{}", encoding="utf-8")
    # 例外なし
    check_required_files(script, audio, assets)


def test_check_required_files_missing_script(tmp_path):
    audio = tmp_path / "audio.json"
    assets = tmp_path / "assets.json"
    audio.write_text("{}", encoding="utf-8")
    assets.write_text("{}", encoding="utf-8")
    with pytest.raises(FileNotFoundError, match="script"):
        check_required_files(tmp_path / "script.json", audio, assets)


def test_check_required_files_missing_audio(tmp_path):
    script = tmp_path / "script.json"
    assets = tmp_path / "assets.json"
    script.write_text("{}", encoding="utf-8")
    assets.write_text("{}", encoding="utf-8")
    with pytest.raises(FileNotFoundError, match="audio"):
        check_required_files(script, tmp_path / "audio.json", assets)


def test_check_required_files_missing_assets(tmp_path):
    script = tmp_path / "script.json"
    audio = tmp_path / "audio.json"
    script.write_text("{}", encoding="utf-8")
    audio.write_text("{}", encoding="utf-8")
    with pytest.raises(FileNotFoundError, match="assets"):
        check_required_files(script, audio, tmp_path / "assets.json")


# ---- merge_render_props ----

def test_merge_render_props_contains_script():
    props = merge_render_props(SAMPLE_SCRIPT, SAMPLE_AUDIO_MANIFEST, SAMPLE_ASSETS_MANIFEST, lang="ja")
    assert props["script"]["item_id"] == "test-001"
    assert props["script"]["title"] == "テストタイトル"


def test_merge_render_props_contains_audio_manifest():
    props = merge_render_props(SAMPLE_SCRIPT, SAMPLE_AUDIO_MANIFEST, SAMPLE_ASSETS_MANIFEST, lang="ja")
    assert "audioManifest" in props
    assert props["audioManifest"]["ja_voice"] == "ja-JP-NanamiNeural"


def test_merge_render_props_contains_assets_manifest():
    props = merge_render_props(SAMPLE_SCRIPT, SAMPLE_AUDIO_MANIFEST, SAMPLE_ASSETS_MANIFEST, lang="ja")
    assert "assetsManifest" in props
    assert len(props["assetsManifest"]["scenes"]) == 3


def test_merge_render_props_lang_ja():
    props = merge_render_props(SAMPLE_SCRIPT, SAMPLE_AUDIO_MANIFEST, SAMPLE_ASSETS_MANIFEST, lang="ja")
    assert props["lang"] == "ja"


def test_merge_render_props_lang_en():
    props = merge_render_props(SAMPLE_SCRIPT, SAMPLE_AUDIO_MANIFEST, SAMPLE_ASSETS_MANIFEST, lang="en")
    assert props["lang"] == "en"


def test_merge_render_props_item_id_match():
    props = merge_render_props(SAMPLE_SCRIPT, SAMPLE_AUDIO_MANIFEST, SAMPLE_ASSETS_MANIFEST, lang="ja")
    assert props["item_id"] == "test-001"


def test_merge_render_props_has_generated_at():
    props = merge_render_props(SAMPLE_SCRIPT, SAMPLE_AUDIO_MANIFEST, SAMPLE_ASSETS_MANIFEST, lang="ja")
    assert "generated_at" in props


# ---- save_render_props ----

def test_save_render_props_creates_file(tmp_path):
    props = merge_render_props(SAMPLE_SCRIPT, SAMPLE_AUDIO_MANIFEST, SAMPLE_ASSETS_MANIFEST)
    out = tmp_path / "render_props.json"
    save_render_props(props, out)
    assert out.exists()


def test_save_render_props_valid_json(tmp_path):
    props = merge_render_props(SAMPLE_SCRIPT, SAMPLE_AUDIO_MANIFEST, SAMPLE_ASSETS_MANIFEST)
    out = tmp_path / "render_props.json"
    save_render_props(props, out)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["item_id"] == "test-001"
    assert "script" in data
    assert "audioManifest" in data
    assert "assetsManifest" in data


def test_save_render_props_creates_parent_dirs(tmp_path):
    props = merge_render_props(SAMPLE_SCRIPT, SAMPLE_AUDIO_MANIFEST, SAMPLE_ASSETS_MANIFEST)
    out = tmp_path / "data" / "render_props.json"
    save_render_props(props, out)
    assert out.exists()
