/**
 * Task 7.4 — VideoRenderer ユーティリティ関数テスト（TDD: RED → GREEN）
 *
 * フレーム計算・アセット取得・音声パス取得の純粋ロジックをテストする。
 */
import {
  calcSceneFrames,
  getAssetForScene,
  getAudioForScene,
  getTotalFrames,
} from "../src/utils";
import { ScriptJSON, AssetsManifest, AudioManifest } from "../src/types";

const SAMPLE_SCRIPT: ScriptJSON = {
  item_id: "test-001",
  title: "テストタイトル",
  title_en: "Test Title",
  hook: "フック",
  hook_en: "Hook",
  scenes: [
    {
      id: 1,
      voiceover: "ナレーション1",
      voiceover_en: "Narration 1",
      visual_note: "ビジュアル1",
      image_keywords: ["space", "nasa"],
      duration_sec: 10,
    },
    {
      id: 2,
      voiceover: "ナレーション2",
      voiceover_en: "Narration 2",
      visual_note: "ビジュアル2",
      image_keywords: ["tech", "innovation"],
      duration_sec: 15,
    },
  ],
  outro: "アウトロ",
  outro_en: "Outro",
  total_duration_sec: 33, // 3 + 10 + 15 + 5
};

const SAMPLE_ASSETS: AssetsManifest = {
  item_id: "test-001",
  generated_at: "2026-01-01T00:00:00Z",
  scenes: [
    {
      scene_id: "hook",
      source: "nasa",
      local_path: "assets/hook/nasa_img.jpg",
      license: "NASA Public Domain",
      original_url: "https://example.com/img.jpg",
    },
    {
      scene_id: "1",
      source: "pexels",
      local_path: "assets/scene_1/pexels_img.jpg",
      license: "Pexels License",
      original_url: "https://pexels.com/img.jpg",
    },
    {
      scene_id: "2",
      source: "fallback",
      local_path: "",
      license: "",
      original_url: "",
    },
    {
      scene_id: "outro",
      source: "nasa",
      local_path: "assets/outro/nasa_img2.jpg",
      license: "NASA Public Domain",
      original_url: "https://example.com/img2.jpg",
    },
  ],
  bgm: {},
};

const SAMPLE_AUDIO: AudioManifest = {
  item_id: "test-001",
  generated_at: "2026-01-01T00:00:00Z",
  ja_voice: "ja-JP-NanamiNeural",
  en_voice: "en-US-JennyNeural",
  hook: { ja: "audio/ja/scene_hook.mp3", en: "audio/en/scene_hook.mp3" },
  scenes: [
    { id: 1, ja: "audio/ja/scene_1.mp3", en: "audio/en/scene_1.mp3" },
    { id: 2, ja: "audio/ja/scene_2.mp3", en: "audio/en/scene_2.mp3" },
  ],
  outro: { ja: "audio/ja/scene_outro.mp3", en: "audio/en/scene_outro.mp3" },
};

// ---- getTotalFrames ----

test("getTotalFrames: total_duration_sec × FPS", () => {
  const frames = getTotalFrames(SAMPLE_SCRIPT, 30);
  expect(frames).toBe(33 * 30); // 990
});

test("getTotalFrames: FPS=60 での計算", () => {
  const frames = getTotalFrames(SAMPLE_SCRIPT, 60);
  expect(frames).toBe(33 * 60);
});

// ---- calcSceneFrames ----

test("calcSceneFrames: hook の開始フレームは 0", () => {
  const frames = calcSceneFrames(SAMPLE_SCRIPT, 30);
  expect(frames.hook.start).toBe(0);
  expect(frames.hook.end).toBe(3 * 30); // 90
  expect(frames.hook.durationFrames).toBe(3 * 30);
});

test("calcSceneFrames: scene[1] は hook の直後から開始", () => {
  const frames = calcSceneFrames(SAMPLE_SCRIPT, 30);
  expect(frames.scenes[0].start).toBe(3 * 30); // 90
  expect(frames.scenes[0].end).toBe((3 + 10) * 30); // 390
  expect(frames.scenes[0].durationFrames).toBe(10 * 30);
});

test("calcSceneFrames: scene[2] は scene[1] の直後から開始", () => {
  const frames = calcSceneFrames(SAMPLE_SCRIPT, 30);
  expect(frames.scenes[1].start).toBe((3 + 10) * 30); // 390
  expect(frames.scenes[1].end).toBe((3 + 10 + 15) * 30); // 840
});

test("calcSceneFrames: outro は全シーン後に開始", () => {
  const frames = calcSceneFrames(SAMPLE_SCRIPT, 30);
  const outroStart = (3 + 10 + 15) * 30; // 840
  expect(frames.outro.start).toBe(outroStart);
  expect(frames.outro.durationFrames).toBe(5 * 30);
});

// ---- getAssetForScene ----

test("getAssetForScene: hook の素材を返す", () => {
  const entry = getAssetForScene(SAMPLE_ASSETS, "hook");
  expect(entry?.source).toBe("nasa");
  expect(entry?.local_path).toBe("assets/hook/nasa_img.jpg");
});

test("getAssetForScene: scene_id='1' の素材を返す", () => {
  const entry = getAssetForScene(SAMPLE_ASSETS, "1");
  expect(entry?.source).toBe("pexels");
});

test("getAssetForScene: fallback シーンを返す", () => {
  const entry = getAssetForScene(SAMPLE_ASSETS, "2");
  expect(entry?.source).toBe("fallback");
});

test("getAssetForScene: 存在しない scene_id は undefined", () => {
  const entry = getAssetForScene(SAMPLE_ASSETS, "99");
  expect(entry).toBeUndefined();
});

// ---- getAudioForScene ----

test("getAudioForScene: hook JA 音声パスを返す", () => {
  const path = getAudioForScene(SAMPLE_AUDIO, "hook", "ja");
  expect(path).toBe("audio/ja/scene_hook.mp3");
});

test("getAudioForScene: hook EN 音声パスを返す", () => {
  const path = getAudioForScene(SAMPLE_AUDIO, "hook", "en");
  expect(path).toBe("audio/en/scene_hook.mp3");
});

test("getAudioForScene: scene id=1 JA 音声パスを返す", () => {
  const path = getAudioForScene(SAMPLE_AUDIO, "1", "ja");
  expect(path).toBe("audio/ja/scene_1.mp3");
});

test("getAudioForScene: scene id=2 EN 音声パスを返す", () => {
  const path = getAudioForScene(SAMPLE_AUDIO, "2", "en");
  expect(path).toBe("audio/en/scene_2.mp3");
});

test("getAudioForScene: outro JA 音声パスを返す", () => {
  const path = getAudioForScene(SAMPLE_AUDIO, "outro", "ja");
  expect(path).toBe("audio/ja/scene_outro.mp3");
});

test("getAudioForScene: 存在しない scene_id は undefined", () => {
  const path = getAudioForScene(SAMPLE_AUDIO, "99", "ja");
  expect(path).toBeUndefined();
});
