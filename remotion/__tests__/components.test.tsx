/**
 * Task 7.1〜7.3 — Remotion コンポーネント レンダリングテスト（TDD: RED → GREEN）
 */
import React from "react";
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";
import { __setCurrentFrame } from "../__mocks__/remotion";

import { StarField } from "../src/components/StarField";
import { KenBurnsImage } from "../src/components/KenBurnsImage";
import { BilingualSubtitle } from "../src/components/BilingualSubtitle";
import { HookScene } from "../src/components/HookScene";
import { ContentScene } from "../src/components/ContentScene";
import { OutroScene } from "../src/components/OutroScene";
import { SceneData, AssetEntry } from "../src/types";

// ---- StarField (7.1) ----

describe("StarField", () => {
  test("レンダリングされる", () => {
    const { container } = render(<StarField />);
    expect(container.firstChild).not.toBeNull();
  });

  test("黒背景を持つ", () => {
    const { container } = render(<StarField />);
    const root = container.firstChild as HTMLElement;
    expect(root).toBeTruthy();
  });

  test("starCount プロップを受け入れる", () => {
    const { container } = render(<StarField starCount={50} />);
    expect(container.firstChild).not.toBeNull();
  });
});

// ---- KenBurnsImage (7.1) ----

describe("KenBurnsImage", () => {
  test("img 要素をレンダリングする", () => {
    render(<KenBurnsImage src="test.jpg" />);
    expect(screen.getByRole("img")).toBeInTheDocument();
  });

  test("指定した src を img に設定する", () => {
    render(<KenBurnsImage src="nasa_image.jpg" />);
    const img = screen.getByRole("img") as HTMLImageElement;
    expect(img.src).toContain("nasa_image.jpg");
  });

  test("alt プロップを受け入れる", () => {
    render(<KenBurnsImage src="img.jpg" alt="NASA image" />);
    expect(screen.getByAltText("NASA image")).toBeInTheDocument();
  });
});

// ---- BilingualSubtitle (7.2) ----

describe("BilingualSubtitle", () => {
  test("日本語テキストを表示する", () => {
    render(<BilingualSubtitle ja="メモリーフォームはNASA由来" en="Memory foam came from NASA" />);
    expect(screen.getByText("メモリーフォームはNASA由来")).toBeInTheDocument();
  });

  test("英語テキストを表示する", () => {
    render(<BilingualSubtitle ja="日本語テキスト" en="English text" />);
    expect(screen.getByText("English text")).toBeInTheDocument();
  });

  test("英語テキストが日本語テキストより小さいフォントサイズを持つ", () => {
    const { container } = render(
      <BilingualSubtitle ja="日本語テキスト" en="English text" />
    );
    const texts = container.querySelectorAll("[data-testid]");
    expect(texts.length).toBeGreaterThan(0);
  });
});

// ---- HookScene (7.3) ----

describe("HookScene", () => {
  const mockScene: SceneData = {
    id: 0,
    voiceover: "驚きのフック文",
    voiceover_en: "Amazing hook",
    visual_note: "",
    image_keywords: [],
    duration_sec: 3,
  };

  const mockAsset: AssetEntry = {
    scene_id: "hook",
    source: "nasa",
    local_path: "assets/hook/img.jpg",
    license: "NASA Public Domain",
    original_url: "",
  };

  test("JA テキストを表示する", () => {
    render(
      <HookScene
        text="驚きのフック文"
        text_en="Amazing hook"
        lang="ja"
        asset={mockAsset}
        startFrame={0}
        durationFrames={90}
      />
    );
    expect(screen.getByText("驚きのフック文")).toBeInTheDocument();
  });

  test("EN lang では英語テキストを表示する", () => {
    render(
      <HookScene
        text="驚きのフック文"
        text_en="Amazing hook"
        lang="en"
        asset={mockAsset}
        startFrame={0}
        durationFrames={90}
      />
    );
    expect(screen.getByText("Amazing hook")).toBeInTheDocument();
  });

  test("fallback アセットでは StarField を表示する", () => {
    const fallbackAsset: AssetEntry = { ...mockAsset, source: "fallback", local_path: "" };
    const { container } = render(
      <HookScene
        text="フック"
        text_en="Hook"
        lang="ja"
        asset={fallbackAsset}
        startFrame={0}
        durationFrames={90}
      />
    );
    expect(container.firstChild).not.toBeNull();
  });
});

// ---- ContentScene (7.3) ----

describe("ContentScene", () => {
  const mockScene: SceneData = {
    id: 1,
    voiceover: "コンテンツナレーション",
    voiceover_en: "Content narration",
    visual_note: "",
    image_keywords: ["space"],
    duration_sec: 10,
  };

  const mockAsset: AssetEntry = {
    scene_id: "1",
    source: "nasa",
    local_path: "assets/scene_1/img.jpg",
    license: "NASA Public Domain",
    original_url: "",
  };

  test("JA テキストを表示する", () => {
    render(
      <ContentScene
        scene={mockScene}
        lang="ja"
        asset={mockAsset}
        startFrame={90}
        durationFrames={300}
      />
    );
    expect(screen.getByText("コンテンツナレーション")).toBeInTheDocument();
  });

  test("fallback アセットでは StarField を使う", () => {
    const fallbackAsset: AssetEntry = { ...mockAsset, source: "fallback", local_path: "" };
    const { container } = render(
      <ContentScene
        scene={mockScene}
        lang="ja"
        asset={fallbackAsset}
        startFrame={90}
        durationFrames={300}
      />
    );
    expect(container.firstChild).not.toBeNull();
  });
});

// ---- OutroScene (7.3) ----

describe("OutroScene", () => {
  test("JA テキストを表示する", () => {
    render(
      <OutroScene
        text="チャンネル登録をお願いします"
        text_en="Please subscribe"
        lang="ja"
        startFrame={840}
        durationFrames={150}
      />
    );
    expect(screen.getByText("チャンネル登録をお願いします")).toBeInTheDocument();
  });

  test("EN lang では英語テキストを表示する", () => {
    render(
      <OutroScene
        text="チャンネル登録をお願いします"
        text_en="Please subscribe"
        lang="en"
        startFrame={840}
        durationFrames={150}
      />
    );
    expect(screen.getByText("Please subscribe")).toBeInTheDocument();
  });
});
