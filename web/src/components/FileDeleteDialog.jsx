
import { Fragment, useState } from "react";
import {
    Dialog,
    DialogPanel,
    DialogTitle,
    Transition,
    TransitionChild,
} from "@headlessui/react";
import {
    ExclamationTriangleIcon,
    ArrowPathIcon,
} from "@heroicons/react/24/outline";
import Alert from "@/components/Alert";
import { deleteFile } from "@/lib/fileApi";
import { fileSize } from "@/lib/util";
import PropTypes from "prop-types";

function FileDeleteDialog({
    open,
    setOpen,
    fileToDelete,
    profile = null,
    onSuccess,
    onError,
    setOperationInProgress,
}) {
    const [deleting, setDeleting] = useState(false);
    const [error, setError] = useState(null);

    const handleClose = () => {
        if (!deleting) {
            setError(null);
            setOpen(false);
        }
    };

    const handleDelete = async () => {
        if (!fileToDelete) {
            setError("No file selected");
            return;
        }

        setDeleting(true);
        setOperationInProgress(true);
        setError(null);

        try {
            await deleteFile(fileToDelete.path, profile);
            onSuccess(`Deleted ${fileToDelete.name}`);
            handleClose();
        } catch (err) {
            setError(err.message);
            onError(err.message);
        } finally {
            setDeleting(false);
            setOperationInProgress(false);
        }
    };

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
                            <DialogPanel className="relative transform overflow-hidden rounded-lg bg-white dark:bg-gray-800 px-4 pb-4 pt-5 text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-lg sm:p-6">
                                <div>
                                    <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-red-100">
                                        <ExclamationTriangleIcon
                                            className="h-6 w-6 text-red-600"
                                            aria-hidden="true"
                                        />
                                    </div>
                                    <div className="mt-3 text-center sm:mt-5">
                                        <DialogTitle
                                            as="h3"
                                            className="text-base font-semibold leading-6 text-gray-900 dark:text-white"
                                        >
                                            Delete File
                                        </DialogTitle>
                                        <div className="mt-4">
                                            <p className="text-sm text-gray-500 dark:text-gray-400">
                                                Are you sure you want to delete this file? This action cannot be undone.
                                            </p>

                                            {fileToDelete && (
                                                <div className="mt-4 bg-gray-50 dark:bg-gray-700 rounded-lg p-3 text-left">
                                                    <div className="text-sm space-y-1">
                                                        <div className="flex justify-between">
                                                            <span className="font-medium text-gray-700 dark:text-gray-300">
                                                                Name:
                                                            </span>
                                                            <span className="text-gray-900 dark:text-gray-100">
                                                                {fileToDelete.name}
                                                            </span>
                                                        </div>
                                                        <div className="flex justify-between">
                                                            <span className="font-medium text-gray-700 dark:text-gray-300">
                                                                Size:
                                                            </span>
                                                            <span className="text-gray-900 dark:text-gray-100">
                                                                {fileSize(fileToDelete.size)}
                                                            </span>
                                                        </div>
                                                        <div className="flex justify-between">
                                                            <span className="font-medium text-gray-700 dark:text-gray-300">
                                                                Path:
                                                            </span>
                                                            <span className="text-gray-900 dark:text-gray-100 text-right break-all">
                                                                {fileToDelete.path}
                                                            </span>
                                                        </div>
                                                    </div>
                                                </div>
                                            )}

                                            {error && (
                                                <Alert
                                                    variant="error"
                                                    title="Error"
                                                    onDismiss={() => setError(null)}
                                                    className="mt-4"
                                                >
                                                    {error}
                                                </Alert>
                                            )}

                                            {deleting && (
                                                <div className="mt-4 flex items-center gap-2 justify-center text-red-600">
                                                    <ArrowPathIcon className="h-5 w-5 animate-spin" />
                                                    <span className="text-sm">Deleting...</span>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                </div>
                                <div className="mt-5 sm:mt-6 sm:grid sm:grid-flow-row-dense sm:grid-cols-2 sm:gap-3">
                                    <button
                                        type="button"
                                        className="inline-flex w-full justify-center rounded-md bg-red-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-red-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-600 disabled:bg-red-200 disabled:cursor-not-allowed sm:col-start-2"
                                        onClick={handleDelete}
                                        disabled={!fileToDelete || deleting}
                                    >
                                        {deleting ? "Deleting..." : "Delete"}
                                    </button>
                                    <button
                                        type="button"
                                        className="mt-3 inline-flex w-full justify-center rounded-md bg-white dark:bg-gray-700 px-3 py-2 text-sm font-semibold text-gray-900 dark:text-gray-100 shadow-sm ring-1 ring-inset ring-gray-300 dark:ring-gray-600 hover:bg-gray-50 dark:hover:bg-gray-600 disabled:bg-gray-100 dark:disabled:bg-gray-800 disabled:cursor-not-allowed sm:col-start-1 sm:mt-0"
                                        onClick={handleClose}
                                        disabled={deleting}
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

FileDeleteDialog.propTypes = {
    open: PropTypes.bool.isRequired,
    setOpen: PropTypes.func.isRequired,
    fileToDelete: PropTypes.object,
    profile: PropTypes.object,
    onSuccess: PropTypes.func.isRequired,
    onError: PropTypes.func.isRequired,
    setOperationInProgress: PropTypes.func.isRequired,
};

export default FileDeleteDialog;
