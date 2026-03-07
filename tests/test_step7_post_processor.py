"""Task 9 PostProcessor テスト（TDD: RED → GREEN）

HTTP・FFmpeg・ファイルシステム操作はすべてモック。
ロジック部分（BGMパス生成・Pixabayレスポンスパース・FFmpegコマンド構築・出力パス生成）を TDD でテストする。
"""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from step7_postprocess import (
    build_output_path,
    build_bgm_path,
    parse_pixabay_response,
    check_ffmpeg_available,
    build_ffmpeg_mix_command,
    find_cached_bgm,
)


# ---- 9.1: 出力パス生成 ----

def test_build_output_path_format():
    path = build_output_path("memory-foam", "2026-03-07", Path("/output"))
    assert str(path) == str(Path("/output/output_memory-foam_20260307.mp4"))


def test_build_output_path_date_format():
    path = build_output_path("test-item", "2026-01-15", Path("/out"))
    assert "20260115" in str(path)


def test_build_output_path_item_id_in_name():
    path = build_output_path("spinoff-001", "2026-03-07", Path("/out"))
    assert "spinoff-001" in str(path)


# ---- 9.1: BGM パス生成 ----

def test_build_bgm_path_uses_filename():
    path = build_bgm_path("space_ambient.mp3", Path("/assets/bgm"))
    assert str(path) == str(Path("/assets/bgm/bgm_space_ambient.mp3"))


def test_build_bgm_path_prefix():
    path = build_bgm_path("epic.mp3", Path("/assets/bgm"))
    assert Path(path).name.startswith("bgm_")


# ---- 9.1: Pixabay レスポンスパース ----

PIXABAY_MUSIC_RESPONSE = {
    "hits": [
        {
            "id": 12345,
            "title": "Space Ambient",
            "duration": 120,
            "audio": "https://cdn.pixabay.com/audio/2024/space_ambient.mp3",
            "user": "artist123",
        },
        {
            "id": 67890,
            "title": "Cinematic Space",
            "duration": 90,
            "audio": "https://cdn.pixabay.com/audio/2024/cinematic.mp3",
            "user": "artist456",
        },
    ]
}

PIXABAY_EMPTY_RESPONSE = {"hits": []}


def test_parse_pixabay_response_returns_first_audio_url():
    url, filename = parse_pixabay_response(PIXABAY_MUSIC_RESPONSE)
    assert url == "https://cdn.pixabay.com/audio/2024/space_ambient.mp3"


def test_parse_pixabay_response_returns_filename():
    url, filename = parse_pixabay_response(PIXABAY_MUSIC_RESPONSE)
    assert filename == "space_ambient.mp3"


def test_parse_pixabay_response_empty_returns_none():
    result = parse_pixabay_response(PIXABAY_EMPTY_RESPONSE)
    assert result is None


def test_parse_pixabay_response_malformed_returns_none():
    result = parse_pixabay_response({})
    assert result is None


# ---- 9.1: BGM キャッシュ検索 ----

def test_find_cached_bgm_returns_first_mp3(tmp_path):
    bgm_dir = tmp_path / "bgm"
    bgm_dir.mkdir()
    (bgm_dir / "bgm_test.mp3").write_bytes(b"fake mp3")
    result = find_cached_bgm(bgm_dir)
    assert result is not None
    assert result.name == "bgm_test.mp3"


def test_find_cached_bgm_returns_none_when_empty(tmp_path):
    bgm_dir = tmp_path / "bgm"
    bgm_dir.mkdir()
    result = find_cached_bgm(bgm_dir)
    assert result is None


def test_find_cached_bgm_returns_none_when_dir_missing(tmp_path):
    result = find_cached_bgm(tmp_path / "nonexistent")
    assert result is None


# ---- 9.1: FFmpeg チェック ----

def test_check_ffmpeg_available_returns_true_when_found():
    with patch("shutil.which", return_value="/usr/bin/ffmpeg"):
        assert check_ffmpeg_available() is True


def test_check_ffmpeg_available_returns_false_when_not_found():
    with patch("shutil.which", return_value=None):
        assert check_ffmpeg_available() is False


# ---- 9.2: FFmpeg コマンド構築 ----

def test_build_ffmpeg_mix_command_includes_input_video():
    cmd = build_ffmpeg_mix_command(
        input_video=Path("tmp/render.mp4"),
        bgm_path=Path("assets/bgm/bgm_test.mp3"),
        output_path=Path("output/out.mp4"),
        video_duration_sec=30,
    )
    assert str(Path("tmp/render.mp4")) in " ".join(cmd)


def test_build_ffmpeg_mix_command_includes_bgm():
    cmd = build_ffmpeg_mix_command(
        input_video=Path("tmp/render.mp4"),
        bgm_path=Path("assets/bgm/bgm_test.mp3"),
        output_path=Path("output/out.mp4"),
        video_duration_sec=30,
    )
    assert str(Path("assets/bgm/bgm_test.mp3")) in " ".join(cmd)


def test_build_ffmpeg_mix_command_bgm_20db():
    cmd = build_ffmpeg_mix_command(
        input_video=Path("tmp/render.mp4"),
        bgm_path=Path("assets/bgm/bgm_test.mp3"),
        output_path=Path("output/out.mp4"),
        video_duration_sec=30,
    )
    # -20dB または volume=-20dB が含まれること
    joined = " ".join(cmd)
    assert "-20dB" in joined or "volume=-20dB" in joined or "volume=0.1" in joined


def test_build_ffmpeg_mix_command_includes_output():
    cmd = build_ffmpeg_mix_command(
        input_video=Path("tmp/render.mp4"),
        bgm_path=Path("assets/bgm/bgm_test.mp3"),
        output_path=Path("output/out.mp4"),
        video_duration_sec=30,
    )
    assert str(Path("output/out.mp4")) in " ".join(cmd)


def test_build_ffmpeg_mix_command_trims_bgm_to_video_length():
    cmd = build_ffmpeg_mix_command(
        input_video=Path("tmp/render.mp4"),
        bgm_path=Path("assets/bgm/bgm_test.mp3"),
        output_path=Path("output/out.mp4"),
        video_duration_sec=45,
    )
    # BGM トリミングのために -t または duration が含まれること
    joined = " ".join(cmd)
    assert "-t" in joined or "duration=first" in joined


def test_build_ffmpeg_mix_command_no_bgm_raises():
    # bgm_path=None は呼び出し側が防ぐが、引数型チェック
    with pytest.raises((TypeError, AttributeError)):
        build_ffmpeg_mix_command(
            input_video=Path("tmp/render.mp4"),
            bgm_path=None,  # type: ignore
            output_path=Path("output/out.mp4"),
            video_duration_sec=30,
        )
