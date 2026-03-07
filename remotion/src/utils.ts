/**
 * VideoRenderer ユーティリティ関数
 * フレーム計算・アセット取得・音声パス取得の純粋ロジック
 */
import { ScriptJSON, AssetsManifest, AudioManifest, AssetEntry } from "./types";

const HOOK_SEC = 3;
const OUTRO_SEC = 5;

export interface SceneFrameInfo {
  start: number;
  end: number;
  durationFrames: number;
}

export interface AllSceneFrames {
  hook: SceneFrameInfo;
  scenes: SceneFrameInfo[];
  outro: SceneFrameInfo;
}

/** total_duration_sec × fps で総フレーム数を返す */
export function getTotalFrames(script: ScriptJSON, fps: number): number {
  return script.total_duration_sec * fps;
}

/**
 * hook・各シーン・outro の開始/終了フレームを計算して返す
 * hook = 3秒、outro = 5秒 固定
 */
export function calcSceneFrames(
  script: ScriptJSON,
  fps: number
): AllSceneFrames {
  let cursor = 0;

  const hookDuration = HOOK_SEC * fps;
  const hook: SceneFrameInfo = {
    start: cursor,
    end: cursor + hookDuration,
    durationFrames: hookDuration,
  };
  cursor += hookDuration;

  const scenes: SceneFrameInfo[] = script.scenes.map((scene) => {
    const d = scene.duration_sec * fps;
    const info: SceneFrameInfo = { start: cursor, end: cursor + d, durationFrames: d };
    cursor += d;
    return info;
  });

  const outroDuration = OUTRO_SEC * fps;
  const outro: SceneFrameInfo = {
    start: cursor,
    end: cursor + outroDuration,
    durationFrames: outroDuration,
  };

  return { hook, scenes, outro };
}

/** sceneId に一致するアセットエントリを返す。見つからない場合は undefined */
export function getAssetForScene(
  assetsManifest: AssetsManifest,
  sceneId: string
): AssetEntry | undefined {
  return assetsManifest.scenes.find((s) => s.scene_id === sceneId);
}

/**
 * sceneId + lang に対応する音声ファイルパスを返す。
 * 見つからない場合は undefined
 */
export function getAudioForScene(
  audioManifest: AudioManifest,
  sceneId: string,
  lang: "ja" | "en"
): string | undefined {
  if (sceneId === "hook") return audioManifest.hook?.[lang];
  if (sceneId === "outro") return audioManifest.outro?.[lang];

  const scene = audioManifest.scenes.find((s) => String(s.id) === sceneId);
  return scene?.[lang];
}
