import { describe, test, expect } from "vitest";

import { formatParamLabel, formatParamValue, terminalReason } from "./JobDetailsPanel";

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

describe("terminalReason", () => {
  test("returns null for non-terminal and unhandled statuses", () => {
    expect(terminalReason(null)).toBeNull();
    expect(terminalReason({ status: "running" })).toBeNull();
    expect(terminalReason({ status: "stopped" })).toBeNull();
    expect(terminalReason({ status: "broken" })).toBeNull();
  });

  test("explains EXHAUSTED with budget and remaining count", () => {
    const r = terminalReason({
      status: "exhausted",
      finished: 48,
      staged: 12,
      errored: 0,
      max_restarts: 20,
      processed_highwater: 48,
    });
    expect(r.headline).toBe("Exhausted restart budget");
    expect(r.detail).toContain("all 20 restarts");
    expect(r.detail).toContain("12 files still unprocessed");
  });

  test("avoids the '0 files unprocessed' non-sequitur for EXHAUSTED", () => {
    const r = terminalReason({
      status: "exhausted",
      finished: 60,
      staged: 0,
      errored: 0,
      max_restarts: 20,
      processed_highwater: 60,
    });
    expect(r.detail).toContain("all 20 restarts");
    expect(r.detail).not.toContain("0 files");
    expect(r.detail).toContain("before finishing");
  });

  test("singularizes a single remaining file", () => {
    const r = terminalReason({
      status: "exhausted",
      finished: 59,
      staged: 1,
      errored: 0,
      max_restarts: 20,
      processed_highwater: 59,
    });
    expect(r.detail).toContain("1 file still unprocessed");
    expect(r.detail).not.toContain("1 files");
  });

  test("explains STALLED with restart count and high-water mark", () => {
    const r = terminalReason({
      status: "stalled",
      finished: 41,
      staged: 3,
      errored: 0,
      stalled_restarts: 1,
      processed_highwater: 41,
    });
    expect(r.headline).toBe("No forward progress");
    expect(r.detail).toContain("across 1 restart");
    expect(r.detail).toContain("stopped at 41/44");
    expect(r.detail).toContain("failing repeatedly");
  });

  test("omits the total when staged is unknown (between allocations)", () => {
    const r = terminalReason({
      status: "stalled",
      finished: 41,
      staged: null,
      errored: 0,
      stalled_restarts: 2,
      processed_highwater: 41,
    });
    expect(r.detail).toContain("across 2 restarts");
    expect(r.detail).not.toContain("stopped at");
  });
});
