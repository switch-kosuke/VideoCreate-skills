/**
 * 7.3 ContentScene — 通常コンテンツシーン（KenBurnsImage or Video 背景 + BilingualSubtitle）
 */
import React from "react";
import { AbsoluteFill, OffthreadVideo, staticFile, useVideoConfig } from "remotion";
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
  asset,
  durationFrames,
}) => {
  const jaText = scene.voiceover;
  const enText = scene.voiceover_en;
  const { fps } = useVideoConfig();

  const useFallback = !asset || asset.source === "fallback" || !asset.local_path;
  const isVideo = !useFallback && asset?.media_type === "video";
  const videoStartFrame = asset?.video_start_sec != null ? Math.round(asset.video_start_sec * fps) : 0;

  return (
    <AbsoluteFill>
      {/* 背景レイヤー: fallback → StarField / それ以外 → ぼかした同素材をフルスクリーン */}
      {useFallback ? (
        <StarField />
      ) : isVideo ? (
        <OffthreadVideo
          src={staticFile(asset!.local_path)}
          trimBefore={videoStartFrame}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            filter: "blur(24px) brightness(0.45)",
            transform: "scale(1.08)",
          }}
          muted
        />
      ) : (
        <div style={{ width: "100%", height: "100%", filter: "blur(24px) brightness(0.45)", transform: "scale(1.08)" }}>
          <KenBurnsImage src={asset!.local_path} durationFrames={durationFrames} />
        </div>
      )}

      {/* メイン素材: 中央50%の高さにシャープ表示 */}
      {!useFallback && (
        <div
          style={{
            position: "absolute",
            top: "50%",
            left: 0,
            transform: "translateY(-50%)",
            width: "100%",
            height: "50%",
            overflow: "hidden",
          }}
        >
          {isVideo ? (
            <OffthreadVideo
              src={staticFile(asset!.local_path)}
              trimBefore={videoStartFrame}
              style={{ width: "100%", height: "100%", objectFit: "cover" }}
              muted
            />
          ) : (
            <KenBurnsImage src={asset!.local_path} durationFrames={durationFrames} />
          )}
        </div>
      )}

      {/* 字幕エリア下部を暗くして可読性向上 */}
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(to bottom, transparent 62%, rgba(0,0,0,0.72) 80%, rgba(0,0,0,0.92) 100%)",
        }}
      />

      {/* 日英字幕 */}
      <BilingualSubtitle ja={jaText} en={enText} />
    </AbsoluteFill>
  );
};
