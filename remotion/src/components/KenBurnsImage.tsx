/**
 * 7.1 KenBurnsImage — 静止画にゆっくりズーム/パンエフェクト（ケンバーンズ）
 */
import React from "react";
import { AbsoluteFill, Img, useCurrentFrame, interpolate } from "remotion";

interface KenBurnsImageProps {
  src: string;
  alt?: string;
  durationFrames?: number;
  /** ズーム開始倍率 (default: 1.0) */
  zoomFrom?: number;
  /** ズーム終了倍率 (default: 1.1) */
  zoomTo?: number;
}

export const KenBurnsImage: React.FC<KenBurnsImageProps> = ({
  src,
  alt,
  durationFrames = 300,
  zoomFrom = 1.0,
  zoomTo = 1.1,
}) => {
  const frame = useCurrentFrame();

  const scale = interpolate(frame, [0, durationFrames], [zoomFrom, zoomTo], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const translateX = interpolate(frame, [0, durationFrames], [0, -2], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      <Img
        src={src}
        alt={alt}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          transform: `scale(${scale}) translateX(${translateX}%)`,
          transformOrigin: "center center",
        }}
      />
    </AbsoluteFill>
  );
};
