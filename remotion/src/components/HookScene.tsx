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

      {/* フックテキスト（フルワイド・インパクトデザイン） */}
      <AbsoluteFill
        style={{ justifyContent: "center", alignItems: "stretch", padding: "0 40px" }}
      >
        <div
          style={{
            opacity,
            transform: `scale(${scale})`,
            backgroundColor: "rgba(0,0,0,0.72)",
            borderRadius: 16,
            borderLeft: "10px solid #FFE500",
            boxShadow: "0 0 40px rgba(0,0,0,0.8), inset 0 0 60px rgba(255,229,0,0.04)",
            paddingTop: 44,
            paddingBottom: 44,
            paddingLeft: 44,
            paddingRight: 44,
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
          }}
        >
          {/* アクセントバー（上） */}
          <div
            style={{
              width: "100%",
              height: 4,
              background: "linear-gradient(to right, #FFE500, transparent)",
              marginBottom: 28,
            }}
          />
          {/* 日本語メインテキスト */}
          <p
            style={{
              fontSize: 66,
              color: "#FFE500",
              fontWeight: "bold",
              textShadow: [
                "-3px -3px 0 #000",
                " 3px -3px 0 #000",
                "-3px  3px 0 #000",
                " 3px  3px 0 #000",
                "0 0 24px rgba(255,229,0,0.5)",
              ].join(","),
              textAlign: "left",
              lineHeight: 1.4,
              margin: 0,
              letterSpacing: "0.02em",
            }}
          >
            {text}
          </p>
          {/* 英語サブテキスト */}
          <p
            style={{
              fontSize: 34,
              color: "rgba(255,255,255,0.85)",
              fontWeight: "bold",
              textShadow: "0 2px 8px rgba(0,0,0,0.9)",
              textAlign: "left",
              lineHeight: 1.4,
              margin: "16px 0 0",
              letterSpacing: "0.01em",
            }}
          >
            {text_en}
          </p>
          {/* アクセントバー（下） */}
          <div
            style={{
              width: "100%",
              height: 4,
              background: "linear-gradient(to right, #FFE500, transparent)",
              marginTop: 28,
            }}
          />
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
