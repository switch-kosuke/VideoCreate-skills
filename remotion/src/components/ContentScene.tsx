/**
 * 7.3 ContentScene — 通常コンテンツシーン（KenBurnsImage 背景 + BilingualSubtitle）
 */
import React from "react";
import { AbsoluteFill } from "remotion";
import { SceneData, AssetEntry } from "../types";
import { StarField } from "./StarField";
import { KenBurnsImage } from "./KenBurnsImage";
import { BilingualSubtitle } from "./BilingualSubtitle";

interface ContentSceneProps {
  scene: SceneData;
  lang: "ja" | "en";
  asset: AssetEntry | undefined;
  startFrame: number;
  durationFrames: number;
}

export const ContentScene: React.FC<ContentSceneProps> = ({
  scene,
  lang,
  asset,
  durationFrames,
}) => {
  const jaText = scene.voiceover;
  const enText = scene.voiceover_en;

  const useFallback = !asset || asset.source === "fallback" || !asset.local_path;

  return (
    <AbsoluteFill>
      {/* 背景画像またはスターフィールド */}
      {useFallback ? (
        <StarField />
      ) : (
        <KenBurnsImage src={asset.local_path} durationFrames={durationFrames} />
      )}

      {/* 半透明グラデーションオーバーレイ（字幕可読性向上） */}
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(to bottom, transparent 50%, rgba(0,0,0,0.7) 100%)",
        }}
      />

      {/* 日英字幕 */}
      <BilingualSubtitle ja={jaText} en={enText} />
    </AbsoluteFill>
  );
};
