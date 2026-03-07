/**
 * 7.4 NasaSpinoffVideo — メインコンポジション
 *
 * render_props.json から VideoCompositionProps を受け取り、
 * hook → scenes → outro の順で各シーンコンポーネントをシーケンス表示する。
 */
import React from "react";
import { AbsoluteFill, Sequence, Audio, useVideoConfig, staticFile } from "remotion";
import { VideoCompositionProps } from "./types";
import { calcSceneFrames, getAssetForScene, getAudioForScene } from "./utils";
import { HookScene } from "./components/HookScene";
import { ContentScene } from "./components/ContentScene";
import { OutroScene } from "./components/OutroScene";

export const NasaSpinoffVideo: React.FC<VideoCompositionProps> = ({
  script,
  audioManifest,
  assetsManifest,
  lang,
}) => {
  const { fps } = useVideoConfig();

  const frames = calcSceneFrames(script, fps);

  const hookAsset = getAssetForScene(assetsManifest, "hook");
  const hookAudio = getAudioForScene(audioManifest, "hook", lang);
  const outroAsset = getAssetForScene(assetsManifest, "outro");
  const outroAudio = getAudioForScene(audioManifest, "outro", lang);

  return (
    <AbsoluteFill style={{ backgroundColor: "black" }}>
      {/* Hook シーン */}
      <Sequence
        from={frames.hook.start}
        durationInFrames={frames.hook.durationFrames}
      >
        <HookScene
          text={script.hook}
          text_en={script.hook_en}
          lang={lang}
          asset={hookAsset}
          startFrame={frames.hook.start}
          durationFrames={frames.hook.durationFrames}
        />
        {hookAudio && <Audio src={staticFile(hookAudio)} />}
      </Sequence>

      {/* Content シーン群 */}
      {script.scenes.map((scene, i) => {
        const sceneFrames = frames.scenes[i];
        if (!sceneFrames) return null;

        const sceneId = String(scene.id);
        const asset = getAssetForScene(assetsManifest, sceneId);
        const audio = getAudioForScene(audioManifest, sceneId, lang);

        return (
          <Sequence
            key={scene.id}
            from={sceneFrames.start}
            durationInFrames={sceneFrames.durationFrames}
          >
            <ContentScene
              scene={scene}
              lang={lang}
              asset={asset}
              startFrame={sceneFrames.start}
              durationFrames={sceneFrames.durationFrames}
            />
            {audio && <Audio src={staticFile(audio)} />}
          </Sequence>
        );
      })}

      {/* Outro シーン */}
      <Sequence
        from={frames.outro.start}
        durationInFrames={frames.outro.durationFrames}
      >
        <OutroScene
          text={script.outro}
          text_en={script.outro_en}
          lang={lang}
          startFrame={frames.outro.start}
          durationFrames={frames.outro.durationFrames}
        />
        {outroAudio && <Audio src={staticFile(outroAudio)} />}
      </Sequence>
    </AbsoluteFill>
  );
};
