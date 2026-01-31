
import { useState, useEffect } from "react";
import { blackfishApiURL } from "@/config";
import { DocumentIcon } from "@heroicons/react/24/outline";
import { fileSize } from "@/lib/util";
import { MAX_PREVIEW_SIZE, truncateTextPreview } from "@/lib/fileApi";
import PropTypes from "prop-types";

function FilePreview({ file, profile = null }) {
    const [textContent, setTextContent] = useState(null);
    const [textLoading, setTextLoading] = useState(false);
    const [textError, setTextError] = useState(null);

    const profileParam = profile && profile.schema !== "local"
        ? `&profile=${encodeURIComponent(profile.name)}`
        : "";

    const isFileTooLarge = file && file.size > MAX_PREVIEW_SIZE;

    useEffect(() => {
        if (file && file.type === "text" && !isFileTooLarge) {
            setTextLoading(true);
            setTextError(null);

            const url = `${blackfishApiURL}/api/text?path=${encodeURIComponent(file.path)}${profileParam}`;
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
    }, [file, profileParam, isFileTooLarge]);

    if (!file) {
        return (
            <div className="bg-white dark:bg-gray-800 p-6 h-full flex flex-col justify-center">
                <div className="text-center">
                    <DocumentIcon className="mx-auto h-12 w-12 text-gray-400" />
                    <p className="mt-4 text-sm font-semibold text-gray-700 dark:text-gray-300">
                        No file selected
                    </p>
                    <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                        Click on a file in the browser to preview it here
                    </p>
                </div>
            </div>
        );
    }

    return (
        <div className="bg-white dark:bg-gray-800 p-6">
            <div className="mb-4">
                <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate" title={file.name}>
                    {file.name}
                </p>
            </div>

            <div className="mb-4 space-y-2 text-sm">
                <div className="flex justify-between">
                    <span className="text-gray-500 dark:text-gray-400">Type:</span>
                    <span className="text-gray-900 dark:text-gray-100 capitalize">
                        {file.type || "-"}
                    </span>
                </div>
                <div className="flex justify-between">
                    <span className="text-gray-500 dark:text-gray-400">Size:</span>
                    <span className="text-gray-900 dark:text-gray-100">{fileSize(file.size)}</span>
                </div>
            </div>

            <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
                {isFileTooLarge ? (
                    <div className="text-center py-8">
                        <DocumentIcon className="mx-auto h-12 w-12 text-gray-300 dark:text-gray-600" />
                        <p className="mt-4 text-sm font-medium text-gray-900 dark:text-gray-100">
                            File too large to preview
                        </p>
                        <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                            {fileSize(file.size)} exceeds the 5 MB preview limit
                        </p>
                    </div>
                ) : file.type === "image" ? (
                    <div className="relative">
                        <img
                            src={`${blackfishApiURL}/api/image?path=${encodeURIComponent(file.path)}${profileParam}`}
                            alt={file.name}
                            className="w-full h-full object-contain rounded-lg border border-gray-200 dark:border-gray-700"
                        />
                    </div>
                ) : file.type === "text" ? (
                    <div>
                        {textLoading ? (
                            <div className="animate-pulse">
                                <div className="h-4 bg-gray-200 rounded mb-2"></div>
                                <div className="h-4 bg-gray-200 rounded mb-2"></div>
                                <div className="h-4 bg-gray-200 rounded mb-2"></div>
                            </div>
                        ) : textError ? (
                            <div className="rounded-md bg-red-50 p-4">
                                <p className="text-sm text-red-700">{textError}</p>
                            </div>
                        ) : textContent ? (
                            <>
                                <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 max-h-96 overflow-y-auto">
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
                ) : file.type === "audio" ? (
                    <div>
                        <audio
                            src={`${blackfishApiURL}/api/audio?path=${encodeURIComponent(file.path)}${profileParam}`}
                            controls
                            className="w-full"
                        />
                        <div className="mt-2 text-xs text-gray-500 dark:text-gray-400 truncate" title={file.path}>
                            {file.path}
                        </div>
                    </div>
                ) : (
                    <div className="text-center py-8">
                        <DocumentIcon className="mx-auto h-12 w-12 text-gray-300 dark:text-gray-600" />
                        <p className="mt-4 text-sm font-medium text-gray-900 dark:text-gray-100">
                            Preview not available
                        </p>
                        <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                            This file type cannot be previewed
                        </p>
                        {file.type && (
                            <p className="mt-2 text-xs text-gray-400 dark:text-gray-500">
                                File type: {file.type}
                            </p>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}

FilePreview.propTypes = {
    file: PropTypes.shape({
        path: PropTypes.string.isRequired,
        name: PropTypes.string.isRequired,
        type: PropTypes.string,
        size: PropTypes.number.isRequired,
        modified_at: PropTypes.string,
    }),
    profile: PropTypes.object,
};

export default FilePreview;
