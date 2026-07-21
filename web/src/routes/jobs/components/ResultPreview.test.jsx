import { describe, test, expect } from "vitest";

import { defaultPreviewSide, resolvePreviewSide } from "./ResultPreview";

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
