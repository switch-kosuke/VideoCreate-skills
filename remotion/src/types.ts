export interface SceneData {
  id: number;
  voiceover: string;
  voiceover_en: string;
  visual_note: string;
  image_keywords: string[];
  duration_sec: number;
}

export interface ScriptJSON {
  item_id: string;
  title: string;
  title_en: string;
  hook: string;
  hook_en: string;
  scenes: SceneData[];
  outro: string;
  outro_en: string;
  hook_duration_sec?: number;
  outro_duration_sec?: number;
  total_duration_sec: number;
}

export interface AudioTrack {
  ja: string;
  en: string;
}

export interface AudioManifest {
  item_id: string;
  generated_at: string;
  ja_voice: string;
  en_voice: string;
  hook: AudioTrack;
  scenes: Array<{ id: number } & AudioTrack>;
  outro: AudioTrack;
}

export interface AssetEntry {
  scene_id: string;
  source: "nasa" | "pexels" | "article" | "fallback";
  media_type: "image" | "video";
  local_path: string;
  license: string;
  original_url: string;
  /** 動画の再生開始秒数 (optional) */
  video_start_sec?: number;
}

export interface AssetsManifest {
  item_id: string;
  generated_at: string;
  scenes: AssetEntry[];
  bgm: Record<string, string>;
}

export interface VideoCompositionProps {
  script: ScriptJSON;
  audioManifest: AudioManifest;
  assetsManifest: AssetsManifest;
  lang: "ja" | "en";
}
