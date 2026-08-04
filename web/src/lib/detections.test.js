import { describe, it, expect } from "vitest";
import {
    parseDetections,
    buildLabelColorMap,
    formatDetectionLabel,
    summarizeLabels,
    filterDetections,
    DETECTION_COLORS,
} from "./detections";

const det = (label, score, box = { xmin: 0, ymin: 0, xmax: 10, ymax: 10 }) => ({
    label,
    score,
    box,
});

describe("parseDetections", () => {
    it("parses a valid detection array", () => {
        const text = JSON.stringify([det("dog", 0.98), det("cat", 0.87)]);
        const result = parseDetections(text);
        expect(result).toHaveLength(2);
        expect(result[0].label).toBe("dog");
        expect(result[1].box.xmax).toBe(10);
    });

    it("returns [] for empty or nullish input", () => {
        expect(parseDetections("")).toEqual([]);
        expect(parseDetections(null)).toEqual([]);
        expect(parseDetections(undefined)).toEqual([]);
    });

    it("returns [] for invalid JSON", () => {
        expect(parseDetections("not json{")).toEqual([]);
    });

    it("returns [] for non-array JSON (e.g. per-frame video output)", () => {
        expect(parseDetections(JSON.stringify({ frame: 0, detections: [] }))).toEqual([]);
    });

    it("filters out malformed detection entries", () => {
        const text = JSON.stringify([
            det("dog", 0.9),
            { label: "missing-box", score: 0.5 },
            { label: "bad-score", score: "high", box: { xmin: 0, ymin: 0, xmax: 1, ymax: 1 } },
            { label: 42, score: 0.5, box: { xmin: 0, ymin: 0, xmax: 1, ymax: 1 } },
            { score: 0.5, box: { xmin: 0, ymin: 0, xmax: 1, ymax: 1 } },
            { label: "partial-box", score: 0.5, box: { xmin: 0, ymin: 0 } },
        ]);
        const result = parseDetections(text);
        expect(result).toHaveLength(1);
        expect(result[0].label).toBe("dog");
    });
});

describe("buildLabelColorMap", () => {
    it("assigns colors by first appearance and reuses them per label", () => {
        const map = buildLabelColorMap([det("dog", 0.9), det("cat", 0.8), det("dog", 0.7)]);
        expect(map.size).toBe(2);
        expect(map.get("dog")).toBe(DETECTION_COLORS[0]);
        expect(map.get("cat")).toBe(DETECTION_COLORS[1]);
    });

    it("wraps around the palette when labels exceed its length", () => {
        const dets = DETECTION_COLORS.map((_, i) => det(`label-${i}`, 0.5)).concat([
            det("overflow", 0.5),
        ]);
        const map = buildLabelColorMap(dets);
        expect(map.get("overflow")).toBe(DETECTION_COLORS[0]);
    });

    it("handles an empty list", () => {
        expect(buildLabelColorMap([]).size).toBe(0);
    });
});

describe("summarizeLabels", () => {
    it("groups by label with count, color, and max score", () => {
        const summary = summarizeLabels([
            det("dog", 0.9),
            det("cat", 0.8),
            det("dog", 0.95),
        ]);
        expect(summary).toHaveLength(2);

        const dog = summary.find((s) => s.label === "dog");
        expect(dog.count).toBe(2);
        expect(dog.maxScore).toBe(0.95);
        expect(dog.color).toBe(DETECTION_COLORS[0]);

        const cat = summary.find((s) => s.label === "cat");
        expect(cat.count).toBe(1);
        expect(cat.color).toBe(DETECTION_COLORS[1]);
    });

    it("preserves first-appearance order", () => {
        const summary = summarizeLabels([det("cat", 0.5), det("dog", 0.5)]);
        expect(summary.map((s) => s.label)).toEqual(["cat", "dog"]);
    });

    it("returns [] for no detections", () => {
        expect(summarizeLabels([])).toEqual([]);
    });
});

describe("filterDetections", () => {
    const dets = [det("dog", 0.9), det("cat", 0.4), det("dog", 0.5)];

    it("excludes hidden labels", () => {
        const result = filterDetections(dets, new Set(["cat"]), 0);
        expect(result).toHaveLength(2);
        expect(result.every((d) => d.label === "dog")).toBe(true);
    });

    it("excludes detections below the confidence threshold", () => {
        const result = filterDetections(dets, new Set(), 0.6);
        expect(result).toHaveLength(1);
        expect(result[0].score).toBe(0.9);
    });

    it("applies both filters together", () => {
        const result = filterDetections(dets, new Set(["dog"]), 0.6);
        expect(result).toEqual([]);
    });

    it("includes everything with no hidden labels and zero threshold", () => {
        expect(filterDetections(dets, new Set(), 0)).toHaveLength(3);
    });

    it("treats the threshold as inclusive", () => {
        expect(filterDetections(dets, new Set(), 0.5)).toHaveLength(2);
    });
});

describe("formatDetectionLabel", () => {
    it("formats label with two-decimal confidence", () => {
        expect(formatDetectionLabel(det("dog", 0.98))).toBe("dog (0.98)");
        expect(formatDetectionLabel(det("cat", 0.8))).toBe("cat (0.80)");
        expect(formatDetectionLabel(det("bird", 0.876))).toBe("bird (0.88)");
    });
});
