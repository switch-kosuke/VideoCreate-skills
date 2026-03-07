/**
 * 7.3 HookScene — フックシーン（フォント1.5倍以上・スケールアップ強調エフェクト）
 */
import React from "react";
import { AbsoluteFill, useCurrentFrame, interpolate, spring, useVideoConfig } from "remotion";
import { AssetEntry } from "../types";
import { StarField } from "./StarField";
import { KenBurnsImage } from "./KenBurnsImage";

interface HookSceneProps {
  text: string;
  text_en: string;
  lang: "ja" | "en";
  asset: AssetEntry | undefined;
  startFrame: number;
  durationFrames: number;
}

export const HookScene: React.FC<HookSceneProps> = ({
  text,
  text_en,
  lang,
  asset,
  startFrame,
  durationFrames,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const localFrame = frame - startFrame;
  const displayText = lang === "ja" ? text : text_en;

  // スケールアップ強調エフェクト
  const scale = spring({
    frame: localFrame,
    fps,
    config: { damping: 20, stiffness: 200 },
  });

  const opacity = interpolate(localFrame, [0, 8], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const useFallback = !asset || asset.source === "fallback" || !asset.local_path;

  return (
    <AbsoluteFill>
      {/* 背景 */}
      {useFallback ? (
        <StarField />
      ) : (
        <KenBurnsImage src={asset.local_path} durationFrames={durationFrames} />
      )}

      {/* 暗いオーバーレイ */}
      <AbsoluteFill style={{ backgroundColor: "rgba(0,0,0,0.45)" }} />

      {/* フックテキスト（中央・大きめ） */}
      <AbsoluteFill
        style={{ justifyContent: "center", alignItems: "center", padding: 48 }}
      >
        <p
          style={{
            fontSize: 72,       // BilingualSubtitle の 1.5倍以上（52 * 1.5 ≈ 78 → 72以上）
            color: "white",
            fontWeight: "bold",
            textShadow: "0 4px 16px rgba(0,0,0,0.95)",
            textAlign: "center",
            lineHeight: 1.3,
            margin: 0,
            opacity,
            transform: `scale(${scale})`,
          }}
        >
          {displayText}
        </p>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
