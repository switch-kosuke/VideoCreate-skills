---
description: NASA Spinoff 自動動画生成パイプライン（Step 1〜7）
allowed-tools: Bash, Read, Write, Edit
argument-hint: [--fetch]
---

# NASA Spinoff 動画生成パイプライン

NASA技術情報からYouTube Shorts向け縦型動画（60秒以内）を自動生成します。

## 起動オプション
- `$1` に `--fetch` を指定すると新規スクレイピングを実行します（省略時は既存ネタを使用）

---

## Step 1: ネタ収集（SpinoffScraper）

```bash
python scripts/step1_scrape.py $1
```

- `--fetch` ありの場合: spinoff.nasa.gov をスクレイピングして `data/spinoff_store.json` に追記保存
- `--fetch` なしの場合: 既存の `data/spinoff_store.json` をそのまま使用

スクリプトが非ゼロ終了した場合は以下を表示してリトライまたは中断をユーザーに確認すること:
> ❌ Step 1 失敗: [エラー内容]
> リトライ / スキップ / 中断 のいずれかを選択してください。

---

## Step 2: ネタ選択（TopicSelector）— Claude Code 処理

### 2-1. 未使用ネタの読み込みとスコアリング

`data/spinoff_store.json` を Read ツールで読み込み、`used: false` のレコードを抽出する。

未使用ネタが **0件** の場合:
> ❌ 未使用ネタがありません。`/nasa-video --fetch` で新規取得してください。
処理を終了する。

各レコードに以下の4軸でバイラルスコア（1〜10の整数）と選定理由（1〜2文）を付与する:
- **意外性**: 「え、これってNASA由来なの！？」と思える驚き度
- **日常関連性**: 視聴者の日常生活との接点の強さ
- **キャッチーさ**: タイトルや概要のフック力
- **日本人親和性**: 日本人視聴者が興味を持ちやすいか

### 2-2. 上位5件の表示

スコア降順で上位5件を以下のフォーマットで表示する:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📡 NASA Spinoff ネタ候補 TOP 5
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[1] スコア: 9/10 | カテゴリ: 医療
    タイトル: Memory Foam
    理由: 日常品との意外な接点が強く、タイトルのキャッチーさが高い

[2] スコア: 8/10 | カテゴリ: 食品
    タイトル: ...
    理由: ...

...（上位5件）

番号を入力してください（1〜5）
「もっと見る」と入力すると次の5件を表示します
```

### 2-3. ユーザー選択ゲート

ユーザーが **有効な番号（1〜表示件数）** を入力するまで次ステップへ進まない。

- 範囲外・無効入力の場合: `❌ 無効な入力です。1〜N の番号を入力してください。` と表示して再入力を促す
- 「もっと見る」の場合: 次点5件を追加スコアリングして表示し、再度入力を待つ

### 2-4. 選択結果の保存

ユーザーが番号を確定したら以下を実行する:

```bash
python scripts/step2_save_selection.py --url "<選択したレコードのURL>" --score <スコア>
```

`data/selected_item.json` が生成され、`data/spinoff_store.json` の該当レコードが `used: true` に更新される。

確認メッセージ:
```
✅ ネタ確定: [タイトル]（スコア: X/10）
   selected_item.json に保存しました。
```

---

## Step 3: 台本生成（ScriptAgent）— Claude Code 処理

### 3-1. 選択ネタの読み込み

`data/selected_item.json` を Read ツールで読み込み、記事タイトル・概要・カテゴリを把握する。

### 3-2. 日英バイリンガル台本の生成

以下のスキーマを持つ JSON を自分で生成する（外部 API 呼び出し禁止）:

```json
{
  "item_id": "<selected_item.record.id>",
  "title": "（25文字以内の日本語タイトル）",
  "title_en": "（英語タイトル）",
  "hook": "（最初の3秒 — 驚きを演出する日本語フック文）",
  "hook_en": "（英語フック文 — 直訳でなく自然な英語意訳）",
  "scenes": [
    {
      "id": 1,
      "voiceover": "（日本語ナレーション）",
      "voiceover_en": "（英語ナレーション — 自然な意訳）",
      "visual_note": "（ビジュアル説明）",
      "image_keywords": ["英語キーワード1", "英語キーワード2"],
      "duration_sec": 7
    }
  ],
  "outro": "NASAの技術が身近に潜んでいる話、もっと見たい人はチャンネル登録！",
  "outro_en": "NASA tech is hiding in your daily life — subscribe for more!",
  "total_duration_sec": 55
}
```

**生成ルール:**
- 口調: 「テンポよく畳み掛ける雑学ショート動画スタイル」— 一文一事実、断定調、体言止め多用
- 英語テキスト: 直訳ではなく英語圏視聴者に自然な意訳
- `title` は 25 文字以内
- `image_keywords` は 2〜4 語の英語キーワード
- `total_duration_sec` = シーン合計 + hook(3秒) + outro(5秒)

**テンポ・構成ルール（重要）:**
- シーン数: **6〜8シーン**（1シーンにつき1事実を完結させる）
- 1シーンあたりの `duration_sec`: **6〜8秒**（長くても9秒まで）
- voiceover は **25〜40文字**（読み上げ約3〜5秒）。1シーンに詰め込みすぎない
- 文末は「〜です。」より「〜なんです！」「〜なんだ。」「実は〜。」など感情を乗せる
- シーン間に「驚き→説明→驚き→深掘り→まとめ」の感情の波を作る
- hook は視聴者が「え？」となる疑問形か衝撃の一言（例:「あなたの枕、実はNASA製かも？」）
- outro は **必ず固定文言** を使う: `「NASAの技術が身近に潜んでいる話、もっと見たい人はチャンネル登録！」`（変更禁止）
- outro_en は固定: `"NASA tech is hiding in your daily life — subscribe for more!"`

**悪い例（やってはいけない）:**
- ❌ 1シーンに2〜3文を詰め込む「〜です。〜があります。〜しています。」
- ❌ 「〜という技術が開発されました」のような説明的な長文
- ❌ duration_sec が10秒超え

**良い例:**
- ✅ Scene 1（7秒）:「実はビールの泡、宇宙技術で作られてるって知ってた？」
- ✅ Scene 2（6秒）:「NASAが開発した圧力制御システム。それがビール工場に転用された。」
- ✅ Scene 3（7秒）:「均一な泡立ち＝飲み心地の革命。コレ、全部NASAのおかげ。」

### 3-3. ユーザー提示・承認ループ（最大3回）

生成した台本を以下のフォーマットで提示する:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 生成された台本
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
タイトル: [title]（[total_duration_sec]秒）

🎣 Hook（3秒）
  JA: [hook]
  EN: [hook_en]

📷 Scene 1（[duration_sec]秒）
  JA: [voiceover]
  EN: [voiceover_en]
  画像キーワード: [image_keywords]

...（各シーン）

🎬 Outro（5秒）
  JA: [outro]
  EN: [outro_en]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
承認する場合は「OK」、修正依頼は具体的に入力してください。
```

- `total_duration_sec` が **65秒超過** の場合: 承認前にシーン圧縮案を提示する（60秒未満の場合はStep 6で自動的にアウトロを延長して60秒に調整される）
- 修正依頼を受けた場合: 指摘を反映して再生成（最大3回まで）
- 3回を超えた場合: 「手動で `data/script_*.json` を編集してください」と案内して終了

### 3-4. 台本の保存

ユーザーが「OK」で承認したら以下を実行する:

```bash
python scripts/step3_save_script.py --script-json '<台本JSONをエスケープした文字列>'
```

または Write ツールで直接 `data/script_{item_id}.json` に書き出す。

確認メッセージ:
```
✅ 台本確定: [title]（[total_duration_sec]秒 / [N]シーン）
   script_{item_id}.json に保存しました。
```

---

## Step 4: 画像素材取得（AssetFetcher）

台本ファイルのパスを確認してから実行する（`data/script_{item_id}.json`）:

```bash
python scripts/step4_fetch_assets.py --script data/script_<item_id>.json
```

- APIキーは `.env` の `PEXELS_API_KEY` から自動読み込みされる
- 期待出力: `assets/<item_id>/manifest.json`、`assets/<item_id>/scene_*/`・`assets/<item_id>/hook/`・`assets/<item_id>/outro/` ディレクトリ

スクリプトが非ゼロ終了した場合:
> ❌ Step 4 失敗: [エラー内容]
> リトライ / スキップ / 中断 のいずれかを選択してください。

完了したら次ステップに続行する前にユーザーに確認する:
> ✅ Step 4 完了: 素材取得 [N]シーン（fallback: [M]件）
> Step 5（音声生成）に進みますか？ [Enter で続行]

---

## Step 5: 音声生成（VoiceGenerator）

```bash
python scripts/step5_voice.py --script data/script_<item_id>.json
```

- デフォルトボイス: JA=`ja-JP-NanamiNeural` / EN=`en-US-JennyNeural`
- デフォルト速度: `+25%`（速め。変更する場合は `--rate +40%` などを追加）
- カスタムボイスを使う場合: `--ja-voice <voice>` / `--en-voice <voice>` を追加
- 期待出力: `audio/ja/scene_*.mp3`・`audio/en/scene_*.mp3`・`data/audio_manifest.json`
- 各音声ファイルの実測長を manifest に記録し、Step 6 でシーン尺を自動調整する

スクリプトが非ゼロ終了した場合:
> ❌ Step 5 失敗: [エラー内容]
> リトライ / スキップ / 中断 のいずれかを選択してください。

完了したら:
> ✅ Step 5 完了: 音声生成 [N]ファイル（JA/EN 各[M]シーン）
> Step 6（動画レンダリング）に進みますか？ [Enter で続行]

---

## Step 6: 動画レンダリング（RenderPreparer + VideoRenderer）

### 6-1. render_props.json の生成

```bash
python scripts/step6_prepare_render.py --id <item_id> --lang ja
```

- 期待出力: `data/render_props.json`（script + audio_manifest + assets_manifest のマージ）
- `--lang en` にすると英語音声トラックで生成される
- 音声の実測長に基づき script の `duration_sec` を自動調整する
- `assets/<item_id>/` と `audio/` を `remotion/public/` に自動同期する

スクリプトが非ゼロ終了した場合（不足ファイルのパスが明示される）:
> ❌ Step 6-1 失敗: [不足ファイルパス]
> 該当ステップをリトライ / 中断 のいずれかを選択してください。

### 6-2. Remotion レンダリング

```bash
cd remotion && npx remotion render src/index.ts NasaSpinoffVideo --props ../data/render_props.json --output ../tmp/render_<item_id>.mp4
```

- 期待出力: `tmp/render_<item_id>.mp4`
- レンダリング失敗時は stderr を表示する

完了したら:
> ✅ Step 6 完了: `tmp/render_<item_id>.mp4` 生成
> Step 7（BGMミックス・最終出力）に進みますか？ [Enter で続行]

---

## Step 7: 後処理（PostProcessor）

```bash
python scripts/step7_postprocess.py --input tmp/render_<item_id>.mp4 --id <item_id>
```

- Pixabay BGM は `.env` の `PIXABAY_API_KEY` から取得（`assets/bgm/` にキャッシュ）
- APIキー未設定 / 取得失敗時は BGM なしで続行
- FFmpeg が見つからない場合はインストール手順を案内して中断する
- 期待出力: `output/output_<item_id>_<YYYYMMDD>.mp4`

スクリプトが非ゼロ終了した場合:
> ❌ Step 7 失敗: [エラー内容]
> リトライ / スキップ / 中断 のいずれかを選択してください。

---

## パイプライン完了サマリー

全ステップ完了後に以下のサマリーを表示する:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎬 NASA Spinoff 動画生成 完了！
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
出力ファイル: output/output_<item_id>_<YYYYMMDD>.mp4
ファイルサイズ: [X] MB
生成シーン数: [N] シーン（hook + [M]コンテンツ + outro）
合計尺: [S] 秒
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

ファイルサイズは以下で取得する:
```bash
python -c "import os; p='output/output_<item_id>_<date>.mp4'; print(f'{os.path.getsize(p)/1024/1024:.1f} MB') if os.path.exists(p) else print('ファイルなし')"
```
