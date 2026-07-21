import { describe, test, expect } from "vitest";

import {
  TASKS,
  coerceParamValue,
  isParamVisible,
  applyTranslateSourceLang,
  buildJobResources,
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

  test("chat is registered, text-only, with a required prompt", () => {
    const chat = TASKS.find((t) => t.id === "chat");
    expect(chat).toBeDefined();
    expect(chat.promptRequired).toBe(true);
    expect(chat.defaultPrompt).toBeTruthy();
    // Preliminary support is text-only (no image extensions yet).
    const exts = chat.inputExtOptions.map((o) => o.value);
    expect(exts).toContain(".txt");
    expect(exts).not.toContain(".jpg");
    // temperature is numeric so it coerces to a real number at submit.
    const temp = chat.params.find((p) => p.name === "temperature");
    expect(temp.valueType).toBe("number");
    // max_image_pixels is deferred with image inputs.
    expect(chat.params.map((p) => p.name)).not.toContain("max_image_pixels");
    // The prompt help explains the {text} placeholder.
    expect(chat.promptHelp).toMatch(/\{text\}/);
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

  test("dtype applies to both image and video (not video-only)", () => {
    const dtype = detect.params.find((p) => p.name === "dtype");
    expect(dtype.videoOnly).toBeUndefined();
    expect(isParamVisible(dtype, { inputExt: ".jpg" })).toBe(true);
    expect(isParamVisible(dtype, { inputExt: ".mp4" })).toBe(true);
  });
});

describe("isParamVisible — showWhen.modelType", () => {
  // detect's `labels` is zero-shot only. A stale value must not leak through
  // any call site when the model type no longer matches.
  const labels = detect.params.find((p) => p.name === "labels");

  test("model-type-gated params show only for the matching model type", () => {
    expect(
      isParamVisible(labels, { modelType: "zero-shot-object-detection" })
    ).toBe(true);
    expect(isParamVisible(labels, { modelType: "object-detection" })).toBe(
      false
    );
    // No model type known yet -> hidden (can't confirm the match).
    expect(isParamVisible(labels, {})).toBe(false);
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

describe("buildJobResources", () => {
  const cpuTier = { name: "CPU Only", gpu_count: 0, cpu_cores: 2, memory_gb: 4 };
  const gpuTier = { name: "GPU", gpu_count: 2, cpu_cores: 6, memory_gb: 32 };

  test("CPU-only tier sends an explicit gpus: 0 (not omitted)", () => {
    // Omitting gpus lets the backend default (1 GPU) apply, so a CPU job would
    // still request a GPU. gpu_count 0 must be sent through.
    const res = buildJobResources(cpuTier);
    expect(res.gpus).toBe(0);
    expect(res.cpus).toBe(2);
    expect(res.mem).toBe(4);
  });

  test("GPU tier maps gpu_count to gpus and memory_gb to mem (int GB)", () => {
    const res = buildJobResources(gpuTier);
    expect(res.gpus).toBe(2);
    expect(res.mem).toBe(32); // key is `mem`, an int, not `memory: \"32GB\"`
    expect(res).not.toHaveProperty("memory");
  });

  test("account and worker timeout are included when provided", () => {
    const res = buildJobResources(gpuTier, {
      account: "cses",
      workerTimeout: "02:00",
    });
    expect(res.account).toBe("cses");
    expect(res.time).toBe("02:00:00");
  });

  test("account and time are omitted when absent", () => {
    const res = buildJobResources(gpuTier);
    expect(res).not.toHaveProperty("account");
    expect(res).not.toHaveProperty("time");
  });

  test("an undefined tier yields an empty resources object", () => {
    expect(buildJobResources(undefined)).toEqual({});
  });
});
