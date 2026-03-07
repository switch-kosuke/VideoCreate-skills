/**
 * 7.2 BilingualSubtitle — 日本語（大）＋英語（70%サイズ）の字幕を画面下部に表示
 * フェードインアニメーション付き
 */
import React from "react";
import { AbsoluteFill, useCurrentFrame, interpolate } from "remotion";

interface BilingualSubtitleProps {
  ja: string;
  en: string;
  /** 日本語フォントサイズ (px, default: 52) */
  jaFontSize?: number;
}

export const BilingualSubtitle: React.FC<BilingualSubtitleProps> = ({
  ja,
  en,
  jaFontSize = 52,
}) => {
  const frame = useCurrentFrame();
  const enFontSize = jaFontSize * 0.7;

  const opacity = interpolate(frame, [0, 10], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const translateY = interpolate(frame, [0, 10], [20, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        justifyContent: "flex-end",
        alignItems: "center",
        paddingBottom: 280,
      }}
    >
      <div
        style={{
          opacity,
          transform: `translateY(${translateY}px)`,
          textAlign: "center",
          paddingLeft: 32,
          paddingRight: 32,
        }}
      >
        {/* 日本語テキスト */}
        <p
          data-testid="subtitle-ja"
          style={{
            fontSize: jaFontSize,
            color: "white",
            fontWeight: "bold",
            textShadow: "0 2px 8px rgba(0,0,0,0.9)",
            margin: 0,
            lineHeight: 1.4,
          }}
        >
          {ja}
        </p>
        {/* 英語テキスト */}
        <p
          data-testid="subtitle-en"
          style={{
            fontSize: enFontSize,
            color: "#e0e0e0",
            textShadow: "0 2px 6px rgba(0,0,0,0.8)",
            margin: 0,
            marginTop: 8,
            lineHeight: 1.4,
          }}
        >
          {en}
        </p>
      </div>
    </AbsoluteFill>
  );
};
