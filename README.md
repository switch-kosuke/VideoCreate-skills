# NASA Spinoff Video Creator

NASA技術スピンオフ情報からYouTube Shorts向け縦型動画（60秒以内）を自動生成するパイプライン。

Claude Code スキルとして再利用できるように設計されており、`/nasa-video` コマンド一発でStep 1〜7が順番に実行される。

---

## 機能概要

| Step | 処理 | 出力 |
|------|------|------|
| 1 | NASA Spinoffサイトのスクレイピング | `data/spinoff_store.json` |
| 2 | ネタ選択（バイラルスコアリング + ユーザー選択） | `data/selected_item.json` |
| 3 | 日英バイリンガル台本生成（Claude Code） | `data/script_{id}.json` |
| 4 | 画像素材取得（NASA Images / Pexels API） | `assets/` |
| 5 | 音声生成（edge-tts、JA + EN） | `audio/` + `data/audio_manifest.json` |
| 6 | Remotionレンダリング準備 + 動画生成 | `tmp/render_{id}.mp4` |
| 7 | BGMミックス・最終出力（FFmpeg） | `output/output_{id}_{date}.mp4` |

---

## 必要環境

### ソフトウェア

- Python 3.11+
- Node.js 18+
- FFmpeg（PATH に通すこと）

### FFmpegのインストール

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt install ffmpeg
```

**Windows:**
[https://ffmpeg.org/download.html](https://ffmpeg.org/download.html) からダウンロードし、PATHを通す。

---

## セットアップ

### 1. リポジトリのクローン

```bash
git clone https://github.com/switch-kosuke/VideoCreate-skills.git
cd VideoCreate-skills
```

### 2. Python依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 3. Node.js依存パッケージのインストール

```bash
cd remotion
npm install
cd ..
```

### 4. APIキーの設定

`.env.example` をコピーして `.env` を作成し、APIキーを入力する。

```bash
cp .env.example .env
```

`.env` を編集:
```
PEXELS_API_KEY=your_pexels_api_key_here
PIXABAY_API_KEY=your_pixabay_api_key_here
```

**APIキーの取得先:**
- **Pexels API（画像取得用）**: [https://www.pexels.com/api/](https://www.pexels.com/api/) — 無料
- **Pixabay API（BGM取得用）**: [https://pixabay.com/api/docs/](https://pixabay.com/api/docs/) — 無料

---

## 使い方

### Claude Codeから実行（推奨）

Claude Codeを起動して以下のコマンドを実行する:

```
/nasa-video
```

または新規スクレイピングを含む場合:

```
/nasa-video --fetch
```

コマンドが対話的にStep 1〜7を順番に実行し、各ステップで確認・エラーハンドリングを行う。

### スクリプトを個別実行

各Pythonスクリプトを直接呼び出すことも可能:

```bash
# Step 1: スクレイピング
python scripts/step1_scrape.py --fetch

# Step 2: 選択保存（URLとスコアを指定）
python scripts/step2_save_selection.py --url "https://..." --score 9

# Step 3: 台本保存
python scripts/step3_save_script.py --script-json '{"item_id": ...}'

# Step 4: 画像素材取得
python scripts/step4_fetch_assets.py --script data/script_memory-foam.json

# Step 5: 音声生成
python scripts/step5_voice.py --script data/script_memory-foam.json

# Step 6-1: レンダリング準備
python scripts/step6_prepare_render.py --id memory-foam --lang ja

# Step 6-2: Remotionでレンダリング
cd remotion && npx remotion render src/index.ts NasaSpinoffVideo \
  --props ../data/render_props.json \
  --output ../tmp/render_memory-foam.mp4

# Step 7: BGMミックス・最終出力
python scripts/step7_postprocess.py --input tmp/render_memory-foam.mp4 --id memory-foam
```

---

## テスト

```bash
# Pythonテスト（224テスト中のPython部分）
python -m pytest tests/ -v

# Remotion TypeScriptテスト
cd remotion && npm test
```

---

## プロジェクト構成

```
VideoCreate-skills/
├── scripts/               # Pythonパイプラインスクリプト
│   ├── step1_scrape.py    # NASA Spinoffスクレイピング
│   ├── step2_save_selection.py
│   ├── step3_save_script.py
│   ├── step4_fetch_assets.py  # 画像素材取得（NASA/Pexels）
│   ├── step5_voice.py     # 音声生成（edge-tts）
│   ├── step6_prepare_render.py  # render_props.json生成
│   └── step7_postprocess.py    # FFmpeg BGMミックス
├── remotion/              # Remotion動画レンダリング
│   ├── src/
│   │   ├── components/    # React UIコンポーネント
│   │   │   ├── HookScene.tsx
│   │   │   ├── ContentScene.tsx
│   │   │   ├── OutroScene.tsx
│   │   │   ├── KenBurnsImage.tsx
│   │   │   ├── BilingualSubtitle.tsx
│   │   │   └── StarField.tsx
│   │   ├── utils.ts       # 純粋ロジック関数
│   │   └── NasaSpinoffVideo.tsx  # メインコンポーネント
│   └── __tests__/         # Jestテスト
├── tests/                 # Pytestテスト
├── .claude/commands/      # Claude Codeカスタムコマンド
│   └── nasa-video.md      # /nasa-video コマンド定義
├── .kiro/specs/           # Kiro仕様書
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## 出力動画の仕様

- フォーマット: MP4
- 解像度: 1080×1920（縦型 / YouTube Shorts対応）
- フレームレート: 30fps
- 最大尺: 60秒
- 音声: 日本語ナレーション + BGM（任意）
- 字幕: 日英バイリンガル（画面下部）

---

## 技術スタック

- **スクレイピング**: BeautifulSoup4
- **画像取得**: NASA Images API + Pexels API
- **音声生成**: edge-tts（Microsoft Edge TTS、無料）
- **動画レンダリング**: Remotion 4 + React 18 + TypeScript
- **動画後処理**: FFmpeg
- **BGM取得**: Pixabay Music API
- **テスト**: pytest（Python）/ Jest + @testing-library/react（TypeScript）

---

## ライセンス

MIT
