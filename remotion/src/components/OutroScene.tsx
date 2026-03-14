/**
 * 7.3 OutroScene — アウトロシーン（チャンネル登録 CTA + 誤タップアニメーション）
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

// 👆 指カーソルコンポーネント
const Finger: React.FC<{ x: number; y: number; pressing: boolean }> = ({ x, y, pressing }) => (
  <div
    style={{
      position: "absolute",
      left: x - 36,
      top: y - 16,
      fontSize: pressing ? 80 : 90,
      transform: `rotate(${pressing ? 10 : 0}deg) scale(${pressing ? 0.85 : 1})`,
      transition: "none",
      filter: "drop-shadow(0 4px 8px rgba(0,0,0,0.6))",
      pointerEvents: "none",
      zIndex: 100,
    }}
  >
    👆
  </div>
);

// ❤️ ハートポップアニメーション
const HeartPop: React.FC<{ x: number; y: number; progress: number }> = ({ x, y, progress }) => {
  if (progress <= 0) return null;
  const scale = interpolate(progress, [0, 0.3, 0.7, 1], [0, 1.6, 1.2, 0]);
  const offsetY = interpolate(progress, [0, 1], [0, -80]);
  const opacity = interpolate(progress, [0, 0.1, 0.7, 1], [0, 1, 1, 0]);
  return (
    <div
      style={{
        position: "absolute",
        left: x - 24,
        top: y - 40 + offsetY,
        fontSize: 48,
        opacity,
        transform: `scale(${scale})`,
        pointerEvents: "none",
        zIndex: 101,
      }}
    >
      ❤️
    </div>
  );
};

export const OutroScene: React.FC<OutroSceneProps> = ({ text, text_en, lang }) => {
  const frame = useCurrentFrame();
  const displayText = lang === "ja" ? text : text_en;

  // --- フェードイン ---
  const opacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // --- ボタン配置 (1080x1920 canvas 想定) ---
  const subscribeX = 540;
  const subscribeY = 1100;
  const likeX = 235;
  const likeY = 1100;

  // --- 指の軌跡 ---
  // Phase 1 (f30-60): 画面外から登録ボタンへ移動
  // Phase 2 (f60-70): 1回目タップ（登録ボタン）
  // Phase 3 (f80-105): 2回目タップへ向けて移動 → ずれていいねボタンへ
  // Phase 4 (f105-115): 2回目タップ（いいねボタン）

  const fingerX = interpolate(
    frame,
    [25, 60, 70, 80, 105, 115, 140],
    [820, subscribeX, subscribeX, subscribeX + 40, likeX + 20, likeX, likeX],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const fingerY = interpolate(
    frame,
    [25, 60, 63, 68, 80, 105, 108, 113, 140],
    [1500, subscribeY + 40, subscribeY - 10, subscribeY + 40, subscribeY - 60, likeY + 40, likeY - 10, likeY + 40, likeY + 40],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const fingerVisible = frame >= 25 && frame <= 145;

  // 1回目タップ中か
  const pressing1 = frame >= 61 && frame <= 67;
  // 2回目タップ中か
  const pressing2 = frame >= 106 && frame <= 112;

  // --- 登録ボタンのリアクション ---
  const subscribeScale = interpolate(
    frame,
    [60, 63, 68, 70],
    [1, 0.88, 1.05, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );
  // タップ後「登録済み✓」表示
  const subscribeDone = frame >= 65;

  // --- いいねボタンのリアクション ---
  const likeActivated = frame >= 108;
  const likeScale = interpolate(
    frame,
    [106, 109, 114, 117],
    [1, 0.85, 1.15, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // ❤️ ポップアップ
  const heartProgress = interpolate(
    frame,
    [108, 135],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // --- ボタン揺れ（誤タップ後の「あれ？」感） ---
  const likeWobble = likeActivated
    ? interpolate(frame, [117, 120, 123, 126, 128], [0, 6, -4, 2, 0], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      })
    : 0;

  return (
    <AbsoluteFill>
      <StarField />

      {/* CTA テキスト */}
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", padding: 48 }}>
        <div style={{ opacity, textAlign: "center" }}>
          <p
            style={{
              fontSize: 52,
              color: "white",
              fontWeight: "bold",
              textShadow: "0 4px 16px rgba(0,0,0,0.9)",
              margin: 0,
              lineHeight: 1.4,
            }}
          >
            {displayText}
          </p>

          {/* ボタン行 */}
          <div
            style={{
              marginTop: 48,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 24,
            }}
          >
            {/* 👍 いいねボタン */}
            <div
              style={{
                backgroundColor: likeActivated ? "#2563eb" : "rgba(255,255,255,0.15)",
                border: `3px solid ${likeActivated ? "#2563eb" : "rgba(255,255,255,0.4)"}`,
                borderRadius: 12,
                paddingTop: 14,
                paddingBottom: 14,
                paddingLeft: 24,
                paddingRight: 24,
                display: "flex",
                alignItems: "center",
                gap: 10,
                transform: `scale(${likeScale}) translateX(${likeWobble}px)`,
                transition: "background-color 0.1s",
              }}
            >
              <span style={{ fontSize: 36 }}>{likeActivated ? "👍" : "👍"}</span>
              <p style={{ fontSize: 34, color: "white", fontWeight: "bold", margin: 0 }}>
                {likeActivated ? (lang === "ja" ? "いいね！" : "Liked!") : (lang === "ja" ? "いいね" : "Like")}
              </p>
            </div>

            {/* 🔴 チャンネル登録ボタン */}
            <div
              style={{
                backgroundColor: subscribeDone ? "#666" : "#ff0000",
                borderRadius: 12,
                paddingTop: 16,
                paddingBottom: 16,
                paddingLeft: 32,
                paddingRight: 32,
                display: "flex",
                alignItems: "center",
                gap: 10,
                transform: `scale(${subscribeScale})`,
              }}
            >
              {subscribeDone && <span style={{ fontSize: 32 }}>✓</span>}
              <p style={{ fontSize: 36, color: "white", fontWeight: "bold", margin: 0 }}>
                {subscribeDone
                  ? (lang === "ja" ? "登録済み" : "Subscribed")
                  : (lang === "ja" ? "チャンネル登録" : "Subscribe")}
              </p>
            </div>
          </div>
        </div>
      </AbsoluteFill>

      {/* 👆 指カーソル */}
      {fingerVisible && (
        <Finger x={fingerX} y={fingerY} pressing={pressing1 || pressing2} />
      )}

      {/* ❤️ ハートポップ */}
      <HeartPop x={likeX} y={likeY - 120} progress={heartProgress} />
    </AbsoluteFill>
  );
};
