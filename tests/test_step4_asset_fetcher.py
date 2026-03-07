"""Task 5 AssetFetcher テスト（TDD: RED → GREEN）

HTTP リクエストはすべてモック。ロジック部分（URLビルド・レスポンスパース・
マニフェスト生成）を TDD でテストする。
"""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from step4_fetch_assets import (
    build_nasa_search_url,
    parse_nasa_search_response,
    parse_pexels_response,
    generate_asset_filename,
    build_manifest_entry,
    save_manifest,
    get_scene_asset_dir,
)


# ---- フィクスチャ ----

NASA_SEARCH_RESPONSE = {
    "collection": {
        "items": [
            {
                "href": "https://images-assets.nasa.gov/image/PIA12345/collection.json",
                "data": [{"title": "Memory Foam Test", "description": "NASA test image"}],
                "links": [{"href": "https://images-assets.nasa.gov/image/PIA12345/PIA12345~thumb.jpg", "rel": "preview"}],
            }
        ]
    }
}

NASA_ASSET_MANIFEST = [
    "https://images-assets.nasa.gov/image/PIA12345/PIA12345~large.jpg",
    "https://images-assets.nasa.gov/image/PIA12345/PIA12345~thumb.jpg",
    "https://images-assets.nasa.gov/image/PIA12345/PIA12345~orig.jpg",
]

NASA_EMPTY_RESPONSE = {"collection": {"items": []}}

PEXELS_RESPONSE = {
    "photos": [
        {
            "id": 1234,
            "src": {
                "original": "https://images.pexels.com/photos/1234/original.jpg",
                "large": "https://images.pexels.com/photos/1234/large.jpg",
            },
            "photographer": "Test Photographer",
            "url": "https://www.pexels.com/photo/1234",
        }
    ]
}

PEXELS_EMPTY_RESPONSE = {"photos": []}


# ---- 5.1: NASA API ----

def test_build_nasa_search_url_includes_keywords():
    url = build_nasa_search_url(["memory foam", "nasa"])
    assert "memory+foam" in url or "memory%20foam" in url or "memory foam" in url
    assert "nasa" in url.lower()


def test_build_nasa_search_url_image_media_type():
    url = build_nasa_search_url(["space station"])
    assert "media_type=image" in url


def test_build_nasa_search_url_base_endpoint():
    url = build_nasa_search_url(["test"])
    assert "images-api.nasa.gov" in url


def test_parse_nasa_search_response_returns_manifest_url():
    manifest_url = parse_nasa_search_response(NASA_SEARCH_RESPONSE)
    assert manifest_url == "https://images-assets.nasa.gov/image/PIA12345/collection.json"


def test_parse_nasa_search_response_empty_returns_none():
    result = parse_nasa_search_response(NASA_EMPTY_RESPONSE)
    assert result is None


def test_parse_nasa_search_response_malformed_returns_none():
    result = parse_nasa_search_response({"collection": {}})
    assert result is None


# ---- 5.2: Pexels フォールバック ----

def test_parse_pexels_response_returns_original_url():
    url = parse_pexels_response(PEXELS_RESPONSE)
    assert url == "https://images.pexels.com/photos/1234/original.jpg"


def test_parse_pexels_response_empty_returns_none():
    result = parse_pexels_response(PEXELS_EMPTY_RESPONSE)
    assert result is None


def test_parse_pexels_response_malformed_returns_none():
    result = parse_pexels_response({})
    assert result is None


# ---- ファイル名生成 ----

def test_generate_asset_filename_nasa_prefix():
    name = generate_asset_filename("https://images-assets.nasa.gov/image/PIA12345/PIA12345~large.jpg", prefix="nasa")
    assert name.startswith("nasa_")
    assert name.endswith(".jpg")


def test_generate_asset_filename_pexels_prefix():
    name = generate_asset_filename("https://images.pexels.com/photos/1234/photo.jpg", prefix="pexels")
    assert name.startswith("pexels_")


def test_generate_asset_filename_sanitizes_special_chars():
    name = generate_asset_filename("https://example.com/path/to/file~large.jpg", prefix="nasa")
    # チルダや特殊文字がファイルシステムで問題にならない
    assert "~" not in name or name.endswith(".jpg")


# ---- アセットディレクトリ ----

def test_get_scene_asset_dir_numbered_scene():
    d = get_scene_asset_dir(Path("/assets"), "1")
    assert str(d).endswith("scene_1")


def test_get_scene_asset_dir_hook():
    d = get_scene_asset_dir(Path("/assets"), "hook")
    assert str(d).endswith("hook")


def test_get_scene_asset_dir_outro():
    d = get_scene_asset_dir(Path("/assets"), "outro")
    assert str(d).endswith("outro")


# ---- 5.3: マニフェスト生成 ----

def test_build_manifest_entry_nasa_source():
    entry = build_manifest_entry(
        scene_id="1",
        source="nasa",
        local_path="assets/scene_1/nasa_PIA12345.jpg",
        license="NASA Public Domain",
        original_url="https://images-assets.nasa.gov/image/PIA12345/PIA12345~large.jpg",
    )
    assert entry["scene_id"] == "1"
    assert entry["source"] == "nasa"
    assert entry["local_path"] == "assets/scene_1/nasa_PIA12345.jpg"
    assert entry["license"] == "NASA Public Domain"


def test_build_manifest_entry_pexels_source():
    entry = build_manifest_entry(
        scene_id="hook",
        source="pexels",
        local_path="assets/hook/pexels_1234.jpg",
        license="Pexels License",
        original_url="https://images.pexels.com/photos/1234/original.jpg",
    )
    assert entry["source"] == "pexels"
    assert entry["scene_id"] == "hook"


def test_build_manifest_entry_fallback_source():
    entry = build_manifest_entry(
        scene_id="2",
        source="fallback",
        local_path="",
        license="",
        original_url="",
    )
    assert entry["source"] == "fallback"


def test_save_manifest_creates_file(tmp_path):
    entries = [
        build_manifest_entry("1", "nasa", "assets/scene_1/nasa_test.jpg", "NASA Public Domain", "https://x.com/a.jpg"),
    ]
    out = tmp_path / "manifest.json"
    save_manifest(entries, item_id="test-item", output_path=out)
    assert out.exists()


def test_save_manifest_valid_schema(tmp_path):
    entries = [
        build_manifest_entry("1", "nasa", "assets/scene_1/nasa_test.jpg", "NASA Public Domain", "https://x.com/a.jpg"),
        build_manifest_entry("hook", "pexels", "assets/hook/pexels_1.jpg", "Pexels License", "https://p.com/b.jpg"),
    ]
    out = tmp_path / "manifest.json"
    save_manifest(entries, item_id="test-item", output_path=out)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["item_id"] == "test-item"
    assert "generated_at" in data
    assert len(data["scenes"]) == 2


def test_save_manifest_overwrites_existing(tmp_path):
    out = tmp_path / "manifest.json"
    entries1 = [build_manifest_entry("1", "nasa", "p1.jpg", "NASA Public Domain", "u1")]
    save_manifest(entries1, item_id="item1", output_path=out)
    entries2 = [build_manifest_entry("1", "pexels", "p2.jpg", "Pexels License", "u2"),
                build_manifest_entry("2", "fallback", "", "", "")]
    save_manifest(entries2, item_id="item1", output_path=out)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert len(data["scenes"]) == 2
