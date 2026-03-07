"""Task 6 VoiceGenerator テスト（TDD: RED → GREEN）

HTTP リクエスト / edge-tts はすべてモック。
ロジック部分（パス生成・マニフェスト生成・バリデーション）を TDD でテストする。
"""
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, call
import asyncio

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from step5_voice import (
    build_audio_path,
    build_audio_manifest,
    save_audio_manifest,
    validate_voices,
    DEFAULT_JA_VOICE,
    DEFAULT_EN_VOICE,
)


# ---- フィクスチャ ----

SAMPLE_SCRIPT = {
    "item_id": "test-001",
    "title": "テスト台本",
    "title_en": "Test Script",
    "hook": "驚きのフック",
    "hook_en": "Amazing hook",
    "scenes": [
        {
            "id": 1,
            "voiceover": "日本語ナレーション1",
            "voiceover_en": "English narration 1",
            "visual_note": "ビジュアル説明",
            "image_keywords": ["space", "nasa"],
            "duration_sec": 10,
        },
        {
            "id": 2,
            "voiceover": "日本語ナレーション2",
            "voiceover_en": "English narration 2",
            "visual_note": "ビジュアル説明2",
            "image_keywords": ["technology", "innovation"],
            "duration_sec": 10,
        },
    ],
    "outro": "チャンネル登録をお願いします",
    "outro_en": "Please subscribe",
    "total_duration_sec": 28,
}


# ---- 6.2: パス生成 ----

def test_build_audio_path_numbered_scene_ja():
    path = build_audio_path("1", "ja", Path("/audio"))
    assert str(path) == str(Path("/audio/ja/scene_1.mp3"))


def test_build_audio_path_numbered_scene_en():
    path = build_audio_path("1", "en", Path("/audio"))
    assert str(path) == str(Path("/audio/en/scene_1.mp3"))


def test_build_audio_path_hook_ja():
    path = build_audio_path("hook", "ja", Path("/audio"))
    assert str(path) == str(Path("/audio/ja/scene_hook.mp3"))


def test_build_audio_path_hook_en():
    path = build_audio_path("hook", "en", Path("/audio"))
    assert str(path) == str(Path("/audio/en/scene_hook.mp3"))


def test_build_audio_path_outro_ja():
    path = build_audio_path("outro", "ja", Path("/audio"))
    assert str(path) == str(Path("/audio/ja/scene_outro.mp3"))


def test_build_audio_path_outro_en():
    path = build_audio_path("outro", "en", Path("/audio"))
    assert str(path) == str(Path("/audio/en/scene_outro.mp3"))


# ---- 6.1: デフォルトボイス ----

def test_default_ja_voice():
    assert DEFAULT_JA_VOICE == "ja-JP-NanamiNeural"


def test_default_en_voice():
    assert DEFAULT_EN_VOICE == "en-US-JennyNeural"


def test_validate_voices_accepts_valid():
    # 有効な文字列が渡れば例外を送出しない
    validate_voices("ja-JP-NanamiNeural", "en-US-JennyNeural")


def test_validate_voices_rejects_empty_ja():
    with pytest.raises(ValueError, match="JA"):
        validate_voices("", "en-US-JennyNeural")


def test_validate_voices_rejects_empty_en():
    with pytest.raises(ValueError, match="EN"):
        validate_voices("ja-JP-NanamiNeural", "")


# ---- 6.2: マニフェスト生成 ----

def test_build_audio_manifest_structure():
    audio_root = Path("/audio")
    manifest = build_audio_manifest(SAMPLE_SCRIPT, "ja-JP-NanamiNeural", "en-US-JennyNeural", audio_root)
    assert manifest["item_id"] == "test-001"
    assert "generated_at" in manifest
    assert manifest["ja_voice"] == "ja-JP-NanamiNeural"
    assert manifest["en_voice"] == "en-US-JennyNeural"
    assert "scenes" in manifest


def test_build_audio_manifest_scene_count():
    audio_root = Path("/audio")
    manifest = build_audio_manifest(SAMPLE_SCRIPT, "ja-JP-NanamiNeural", "en-US-JennyNeural", audio_root)
    # hook + 2 scenes + outro = 4
    assert len(manifest["scenes"]) == 4


def test_build_audio_manifest_hook_entry():
    audio_root = Path("/audio")
    manifest = build_audio_manifest(SAMPLE_SCRIPT, "ja-JP-NanamiNeural", "en-US-JennyNeural", audio_root)
    hook = next(s for s in manifest["scenes"] if s["scene_id"] == "hook")
    assert hook["ja_path"].endswith("scene_hook.mp3")
    assert hook["en_path"].endswith("scene_hook.mp3")


def test_build_audio_manifest_numbered_scene_entry():
    audio_root = Path("/audio")
    manifest = build_audio_manifest(SAMPLE_SCRIPT, "ja-JP-NanamiNeural", "en-US-JennyNeural", audio_root)
    scene1 = next(s for s in manifest["scenes"] if s["scene_id"] == "1")
    assert scene1["ja_path"].endswith("scene_1.mp3")
    assert scene1["en_path"].endswith("scene_1.mp3")
    assert "ja" in scene1["ja_path"]
    assert "en" in scene1["en_path"]


def test_build_audio_manifest_outro_entry():
    audio_root = Path("/audio")
    manifest = build_audio_manifest(SAMPLE_SCRIPT, "ja-JP-NanamiNeural", "en-US-JennyNeural", audio_root)
    outro = next(s for s in manifest["scenes"] if s["scene_id"] == "outro")
    assert outro["ja_path"].endswith("scene_outro.mp3")
    assert outro["en_path"].endswith("scene_outro.mp3")


# ---- 6.2: マニフェスト保存 ----

def test_save_audio_manifest_creates_file(tmp_path):
    audio_root = Path("/audio")
    manifest = build_audio_manifest(SAMPLE_SCRIPT, "ja-JP-NanamiNeural", "en-US-JennyNeural", audio_root)
    out = tmp_path / "audio_manifest.json"
    save_audio_manifest(manifest, out)
    assert out.exists()


def test_save_audio_manifest_valid_json(tmp_path):
    audio_root = Path("/audio")
    manifest = build_audio_manifest(SAMPLE_SCRIPT, "ja-JP-NanamiNeural", "en-US-JennyNeural", audio_root)
    out = tmp_path / "audio_manifest.json"
    save_audio_manifest(manifest, out)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["item_id"] == "test-001"
    assert len(data["scenes"]) == 4


def test_save_audio_manifest_creates_parent_dirs(tmp_path):
    audio_root = Path("/audio")
    manifest = build_audio_manifest(SAMPLE_SCRIPT, "ja-JP-NanamiNeural", "en-US-JennyNeural", audio_root)
    out = tmp_path / "nested" / "dir" / "audio_manifest.json"
    save_audio_manifest(manifest, out)
    assert out.exists()


def test_save_audio_manifest_overwrites(tmp_path):
    audio_root = Path("/audio")
    out = tmp_path / "audio_manifest.json"
    manifest1 = build_audio_manifest(SAMPLE_SCRIPT, "ja-JP-NanamiNeural", "en-US-JennyNeural", audio_root)
    save_audio_manifest(manifest1, out)
    manifest2 = build_audio_manifest(SAMPLE_SCRIPT, "ja-JP-KeitaNeural", "en-US-GuyNeural", audio_root)
    save_audio_manifest(manifest2, out)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["ja_voice"] == "ja-JP-KeitaNeural"
