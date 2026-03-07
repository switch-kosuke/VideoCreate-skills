import React from "react";
import { Composition } from "remotion";
import { NasaSpinoffVideo } from "./NasaSpinoffVideo";
import { VideoCompositionProps } from "./types";

const defaultProps: VideoCompositionProps = {
  script: {
    item_id: "test",
    title: "NASA技術が日常に",
    title_en: "NASA Tech in Daily Life",
    hook: "実はあの技術、宇宙から来ていた。",
    hook_en: "That technology actually came from space.",
    scenes: [
      {
        id: 1,
        voiceover: "NASAが開発したこの技術は...",
        voiceover_en: "This technology developed by NASA...",
        visual_note: "宇宙ステーション映像",
        image_keywords: ["space station", "NASA"],
        duration_sec: 10,
      },
    ],
    outro: "チャンネル登録で最新情報をお届けします！",
    outro_en: "Subscribe for the latest updates!",
    total_duration_sec: 60,
  },
  audioManifest: {
    item_id: "test",
    generated_at: "",
    ja_voice: "ja-JP-NanamiNeural",
    en_voice: "en-US-JennyNeural",
    hook: { ja: "", en: "" },
    scenes: [{ id: 1, ja: "", en: "" }],
    outro: { ja: "", en: "" },
  },
  assetsManifest: {
    item_id: "test",
    generated_at: "",
    scenes: [],
    bgm: {},
  },
  lang: "ja",
};

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="NasaSpinoffVideo"
        component={NasaSpinoffVideo}
        durationInFrames={1800}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={defaultProps}
      />
    </>
  );
};
