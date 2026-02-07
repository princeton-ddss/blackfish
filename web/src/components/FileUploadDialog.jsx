
import { Fragment, useState, useRef } from "react";
import {
    Dialog,
    DialogPanel,
    DialogTitle,
    Transition,
    TransitionChild,
} from "@headlessui/react";
import Alert from "@/components/Alert";
import { uploadFile, validateFileForUpload, getFileType, FILE_TYPE_CONFIG } from "@/lib/fileApi";
import { fileSize } from "@/lib/util";
import { DocumentTextIcon, PhotoIcon, MusicalNoteIcon, XMarkIcon } from "@heroicons/react/24/outline";
import { joinPath } from "@/lib/pathUtils";
import PropTypes from "prop-types";

function FileUploadDialog({
    open,
    setOpen,
    currentPath,
    profile = null,
    onSuccess,
    onError,
    setOperationInProgress,
}) {
    const [selectedFile, setSelectedFile] = useState(null);
    const [uploading, setUploading] = useState(false);
    const [error, setError] = useState(null);
    const [isDragging, setIsDragging] = useState(false);
    const fileInputRef = useRef(null);

    const handleClose = () => {
        if (!uploading) {
            setSelectedFile(null);
            setError(null);
            setOpen(false);
        }
    };

    const handleFileChange = (e) => {
        const file = e.target.files?.[0];
        if (file) {
            setSelectedFile(file);
            setError(null);
        }
    };

    const handleDragOver = (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (!uploading) {
            setIsDragging(true);
        }
    };

    const handleDragLeave = (e) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(false);
    };

    const handleDrop = (e) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(false);

        if (uploading) return;

        const file = e.dataTransfer.files?.[0];
        if (file) {
            setSelectedFile(file);
            setError(null);
        }
    };

    const handleDropZoneClick = () => {
        if (!uploading) {
            fileInputRef.current?.click();
        }
    };

    const handleUpload = async () => {
        if (!selectedFile) {
            setError("Please select a file");
            return;
        }

        const destinationPath = joinPath(currentPath, selectedFile.name);
        const validationErrors = validateFileForUpload(selectedFile, destinationPath);

        if (validationErrors.length > 0) {
            setError(validationErrors.join(", "));
            return;
        }

        setUploading(true);
        setOperationInProgress(true);
        setError(null);

        try {
            const response = await uploadFile(destinationPath, selectedFile, profile);
            onSuccess(`Uploaded ${response.filename}`);
            handleClose();
        } catch (err) {
            setError(err.message);
            onError(err.message);
        } finally {
            setUploading(false);
            setOperationInProgress(false);
        }
    };

    const acceptedExtensions = Object.values(FILE_TYPE_CONFIG)
        .flatMap(c => c.extensions)
        .join(",");

    return (
        <Transition show={open} as={Fragment}>
            <Dialog as="div" className="relative z-50" onClose={handleClose}>
                <TransitionChild
                    as={Fragment}
                    enter="ease-out duration-300"
                    enterFrom="opacity-0"
                    enterTo="opacity-100"
                    leave="ease-in duration-200"
                    leaveFrom="opacity-100"
                    leaveTo="opacity-0"
                >
                    <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" />
                </TransitionChild>

                <div className="fixed inset-0 z-10 overflow-y-auto">
                    <div className="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
                        <TransitionChild
                            as={Fragment}
                            enter="ease-out duration-300"
                            enterFrom="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
                            enterTo="opacity-100 translate-y-0 sm:scale-100"
                            leave="ease-in duration-200"
                            leaveFrom="opacity-100 translate-y-0 sm:scale-100"
                            leaveTo="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
                        >
                            <DialogPanel className="relative transform overflow-hidden rounded-lg bg-white dark:bg-gray-800 p-4 text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-lg">
                                <div>
                                    <DialogTitle
                                        as="h3"
                                        className="text-base font-semibold leading-6 text-gray-900 dark:text-white"
                                    >
                                        Upload File
                                    </DialogTitle>
                                        <div className="mt-3">
                                            <div className="space-y-3">
                                                {selectedFile ? (
                                                    <div className="rounded-md bg-gray-50 dark:bg-gray-700 px-4 py-3 flex items-start justify-between">
                                                        <div className="flex items-start">
                                                            {(() => {
                                                                const type = getFileType(selectedFile.name);
                                                                const iconClass = "h-6 w-6 shrink-0 text-gray-400 dark:text-gray-500";
                                                                if (type === "image") return <PhotoIcon className={iconClass} />;
                                                                if (type === "audio") return <MusicalNoteIcon className={iconClass} />;
                                                                return <DocumentTextIcon className={iconClass} />;
                                                            })()}
                                                            <div className="ml-3">
                                                                <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                                                                    {selectedFile.name}
                                                                </div>
                                                                <div className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                                                                    {fileSize(selectedFile.size)}
                                                                    <span className="mx-2">&middot;</span>
                                                                    Last modified {new Date(selectedFile.lastModified).toLocaleDateString()}
                                                                </div>
                                                            </div>
                                                        </div>
                                                        <button
                                                            type="button"
                                                            onClick={() => setSelectedFile(null)}
                                                            disabled={uploading}
                                                            className="ml-4 shrink-0 p-1 text-gray-400 hover:text-gray-500 dark:hover:text-gray-300 disabled:opacity-50"
                                                            aria-label="Remove file"
                                                        >
                                                            <XMarkIcon className="h-5 w-5" />
                                                        </button>
                                                    </div>
                                                ) : (
                                                    <div
                                                        onClick={handleDropZoneClick}
                                                        onDragOver={handleDragOver}
                                                        onDragLeave={handleDragLeave}
                                                        onDrop={handleDrop}
                                                        className={`relative border-2 border-dashed rounded-lg p-4 text-center cursor-pointer transition-colors ${isDragging
                                                                ? "border-blue-500 bg-blue-50 dark:bg-blue-900/30"
                                                                : "border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 hover:border-gray-400 dark:hover:border-gray-500"
                                                            }`}
                                                    >
                                                        <p className="text-sm text-gray-600 dark:text-gray-300">
                                                            Click to upload or drag and drop
                                                        </p>
                                                        <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                                                            PNG, JPG, TXT, MD, JSON, WAV, MP3 (max 100MB)
                                                        </p>
                                                    </div>
                                                )}
                                                <input
                                                    ref={fileInputRef}
                                                    type="file"
                                                    accept={acceptedExtensions}
                                                    onChange={handleFileChange}
                                                    disabled={uploading}
                                                    className="hidden"
                                                />

                                                {error && (
                                                    <Alert
                                                        variant="error"
                                                        title="Error"
                                                        onDismiss={() => setError(null)}
                                                    >
                                                        {error}
                                                    </Alert>
                                                )}

                                            </div>
                                        </div>
                                </div>
                                <div className="mt-5 sm:mt-6 flex justify-end gap-3">
                                    <button
                                        type="button"
                                        className="text-sm font-medium text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 px-3 py-2"
                                        onClick={handleClose}
                                        disabled={uploading}
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        type="button"
                                        className="w-28 inline-flex justify-center items-center gap-2 rounded-md bg-blue-500 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-400 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-500 disabled:bg-gray-300 dark:disabled:bg-gray-600"
                                        onClick={handleUpload}
                                        disabled={!selectedFile || uploading}
                                    >
                                        {uploading ? (
                                            <>
                                                <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                                </svg>
                                                Uploading
                                            </>
                                        ) : (
                                            "Upload"
                                        )}
                                    </button>
                                </div>
                            </DialogPanel>
                        </TransitionChild>
                    </div>
                </div>
            </Dialog>
        </Transition>
    );
}

FileUploadDialog.propTypes = {
    open: PropTypes.bool.isRequired,
    setOpen: PropTypes.func.isRequired,
    currentPath: PropTypes.string,
    profile: PropTypes.object,
    onSuccess: PropTypes.func.isRequired,
    onError: PropTypes.func.isRequired,
    setOperationInProgress: PropTypes.func.isRequired,
};

export default FileUploadDialog;
