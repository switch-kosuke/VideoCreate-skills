# 要件定義書

## はじめに

本ドキュメントは「NASA Spinoff 自動動画生成パイプライン」の要件を定義する。
本パイプラインは、NASAのSpinoff技術情報をソースとして、YouTube Shorts向け縦型動画（60秒以内）を完全自動で生成するシステムである。
スクレイピング・ネタ蓄積・バイラルスコアリングによるユーザー選択・台本生成・音声合成・動画レンダリング・後処理の7ステップで構成され、Claude Code上で会話形式で操作可能なことを目指す。

---

## 要件

### 要件 1: NASA Spinoffネタ取得・永続保存

**目的:** コンテンツ制作者として、spinoff.nasa.govから最新のSpinoff技術情報を自動取得し、過去に取得したネタも含めて蓄積・管理したい。それにより、毎回スクレイピングせずとも蓄積済みのネタプールから動画素材を選べる。

#### 受け入れ基準

1. When パイプラインのStep 1が実行されたとき、the SpinoffScraper shall spinoff.nasa.govのWebページまたはRSSフィードにアクセスし、最新のSpinoff記事一覧を取得する。
2. When スクレイピングが成功したとき、the SpinoffScraper shall 各記事からタイトル・概要・カテゴリ（医療/日用品/食品/環境など）・記事URL・取得日時を抽出する。
3. When データ抽出が完了したとき、the SpinoffScraper shall 抽出した情報を永続ストア（`data/spinoff_store.json`）に追記保存する。
4. The SpinoffScraper shall 重複する記事（同一URL）を永続ストアに重複登録しない。
5. The SpinoffScraper shall 永続ストアの各レコードに`used`フラグ（boolean）と`used_at`タイムスタンプを持たせ、動画生成済みのネタを識別できるようにする。
6. If ネットワークエラーまたはスクレイピングに失敗したとき、the SpinoffScraper shall エラー内容をログに出力し、既存の永続ストアを破壊せずに処理を中断してユーザーに通知する。
7. The SpinoffScraper shall `--fetch`フラグなしで実行された場合、新規スクレイピングをスキップし、永続ストアの既存データのみを対象とする。

---

### 要件 2: バイラルスコアリング＆ユーザー選択

**目的:** コンテンツ制作者として、蓄積されたSpinoffネタの中から「再生数が稼げそうなネタ」をClaudeが評価・ランキングし、番号選択形式でネタを選びたい。それにより、バズりやすいコンテンツに集中して動画制作できる。

#### 受け入れ基準

1. When Step 2が実行されたとき、the TopicSelector shall 永続ストアから`used: false`のネタ一覧を読み込む。
2. When 未使用ネタが読み込まれたとき、the TopicSelector shall Claude APIを使用して各ネタにバイラルスコア（1〜10の整数）と選定理由（1〜2文）を付与する。バイラルスコアの評価軸は「意外性・日常との関連性・タイトルのキャッチーさ・日本人視聴者との親和性」とする。
3. When スコアリングが完了したとき、the TopicSelector shall バイラルスコアの高い順に上位5件を選び、以下の形式でClaude Code上に表示する：
   ```
   [1] スコア: 9/10 | カテゴリ: 医療
       タイトル: Memory Foam
       理由: 日常品との意外な接点が強く、タイトルのキャッチーさが高い
   [2] スコア: 8/10 | カテゴリ: 食品
       ...
   ```
4. When 候補一覧が表示されたとき、the TopicSelector shall ユーザーに番号入力を促し、入力が確定するまで次のステップを実行しない。
5. When ユーザーが有効な番号を入力したとき、the TopicSelector shall 選択されたネタを`data/selected_item.json`として保存する。
6. If ユーザーが範囲外の番号または無効な入力をしたとき、the TopicSelector shall 再入力を促すメッセージを表示する。
7. When ユーザーがネタを選択・確定したとき、the TopicSelector shall 永続ストア内の該当レコードの`used`フラグを`true`に、`used_at`に現在日時を記録する。
8. If 未使用ネタが0件のとき、the TopicSelector shall 「未使用ネタがありません。`--fetch`オプションで新規取得してください」と表示し、処理を終了する。
9. Where ユーザーが候補一覧の「もっと見る」を選択したとき、the TopicSelector shall 次点のネタを5件追加表示する。

---

### 要件 3: 台本自動生成

**目的:** コンテンツ制作者として、ユーザーが選択したSpinoffネタをもとに、Claude Code エージェント（またはサブエージェント）が直接YouTube Shorts向けの日英台本を生成してほしい。それにより、外部APIキーの管理不要で、会話の流れの中でそのまま台本が得られる。

#### 受け入れ基準

1. When Step 3が実行されたとき、the ScriptAgent shall `data/selected_item.json`（要件2で選択されたネタ）を読み込み、Claude Code エージェント自身（またはサブエージェント）が台本生成タスクを実行する。外部 Claude API の直接呼び出しは行わない。
2. When 台本生成タスクが完了したとき、the ScriptAgent shall 以下のスキーマを持つJSONとして台本を出力する：`title`（25文字以内）、`title_en`（英語タイトル）、`hook`（最初の3秒の日本語セリフ）、`hook_en`（英語セリフ）、`scenes`（各シーンの`id`・`voiceover`・`voiceover_en`・`visual_note`・`image_keywords`（画像検索用英語キーワード配列、2〜4語）・`duration_sec`）、`outro`、`outro_en`、`total_duration_sec`。
3. The ScriptAgent shall 台本の口調を「親しみやすく、驚きを演出するテンポ感」で生成する。日英両言語で同一のトーン・ニュアンスが保たれるようにする。
4. The ScriptAgent shall 英語テキストは直訳でなく、英語圏視聴者に自然に伝わる意訳として生成する。
5. When 台本が生成されたとき、the ScriptAgent shall 生成した台本をユーザーに提示し、修正依頼を受け付ける。ユーザーが承認したあと`data/script_{記事ID}.json`として保存する。
6. When ユーザーが台本の修正を依頼したとき、the ScriptAgent shall 指摘箇所を反映した台本を再生成し、再度ユーザーに提示する。
7. When 台本が確定したとき、the ScriptAgent shall `total_duration_sec`が60秒以下になるよう各シーンの`duration_sec`の合計を検証し、超過している場合はシーン圧縮案をユーザーに提案する。

---

### 要件 4: 画像・動画素材取得

**目的:** コンテンツ制作者として、各シーンの `image_keywords` をもとにNASA公式ライブラリおよびフリー素材APIから関連画像・動画を自動取得したい。それにより、著作権フリーのビジュアルで動画クオリティを高められる。

#### 受け入れ基準

1. When Step 4が実行されたとき、the AssetFetcher shall 台本JSONの全シーンの`image_keywords`を読み込み、素材取得を開始する。
2. The AssetFetcher shall まず NASA Image and Video Library API（`images-api.nasa.gov/search`）に対して`image_keywords`で検索し、画像または動画クリップを取得する。APIキー不要で利用できる。
3. When NASA APIの検索結果が1件以上あったとき、the AssetFetcher shall 最もrelevance scoreの高いメディアファイルをダウンロードし、`assets/scene_{id}/nasa_{filename}`として保存する。
4. If NASA APIの検索結果が0件、またはダウンロードに失敗したとき、the AssetFetcher shall フォールバックとしてPexels API（`api.pexels.com/v1/search`）に同じキーワードで検索し、ライセンスフリーの写真を取得する。PexelsのAPIキーは`.env`から読み込む。
5. When Pexels APIから結果を取得したとき、the AssetFetcher shall 横長（landscape）または縦長（portrait）に関わらず解像度が最も高いものを1枚選択し、`assets/scene_{id}/pexels_{filename}`として保存する。
6. If NASA・Pexels双方で素材が取得できないとき、the AssetFetcher shall 該当シーンIDをログに記録し、フォールバック素材として星フィールド背景のみを使用するフラグを`assets/manifest.json`にセットする。
7. The AssetFetcher shall `hook`・`outro`シーンについても同様にキーワード検索を行い、`assets/hook/`・`assets/outro/`に保存する。
8. When 全シーンの素材取得が完了したとき、the AssetFetcher shall 各シーンのローカルパス・素材ソース（nasa/pexels/fallback）・ライセンス情報を`assets/manifest.json`に書き出す。

---

### 要件 5: ナレーション音声生成

**目的:** コンテンツ制作者として、台本の各シーンテキストから自動的にMP3音声ファイルを生成したい。それにより、プロ品質の日本語ナレーションを無料で作成できる。

#### 受け入れ基準

1. When Step 5が実行されたとき、the VoiceGenerator shall Step 3で生成した台本JSONを読み込み、`scenes`配列の全`voiceover`（日本語）および`voiceover_en`（英語）テキストを取得する。
2. When `voiceover`テキストが取得できたとき、the VoiceGenerator shall edge-ttsライブラリを使用して日本語・英語それぞれをMP3に変換する。
3. The VoiceGenerator shall 日本語音声のデフォルトを`ja-JP-NanamiNeural`（女性）とし、設定ファイルまたは引数で`ja-JP-KeitaNeural`（男性）に切り替え可能とする。
4. The VoiceGenerator shall 英語音声のデフォルトを`en-US-JennyNeural`（女性）とし、設定ファイルまたは引数で`en-US-GuyNeural`（男性）に切り替え可能とする。
5. When 音声ファイルが生成されたとき、the VoiceGenerator shall 日本語音声を`audio/ja/scene_{id}.mp3`、英語音声を`audio/en/scene_{id}.mp3`の形式で言語別ディレクトリに保存する。
6. The VoiceGenerator shall `hook`と`outro`の音声も同様に`audio/ja/scene_hook.mp3`・`audio/en/scene_hook.mp3`の形式で生成する。
7. If 特定のシーンで音声生成に失敗したとき、the VoiceGenerator shall 言語・シーンIDとエラー内容をログに出力し、処理を停止する。
8. The VoiceGenerator shall 生成した全音声ファイルのパス一覧を`data/audio_manifest.json`に書き出し、後続ステップから参照できるようにする。

---

### 要件 6: Remotionによる動画レンダリング

**目的:** コンテンツ制作者として、台本・音声・取得済み画像素材をもとにNASAらしい宇宙テイストのビジュアルを持つ縦型動画をRemotionで自動生成したい。それにより、デザインスキルなしにShorts対応のMP4を作成できる。

#### 受け入れ基準

1. The VideoRenderer shall 解像度1080×1920（9:16縦型）でYouTube Shorts対応のMP4を出力する。
2. The VideoRenderer shall `assets/manifest.json`を読み込み、各シーンに対応する画像素材をフルスクリーン背景として表示する。素材ソースが`fallback`のシーンは黒背景＋星フィールドアニメーションを使用する。
3. When 画像背景を表示するとき、the VideoRenderer shall ケンバーンズエフェクト（ゆっくりズームまたはパン）を適用し、静止画でも動きのある演出にする。
4. When フックシーンが表示されるとき、the VideoRenderer shall 大きな文字（フォントサイズを他シーンより1.5倍以上）と強調エフェクト（スケールアップまたは点滅）を適用する。
5. When 各シーンが遷移するとき、the VideoRenderer shall テキストにフェードインまたはスライドインアニメーションを適用する。
6. The VideoRenderer shall 各シーンの字幕を日英併記で表示する。日本語テキスト（`voiceover`）を画面下部メインに大きく、英語テキスト（`voiceover_en`）をその直下に小さく（日本語の70%サイズ）表示する。
7. The VideoRenderer shall 字幕の表示タイミングを日本語音声（`audio/ja/`）の再生と同期させる。
8. When `npx remotion render`が実行されたとき、the VideoRenderer shall Step 3の台本JSON・`data/audio_manifest.json`・`assets/manifest.json`を読み込み、シーン構成を自動組み立てする。
9. The VideoRenderer shall レンダリング対象の音声言語を引数（例: `--lang ja`）で指定可能とし、デフォルトは日本語音声とする。
10. The VideoRenderer shall 各シーンの表示時間を台本JSONの`duration_sec`に従って制御する。
11. If 音声ファイルまたは`assets/manifest.json`が見つからないとき、the VideoRenderer shall 該当ファイルパスを明示したエラーメッセージを出力し、レンダリングを中断する。

---

### 要件 7: FFmpegによる後処理

**目的:** コンテンツ制作者として、レンダリング済み動画にBGMを自動ミックスして最終MP4を出力したい。それにより、完成品のクオリティを高め投稿可能な状態にできる。

#### 受け入れ基準

1. When Step 7が実行されたとき、the PostProcessor shall BGM素材が`assets/bgm/`に存在するか確認し、存在しない場合はPixabay Audio API（`pixabay.com/api/`）からフリーBGMを自動取得する。
2. When Pixabay Audio APIを呼び出すとき、the PostProcessor shall 「space ambient」または「epic cinematic」キーワードで検索し、再生時間が30秒以上のトラックを取得する。PixabayのAPIキーは`.env`から読み込む。
3. When BGM取得が完了したとき、the PostProcessor shall ダウンロードしたBGMを`assets/bgm/bgm_{filename}.mp3`として保存し、次回以降の再利用に備える。
4. If Pixabay APIの取得に失敗したとき、the PostProcessor shall `assets/bgm/`内の既存ファイルを使用し、それも存在しない場合はBGMなしで続行してユーザーに通知する。
5. The PostProcessor shall Step 6で生成したMP4とBGMをFFmpegでミックスする。BGMはナレーション音声の背後に-20dBで調整し、ナレーションの音量は変更しない。
6. When ミックスが完了したとき、the PostProcessor shall 最終MP4を`output/`フォルダに`output_{記事ID}_{YYYYMMDD}.mp4`の形式で保存する。
7. If FFmpegが見つからない（パス未設定）とき、the PostProcessor shall インストール手順を案内するメッセージを出力し、処理を中断する。
8. The PostProcessor shall 動画の長さがBGMより短い場合、BGMを動画の長さにトリミングして出力する。

---

### 要件 8: パイプライン統合・オーケストレーション

**目的:** コンテンツ制作者として、`/nasa-video` と入力するだけでClaude Codeが全ステップを会話の流れでガイドしてほしい。それにより、ツールの切り替えやAPIキー管理なしにエンドツーエンドの動画生成を完結できる。

#### 受け入れ基準

1. The Pipeline shall `.claude/commands/nasa-video.md` にカスタムスラッシュコマンドとして実装し、ユーザーが `/nasa-video` と入力することでパイプラインが起動する。
2. The Pipeline shall Claude Code エージェントをオーケストレーターとして、Step 1〜7 を会話の流れで順番に進行させる。Step 2のユーザー選択・Step 3の台本承認など、ユーザーの確認を要するステップでは必ず一時停止する。
3. The Pipeline shall Step 1（スクレイピング）・Step 4（画像取得）・Step 5（音声生成）・Step 6（動画レンダリング）・Step 7（FFmpeg後処理）をPythonスクリプトとして実装し、Claude Code が Bash ツール経由で呼び出す。
4. The Pipeline shall Step 2（ネタ選択）・Step 3（台本生成）は Claude Code エージェント自身（またはサブエージェント）が会話形式で処理する。
5. When 各 Step が完了したとき、the Pipeline shall 次のステップの概要と実行確認をユーザーに提示し、承認を得てから次のステップに進む。
6. If 任意のステップが失敗したとき、the Pipeline shall 失敗したステップ番号・原因・推奨対処法をユーザーに提示し、リトライまたはスキップの選択肢を提供する。
7. The Pipeline shall Pexels・Pixabay 等の外部APIキーを`.env`ファイルで管理する。Claude Code 自身の認証情報はコードに含めない。
8. When パイプライン全体が完了したとき、the Pipeline shall 出力ファイルのパス・所要時間・生成シーン数・出力ファイルサイズを含むサマリーをユーザーに表示する。
9. The Pipeline shall Python 3.10以上およびNode.js 18以上の実行環境を前提とし、`requirements.txt`と`package.json`で依存関係を管理する。
