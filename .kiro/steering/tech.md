# Technology Stack

## Architecture

**ファイルベース順次パイプライン + Claude Code オーケストレーター**。Claude Code（スラッシュコマンド）が全体を進行し、各処理をPythonスクリプトまたはRemotionのCLI呼び出しで実行する。ステップ間のデータ受け渡しはJSONファイルで行う。

## Core Technologies

- **Orchestrator**: Claude Code slash command (`.claude/commands/nasa-video.md`)
- **Python**: 3.10+ — スクレイピング・素材取得・音声生成・後処理
- **Node.js**: 18+ — Remotion動画レンダリング
- **TypeScript**: Remotionコンポーネント（strict mode、`any` 禁止）
- **Remotion**: 4.0.x — React/TypeScriptで動画をコードとして記述
- **FFmpeg**: システムインストール — 動画・音声後処理

## Key Libraries

| ライブラリ | 用途 |
|-----------|------|
| `requests` + `BeautifulSoup4` | spinoff.nasa.gov HTMLスクレイピング |
| `edge-tts` 7.x | 日英ナレーションMP3生成（APIキー不要） |
| `ffmpeg-python` | FFmpegのPythonバインディング |
| `python-dotenv` | `.env` からAPIキー読み込み |
| `Remotion 4.0.x` | React/TSベース動画コンポーザー |

## Development Standards

### Type Safety
- **Python**: `TypedDict` で全データ構造を型定義、境界での入力検証を実施
- **TypeScript（Remotion）**: strict mode。`any` 禁止。Remotion `inputProps` は必ずインターフェース定義を持つ

### APIキー管理
- 全APIキーは `.env` で管理し、コードへの直接記述を禁止する
- `.env.example` にキー名だけ記載（値なし）でテンプレートを提供

### エラーハンドリング
- 各Pythonスクリプトはエラー時に非ゼロ exit code で終了
- グレースフルデグレード: 素材取得失敗時は fallback（星フィールド背景）で継続

## Development Environment

### Required Tools
- Python 3.10+
- Node.js 18+
- FFmpeg（PATH設定）
- Git

### Common Commands
```bash
# Step 1: スクレイピング
python scripts/step1_scrape.py --fetch

# Step 4: 画像取得
python scripts/step4_fetch_assets.py --script data/script_{id}.json

# Step 5: 音声生成
python scripts/step5_voice.py --script data/script_{id}.json

# Step 6: render_props.json 生成（3マニフェストマージ）
python scripts/step6_prepare_render.py --id {id}

# Step 6: 動画レンダリング
npx remotion render remotion/src/index.ts NasaSpinoffVideo --props data/render_props.json --output tmp/render_{id}.mp4

# Step 7: BGM後処理
python scripts/step7_postprocess.py --input tmp/render_{id}.mp4 --id {id}

# パイプライン全体（Claude Code経由）
# /nasa-video
```

## Key Technical Decisions

- **ファイルベースIPC**: 異言語間（Python/Node.js/Claude Code）のデータ受け渡しをJSON経由に統一。デバッグ容易性・途中再実行対応を優先した
- **Claude Code as Orchestrator**: 外部APIキー不要でStep 2（スコアリング）・Step 3（台本生成）を実行。会話でユーザーが承認できる
- **Remotion `--props` 方式**: `render_props.json`（台本+音声+素材マニフェストのマージ）をCLI引数で渡す。Remotion公式推奨
- **NASA API優先 → Pexelsフォールバック**: NASA素材はパブリックドメインで最優先、取得失敗時のみPexelsへ

---
_Document standards and patterns, not every dependency_
