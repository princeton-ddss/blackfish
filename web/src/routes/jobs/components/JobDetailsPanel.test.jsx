import { describe, test, expect } from "vitest";

import { formatParamLabel, formatParamValue } from "./JobDetailsPanel";

describe("formatParamLabel", () => {
  test("uses friendly labels for known params", () => {
    expect(formatParamLabel("overlap_s")).toBe("Window overlap (s)");
    expect(formatParamLabel("batch_size")).toBe("Batch size");
    expect(formatParamLabel("sample_fps")).toBe("Sample FPS");
    expect(formatParamLabel("target_lang")).toBe("Target language");
  });

  test("title-cases unknown snake_case keys", () => {
    expect(formatParamLabel("windowing")).toBe("Windowing");
    expect(formatParamLabel("some_new_param")).toBe("Some new param");
  });
});

describe("formatParamValue", () => {
  test("renders booleans as Yes/No", () => {
    expect(formatParamValue("raw", true)).toBe("Yes");
    expect(formatParamValue("raw", false)).toBe("No");
  });

  test("renders an empty transcribe language as Auto-detect", () => {
    expect(formatParamValue("language", "")).toBe("Auto-detect");
  });

  test("stringifies other values", () => {
    expect(formatParamValue("batch_size", 16)).toBe("16");
    expect(formatParamValue("windowing", "batched")).toBe("batched");
  });
});
