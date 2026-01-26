
import { Fragment, useState, useRef } from "react";
import {
    Dialog,
    DialogPanel,
    DialogTitle,
    Transition,
    TransitionChild,
} from "@headlessui/react";
import {
    ArrowUpTrayIcon,
    XMarkIcon,
    ExclamationCircleIcon,
    ArrowPathIcon,
} from "@heroicons/react/24/outline";
import { uploadFile, validateFileForUpload, getFileType, FILE_TYPE_CONFIG } from "@/lib/fileApi";
import { fileSize } from "@/lib/util";
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

    const fileType = selectedFile ? getFileType(selectedFile.name) : null;
    const destinationPath = selectedFile
        ? joinPath(currentPath, selectedFile.name)
        : "";

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
                            <DialogPanel className="relative transform overflow-hidden rounded-lg bg-white px-4 pb-4 pt-5 text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-lg sm:p-6">
                                <div>
                                    <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-blue-100">
                                        <ArrowUpTrayIcon
                                            className="h-6 w-6 text-blue-600"
                                            aria-hidden="true"
                                        />
                                    </div>
                                    <div className="mt-3 text-center sm:mt-5">
                                        <DialogTitle
                                            as="h3"
                                            className="text-base font-semibold leading-6 text-gray-900"
                                        >
                                            Upload File
                                        </DialogTitle>
                                        <div className="mt-4">
                                            <div className="space-y-4">
                                                <div>
                                                    <label className="block text-sm font-medium text-gray-700 text-left mb-2">
                                                        Select File
                                                    </label>
                                                    <div
                                                        onClick={handleDropZoneClick}
                                                        onDragOver={handleDragOver}
                                                        onDragLeave={handleDragLeave}
                                                        onDrop={handleDrop}
                                                        className={`relative border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors ${isDragging
                                                                ? "border-blue-500 bg-blue-50"
                                                                : "border-gray-300 bg-gray-50 hover:border-gray-400"
                                                            } ${uploading ? "opacity-50 cursor-not-allowed" : ""}`}
                                                    >
                                                        <ArrowUpTrayIcon className="mx-auto h-12 w-12 text-gray-400" />
                                                        <p className="mt-2 text-sm text-gray-600">
                                                            <span className="font-semibold text-blue-600">
                                                                Click to upload
                                                            </span>{" "}
                                                            or drag and drop
                                                        </p>
                                                        <p className="mt-1 text-xs text-gray-500">
                                                            PNG, JPG, TXT, MD, JSON, WAV, MP3 (max 100MB)
                                                        </p>
                                                        <input
                                                            ref={fileInputRef}
                                                            type="file"
                                                            accept={acceptedExtensions}
                                                            onChange={handleFileChange}
                                                            disabled={uploading}
                                                            className="hidden"
                                                        />
                                                    </div>
                                                </div>

                                                {selectedFile && (
                                                    <div className="bg-gray-50 rounded-lg p-3 text-left">
                                                        <div className="text-sm space-y-1">
                                                            <div className="flex justify-between">
                                                                <span className="font-medium text-gray-700">
                                                                    Name:
                                                                </span>
                                                                <span className="text-gray-900">
                                                                    {selectedFile.name}
                                                                </span>
                                                            </div>
                                                            <div className="flex justify-between">
                                                                <span className="font-medium text-gray-700">
                                                                    Size:
                                                                </span>
                                                                <span className="text-gray-900">
                                                                    {fileSize(selectedFile.size)}
                                                                </span>
                                                            </div>
                                                            <div className="flex justify-between">
                                                                <span className="font-medium text-gray-700">
                                                                    Type:
                                                                </span>
                                                                <span className="text-gray-900">
                                                                    {fileType
                                                                        ? fileType.charAt(0).toUpperCase() +
                                                                        fileType.slice(1)
                                                                        : "-"}
                                                                </span>
                                                            </div>
                                                        </div>
                                                    </div>
                                                )}

                                                {selectedFile && (
                                                    <div>
                                                        <label className="block text-sm font-medium text-gray-700 text-left mb-2">
                                                            Destination Path
                                                        </label>
                                                        <div className="block w-full rounded-md border-0 py-2 px-3 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 bg-gray-50 text-sm">
                                                            {destinationPath}
                                                        </div>
                                                    </div>
                                                )}

                                                {error && (
                                                    <div className="rounded-md bg-red-50 p-4">
                                                        <div className="flex">
                                                            <ExclamationCircleIcon
                                                                className="h-5 w-5 text-red-400"
                                                                aria-hidden="true"
                                                            />
                                                            <div className="ml-3">
                                                                <h3 className="text-sm font-medium text-red-800">
                                                                    Error
                                                                </h3>
                                                                <p className="mt-2 text-sm text-red-700">
                                                                    {error}
                                                                </p>
                                                            </div>
                                                            <button
                                                                onClick={() => setError(null)}
                                                                className="ml-auto"
                                                            >
                                                                <XMarkIcon className="h-5 w-5 text-red-400" />
                                                            </button>
                                                        </div>
                                                    </div>
                                                )}

                                                {uploading && (
                                                    <div className="flex items-center gap-2 justify-center text-blue-600">
                                                        <ArrowPathIcon className="h-5 w-5 animate-spin" />
                                                        <span className="text-sm">Uploading...</span>
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                <div className="mt-5 sm:mt-6 sm:grid sm:grid-flow-row-dense sm:grid-cols-2 sm:gap-3">
                                    <button
                                        type="button"
                                        className="inline-flex w-full justify-center rounded-md bg-blue-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:bg-blue-200 disabled:cursor-not-allowed sm:col-start-2"
                                        onClick={handleUpload}
                                        disabled={!selectedFile || uploading}
                                    >
                                        {uploading ? "Uploading..." : "Upload"}
                                    </button>
                                    <button
                                        type="button"
                                        className="mt-3 inline-flex w-full justify-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 disabled:bg-gray-100 disabled:cursor-not-allowed sm:col-start-1 sm:mt-0"
                                        onClick={handleClose}
                                        disabled={uploading}
                                    >
                                        Cancel
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
