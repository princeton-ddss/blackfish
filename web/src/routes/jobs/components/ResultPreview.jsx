import { useState, useEffect, useCallback, useMemo } from "react";
import { Popover, PopoverButton, PopoverPanel } from "@headlessui/react";
import {
    DocumentIcon,
    CheckCircleIcon,
    CheckIcon,
    XCircleIcon,
    XMarkIcon,
    AdjustmentsHorizontalIcon,
} from "@heroicons/react/24/outline";
import { blackfishApiURL } from "@/config";
import { getFileType, truncateTextPreview } from "@/lib/fileApi";
import { isRemoteProfile } from "@/lib/util";
import {
    parseDetections,
    buildLabelColorMap,
    formatDetectionLabel,
    summarizeLabels,
    filterDetections,
} from "@/lib/detections";
import PropTypes from "prop-types";

function TruncatedPath({ path, maxWidth = "max-w-[14rem]" }) {
    const [copied, setCopied] = useState(false);

    const handleClick = useCallback(() => {
        navigator.clipboard.writeText(path).then(() => {
            setCopied(true);
            setTimeout(() => setCopied(false), 1500);
        }).catch(() => {});
    }, [path]);

    if (!path) return "-";

    return (
        <span
            className="cursor-pointer inline-flex items-center gap-1"
            title={path}
            onClick={handleClick}
        >
            {copied ? (
                <>
                    <span className="text-green-600 dark:text-green-400">Copied</span>
                    <CheckIcon className="h-3.5 w-3.5 text-green-500 flex-shrink-0" />
                </>
            ) : (
                <span className={`truncate ${maxWidth} text-xs font-mono`}>{path}</span>
            )}
        </span>
    );
}

TruncatedPath.propTypes = {
    path: PropTypes.string,
    maxWidth: PropTypes.string,
};

function formatDateTime(isoString) {
    if (!isoString) return "-";
    const date = new Date(isoString);
    return date.toLocaleString();
}

function formatElapsedTime(startedAt, finishedAt) {
    if (!startedAt || !finishedAt) return "-";

    const start = new Date(startedAt);
    const end = new Date(finishedAt);
    const diffMs = end - start;

    if (diffMs < 1000) {
        return `${diffMs}ms`;
    } else if (diffMs < 60000) {
        return `${(diffMs / 1000).toFixed(1)}s`;
    } else {
        const minutes = Math.floor(diffMs / 60000);
        const seconds = ((diffMs % 60000) / 1000).toFixed(0);
        return `${minutes}m ${seconds}s`;
    }
}

// An object-detection result: an image input with a JSON output file. Used to
// decide whether to offer the bounding-box overlay on the input image.
export function isDetectionResult(inputFile, outputFile) {
    return (
        getFileType(inputFile) === "image" &&
        Boolean(outputFile) &&
        outputFile.toLowerCase().endsWith(".json")
    );
}

// Fetch and parse object-detection boxes from a JSON detection file. Returns []
// while loading, on error, or when there is no detection file.
function useDetections(detectionFile, profileParam) {
    const [detections, setDetections] = useState([]);

    useEffect(() => {
        let cancelled = false;
        setDetections([]);
        if (!detectionFile) return;

        const url = `${blackfishApiURL}/api/text?path=${encodeURIComponent(detectionFile)}${profileParam}`;
        fetch(url)
            .then(res => (res.ok ? res.text() : Promise.reject(new Error("Failed to load detections"))))
            .then(text => {
                if (!cancelled) setDetections(parseDetections(text));
            })
            .catch(() => {
                if (!cancelled) setDetections([]);
            });

        return () => {
            cancelled = true;
        };
    }, [detectionFile, profileParam]);

    return detections;
}

// An image preview that can superimpose object-detection bounding boxes. The
// (already filtered) `detections` and their `colorMap` are owned by the parent
// so the filter controls can live in the shared preview header, and colors stay
// stable regardless of which categories are currently shown.
function DetectableImage({ src, alt, detections = [], colorMap = new Map() }) {
    // Natural (intrinsic) image size, needed to scale absolute-pixel boxes to
    // the rendered element size.
    const [natural, setNatural] = useState(null);
    const [loaded, setLoaded] = useState(false);
    const [error, setError] = useState(false);

    // Reset load state when the image source changes.
    useEffect(() => {
        setLoaded(false);
        setError(false);
    }, [src]);

    const markLoaded = useCallback((img) => {
        setNatural({ width: img.naturalWidth, height: img.naturalHeight });
        setLoaded(true);
    }, []);

    // Handle images the browser already has cached: they can fire `load` before
    // React attaches onLoad, so check `complete` when the element mounts.
    const imgRef = useCallback((img) => {
        if (img && img.complete && img.naturalWidth > 0) {
            markLoaded(img);
        }
    }, [markLoaded]);

    if (error) {
        return (
            <div className="text-center py-4">
                <DocumentIcon className="mx-auto h-8 w-8 text-gray-300 dark:text-gray-600" />
                <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                    Failed to load image
                </p>
            </div>
        );
    }

    return (
        <div className="relative">
            <img
                ref={imgRef}
                src={src}
                alt={alt}
                onLoad={(e) => markLoaded(e.target)}
                onError={() => setError(true)}
                className={`w-full h-auto rounded-lg ${loaded ? "border border-gray-200 dark:border-gray-700" : "block"}`}
            />
            {!loaded && (
                <div className="absolute inset-0 animate-pulse rounded-lg bg-gray-200 dark:bg-gray-700 min-h-[8rem]" />
            )}
            {loaded && detections.length > 0 && natural && (
                <svg
                    className="absolute inset-0 w-full h-full pointer-events-none"
                    viewBox={`0 0 ${natural.width} ${natural.height}`}
                    preserveAspectRatio="none"
                >
                    {detections.map((det, i) => {
                        const { xmin, ymin, xmax, ymax } = det.box;
                        const color = colorMap.get(det.label);
                        const label = formatDetectionLabel(det);
                        // Scale stroke/text with image size so they stay
                        // legible regardless of the source resolution.
                        const stroke = Math.max(natural.width, natural.height) * 0.004;
                        const fontSize = Math.max(natural.width, natural.height) * 0.02;
                        const padX = fontSize * 0.3;
                        const textWidth = label.length * fontSize * 0.55;
                        const tagHeight = fontSize * 1.3;
                        // Draw the label tag above the box, but flip it just
                        // inside the top edge when there isn't room above (box
                        // near the top of the image) so it never gets clipped.
                        const above = ymin - tagHeight >= 0;
                        const tagY = above ? ymin - tagHeight : ymin;
                        const textY = tagY + fontSize * 0.95;
                        return (
                            <g key={i}>
                                <rect
                                    x={xmin}
                                    y={ymin}
                                    width={xmax - xmin}
                                    height={ymax - ymin}
                                    fill="none"
                                    stroke={color}
                                    strokeWidth={stroke}
                                />
                                <rect
                                    x={xmin}
                                    y={tagY}
                                    width={textWidth + padX * 2}
                                    height={tagHeight}
                                    fill={color}
                                />
                                <text
                                    x={xmin + padX}
                                    y={textY}
                                    fill="#ffffff"
                                    fontSize={fontSize}
                                    fontFamily="ui-sans-serif, system-ui, sans-serif"
                                >
                                    {label}
                                </text>
                            </g>
                        );
                    })}
                </svg>
            )}
        </div>
    );
}

DetectableImage.propTypes = {
    src: PropTypes.string.isRequired,
    alt: PropTypes.string,
    detections: PropTypes.array,
    colorMap: PropTypes.instanceOf(Map),
};

// Popover for filtering the overlaid detections: toggle categories on/off and
// set a minimum confidence. Mirrors the service launch "Parameters" popover.
function DetectionFilterPopover({
    labels,
    hiddenLabels,
    onToggleLabel,
    onShowAll,
    onHideAll,
    minConfidence,
    onConfidenceChange,
}) {
    const allShown = hiddenLabels.size === 0;
    const allHidden = hiddenLabels.size >= labels.length;
    return (
        <Popover className="relative">
            <PopoverButton
                title="Filter boxes"
                className="p-1.5 rounded-md text-gray-500 hover:text-gray-700 hover:bg-gray-100 dark:text-gray-400 dark:hover:text-gray-200 dark:hover:bg-gray-700 focus:outline-none"
            >
                <AdjustmentsHorizontalIcon className="h-5 w-5" />
            </PopoverButton>
            <PopoverPanel
                anchor="left end"
                className="z-50 mr-2 w-72 rounded-lg bg-white dark:bg-gray-800 shadow-lg ring-1 ring-gray-200 dark:ring-gray-700 p-4"
            >
                {({ close }) => (
                    <div>
                        <div className="flex items-center justify-between mb-3">
                            <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                                Bounding boxes
                            </span>
                            <button
                                onClick={close}
                                className="p-1 rounded-md text-gray-400 hover:text-gray-500 dark:hover:text-gray-300 focus:outline-none"
                            >
                                <XMarkIcon className="h-4 w-4" />
                            </button>
                        </div>

                        {/* Confidence threshold */}
                        <div className="mb-4">
                            <div className="flex items-center justify-between mb-1">
                                <label
                                    htmlFor="detection-confidence"
                                    className="text-xs text-gray-600 dark:text-gray-300"
                                >
                                    Min. confidence
                                </label>
                                <span className="text-xs font-mono text-gray-900 dark:text-gray-100">
                                    {minConfidence.toFixed(2)}
                                </span>
                            </div>
                            <input
                                id="detection-confidence"
                                type="range"
                                min="0"
                                max="1"
                                step="0.01"
                                value={minConfidence}
                                onChange={(e) => onConfidenceChange(Number(e.target.value))}
                                className="w-full accent-blue-600"
                            />
                        </div>

                        {/* Category toggles */}
                        <div className="flex items-center justify-between mb-2">
                            <span className="text-xs font-medium text-gray-600 dark:text-gray-300">
                                Categories
                            </span>
                            <div className="flex items-center gap-1 text-xs">
                                <button
                                    type="button"
                                    onClick={onShowAll}
                                    disabled={allShown}
                                    className="text-blue-600 dark:text-blue-400 hover:underline disabled:text-gray-300 dark:disabled:text-gray-600 disabled:no-underline disabled:cursor-default focus:outline-none"
                                >
                                    All
                                </button>
                                <span className="text-gray-300 dark:text-gray-600">/</span>
                                <button
                                    type="button"
                                    onClick={onHideAll}
                                    disabled={allHidden}
                                    className="text-blue-600 dark:text-blue-400 hover:underline disabled:text-gray-300 dark:disabled:text-gray-600 disabled:no-underline disabled:cursor-default focus:outline-none"
                                >
                                    None
                                </button>
                            </div>
                        </div>
                        <div className="space-y-1.5 max-h-56 overflow-y-auto">
                            {labels.map((entry) => (
                                <label
                                    key={entry.label}
                                    className="flex items-center gap-2 text-xs text-gray-700 dark:text-gray-200 cursor-pointer select-none"
                                >
                                    <input
                                        type="checkbox"
                                        checked={!hiddenLabels.has(entry.label)}
                                        onChange={() => onToggleLabel(entry.label)}
                                        className="rounded border-gray-300 dark:border-gray-600"
                                    />
                                    <span
                                        className="inline-block h-3 w-3 rounded-sm flex-shrink-0"
                                        style={{ backgroundColor: entry.color }}
                                    />
                                    <span className="truncate flex-1" title={entry.label}>
                                        {entry.label}
                                    </span>
                                    <span className="text-gray-400 dark:text-gray-500 font-mono">
                                        {entry.count}
                                    </span>
                                </label>
                            ))}
                        </div>
                    </div>
                )}
            </PopoverPanel>
        </Popover>
    );
}

DetectionFilterPopover.propTypes = {
    labels: PropTypes.array.isRequired,
    hiddenLabels: PropTypes.instanceOf(Set).isRequired,
    onToggleLabel: PropTypes.func.isRequired,
    onShowAll: PropTypes.func.isRequired,
    onHideAll: PropTypes.func.isRequired,
    minConfidence: PropTypes.number.isRequired,
    onConfidenceChange: PropTypes.func.isRequired,
};

function OutputFilePreview({ file, profile = null, detections = [], colorMap = new Map() }) {
    const [textContent, setTextContent] = useState(null);
    const [textLoading, setTextLoading] = useState(false);
    const [textError, setTextError] = useState(null);

    const fileType = file ? getFileType(file) : null;
    const profileParam = isRemoteProfile(profile)
        ? `&profile=${encodeURIComponent(profile.name)}`
        : "";

    useEffect(() => {
        if (file && fileType === "text") {
            setTextLoading(true);
            setTextError(null);

            const url = `${blackfishApiURL}/api/text?path=${encodeURIComponent(file)}${profileParam}`;
            fetch(url)
                .then(res => {
                    if (!res.ok) throw new Error("Failed to load file");
                    return res.text();
                })
                .then(text => {
                    setTextContent(truncateTextPreview(text));
                    setTextLoading(false);
                })
                .catch(err => {
                    setTextError(err.message);
                    setTextLoading(false);
                });
        }
    }, [file, fileType, profileParam]);

    if (!file) {
        return (
            <div className="text-center py-4">
                <p className="text-sm text-gray-500 dark:text-gray-400">No output file</p>
            </div>
        );
    }

    return (
        <div>
            {fileType === "image" && (
                <DetectableImage
                    src={`${blackfishApiURL}/api/image?path=${encodeURIComponent(file)}${profileParam}`}
                    alt={file}
                    detections={detections}
                    colorMap={colorMap}
                />
            )}

            {fileType === "text" && (
                <div>
                    {textLoading ? (
                        <div className="animate-pulse">
                            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded mb-2"></div>
                            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded mb-2"></div>
                            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded mb-2"></div>
                        </div>
                    ) : textError ? (
                        <div className="rounded-md bg-red-50 dark:bg-red-900/20 p-4">
                            <p className="text-sm text-red-700 dark:text-red-400">{textError}</p>
                        </div>
                    ) : textContent ? (
                        <>
                            <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 overflow-y-auto">
                                <pre className="text-xs text-gray-900 dark:text-gray-100 whitespace-pre-wrap font-mono">
                                    {textContent.text}
                                </pre>
                            </div>
                            {textContent.truncated && (
                                <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                                    Showing first 500 of {textContent.totalLines.toLocaleString()} lines
                                </p>
                            )}
                        </>
                    ) : null}
                </div>
            )}

            {fileType === "audio" && (
                <div>
                    <audio
                        src={`${blackfishApiURL}/api/audio?path=${encodeURIComponent(file)}${profileParam}`}
                        controls
                        className="w-full"
                    />
                </div>
            )}

            {(!fileType || (fileType !== "image" && fileType !== "text" && fileType !== "audio")) && (
                <div className="text-center py-4">
                    <DocumentIcon className="mx-auto h-8 w-8 text-gray-300 dark:text-gray-600" />
                    <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                        Preview not available
                    </p>
                </div>
            )}
        </div>
    );
}

OutputFilePreview.propTypes = {
    file: PropTypes.string,
    profile: PropTypes.object,
    detections: PropTypes.array,
    colorMap: PropTypes.instanceOf(Map),
};

// The initial toggle side: output when it exists (success), else input.
export function defaultPreviewSide(hasOutput) {
    return hasOutput ? "output" : "input";
}

// Resolve the side actually shown: fall back to input when output is chosen
// but unavailable (e.g. a failed file with no output).
export function resolvePreviewSide(side, hasOutput) {
    return side === "output" && !hasOutput ? "input" : side;
}

// Preview pane with an input/output toggle. Output only exists on success, so
// the toggle defaults to output when available and falls back to input.
function FilePreviewPanel({ inputFile, outputFile, profile = null }) {
    const hasOutput = Boolean(outputFile);
    const [side, setSide] = useState(defaultPreviewSide(hasOutput));

    const activeSide = resolvePreviewSide(side, hasOutput);
    const file = activeSide === "output" ? outputFile : inputFile;

    const profileParam = isRemoteProfile(profile)
        ? `&profile=${encodeURIComponent(profile.name)}`
        : "";

    // For object-detection results, offer a bounding-box overlay on the input
    // image, drawn from the JSON output file.
    const detectionFile = isDetectionResult(inputFile, outputFile) ? outputFile : null;
    const detections = useDetections(detectionFile, profileParam);
    const [hiddenLabels, setHiddenLabels] = useState(() => new Set());
    const [minConfidence, setMinConfidence] = useState(0);

    // Reset filters when the underlying detection set changes.
    useEffect(() => {
        setHiddenLabels(new Set());
        setMinConfidence(0);
    }, [detectionFile]);

    const labelSummary = useMemo(() => summarizeLabels(detections), [detections]);
    // Stable label -> color map built from the full detection set, so a box's
    // color never changes as categories are toggled on and off.
    const colorMap = useMemo(() => buildLabelColorMap(detections), [detections]);
    const visibleDetections = useMemo(
        () => filterDetections(detections, hiddenLabels, minConfidence),
        [detections, hiddenLabels, minConfidence]
    );

    const toggleLabel = useCallback((label) => {
        setHiddenLabels((prev) => {
            const next = new Set(prev);
            if (next.has(label)) next.delete(label);
            else next.add(label);
            return next;
        });
    }, []);

    const showAllLabels = useCallback(() => setHiddenLabels(new Set()), []);
    const hideAllLabels = useCallback(
        () => setHiddenLabels(new Set(labelSummary.map((entry) => entry.label))),
        [labelSummary]
    );

    // Only overlay boxes on the input image side, and only when there's data.
    const canShowBoxes = activeSide === "input" && detections.length > 0;

    const tabClass = (isActive) =>
        `px-2 py-1 text-xs rounded-md ${isActive
            ? "bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm font-medium"
            : "text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
        }`;

    return (
        <div className="border-t border-gray-200 dark:border-gray-700 pt-4 flex-1 min-h-0 flex flex-col">
            <div className="flex items-center justify-between mb-2">
                <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100">
                    Preview
                </h4>
                <div className="flex items-center gap-2">
                    {canShowBoxes && (
                        <DetectionFilterPopover
                            labels={labelSummary}
                            hiddenLabels={hiddenLabels}
                            onToggleLabel={toggleLabel}
                            onShowAll={showAllLabels}
                            onHideAll={hideAllLabels}
                            minConfidence={minConfidence}
                            onConfidenceChange={setMinConfidence}
                        />
                    )}
                    <div className="inline-flex gap-1 rounded-lg bg-gray-100 dark:bg-gray-900 p-0.5">
                        <button
                            type="button"
                            onClick={() => setSide("input")}
                            className={tabClass(activeSide === "input")}
                        >
                            Input
                        </button>
                        <button
                            type="button"
                            onClick={() => setSide("output")}
                            disabled={!hasOutput}
                            title={hasOutput ? undefined : "No output for this file"}
                            className={`${tabClass(activeSide === "output")} disabled:opacity-40 disabled:cursor-not-allowed`}
                        >
                            Output
                        </button>
                    </div>
                </div>
            </div>
            <div className="flex-1 min-h-0 overflow-y-auto">
                <OutputFilePreview
                    file={file}
                    profile={profile}
                    detections={canShowBoxes ? visibleDetections : []}
                    colorMap={colorMap}
                />
            </div>
        </div>
    );
}

FilePreviewPanel.propTypes = {
    inputFile: PropTypes.string,
    outputFile: PropTypes.string,
    profile: PropTypes.object,
};

function ResultPreview({ result, job, profile = null }) {
    if (!result) {
        return (
            <div className="bg-white dark:bg-gray-800 p-6 h-full flex flex-col justify-center">
                <div className="text-center">
                    <DocumentIcon className="mx-auto h-12 w-12 text-gray-400" />
                    <p className="mt-4 text-sm font-semibold text-gray-700 dark:text-gray-300">
                        No result selected
                    </p>
                    <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                        Click on a result in the table to preview it here
                    </p>
                </div>
            </div>
        );
    }

    return (
        <div className="bg-white dark:bg-gray-800 p-6 h-full flex flex-col">
            {/* Status Header */}
            <div className="flex items-center gap-3 mb-4">
                {result.success ? (
                    <CheckCircleIcon className="h-6 w-6 text-green-500" />
                ) : (
                    <XCircleIcon className="h-6 w-6 text-red-500" />
                )}
                <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                    {result.success ? "Success" : "Failed"}
                </p>
            </div>

            {/* File Information */}
            <div className="mb-4 space-y-2 text-sm">
                <div className="flex justify-between">
                    <span className="text-gray-500 dark:text-gray-400">Input File:</span>
                    <span className="text-gray-900 dark:text-gray-100 ml-2">
                        <TruncatedPath path={result.input_file} maxWidth="max-w-[22rem]" />
                    </span>
                </div>
                <div className="flex justify-between">
                    <span className="text-gray-500 dark:text-gray-400">Output File:</span>
                    <span className="text-gray-900 dark:text-gray-100 ml-2">
                        <TruncatedPath path={result.output_file} maxWidth="max-w-[22rem]" />
                    </span>
                </div>
            </div>

            {/* Timing Information */}
            <div className="border-t border-gray-200 dark:border-gray-700 pt-4 mb-4">
                <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
                    Timing
                </h4>
                <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                        <span className="text-gray-500 dark:text-gray-400">Started:</span>
                        <span className="text-gray-900 dark:text-gray-100">
                            {formatDateTime(result.started_at)}
                        </span>
                    </div>
                    <div className="flex justify-between">
                        <span className="text-gray-500 dark:text-gray-400">Finished:</span>
                        <span className="text-gray-900 dark:text-gray-100">
                            {formatDateTime(result.finished_at)}
                        </span>
                    </div>
                    <div className="flex justify-between">
                        <span className="text-gray-500 dark:text-gray-400">Elapsed:</span>
                        <span className="text-gray-900 dark:text-gray-100">
                            {formatElapsedTime(result.started_at, result.finished_at)}
                        </span>
                    </div>
                </div>
            </div>

            {/* Job Context */}
            {job && (
                <div className="border-t border-gray-200 dark:border-gray-700 pt-4 mb-4">
                    <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
                        Job
                    </h4>
                    <div className="space-y-2 text-sm">
                        <div className="flex justify-between">
                            <span className="text-gray-500 dark:text-gray-400">Name:</span>
                            <span className="text-gray-900 dark:text-gray-100 truncate ml-2" title={job.name}>
                                {job.name}
                            </span>
                        </div>
                        {job.prompt && (
                            <div>
                                <span className="text-gray-500 dark:text-gray-400 block mb-1">Prompt:</span>
                                <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-3">
                                    <pre className="text-xs text-gray-900 dark:text-gray-100 whitespace-pre-wrap font-mono">
                                        {job.prompt}
                                    </pre>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Error Message */}
            {!result.success && result.error && (
                <div className="border-t border-gray-200 dark:border-gray-700 pt-4 mb-4">
                    <h4 className="text-sm font-medium text-red-600 dark:text-red-400 mb-2">
                        Error
                    </h4>
                    <div className="rounded-md bg-red-50 dark:bg-red-900/20 p-3">
                        <p className="text-sm text-red-700 dark:text-red-400">
                            {result.error}
                        </p>
                    </div>
                </div>
            )}

            {/* File preview with input/output toggle — fills remaining space.
                Keyed on the result so the toggle resets per selection. */}
            {result.input_file && (
                <FilePreviewPanel
                    key={result.id}
                    inputFile={result.input_file}
                    outputFile={result.output_file}
                    profile={profile}
                />
            )}
        </div>
    );
}

ResultPreview.propTypes = {
    result: PropTypes.shape({
        id: PropTypes.string,
        input_file: PropTypes.string,
        output_file: PropTypes.string,
        started_at: PropTypes.string,
        finished_at: PropTypes.string,
        success: PropTypes.bool,
        error: PropTypes.string,
    }),
    job: PropTypes.shape({
        id: PropTypes.string,
        name: PropTypes.string,
        prompt: PropTypes.string,
    }),
    profile: PropTypes.object,
};

export default ResultPreview;
