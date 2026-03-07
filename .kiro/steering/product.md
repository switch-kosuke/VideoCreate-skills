# Product Overview

NASA Spinoff 自動動画生成パイプライン。spinoff.nasa.govのNASA技術情報をソースに、YouTube Shorts向け縦型動画（9:16）を完全自動生成するコンテンツ制作ツール。

## Core Capabilities

- **ネタ収集・蓄積**: spinoff.nasa.govからSpinoff技術情報をスクレイピングして永続ストアに蓄積する
- **AI駆動のネタ選択**: バイラルスコアリングで再生数が見込めるネタをランキングし、ユーザーが番号選択する
- **会話型台本生成**: Claude Codeが日英バイリンガル台本を生成し、ユーザーが承認・修正する
- **フルオートメディア合成**: 画像取得（NASA API / Pexels）・音声合成（edge-tts）・動画レンダリング（Remotion）・BGMミックス（FFmpeg）を自動実行する

## Target Use Cases

- YouTubeショートコンテンツを週次・日次で量産したいソロクリエイター
- NASA技術の「意外な日常接点」をネタにバイラルを狙うチャンネル運営
- 日本語・英語バイリンガル字幕で海外視聴者にもリーチしたい配信者

## Value Proposition

`/nasa-video` 一行で起動し、ネタ選択から最終MP4まで会話の流れで完結する。外部APIキーの管理が最小限で済み（NASA Image APIはキー不要）、全素材が著作権フリー（NASA公開ドメイン / Pexelsライセンス / Pixabayライセンス）。

---
_Focus on patterns and purpose, not exhaustive feature lists_
