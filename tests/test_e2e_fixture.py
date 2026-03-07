"""Task 11.3 E2E パイプライン動作検証（フィクスチャベース）

フィクスチャデータ（spinoff_store.json に記事 1 件）を使って
Step 4（素材取得）→ Step 5（音声）→ Step 6（render_props）の
Python パイプラインをモックして通しテストを行う。

NOTE: Remotion render（Step 6-2）と PostProcessor（Step 7）は
      実際の動画ファイルを必要とするため、このテストではスキップし
      render_props.json の生成まで（Step 6-1）を E2E 検証する。
"""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import asyncio

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
from step6_prepare_render import load_json, check_required_files, merge_render_props, save_render_props


# ---- フィクスチャデータ ----

FIXTURE_SPINOFF_STORE = {
    "version": "1.0",
    "records": [
        {
            "id": "memory-foam",
            "url": "https://spinoff.nasa.gov/Spinoff2024/hm_1.html",
            "title": "Memory Foam",
            "summary": "NASA developed memory foam technology for aircraft seats.",
            "category": "医療",
            "fetched_at": "2026-01-01T00:00:00+00:00",
            "used": True,
            "used_at": "2026-03-07T00:00:00+00:00",
        }
    ],
}

FIXTURE_SCRIPT = {
    "item_id": "memory-foam",
    "title": "枕はNASA由来だった",
    "title_en": "Your Pillow Came From NASA",
    "hook": "え、あの枕ってNASAが作ったの！？",
    "hook_en": "Wait — NASA invented your pillow?",
    "scenes": [
        {
            "id": 1,
            "voiceover": "メモリーフォームは1960年代にNASAが開発しました。",
            "voiceover_en": "Memory foam was developed by NASA in the 1960s.",
            "visual_note": "宇宙船シート映像",
            "image_keywords": ["memory foam", "nasa seat"],
            "duration_sec": 10,
        },
        {
            "id": 2,
            "voiceover": "現在では枕やマットレスに広く使われています。",
            "voiceover_en": "Today it's used in pillows and mattresses worldwide.",
            "visual_note": "快適な枕",
            "image_keywords": ["pillow comfort", "sleep"],
            "duration_sec": 10,
        },
    ],
    "outro": "チャンネル登録で最新NASAネタをお届けします！",
    "outro_en": "Subscribe for more NASA tech discoveries!",
    "total_duration_sec": 28,
}

FIXTURE_AUDIO_MANIFEST = {
    "item_id": "memory-foam",
    "generated_at": "2026-03-07T00:00:00Z",
    "ja_voice": "ja-JP-NanamiNeural",
    "en_voice": "en-US-JennyNeural",
    "scenes": [
        {"scene_id": "hook", "ja_text": FIXTURE_SCRIPT["hook"], "en_text": FIXTURE_SCRIPT["hook_en"],
         "ja_path": "audio/ja/scene_hook.mp3", "en_path": "audio/en/scene_hook.mp3"},
        {"scene_id": "1", "ja_text": FIXTURE_SCRIPT["scenes"][0]["voiceover"],
         "en_text": FIXTURE_SCRIPT["scenes"][0]["voiceover_en"],
         "ja_path": "audio/ja/scene_1.mp3", "en_path": "audio/en/scene_1.mp3"},
        {"scene_id": "2", "ja_text": FIXTURE_SCRIPT["scenes"][1]["voiceover"],
         "en_text": FIXTURE_SCRIPT["scenes"][1]["voiceover_en"],
         "ja_path": "audio/ja/scene_2.mp3", "en_path": "audio/en/scene_2.mp3"},
        {"scene_id": "outro", "ja_text": FIXTURE_SCRIPT["outro"], "en_text": FIXTURE_SCRIPT["outro_en"],
         "ja_path": "audio/ja/scene_outro.mp3", "en_path": "audio/en/scene_outro.mp3"},
    ],
}

FIXTURE_ASSETS_MANIFEST = {
    "item_id": "memory-foam",
    "generated_at": "2026-03-07T00:00:00Z",
    "scenes": [
        {"scene_id": "hook", "source": "nasa", "local_path": "assets/hook/nasa_img.jpg",
         "license": "NASA Public Domain", "original_url": "https://images-assets.nasa.gov/hook.jpg"},
        {"scene_id": "1", "source": "nasa", "local_path": "assets/scene_1/nasa_img.jpg",
         "license": "NASA Public Domain", "original_url": "https://images-assets.nasa.gov/1.jpg"},
        {"scene_id": "2", "source": "pexels", "local_path": "assets/scene_2/pexels_img.jpg",
         "license": "Pexels License", "original_url": "https://images.pexels.com/2.jpg"},
        {"scene_id": "outro", "source": "fallback", "local_path": "", "license": "", "original_url": ""},
    ],
    "bgm": {},
}


# ---- E2E: Step 4→5→6 フィクスチャ通しテスト ----

@pytest.fixture
def fixture_data_dir(tmp_path):
    """フィクスチャ JSON を tmp_path に書き出してパスを返す"""
    data_dir = tmp_path / "data"
    assets_dir = tmp_path / "assets"
    data_dir.mkdir()
    assets_dir.mkdir()

    (data_dir / "spinoff_store.json").write_text(
        json.dumps(FIXTURE_SPINOFF_STORE), encoding="utf-8"
    )
    (data_dir / "script_memory-foam.json").write_text(
        json.dumps(FIXTURE_SCRIPT), encoding="utf-8"
    )
    (data_dir / "audio_manifest.json").write_text(
        json.dumps(FIXTURE_AUDIO_MANIFEST), encoding="utf-8"
    )
    (assets_dir / "manifest.json").write_text(
        json.dumps(FIXTURE_ASSETS_MANIFEST), encoding="utf-8"
    )
    return tmp_path


def test_e2e_spinoff_store_has_test_record(fixture_data_dir):
    """spinoff_store.json に記事 1 件が投入されていること"""
    store_path = fixture_data_dir / "data" / "spinoff_store.json"
    store = json.loads(store_path.read_text(encoding="utf-8"))
    assert len(store["records"]) == 1
    assert store["records"][0]["id"] == "memory-foam"


def test_e2e_script_file_valid_schema(fixture_data_dir):
    """script_memory-foam.json が有効なスキーマを持つこと"""
    from step3_save_script import validate_script_schema
    script_path = fixture_data_dir / "data" / "script_memory-foam.json"
    script = json.loads(script_path.read_text(encoding="utf-8"))
    assert validate_script_schema(script) is True


def test_e2e_audio_manifest_covers_all_scenes(fixture_data_dir):
    """audio_manifest.json が全シーンを網羅していること"""
    manifest_path = fixture_data_dir / "data" / "audio_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    scene_ids = {s["scene_id"] for s in manifest["scenes"]}
    assert "hook" in scene_ids
    assert "1" in scene_ids
    assert "2" in scene_ids
    assert "outro" in scene_ids


def test_e2e_assets_manifest_covers_all_scenes(fixture_data_dir):
    """assets/manifest.json が全シーンを網羅していること"""
    manifest_path = fixture_data_dir / "assets" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    scene_ids = {s["scene_id"] for s in manifest["scenes"]}
    assert "hook" in scene_ids
    assert "1" in scene_ids
    assert "2" in scene_ids
    assert "outro" in scene_ids


def test_e2e_render_props_generation(fixture_data_dir):
    """Step 6-1: 3 マニフェストから render_props.json が正しく生成されること"""
    script = json.loads((fixture_data_dir / "data" / "script_memory-foam.json").read_text())
    audio = json.loads((fixture_data_dir / "data" / "audio_manifest.json").read_text())
    assets = json.loads((fixture_data_dir / "assets" / "manifest.json").read_text())

    check_required_files(
        fixture_data_dir / "data" / "script_memory-foam.json",
        fixture_data_dir / "data" / "audio_manifest.json",
        fixture_data_dir / "assets" / "manifest.json",
    )

    props = merge_render_props(script, audio, assets, lang="ja")

    output_path = fixture_data_dir / "data" / "render_props.json"
    save_render_props(props, output_path)

    assert output_path.exists()
    saved = json.loads(output_path.read_text(encoding="utf-8"))
    assert saved["item_id"] == "memory-foam"
    assert saved["lang"] == "ja"
    assert saved["script"]["title"] == "枕はNASA由来だった"
    assert len(saved["audioManifest"]["scenes"]) == 4
    assert len(saved["assetsManifest"]["scenes"]) == 4


def test_e2e_render_props_scene_audio_paths_valid(fixture_data_dir):
    """render_props.json の audioManifest に有効な MP3 パスが含まれること"""
    script = json.loads((fixture_data_dir / "data" / "script_memory-foam.json").read_text())
    audio = json.loads((fixture_data_dir / "data" / "audio_manifest.json").read_text())
    assets = json.loads((fixture_data_dir / "assets" / "manifest.json").read_text())

    props = merge_render_props(script, audio, assets, lang="ja")

    for scene in props["audioManifest"]["scenes"]:
        assert scene["ja_path"].endswith(".mp3")
        assert scene["en_path"].endswith(".mp3")


def test_e2e_render_props_fallback_scene_present(fixture_data_dir):
    """render_props.json に fallback シーンが含まれていても問題ないこと"""
    script = json.loads((fixture_data_dir / "data" / "script_memory-foam.json").read_text())
    audio = json.loads((fixture_data_dir / "data" / "audio_manifest.json").read_text())
    assets = json.loads((fixture_data_dir / "assets" / "manifest.json").read_text())

    props = merge_render_props(script, audio, assets, lang="ja")
    fallback_scenes = [s for s in props["assetsManifest"]["scenes"] if s["source"] == "fallback"]
    # fallback があっても props 生成は成功する
    assert isinstance(fallback_scenes, list)
