import { describe, test, expect } from "vitest";

import {
  defaultPreviewSide,
  resolvePreviewSide,
  isDetectionResult,
} from "./ResultPreview";

describe("defaultPreviewSide", () => {
  test("defaults to output when output exists (success)", () => {
    expect(defaultPreviewSide(true)).toBe("output");
  });

  test("defaults to input when there is no output (failure)", () => {
    expect(defaultPreviewSide(false)).toBe("input");
  });
});

describe("resolvePreviewSide", () => {
  test("keeps the chosen side when it is available", () => {
    expect(resolvePreviewSide("input", true)).toBe("input");
    expect(resolvePreviewSide("output", true)).toBe("output");
    expect(resolvePreviewSide("input", false)).toBe("input");
  });

  test("falls back to input when output is chosen but unavailable", () => {
    expect(resolvePreviewSide("output", false)).toBe("input");
  });
});

describe("isDetectionResult", () => {
  test("is true for an image input with a JSON output", () => {
    expect(isDetectionResult("photo.jpg", "photo.json")).toBe(true);
    expect(isDetectionResult("PHOTO.PNG", "OUT.JSON")).toBe(true);
  });

  test("is false when the input is not an image", () => {
    expect(isDetectionResult("clip.mp4", "clip.json")).toBe(false);
    expect(isDetectionResult("notes.txt", "notes.json")).toBe(false);
  });

  test("is false when the output is not JSON", () => {
    expect(isDetectionResult("photo.jpg", "photo.txt")).toBe(false);
    expect(isDetectionResult("photo.jpg", null)).toBe(false);
    expect(isDetectionResult("photo.jpg", undefined)).toBe(false);
  });
});
