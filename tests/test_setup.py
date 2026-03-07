"""Task 1 環境セットアップ検証テスト（TDD: RED → GREEN）"""
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


# --- Task 1.1: Python 環境 ---

def test_requirements_txt_exists():
    assert (PROJECT_ROOT / "requirements.txt").exists()


def test_requirements_txt_contains_required_packages():
    content = (PROJECT_ROOT / "requirements.txt").read_text()
    for pkg in ["requests", "beautifulsoup4", "edge-tts", "ffmpeg-python", "python-dotenv"]:
        assert pkg in content, f"{pkg} が requirements.txt に含まれていません"


def test_env_example_exists():
    assert (PROJECT_ROOT / ".env.example").exists()


def test_env_example_contains_required_keys():
    content = (PROJECT_ROOT / ".env.example").read_text()
    assert "PEXELS_API_KEY" in content
    assert "PIXABAY_API_KEY" in content


def test_required_directories_exist():
    for d in ["data", "assets", "audio", "tmp", "output", "logs"]:
        path = PROJECT_ROOT / d
        assert path.exists() and path.is_dir(), f"{d}/ が存在しません"


def test_gitkeep_files_exist():
    for d in ["data", "assets", "audio", "tmp", "output", "logs"]:
        assert (PROJECT_ROOT / d / ".gitkeep").exists(), f"{d}/.gitkeep が存在しません"


# --- Task 1.2: Remotion プロジェクト ---

def test_remotion_package_json_exists():
    assert (PROJECT_ROOT / "remotion" / "package.json").exists()


def test_remotion_package_json_has_required_deps():
    data = json.loads((PROJECT_ROOT / "remotion" / "package.json").read_text())
    deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
    for pkg in ["remotion", "@remotion/cli", "react", "react-dom"]:
        assert pkg in deps, f"{pkg} が remotion/package.json に含まれていません"


def test_remotion_config_ts_exists():
    assert (PROJECT_ROOT / "remotion" / "remotion.config.ts").exists()


def test_remotion_root_tsx_exists():
    assert (PROJECT_ROOT / "remotion" / "src" / "Root.tsx").exists()


def test_remotion_index_ts_exists():
    assert (PROJECT_ROOT / "remotion" / "src" / "index.ts").exists()


def test_remotion_tsconfig_exists():
    assert (PROJECT_ROOT / "remotion" / "tsconfig.json").exists()


def test_remotion_tsconfig_strict_mode():
    data = json.loads((PROJECT_ROOT / "remotion" / "tsconfig.json").read_text())
    assert data["compilerOptions"].get("strict") is True, "TypeScript strict mode が有効ではありません"
