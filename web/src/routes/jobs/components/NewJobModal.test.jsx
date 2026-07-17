import { describe, test, expect } from "vitest";

import {
  TASKS,
  coerceParamValue,
  isParamVisible,
  applyTranslateSourceLang,
} from "./NewJobModal";

const detect = TASKS.find((t) => t.id === "detect");
const translate = TASKS.find((t) => t.id === "translate");
const transcribe = TASKS.find((t) => t.id === "transcribe");

describe("coerceParamValue", () => {
  test("coerces number-typed params to real numbers", () => {
    // Form inputs are strings; tigerflow consumes these raw (e.g. batch_size > 1),
    // so a string would crash the task. They must arrive as JSON numbers.
    expect(coerceParamValue(detect, "batch_size", "4")).toBe(4);
    expect(coerceParamValue(detect, "threshold", "0.3")).toBe(0.3);
    expect(typeof coerceParamValue(detect, "batch_size", "4")).toBe("number");
  });

  test("coerces boolean-typed params to real booleans", () => {
    // Checkboxes store real booleans; legacy string values still coerce.
    expect(coerceParamValue(detect, "compile", true)).toBe(true);
    expect(coerceParamValue(detect, "compile", false)).toBe(false);
    expect(coerceParamValue(detect, "compile", "true")).toBe(true);
    expect(coerceParamValue(transcribe, "raw", "false")).toBe(false);
  });

  test("passes string params through unchanged", () => {
    expect(coerceParamValue(detect, "dtype", "float16")).toBe("float16");
    expect(coerceParamValue(detect, "labels", "cat,dog")).toBe("cat,dog");
  });

  test("returns an unparseable number value unchanged", () => {
    expect(coerceParamValue(detect, "batch_size", "abc")).toBe("abc");
  });

  test("returns the raw value for an unknown param", () => {
    expect(coerceParamValue(detect, "not_a_param", "x")).toBe("x");
  });
});

describe("TASKS param definitions", () => {
  test("every task exposes a params array", () => {
    for (const task of TASKS) {
      expect(Array.isArray(task.params)).toBe(true);
    }
  });

  test("boolean params are checkboxes with a boolean valueType", () => {
    // Guard against re-introducing the string-typed bug: any conceptual boolean
    // must be a checkbox carrying valueType "boolean" so it is coerced.
    const booleans = new Set(["compile", "raw", "use_fallback_prompt"]);
    for (const task of TASKS) {
      for (const param of task.params) {
        if (booleans.has(param.name)) {
          expect(param.type).toBe("checkbox");
          expect(param.valueType).toBe("boolean");
        }
      }
    }
  });

  test("ocr marks its prompt as required (no server-side default)", () => {
    const ocr = TASKS.find((t) => t.id === "ocr");
    expect(ocr.promptRequired).toBe(true);
    expect(ocr.defaultPrompt).toBeTruthy();
  });

  test("translate target language defaults to English", () => {
    // Without an explicit default the renderer falls back to options[0]
    // (Afrikaans), which is a poor default; the image default is "en".
    const targetLang = translate.params.find((p) => p.name === "target_lang");
    expect(targetLang.default).toBe("en");
  });
});

describe("isParamVisible — videoOnly", () => {
  const videoParam = detect.params.find((p) => p.name === "batch_size");
  const imageParam = detect.params.find((p) => p.name === "threshold");

  test("video-only params are hidden for image inputs", () => {
    expect(isParamVisible(videoParam, { inputExt: ".jpg" })).toBe(false);
    expect(isParamVisible(videoParam, { inputExt: ".png" })).toBe(false);
  });

  test("video-only params are shown for video inputs", () => {
    expect(isParamVisible(videoParam, { inputExt: ".mp4" })).toBe(true);
    expect(isParamVisible(videoParam, { inputExt: ".mov" })).toBe(true);
  });

  test("non-video params are always visible", () => {
    expect(isParamVisible(imageParam, { inputExt: ".jpg" })).toBe(true);
    expect(isParamVisible(imageParam, { inputExt: ".mp4" })).toBe(true);
  });

  test("detect's video-only params are flagged", () => {
    for (const name of ["batch_size", "sample_fps", "compile"]) {
      const p = detect.params.find((x) => x.name === name);
      expect(p.videoOnly).toBe(true);
    }
  });
});

describe("isParamVisible — showWhenParam", () => {
  const batchSize = transcribe.params.find((p) => p.name === "batch_size");
  const raw = transcribe.params.find((p) => p.name === "raw");

  test("transcribe batch_size shows only for the batched strategy", () => {
    // Default (windowing unset) falls back to the gate's default "batched".
    expect(isParamVisible(batchSize, { taskParams: {} })).toBe(true);
    expect(
      isParamVisible(batchSize, { taskParams: { windowing: "batched" } })
    ).toBe(true);
    expect(
      isParamVisible(batchSize, { taskParams: { windowing: "native" } })
    ).toBe(false);
  });

  test("transcribe raw shows only for JSON output", () => {
    expect(isParamVisible(raw, { taskParams: { output_format: "json" } })).toBe(
      true
    );
    // Default output_format is "text", so raw is hidden by default.
    expect(isParamVisible(raw, { taskParams: {} })).toBe(false);
    expect(isParamVisible(raw, { taskParams: { output_format: "text" } })).toBe(
      false
    );
  });

  test("prompt params show for chat/auto backends, not tgemma", () => {
    // Both prompt_template and use_fallback_prompt are unused for tgemma models.
    for (const name of ["prompt_template", "use_fallback_prompt"]) {
      const p = translate.params.find((x) => x.name === name);
      expect(isParamVisible(p, { taskParams: {} })).toBe(true); // default "auto"
      expect(
        isParamVisible(p, { taskParams: { model_backend: "chat" } })
      ).toBe(true);
      expect(
        isParamVisible(p, { taskParams: { model_backend: "tgemma" } })
      ).toBe(false);
    }
  });
});

describe("applyTranslateSourceLang", () => {
  test("'auto' becomes auto_lang_detect=true with no source_lang", () => {
    const params = { source_lang: "auto", target_lang: "de" };
    applyTranslateSourceLang(params);
    expect(params.source_lang).toBeUndefined();
    expect(params.auto_lang_detect).toBe(true);
  });

  test("an explicit language sets auto_lang_detect=false and keeps source_lang", () => {
    const params = { source_lang: "fr", target_lang: "en" };
    applyTranslateSourceLang(params);
    expect(params.source_lang).toBe("fr");
    expect(params.auto_lang_detect).toBe(false);
  });

  test("the source_lang dropdown is the only auto-detect control", () => {
    // The redundant auto_lang_detect checkbox was removed; the dropdown drives it.
    const names = translate.params.map((p) => p.name);
    expect(names).toContain("source_lang");
    expect(names).not.toContain("auto_lang_detect");
  });

  test("translate uses prompt_template, not a generic prompt field", () => {
    // The translate task has no `prompt` param; a defaultPrompt would render a
    // spurious "Prompt" field. prompt_template is the real control.
    expect(translate.defaultPrompt).toBeNull();
    expect(translate.params.map((p) => p.name)).toContain("prompt_template");
  });
});
