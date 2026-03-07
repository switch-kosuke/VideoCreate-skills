# Project Structure

## Organization Philosophy

**レイヤーバイステップ**: パイプラインの各ステップ（Step 1〜7）が独立したスクリプトとして分離する。ステップ間の依存はJSONファイルのみ。Remotionプロジェクトはサブディレクトリ (`remotion/`) に完全隔離する。

## Directory Patterns

### Pipeline Scripts
**Location**: `scripts/`
**Purpose**: 各パイプラインステップのPython実装（Step 1・4・5・7）
**Example**: `step1_scrape.py`・`step4_fetch_assets.py`・`step5_voice.py`・`step7_postprocess.py`
**Convention**: `step{N}_{動詞}_{対象}.py` の命名。CLIは `argparse` で引数定義

### Remotion Video Project
**Location**: `remotion/`
**Purpose**: Remotion（React/TypeScript）による動画コンポーネント群
**Example**: `remotion/src/NasaSpinoffVideo.tsx`（メインコンポジション）、`remotion/src/components/`（共通コンポーネント）
**Convention**: コンポーネントはPascalCase。`remotion/package.json` は独立した依存管理

### JSON File Store（パイプライン中間データ）
**Location**: `data/`
**Purpose**: ステップ間のデータ受け渡しに使うJSONファイル
**Example**: `spinoff_store.json`（永続ネタDB）・`script_{id}.json`（台本）・`render_props.json`（Remotion用マージJSON）
**Convention**: ステップが生成するファイルは `{生成物名}_{id}.json` で命名

### Media Assets
**Location**: `assets/`
**Purpose**: 取得した画像・BGMのキャッシュ（再取得回避）
**Convention**: `assets/scene_{id}/`（シーン別画像）・`assets/bgm/`（BGMキャッシュ）・`assets/manifest.json`（マニフェスト）

### Audio Files
**Location**: `audio/`
**Purpose**: edge-ttsで生成したナレーションMP3を言語別に格納
**Convention**: `audio/ja/scene_{id}.mp3`・`audio/en/scene_{id}.mp3`。`hook`・`outro` は `scene_hook`・`scene_outro` で命名

### Output
**Location**: `output/`
**Purpose**: 最終完成MP4の保管
**Convention**: `output_{item_id}_{YYYYMMDD}.mp4`

## Naming Conventions

- **Python スクリプト**: `snake_case`（例: `step1_scrape.py`）
- **TypeScript/React コンポーネント**: `PascalCase`（例: `KenBurnsImage.tsx`）
- **JSON データファイル**: `snake_case`（例: `spinoff_store.json`）
- **Python 型定義**: `PascalCase` + `TypedDict`（例: `class SpinoffRecord(TypedDict)`）
- **TypeScript 型**: `PascalCase` インターフェース（例: `interface ScriptJSON`）

## Code Organization Principles

- **各スクリプトは単一責任**: 1スクリプト = 1ステップ。複数ステップをまたぐロジックはOrchestrator（`nasa-video.md`）が担う
- **設定は `.env` へ**: APIキー・デフォルト音声名などの設定値はコードに直書きしない
- **再利用可能な型定義**: Python の `TypedDict` と TypeScript の `interface` は `*_types.py` / `types.ts` に集約する（スクリプト間共有が必要になった時点で実施）
- **マニフェストパターン**: 複数ファイルを後続ステップへ渡す際は必ずマニフェストJSON（`manifest.json`）を生成する

## Spec-Driven Development

本プロジェクトはKiro Spec-Driven Developmentで管理されている。
アクティブな仕様は `.kiro/specs/nasa-spinoff-video-pipeline/` を参照。
設計判断の背景は `.kiro/specs/nasa-spinoff-video-pipeline/research.md` に記録されている。

---
_Document patterns, not file trees. New files following patterns shouldn't require updates_
