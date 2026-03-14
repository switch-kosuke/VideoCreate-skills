/**
 * 7.1 KenBurnsImage — 静止画にゆっくりズーム/パンエフェクト（ケンバーンズ）
 * srcのハッシュ値でパン方向をランダム化し、シーンごとに動きが変わる
 */
import React, { useMemo } from "react";
import { AbsoluteFill, Img, useCurrentFrame, interpolate, staticFile } from "remotion";

interface KenBurnsImageProps {
  src: string;
  alt?: string;
  durationFrames?: number;
  /** ズーム開始倍率 (default: 1.0) */
  zoomFrom?: number;
  /** ズーム終了倍率 (default: 1.1) */
  zoomTo?: number;
}

/** srcの文字列から決定論的なハッシュ値を生成 */
function hashString(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) {
    h = (Math.imul(31, h) + s.charCodeAt(i)) | 0;
  }
  return Math.abs(h);
}

export const KenBurnsImage: React.FC<KenBurnsImageProps> = ({
  src,
  alt,
  durationFrames = 300,
  zoomFrom = 1.0,
  zoomTo = 1.1,
}) => {
  const frame = useCurrentFrame();

  // srcハッシュでパン方向を決定（4パターン）
  const { txFrom, txTo, tyFrom, tyTo } = useMemo(() => {
    const h = hashString(src);
    const pattern = h % 4;
    switch (pattern) {
      case 0: return { txFrom: 0,  txTo: -3, tyFrom: 0,  tyTo: -2 }; // 左上へ
      case 1: return { txFrom: -3, txTo: 0,  tyFrom: 0,  tyTo: -2 }; // 右上へ
      case 2: return { txFrom: 0,  txTo: -3, tyFrom: -2, tyTo: 0  }; // 左下へ
      case 3: return { txFrom: -3, txTo: 0,  tyFrom: -2, tyTo: 0  }; // 右下へ
      default: return { txFrom: 0, txTo: -3, tyFrom: 0,  tyTo: -2 };
    }
  }, [src]);

  const scale = interpolate(frame, [0, durationFrames], [zoomFrom, zoomTo], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const translateX = interpolate(frame, [0, durationFrames], [txFrom, txTo], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const translateY = interpolate(frame, [0, durationFrames], [tyFrom, tyTo], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      <Img
        src={staticFile(src)}
        alt={alt}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          transform: `scale(${scale}) translateX(${translateX}%) translateY(${translateY}%)`,
          transformOrigin: "center center",
        }}
      />
    </AbsoluteFill>
  );
};
