/**
 * 7.1 StarField — 黒背景＋星パーティクルアニメーション（fallback 背景）
 */
import React, { useMemo } from "react";
import { AbsoluteFill, useCurrentFrame, interpolate } from "remotion";

interface StarFieldProps {
  starCount?: number;
}

interface Star {
  x: number;
  y: number;
  size: number;
  speed: number;
  seed: number;
}

export const StarField: React.FC<StarFieldProps> = ({ starCount = 80 }) => {
  const frame = useCurrentFrame();

  const stars = useMemo<Star[]>(() => {
    const arr: Star[] = [];
    for (let i = 0; i < starCount; i++) {
      // 決定論的な疑似乱数（シードベース）
      const seed = (i * 9301 + 49297) % 233280;
      arr.push({
        x: (seed / 233280) * 100,
        y: ((seed * 7 + 13) % 233280) / 233280 * 100,
        size: 1 + ((seed * 3) % 3),
        speed: 0.02 + ((seed % 10) / 100),
        seed,
      });
    }
    return arr;
  }, [starCount]);

  return (
    <AbsoluteFill
      style={{ backgroundColor: "#000010", overflow: "hidden" }}
    >
      {stars.map((star, i) => {
        const opacity = interpolate(
          (frame * star.speed + star.seed) % 60,
          [0, 30, 60],
          [0.4, 1, 0.4],
          { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
        );
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: `${star.x}%`,
              top: `${star.y}%`,
              width: star.size,
              height: star.size,
              borderRadius: "50%",
              backgroundColor: "white",
              opacity,
            }}
          />
        );
      })}
    </AbsoluteFill>
  );
};
