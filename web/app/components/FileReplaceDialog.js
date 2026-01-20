"use client";

import { Fragment, useState, useRef, useEffect } from "react";
import {
    Dialog,
    DialogPanel,
    DialogTitle,
    Transition,
    TransitionChild,
} from "@headlessui/react";
import {
    PencilSquareIcon,
    XMarkIcon,
    ExclamationCircleIcon,
    ArrowPathIcon,
} from "@heroicons/react/24/outline";
import { replaceFile, getFileType } from "@/app/utils/fileApi";
import { fileSize, lastModified } from "@/app/lib/util";
import PropTypes from "prop-types";

function FileReplaceDialog({
    open,
    setOpen,
    fileToReplace,
    profile = null,
    onSuccess,
    onError,
    setOperationInProgress,
}) {
    const [selectedFile, setSelectedFile] = useState(null);
    const [replacing, setReplacing] = useState(false);
    const [error, setError] = useState(null);
    const fileInputRef = useRef(null);

    useEffect(() => {
        if (open && fileToReplace) {
            setSelectedFile(null);
            setError(null);
        }
    }, [open, fileToReplace]);

    const handleClose = () => {
        if (!replacing) {
            setSelectedFile(null);
            setError(null);
            setOpen(false);
        }
    };

    const handleFileChange = (e) => {
        const file = e.target.files?.[0];
        if (file) {
            const originalExt = fileToReplace.name
                .toLowerCase()
                .match(/\.[^.]+$/)?.[0];
            const newFileExt = file.name.toLowerCase().match(/\.[^.]+$/)?.[0];

            if (originalExt !== newFileExt) {
                setError(
                    `File type mismatch: expected ${originalExt}, got ${newFileExt}`
                );
                setSelectedFile(null);
                return;
            }

            setSelectedFile(file);
            setError(null);
        }
    };

    const handleReplace = async () => {
        if (!selectedFile || !fileToReplace) return;

        setReplacing(true);
        setOperationInProgress(true);
        setError(null);

        try {
            const response = await replaceFile(fileToReplace.path, selectedFile, profile);
            onSuccess(`Replaced ${response.filename}`);
            handleClose();
        } catch (err) {
            setError(err.message);
            onError(err.message);
        } finally {
            setReplacing(false);
            setOperationInProgress(false);
        }
    };

    if (!fileToReplace) return null;

    const fileType = getFileType(fileToReplace.name);
    const fileExt = fileToReplace.name.toLowerCase().match(/\.[^.]+$/)?.[0];
    const acceptPattern = fileExt || "*";

    const sizeDiff =
        selectedFile && fileToReplace
            ? selectedFile.size - fileToReplace.size
            : 0;

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
                                        <PencilSquareIcon
                                            className="h-6 w-6 text-blue-600"
                                            aria-hidden="true"
                                        />
                                    </div>
                                    <div className="mt-3 text-center sm:mt-5">
                                        <DialogTitle
                                            as="h3"
                                            className="text-base font-semibold leading-6 text-gray-900"
                                        >
                                            Replace File
                                        </DialogTitle>
                                        <div className="mt-4">
                                            <div className="space-y-4">
                                                <div className="bg-gray-50 rounded-lg p-3 text-left">
                                                    <h4 className="text-sm font-medium text-gray-700 mb-2">
                                                        Current File
                                                    </h4>
                                                    <div className="text-sm space-y-1">
                                                        <div className="flex justify-between">
                                                            <span className="font-medium text-gray-600">
                                                                Name:
                                                            </span>
                                                            <span className="text-gray-900">
                                                                {fileToReplace.name}
                                                            </span>
                                                        </div>
                                                        <div className="flex justify-between">
                                                            <span className="font-medium text-gray-600">
                                                                Size:
                                                            </span>
                                                            <span className="text-gray-900">
                                                                {fileSize(fileToReplace.size)}
                                                            </span>
                                                        </div>
                                                        <div className="flex justify-between">
                                                            <span className="font-medium text-gray-600">
                                                                Last Modified:
                                                            </span>
                                                            <span className="text-gray-900">
                                                                {lastModified(fileToReplace.modified_at)}
                                                            </span>
                                                        </div>
                                                        <div className="flex justify-between">
                                                            <span className="font-medium text-gray-600">
                                                                Type:
                                                            </span>
                                                            <span className="text-gray-900">
                                                                {fileType
                                                                    ? fileType.charAt(0).toUpperCase() +
                                                                    fileType.slice(1)
                                                                    : "Unknown"}
                                                            </span>
                                                        </div>
                                                    </div>
                                                </div>

                                                <div>
                                                    <label className="block text-sm font-medium text-gray-700 text-left mb-2">
                                                        Select Replacement File (must be {fileExt})
                                                    </label>
                                                    <input
                                                        ref={fileInputRef}
                                                        type="file"
                                                        accept={acceptPattern}
                                                        onChange={handleFileChange}
                                                        disabled={replacing}
                                                        className="block w-full text-sm text-gray-900 border border-gray-300 rounded-lg cursor-pointer bg-gray-50 focus:outline-none disabled:bg-gray-100 disabled:cursor-not-allowed"
                                                    />
                                                </div>

                                                {selectedFile && (
                                                    <div className="bg-blue-50 rounded-lg p-3 text-left">
                                                        <h4 className="text-sm font-medium text-blue-700 mb-2">
                                                            New File
                                                        </h4>
                                                        <div className="text-sm space-y-1">
                                                            <div className="flex justify-between">
                                                                <span className="font-medium text-blue-600">
                                                                    Name:
                                                                </span>
                                                                <span className="text-gray-900">
                                                                    {selectedFile.name}
                                                                </span>
                                                            </div>
                                                            <div className="flex justify-between">
                                                                <span className="font-medium text-blue-600">
                                                                    Size:
                                                                </span>
                                                                <span className="text-gray-900">
                                                                    {fileSize(selectedFile.size)}
                                                                    {sizeDiff !== 0 && (
                                                                        <span
                                                                            className={`ml-2 text-xs ${sizeDiff > 0 ? "text-orange-600" : "text-green-600"}`}
                                                                        >
                                                                            ({sizeDiff > 0 ? "+" : ""}
                                                                            {fileSize(Math.abs(sizeDiff))})
                                                                        </span>
                                                                    )}
                                                                </span>
                                                            </div>
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

                                                {replacing && (
                                                    <div className="flex items-center gap-2 justify-center text-blue-600">
                                                        <ArrowPathIcon className="h-5 w-5 animate-spin" />
                                                        <span className="text-sm">Replacing...</span>
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
                                        onClick={handleReplace}
                                        disabled={!selectedFile || replacing}
                                    >
                                        {replacing ? "Replacing..." : "Replace"}
                                    </button>
                                    <button
                                        type="button"
                                        className="mt-3 inline-flex w-full justify-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 disabled:bg-gray-100 disabled:cursor-not-allowed sm:col-start-1 sm:mt-0"
                                        onClick={handleClose}
                                        disabled={replacing}
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

FileReplaceDialog.propTypes = {
    open: PropTypes.bool.isRequired,
    setOpen: PropTypes.func.isRequired,
    fileToReplace: PropTypes.object,
    profile: PropTypes.object,
    onSuccess: PropTypes.func.isRequired,
    onError: PropTypes.func.isRequired,
    setOperationInProgress: PropTypes.func.isRequired,
};

export default FileReplaceDialog;
