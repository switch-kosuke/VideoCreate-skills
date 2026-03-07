# リサーチ・設計判断ログ

---
**Purpose**: 設計フェーズの調査結果・アーキテクチャ判断の根拠を記録する。
---

## サマリー

- **フィーチャー**: `nasa-spinoff-video-pipeline`
- **ディスカバリースコープ**: 新規構築（Greenfield）/ 複合インテグレーション
- **主要調査結果**:
  - Remotion v4.0.434（最新）は `inputProps` 経由でJSONデータを受け取りMP4に変換できる。Node.js 16+ 必須。
  - edge-tts v7.2.7（最新）は非同期Python APIで、APIキー不要でMicrosoft EdgeのTTSサービスを利用できる。
  - NASA Image and Video Library API（`images-api.nasa.gov`）はAPIキー不要、IPベースのレート制限あり（DEMO KEY: 30req/h）。
  - Pexels API は 200req/h・20,000req/月の制限、`Authorization` ヘッダーにAPIキーが必要。
  - Pixabay Music API（`https://pixabay.com/api/music/`）は無制限リクエスト、APIキー必要。
  - spinoff.nasa.gov にRSSフィードは存在しない。HTMLスクレイピング（`.feature` アンカータグ）が必要。

---

## リサーチログ

### Remotion v4 アーキテクチャ

- **Context**: 動画レンダリングライブラリの選定と制約確認
- **Sources Consulted**: npmjs.com/package/remotion, remotion.dev/docs
- **Findings**:
  - 最新版 v4.0.434（2025年アクティブ開発中）
  - `npx remotion render` でCLIからMP4を出力可能
  - `--props` オプションでJSONファイルのパスを渡すと `inputProps` として受け取れる
  - 全 `@remotion/*` パッケージはバージョンを揃える必要がある（`^` 不使用推奨）
  - Node.js 16+ / Windows x64・macOS・Linux 対応
  - FPS・解像度・出力フォーマットはCLI引数またはcomposition設定で制御
- **Implications**:
  - 台本JSONとマニフェストJSONをCLIの `--props` で渡す設計が最もシンプル
  - Remotionプロジェクトは `remotion/` サブディレクトリに独立させる

### edge-tts 音声生成

- **Context**: 無料TTSの選定
- **Sources Consulted**: pypi.org/project/edge-tts, github.com/rany2/edge-tts
- **Findings**:
  - v7.2.7（2025年12月リリース）、Python 3.7+ 対応
  - 非同期API: `await communicate.save(filename)` でMP3/WAVを保存
  - `ja-JP-NanamiNeural`・`ja-JP-KeitaNeural`（日本語）、`en-US-JennyNeural`・`en-US-GuyNeural`（英語）はいずれも利用可能
  - APIキー不要、レート制限の明示的な公開ドキュメントなし（事実上Microsoft EdgeのクラウドTTSを利用）
- **Implications**:
  - 大量並列リクエストは避ける（シーン単位で順次生成が安全）
  - asyncio ベースのスクリプトで実装する

### NASA Image and Video Library API

- **Context**: 公式素材取得の実現可能性確認
- **Sources Consulted**: api.nasa.gov, images.nasa.gov
- **Findings**:
  - エンドポイント: `GET https://images-api.nasa.gov/search?q={keywords}&media_type=image,video`
  - APIキー不要（DEMO KEYとして動作、IPベース制限）
  - レスポンス: `collection.items[]` に `href`（asset manifest URL）と `data[0]`（メタデータ）
  - 画像DLは2段階: ① search → ② asset manifest URL取得 → ③ 実ファイルURL取得
  - 全コンテンツはNASAパブリックドメイン（商用利用可）
- **Implications**:
  - 検索→manifest取得→ダウンロードの3ステップが必要
  - `media_type=image` を優先し、動画は `media_type=video` でフォールバック検索も可能

### Pexels API

- **Context**: NASAフォールバック素材の選定
- **Sources Consulted**: pexels.com/api/documentation
- **Findings**:
  - エンドポイント: `GET https://api.pexels.com/v1/search?query={keywords}&per_page=5`
  - 認証: `Authorization: {API_KEY}` ヘッダー
  - レート制限: 200req/h・20,000req/month（超過時 429 Too Many Requests）
  - レスポンスヘッダー: `X-Ratelimit-Remaining` で残枠確認可能
  - 写真ライセンス: Pexelsライセンス（商用利用可、帰属表示推奨）
- **Implications**:
  - `per_page=5` で上位5件取得し最高解像度を選択
  - `X-Ratelimit-Remaining` を確認してスロットリング制御

### Pixabay Music API

- **Context**: BGM自動取得の実現可能性確認
- **Sources Consulted**: pixabay.com/service/about/api
- **Findings**:
  - Music エンドポイント: `GET https://pixabay.com/api/music/?key={API_KEY}&q={query}`
  - 無制限リクエスト（公式サイト記載）
  - レスポンスに `duration`・`download`（直接DL URL）が含まれる
  - ライセンス: Pixabayライセンス（商用利用可、帰属表示不要）
- **Implications**:
  - `duration=30-` フィルターで30秒以上を指定して取得

### spinoff.nasa.gov スクレイピング

- **Context**: データソースの構造確認
- **Sources Consulted**: spinoff.nasa.gov（直接フェッチ）
- **Findings**:
  - RSSフィード: **存在しない**（確認済み）
  - 記事一覧: `.feature` アンカータグでラップされた記事カード
  - 記事URL: `/[article-slug]` 形式（例: `/Memory_Foam`）
  - 記事は「load more」ボタンで追加表示（JS依存）
  - カテゴリ: Computing / Health / Industry / Public Safety / Transportation 等
  - 詳細ページには概要テキスト・カテゴリ・画像が含まれる
- **Implications**:
  - BeautifulSoup + requests でHTMLパース
  - JS依存の「load more」は `?page=N` またはリクエストパラメータで回避を試みる
  - 詳細ページも別途フェッチして概要を抽出する2段階スクレイピングが必要

---

## アーキテクチャパターン評価

| オプション | 説明 | 強み | リスク | 評価 |
|-----------|------|------|--------|------|
| ファイルベースパイプライン | JSON ファイルを媒介にステップ間でデータを受け渡す | シンプル、デバッグ容易、再開可能 | ファイル管理が必要 | **採用** |
| インプロセスパイプライン | Python 1プロセス内で全ステップを実行 | 高速 | Claude Code統合が困難 | 不採用 |
| メッセージキュー | Redis/RabbitMQ 経由でステップを非同期連携 | スケーラブル | 過剰エンジニアリング | 不採用 |

---

## 設計判断

### 判断: データ受け渡し方式

- **Context**: 異言語（Python・Node.js・Claude Code）間のデータ連携が必要
- **選択肢**:
  1. ファイルベースJSON（各ステップが読み書き）
  2. SQLite（1ファイルDB）
  3. 環境変数・標準入出力
- **採用**: ファイルベースJSON
- **理由**: デバッグが容易、途中再実行に対応、Claude Code がファイルをRead/Writeツールで直接操作できる
- **トレードオフ**: 並列実行は不可（本パイプラインはシーケンシャルなので問題なし）

### 判断: Remotion へのデータ渡し方式

- **Context**: 台本JSON・音声マニフェスト・素材マニフェストをRemotionに渡す方法
- **選択肢**:
  1. `--props props.json` CLI引数（Remotion公式サポート）
  2. 環境変数
  3. HTTP APIサーバー経由
- **採用**: `--props props.json`（レンダリング用のまとめpropsファイルを生成して渡す）
- **理由**: Remotion公式の推奨方式、CLIからシンプルに渡せる

### 判断: Claude Code スラッシュコマンドの実装方式

- **Context**: `/nasa-video` 起動時の動作定義
- **選択肢**:
  1. `.claude/commands/nasa-video.md`（MarkdownでClaude Codeへの指示を記述）
  2. Claude Agent SDK によるサブエージェント
- **採用**: `.claude/commands/nasa-video.md`（マークダウン指示ファイル）
- **理由**: 追加の実装なし、Claude Code がステップ指示に従って自律的に動作する

---

## リスク・緩和策

- **spinoff.nasa.gov のHTML変更**: セレクタが変わるとスクレイピングが壊れる → エラー時に詳細ログを出力し、セレクタを設定ファイル（`config.json`）で外出し
- **edge-ttsのレート制限**: 非公開のため突然制限される可能性 → シーン間に 0.5秒のスリープを挿入
- **Remotionレンダリング時間**: 1080x1920・60fps・60秒で数分かかる場合がある → タイムアウト値を設定、進捗を表示
- **NASA APIの2段階DL**: マニフェストURLからファイルURLを取得する2ステップが失敗しやすい → 各ステップで個別にエラーハンドリング

---

## 参考文献

- [Remotion 公式ドキュメント](https://www.remotion.dev/docs/)
- [edge-tts GitHub](https://github.com/rany2/edge-tts)
- [NASA Image and Video Library API](https://images.nasa.gov/)
- [Pexels API ドキュメント](https://www.pexels.com/api/documentation/)
- [Pixabay API](https://pixabay.com/service/about/api/)
- [spinoff.nasa.gov](https://spinoff.nasa.gov)
