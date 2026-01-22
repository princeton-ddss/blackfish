
import { useState, useEffect } from "react";
import { blackfishApiURL } from "@/config";
import { DocumentIcon } from "@heroicons/react/24/outline";
import { fileSize } from "@/lib/util";
import PropTypes from "prop-types";

function FilePreview({ file, profile = null }) {
    const [textContent, setTextContent] = useState(null);
    const [textLoading, setTextLoading] = useState(false);
    const [textError, setTextError] = useState(null);

    const profileParam = profile && profile.schema !== "local"
        ? `&profile=${encodeURIComponent(profile.name)}`
        : "";

    useEffect(() => {
        if (file && file.type === "text") {
            setTextLoading(true);
            setTextError(null);

            const url = `${blackfishApiURL}/api/text?path=${encodeURIComponent(file.path)}${profileParam}`;
            fetch(url)
                .then(res => {
                    if (!res.ok) throw new Error("Failed to load file");
                    return res.text();
                })
                .then(text => {
                    setTextContent(text);
                    setTextLoading(false);
                })
                .catch(err => {
                    setTextError(err.message);
                    setTextLoading(false);
                });
        }
    }, [file, profileParam]);

    if (!file) {
        return (
            <div className="bg-white p-6 rounded-lg">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">File Preview</h3>
                <div className="text-center py-12">
                    <DocumentIcon className="mx-auto h-12 w-12 text-gray-400" />
                    <p className="mt-4 text-sm font-semibold text-gray-700">
                        No file selected
                    </p>
                    <p className="mt-2 text-sm text-gray-500">
                        Click on a file in the browser to preview it here
                    </p>
                </div>
            </div>
        );
    }

    return (
        <div className="bg-white p-6 rounded-lg">
            <div className="mb-4">
                <h3 className="text-lg font-semibold text-gray-900 mb-1 truncate">
                    File Preview
                </h3>
                <p className="text-xs text-gray-500 truncate" title={file.name}>
                    {file.name}
                </p>
            </div>

            <div className="mb-4 space-y-2 text-sm">
                <div className="flex justify-between">
                    <span className="text-gray-500">Type:</span>
                    <span className="text-gray-900 capitalize">
                        {file.type || "Unknown"}
                    </span>
                </div>
                <div className="flex justify-between">
                    <span className="text-gray-500">Size:</span>
                    <span className="text-gray-900">{fileSize(file.size)}</span>
                </div>
            </div>

            <div className="border-t border-gray-200 pt-4">
                {file.type === "image" && (
                    <div className="relative">
                        <img
                            src={`${blackfishApiURL}/api/image?path=${encodeURIComponent(file.path)}${profileParam}`}
                            alt={file.name}
                            width={400}
                            height={400}
                            className="w-full h-auto rounded-lg border border-gray-200"
                        />
                    </div>
                )}

                {file.type === "text" && (
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
                        ) : (
                            <div className="bg-gray-50 rounded-lg p-4 max-h-96 overflow-y-auto">
                                <pre className="text-xs text-gray-900 whitespace-pre-wrap font-mono">
                                    {textContent}
                                </pre>
                            </div>
                        )}
                    </div>
                )}

                {file.type === "audio" && (
                    <div>
                        <audio
                            src={`${blackfishApiURL}/api/audio?path=${encodeURIComponent(file.path)}${profileParam}`}
                            controls
                            className="w-full"
                        />
                        <div className="mt-2 text-xs text-gray-500 truncate" title={file.path}>
                            {file.path}
                        </div>
                    </div>
                )}

                {(!file.type || (file.type !== "image" && file.type !== "text" && file.type !== "audio")) && (
                    <div className="text-center py-8">
                        <DocumentIcon className="mx-auto h-12 w-12 text-gray-300" />
                        <p className="mt-4 text-sm font-medium text-gray-900">
                            Preview not available
                        </p>
                        <p className="mt-1 text-xs text-gray-500">
                            This file type cannot be previewed
                        </p>
                        {file.type && (
                            <p className="mt-2 text-xs text-gray-400">
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
        type: PropTypes.string.isRequired,
        size: PropTypes.number.isRequired,
        modified_at: PropTypes.string,
    }),
    profile: PropTypes.object,
};

export default FilePreview;
