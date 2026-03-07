/**
 * 7.3 OutroScene — アウトロシーン（チャンネル登録 CTA 表示）
 */
import React from "react";
import { AbsoluteFill, useCurrentFrame, interpolate } from "remotion";
import { StarField } from "./StarField";

interface OutroSceneProps {
  text: string;
  text_en: string;
  lang: "ja" | "en";
  startFrame: number;
  durationFrames: number;
}

export const OutroScene: React.FC<OutroSceneProps> = ({
  text,
  text_en,
  lang,
}) => {
  const frame = useCurrentFrame();
  const displayText = lang === "ja" ? text : text_en;

  const opacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill>
      <StarField />

      {/* CTA テキスト */}
      <AbsoluteFill
        style={{ justifyContent: "center", alignItems: "center", padding: 48 }}
      >
        <div
          style={{
            opacity,
            textAlign: "center",
          }}
        >
          {/* メッセージ */}
          <p
            style={{
              fontSize: 56,
              color: "white",
              fontWeight: "bold",
              textShadow: "0 4px 16px rgba(0,0,0,0.9)",
              margin: 0,
              lineHeight: 1.4,
            }}
          >
            {displayText}
          </p>

          {/* チャンネル登録ボタン風 CTA */}
          <div
            style={{
              marginTop: 40,
              backgroundColor: "#ff0000",
              borderRadius: 8,
              paddingTop: 16,
              paddingBottom: 16,
              paddingLeft: 32,
              paddingRight: 32,
              display: "inline-block",
            }}
          >
            <p
              style={{
                fontSize: 40,
                color: "white",
                fontWeight: "bold",
                margin: 0,
              }}
            >
              {lang === "ja" ? "チャンネル登録" : "Subscribe"}
            </p>
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
