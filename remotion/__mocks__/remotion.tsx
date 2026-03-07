/**
 * Remotion モック（Jest テスト用）
 * useCurrentFrame, useVideoConfig など Remotion フックをスタブ化する
 */
import React from "react";

// フレーム制御
let _currentFrame = 0;
export const __setCurrentFrame = (frame: number) => { _currentFrame = frame; };
export const useCurrentFrame = () => _currentFrame;

// ビデオ設定
export const useVideoConfig = () => ({
  fps: 30,
  durationInFrames: 1800,
  width: 1080,
  height: 1920,
  id: "NasaSpinoffVideo",
});

// interpolate: 線形補間（実装をそのまま）
export const interpolate = (
  frame: number,
  inputRange: [number, number],
  outputRange: [number, number],
  options?: { extrapolateLeft?: string; extrapolateRight?: string }
) => {
  const [inMin, inMax] = inputRange;
  const [outMin, outMax] = outputRange;
  const clamped = Math.min(Math.max(frame, inMin), inMax);
  return outMin + ((clamped - inMin) / (inMax - inMin)) * (outMax - outMin);
};

// spring: ダミー（常に 1 を返す）
export const spring = () => 1;

// Easing: ダミー
export const Easing = {
  ease: (t: number) => t,
  linear: (t: number) => t,
  easeInOut: (t: number) => t,
};

// Sequence
export const Sequence: React.FC<{
  from?: number;
  durationInFrames?: number;
  children: React.ReactNode;
}> = ({ children }) => <>{children}</>;

// AbsoluteFill
export const AbsoluteFill: React.FC<{
  style?: React.CSSProperties;
  children?: React.ReactNode;
}> = ({ style, children }) => (
  <div style={{ position: "absolute", inset: 0, ...style }}>{children}</div>
);

// Audio
export const Audio: React.FC<{ src: string }> = () => null;

// Img
export const Img: React.FC<{
  src: string;
  style?: React.CSSProperties;
  alt?: string;
}> = ({ src, style, alt }) => <img src={src} style={style} alt={alt ?? ""} />;

// Composition (for Root.tsx — not used in tests but avoids import errors)
export const Composition: React.FC<Record<string, unknown>> = () => null;

// staticFile: ファイルパスをそのまま返す
export const staticFile = (path: string) => path;
