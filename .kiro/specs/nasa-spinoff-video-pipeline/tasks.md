# 実装計画

## タスク一覧

- [x] 1. 環境セットアップと依存関係の初期化
- [x] 1.1 (P) Python環境のセットアップ
  - Python依存ライブラリ（requests, beautifulsoup4, edge-tts, ffmpeg-python, python-dotenv）を`requirements.txt`に記載する
  - `.env.example`に`PEXELS_API_KEY`・`PIXABAY_API_KEY`のキー名のみ記載してテンプレートを作成する
  - `data/`・`assets/`・`audio/`・`tmp/`・`output/`・`logs/`の空ディレクトリ（`.gitkeep`付き）を作成する
  - _Requirements: 8.9_

- [x] 1.2 (P) Remotionプロジェクトの初期化
  - `remotion/`ディレクトリにRemotionプロジェクト（`package.json`・`remotion.config.ts`）を初期化する
  - Remotion 4.0.434・React 18・TypeScript strict modeの依存関係を設定する
  - `remotion/src/Root.tsx`の骨格を作成し、`npx remotion studio`が起動することを確認する
  - _Requirements: 8.9_

- [x] 2. SpinoffScraperの実装（Step 1）
- [x] 2.1 spinoff.nasa.govスクレイピングロジックの実装
  - `--fetch`フラグ付きで起動したとき、`https://spinoff.nasa.gov`の`.feature`アンカータグから記事URLを収集する
  - 各記事の詳細ページにアクセスしてタイトル・概要・カテゴリを抽出する（リクエスト間1〜2秒スリープ）
  - スクレイピング前にrobots.txtを確認し、識別可能なUser-Agent（`NASA-Spinoff-VideoBot/1.0`）を設定する
  - セレクタ設定を`config.json`に外出しして変更への柔軟性を持たせる
  - ネットワークエラー・スクレイピング失敗時はエラー内容をログ出力し、非ゼロ終了コードで終了する
  - _Requirements: 1.1, 1.2, 1.6_

- [x] 2.2 永続ストア管理の実装
  - `data/spinoff_store.json`が存在する場合は既存データを読み込み、URLをユニークキーとして重複チェックのうえ追記保存する
  - 各レコードに`used`（bool）・`used_at`（ISO 8601 or null）フィールドを持たせる
  - `--fetch`フラグなしで実行した場合はスクレイピングをスキップし、既存ストアデータのみを対象とする
  - _Requirements: 1.3, 1.4, 1.5, 1.7_

- [x] 3. TopicSelectorの実装（Step 2 — Claude Codeオーケストレーション内）
- [x] 3.1 バイラルスコアリングと候補表示UIの実装
  - `spinoff_store.json`から`used: false`のネタを読み込み、Claude Code自身が4軸（意外性・日常関連性・キャッチーさ・日本人親和性）でスコア1〜10を付与する
  - スコア上位5件を指定フォーマット（番号・スコア・カテゴリ・タイトル・選定理由）で会話内に表示する
  - 「もっと見る」が選択されたとき次点の5件を追加スコアリングして表示する
  - 未使用ネタが0件の場合は再取得を促すメッセージを表示して処理を終了する
  - _Requirements: 2.1, 2.2, 2.3, 2.8, 2.9_

- [x] 3.2 ユーザー選択処理と状態更新の実装
  - ユーザーが有効な番号を入力するまで次ステップへ進まないゲートを設ける
  - 範囲外または無効な入力の場合は再入力を促すメッセージを表示する
  - 選択確定後に`data/selected_item.json`（レコード・スコア・`selected_at`）を保存する
  - 選択したレコードの`used: true`・`used_at`を`spinoff_store.json`に書き戻す
  - _Requirements: 2.4, 2.5, 2.6, 2.7_

- [x] 4. ScriptAgentの実装（Step 3 — Claude Codeオーケストレーション内）
- [x] 4.1 日英バイリンガル台本生成ロジックの実装
  - `data/selected_item.json`を読み込み、Claude Code自身が日英バイリンガル台本JSONを生成する（外部API呼び出しなし）
  - 口調は「親しみやすく、驚きを演出するテンポ感」とし、英語は直訳でなく英語圏視聴者に自然な意訳で生成する
  - `total_duration_sec`が60秒を超えるとき、シーン圧縮案をユーザーに提示してから保存する
  - 台本JSONスキーマの全フィールド（title 25文字以内・hook・scenes・outro・各`duration_sec`・`image_keywords` 2〜4語）を検証する
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.7_

- [x] 4.2 ユーザー承認ループと台本保存の実装
  - 生成した台本をユーザーに提示し、修正依頼を受け付ける（最大3回の修正ループ）
  - ユーザーが承認したとき`data/script_{item_id}.json`として保存する
  - _Requirements: 3.5, 3.6_

- [x] 5. (P) AssetFetcherの実装（Step 4）
- [x] 5.1 (P) NASA Image API統合の実装
  - 台本JSONの全シーン（hook・各scene・outro）の`image_keywords`に対してNASA Image and Video Library APIを検索する
  - 2段階取得（search → asset manifest URL → 実ファイルURL）で最高relevanceのメディアをダウンロードし、`assets/scene_{id}/nasa_{filename}`に保存する
  - `X-Ratelimit-Remaining`ヘッダーが10件未満のときスリープを挿入する
  - _Requirements: 4.1, 4.2, 4.3_

- [x] 5.2 (P) Pexelsフォールバックとfallbackフラグの実装
  - NASA APIで結果0件またはダウンロード失敗のとき、Pexels APIで同キーワードを検索し最高解像度画像を`assets/scene_{id}/pexels_{filename}`に保存する
  - NASA・Pexels双方で取得できないとき、該当シーンに`source: 'fallback'`をセットしてログに記録する
  - hook・outroも同様に`assets/hook/`・`assets/outro/`に保存する
  - _Requirements: 4.4, 4.5, 4.6, 4.7_

- [x] 5.3 素材マニフェスト生成の実装
  - 全シーン取得完了後、各シーンのローカルパス・ソース（nasa/pexels/fallback）・ライセンス情報を`assets/manifest.json`に書き出す
  - _Requirements: 4.8_

- [x] 6. (P) VoiceGeneratorの実装（Step 5）
- [x] 6.1 (P) edge-tts JA/EN音声生成の実装
  - 台本JSONの全テキスト（hook・scenes・outro）に対してedge-ttsでJA・ENのMP3を非同期生成する
  - デフォルトボイス（JA: `ja-JP-NanamiNeural`、EN: `en-US-JennyNeural`）を使用し、CLIオプションで切り替え可能にする
  - シーン間に0.5秒スリープを挿入してレート制限に配慮する
  - 音声生成失敗時は言語・シーンIDとエラー内容をログ出力し、処理を停止する
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.7_

- [x] 6.2 音声ファイル保存と音声マニフェスト生成の実装
  - 日本語音声を`audio/ja/scene_{id}.mp3`・英語音声を`audio/en/scene_{id}.mp3`に保存する（hook/outroは`scene_hook`・`scene_outro`）
  - 全音声ファイルのパス一覧を`data/audio_manifest.json`に書き出す
  - _Requirements: 5.5, 5.6, 5.8_

- [x] 7. VideoRendererのRemotionコンポーネント実装
- [x] 7.1 (P) 背景・エフェクトコンポーネントの実装
  - 黒背景＋星パーティクルアニメーションを描画するStarFieldコンポーネントを実装する
  - 静止画にゆっくりズーム/パンエフェクト（ケンバーンズ）を適用するKenBurnsImageコンポーネントを実装する
  - _Requirements: 6.2, 6.3_

- [x] 7.2 (P) BilingualSubtitleコンポーネントの実装
  - 日本語テキストを画面下部大きく、英語テキストをその直下70%サイズで表示する字幕コンポーネントを実装する
  - フェードインまたはスライドインアニメーションを各シーン遷移に適用する
  - _Requirements: 6.5, 6.6_

- [x] 7.3 シーンコンポーネントの実装
  - HookSceneコンポーネントを実装する（フォント1.5倍以上・スケールアップ強調エフェクト）
  - ContentSceneコンポーネントを実装する（KenBurnsImage背景＋BilingualSubtitle）
  - OutroSceneコンポーネントを実装する（チャンネル登録CTA表示）
  - `source === 'fallback'`のシーンはStarFieldを背景として使用する
  - _Requirements: 6.2, 6.4_

- [x] 7.4 NasaSpinoffVideoメインコンポジションの実装
  - `render_props.json`からVideoCompositionPropsを受け取り、シーン順序・タイミングを制御するメインコンポジションを実装する
  - 各シーンの表示時間を`duration_sec`の累積フレーム計算で制御し、edge-tts音声の実長が`duration_sec`と異なる場合は音声長を優先する
  - `lang`プロパティで日本語/英語音声トラックを切り替え可能にし、デフォルトは日本語とする
  - 必要ファイルが見つからない場合は不足パスを明示したエラーを出力しレンダリングを中断する
  - _Requirements: 6.1, 6.7, 6.8, 6.9, 6.10, 6.11_

- [x] 8. RenderPreparerの実装（Step 6準備）
  - Step 5完了後に`data/script_{id}.json`・`data/audio_manifest.json`・`assets/manifest.json`を読み込み、`data/render_props.json`にマージして保存するスクリプトを実装する
  - 入力ファイルの存在チェックを行い、不足ファイルがある場合はパスを明示してエラー終了する
  - _Requirements: 8.2, 8.3_

- [x] 9. PostProcessorの実装（Step 7）
- [x] 9.1 Pixabay BGM自動取得の実装
  - `assets/bgm/`にファイルが存在しない場合、Pixabay Music APIで「space ambient」または「epic cinematic」キーワード・30秒以上の条件で検索し、BGMを`assets/bgm/bgm_{filename}.mp3`にキャッシュする
  - Pixabay API取得失敗時は既存キャッシュを使用し、キャッシュもない場合はBGMなしで続行してユーザーに通知する
  - _Requirements: 7.1, 7.2, 7.3, 7.4_

- [x] 9.2 FFmpegミックスと最終MP4出力の実装
  - `tmp/render_{id}.mp4`とBGMをFFmpegでミックスする（BGM -20dB、ナレーション音量不変）
  - BGMが動画より長い場合は動画の長さにトリミングする
  - 最終MP4を`output/output_{item_id}_{YYYYMMDD}.mp4`に保存する
  - FFmpegが見つからない場合はインストール手順を案内して処理を中断する
  - _Requirements: 7.5, 7.6, 7.7, 7.8_

- [x] 10. Pipeline Orchestratorの実装（nasa-video.md）
  - `.claude/commands/nasa-video.md`にStep 1〜7の実行コマンド・期待出力ファイル・ユーザーゲートを記述する
  - Step 1・4・5・6準備・7をBashツール経由で呼び出し、Step 2・3はClaude Code自身が会話内で処理するよう分岐を明記する
  - 各ステップ開始前に概要と`[Enter で続行]`ゲートを提示し、完了後に次ステップ確認を行う
  - ステップ失敗時に失敗ステップ番号・原因・推奨対処法を表示し、リトライ/スキップの選択肢を提供する
  - パイプライン完了時に出力パス・所要時間・生成シーン数・ファイルサイズのサマリーを表示する
  - PexelsおよびPixabayのAPIキーは`.env`から読み込み、コードには記述しない
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8_

- [x] 11. テストと動作検証
- [x] 11.1 (P) Pythonスクリプトのユニットテスト
  - HTMLフィクスチャを使ったSpinoffScraperパース結果の検証（セレクタ一致・重複URLスキップ）
  - AssetFetcherのNASA APIレスポンスモックとPexelsフォールバック動作の検証
  - VoiceGeneratorの音声ファイルパス生成ロジック検証（ファイル名規則）
  - PostProcessorのFFmpegコマンド組み立て検証（-20dBパラメータ・トリミング条件）
  - _Requirements: 1.1, 1.2, 4.2, 4.4, 5.5, 7.5_

- [x] 11.2 (P) スキーマ整合性テスト
  - 台本JSONスキーマ検証（`total_duration_sec` ≤ 60・全必須フィールド存在チェック）
  - Step 1→2間のJSONスキーマ整合性（`spinoff_store.json` → TopicSelector読み込み）
  - Step 3→4間のJSONスキーマ整合性（`script_{id}.json` → AssetFetcher・VoiceGenerator読み込み）
  - Step 5→6間のマニフェスト整合性（`audio_manifest.json` → `render_props.json`）
  - _Requirements: 3.7, 8.2_

- [x] 11.3 E2Eパイプライン動作検証
  - フィクスチャデータ（`spinoff_store.json`にテスト記事1件投入）でStep 4〜7を通して実行し、`output/`に有効なMP4が生成されることを確認する
  - _Requirements: 8.1, 8.8_
