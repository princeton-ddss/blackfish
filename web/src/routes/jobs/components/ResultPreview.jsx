import { useState, useEffect } from "react";
import {
    DocumentIcon,
    CheckCircleIcon,
    XCircleIcon,
} from "@heroicons/react/24/outline";
import { blackfishApiURL } from "@/config";
import { getFileType, truncateTextPreview } from "@/lib/fileApi";
import PropTypes from "prop-types";

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

function OutputFilePreview({ file, profile = null }) {
    const [textContent, setTextContent] = useState(null);
    const [textLoading, setTextLoading] = useState(false);
    const [textError, setTextError] = useState(null);

    const fileType = file ? getFileType(file) : null;
    const profileParam = profile && profile.schema !== "local"
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
                <div className="relative">
                    <img
                        src={`${blackfishApiURL}/api/image?path=${encodeURIComponent(file)}${profileParam}`}
                        alt={file}
                        className="w-full h-auto rounded-lg border border-gray-200 dark:border-gray-700"
                    />
                </div>
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
                            <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 max-h-48 overflow-y-auto">
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
        <div className="bg-white dark:bg-gray-800 p-6">
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
                    <span className="text-gray-900 dark:text-gray-100 truncate ml-2" title={result.input_file}>
                        {result.input_file}
                    </span>
                </div>
                <div className="flex justify-between">
                    <span className="text-gray-500 dark:text-gray-400">Output File:</span>
                    <span className="text-gray-900 dark:text-gray-100 truncate ml-2" title={result.output_file || "-"}>
                        {result.output_file || "-"}
                    </span>
                </div>
            </div>

            {/* Output File Preview */}
            {result.output_file && (
                <div className="border-t border-gray-200 dark:border-gray-700 pt-4 mb-4">
                    <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
                        Output Preview
                    </h4>
                    <OutputFilePreview file={result.output_file} profile={profile} />
                </div>
            )}

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
                        Job Context
                    </h4>
                    <div className="space-y-2 text-sm">
                        <div className="flex justify-between">
                            <span className="text-gray-500 dark:text-gray-400">Job:</span>
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
                <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
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
