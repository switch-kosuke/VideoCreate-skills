"""Task 10 Pipeline Orchestrator テスト（TDD: RED → GREEN）

.claude/commands/nasa-video.md の内容を検証する。
Markdown 指示書として必要なセクション・コマンド・ゲートが含まれることをテストする。
"""
from pathlib import Path

import pytest

COMMAND_FILE = Path(__file__).parent.parent / ".claude" / "commands" / "nasa-video.md"


@pytest.fixture
def content() -> str:
    return COMMAND_FILE.read_text(encoding="utf-8")


# ---- Step 4 (AssetFetcher) ----

def test_step4_bash_command_present(content: str):
    assert "step4_fetch_assets.py" in content


def test_step4_script_arg_present(content: str):
    assert "--script" in content


def test_step4_expected_output_mentioned(content: str):
    assert "manifest.json" in content


# ---- Step 5 (VoiceGenerator) ----

def test_step5_bash_command_present(content: str):
    assert "step5_voice.py" in content


def test_step5_expected_output_mentioned(content: str):
    assert "audio_manifest.json" in content


# ---- Step 6 (RenderPreparer + Remotion render) ----

def test_step6_prepare_render_command_present(content: str):
    assert "step6_prepare_render.py" in content


def test_step6_remotion_render_command_present(content: str):
    assert "remotion render" in content


def test_step6_render_props_mentioned(content: str):
    assert "render_props.json" in content


def test_step6_output_tmp_mentioned(content: str):
    assert "tmp/" in content


# ---- Step 7 (PostProcessor) ----

def test_step7_bash_command_present(content: str):
    assert "step7_postprocess.py" in content


def test_step7_output_path_mentioned(content: str):
    assert "output/" in content


# ---- ユーザーゲート ----

def test_enter_gate_present(content: str):
    assert "Enter" in content or "続行" in content


# ---- エラーハンドリング ----

def test_failure_handling_mentioned(content: str):
    assert "失敗" in content or "エラー" in content


def test_retry_skip_options_mentioned(content: str):
    assert "リトライ" in content or "スキップ" in content


# ---- 完了サマリー ----

def test_completion_summary_output_path(content: str):
    assert "output" in content


def test_completion_summary_mentioned(content: str):
    assert "完了" in content or "サマリー" in content or "ファイルサイズ" in content


# ---- APIキー管理 ----

def test_env_file_mentioned(content: str):
    assert ".env" in content


def test_pexels_key_not_hardcoded(content: str):
    # APIキーの値（典型的なランダム文字列）がハードコードされていないこと
    assert "PEXELS_API_KEY" not in content or "=" not in content.split("PEXELS_API_KEY")[-1][:5]
