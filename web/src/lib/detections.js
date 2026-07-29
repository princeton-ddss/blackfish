// Helpers for object-detection bounding-box overlays.
//
// The detection output is a JSON array produced by the inference backend. Each
// element has the shape:
//   { label: string, score: number, box: { xmin, ymin, xmax, ymax } }
// where the box coordinates are absolute pixels in the input image's natural
// dimensions.

/**
 * A fixed, color-blind-friendly palette. Labels are assigned colors
 * deterministically by insertion order so the same label always keeps the same
 * color within a preview (and repeats predictably if there are many labels).
 */
export const DETECTION_COLORS = [
    "#ef4444", // red-500
    "#3b82f6", // blue-500
    "#22c55e", // green-500
    "#f59e0b", // amber-500
    "#a855f7", // purple-500
    "#ec4899", // pink-500
    "#14b8a6", // teal-500
    "#f97316", // orange-500
    "#84cc16", // lime-500
    "#06b6d4", // cyan-500
];

/**
 * Build a stable label -> color map for a list of detections. Labels are
 * ordered by first appearance so colors are consistent across renders of the
 * same output.
 */
export function buildLabelColorMap(detections) {
    const map = new Map();
    for (const det of detections) {
        if (!map.has(det.label)) {
            map.set(det.label, DETECTION_COLORS[map.size % DETECTION_COLORS.length]);
        }
    }
    return map;
}

/**
 * Summarize the distinct labels in a list of detections: one entry per label
 * with its color, count, and the maximum confidence seen for that label.
 * Ordered by first appearance (matching the color assignment).
 */
export function summarizeLabels(detections) {
    const colorMap = buildLabelColorMap(detections);
    const byLabel = new Map();
    for (const det of detections) {
        const existing = byLabel.get(det.label);
        if (existing) {
            existing.count += 1;
            existing.maxScore = Math.max(existing.maxScore, det.score);
        } else {
            byLabel.set(det.label, {
                label: det.label,
                color: colorMap.get(det.label),
                count: 1,
                maxScore: det.score,
            });
        }
    }
    return Array.from(byLabel.values());
}

/**
 * Filter detections by a set of hidden labels and a minimum confidence.
 * `hiddenLabels` is a Set of label strings to exclude; `minConfidence` is a
 * lower bound (inclusive) on the score.
 */
export function filterDetections(detections, hiddenLabels, minConfidence = 0) {
    return detections.filter(
        (det) => !hiddenLabels.has(det.label) && det.score >= minConfidence
    );
}

/**
 * Parse the raw detection-output text into a normalized array of detections.
 * Returns [] for empty/invalid input or shapes we don't recognize (e.g. the
 * per-frame video output), so callers can safely treat "no boxes" uniformly.
 */
export function parseDetections(text) {
    if (!text) return [];

    let data;
    try {
        data = JSON.parse(text);
    } catch {
        return [];
    }

    if (!Array.isArray(data)) return [];

    return data.filter(isValidDetection);
}

function isValidDetection(det) {
    if (!det || typeof det !== "object") return false;
    if (typeof det.label !== "string") return false;
    if (typeof det.score !== "number") return false;
    const box = det.box;
    if (!box || typeof box !== "object") return false;
    return ["xmin", "ymin", "xmax", "ymax"].every(
        (k) => typeof box[k] === "number"
    );
}

/** Format a detection's confidence for display, e.g. "dog (0.98)". */
export function formatDetectionLabel(detection) {
    return `${detection.label} (${detection.score.toFixed(2)})`;
}
