import { Fragment, useState } from "react";
import {
    Dialog,
    DialogPanel,
    DialogTitle,
    Transition,
    TransitionChild,
} from "@headlessui/react";
import { CubeIcon } from "@heroicons/react/24/outline";
import Alert from "@/components/Alert";
import { deleteModel } from "@/lib/requests";
import PropTypes from "prop-types";

function LocationBadge({ path, cacheDir, homeDir }) {
    if (!path) {
        return <span className="text-gray-500 dark:text-gray-400">-</span>;
    }

    const isCache = cacheDir && path.startsWith(cacheDir);
    const isHome = homeDir && path.startsWith(homeDir);

    if (!isCache && !isHome) {
        return (
            <span className="inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium ring-1 ring-inset bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-300 ring-red-600/20">
                unknown
            </span>
        );
    }

    const label = isCache ? "cache" : "home";

    return (
        <span
            className="inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium ring-1 ring-inset bg-gray-50 dark:bg-gray-700 text-gray-600 dark:text-gray-400 ring-gray-500/10 dark:ring-gray-600"
            title={path}
        >
            {label}
        </span>
    );
}

LocationBadge.propTypes = {
    path: PropTypes.string,
    cacheDir: PropTypes.string,
    homeDir: PropTypes.string,
};

function ModelDeleteDialog({
    open,
    setOpen,
    modelToDelete,
    cacheDir,
    homeDir,
    onSuccess,
    onError,
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
        if (!modelToDelete?.id) {
            setError("No model selected");
            return;
        }

        setDeleting(true);
        setError(null);

        try {
            await deleteModel(modelToDelete.id);
            onSuccess(`Deleted ${modelToDelete.repo_id}`);
            handleClose();
        } catch (err) {
            setError(err.message);
            onError(err.message);
        } finally {
            setDeleting(false);
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
                            <DialogPanel className="relative transform overflow-hidden rounded-lg bg-white dark:bg-gray-800 p-4 text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-lg">
                                <div>
                                    <DialogTitle
                                        as="h3"
                                        className="text-base font-semibold leading-6 text-gray-900 dark:text-white"
                                    >
                                        Delete Model
                                    </DialogTitle>
                                    <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                                        Are you sure you want to delete this model? This action cannot be undone.
                                    </p>

                                    {modelToDelete && (
                                        <div className="mt-4 rounded-md bg-gray-50 dark:bg-gray-700 px-4 py-3 sm:flex sm:items-start">
                                            <CubeIcon className="h-8 w-8 text-gray-400 dark:text-gray-500 sm:h-6 sm:shrink-0" />
                                            <div className="mt-2 sm:mt-0 sm:ml-3 min-w-0">
                                                <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                                                    {modelToDelete.repo_id}
                                                </div>
                                                <div className="mt-1 text-sm text-gray-500 dark:text-gray-400 flex items-center gap-2">
                                                    <span className="font-mono text-xs">
                                                        {modelToDelete.revision?.slice(0, 7)}
                                                    </span>
                                                    {modelToDelete.model_size_gb && (
                                                        <>
                                                            <span>&middot;</span>
                                                            <span className="text-xs">
                                                                {modelToDelete.model_size_gb >= 1
                                                                    ? `${modelToDelete.model_size_gb.toFixed(1)} GB`
                                                                    : `${(modelToDelete.model_size_gb * 1024).toFixed(0)} MB`}
                                                            </span>
                                                        </>
                                                    )}
                                                    <span>&middot;</span>
                                                    <LocationBadge
                                                        path={modelToDelete.model_dir}
                                                        cacheDir={cacheDir}
                                                        homeDir={homeDir}
                                                    />
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
                                </div>
                                <div className="mt-5 sm:mt-6 flex justify-end gap-3">
                                    <button
                                        type="button"
                                        className="text-sm font-medium text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 px-3 py-2"
                                        onClick={handleClose}
                                        disabled={deleting}
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        type="button"
                                        className="w-28 inline-flex justify-center items-center gap-2 rounded-md bg-red-500 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-red-400 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-500 disabled:bg-gray-300 dark:disabled:bg-gray-600"
                                        onClick={handleDelete}
                                        disabled={!modelToDelete || deleting}
                                    >
                                        {deleting ? (
                                            <>
                                                <svg
                                                    className="animate-spin h-4 w-4"
                                                    xmlns="http://www.w3.org/2000/svg"
                                                    fill="none"
                                                    viewBox="0 0 24 24"
                                                >
                                                    <circle
                                                        className="opacity-25"
                                                        cx="12"
                                                        cy="12"
                                                        r="10"
                                                        stroke="currentColor"
                                                        strokeWidth="4"
                                                    ></circle>
                                                    <path
                                                        className="opacity-75"
                                                        fill="currentColor"
                                                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                                                    ></path>
                                                </svg>
                                                Deleting
                                            </>
                                        ) : (
                                            "Delete"
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

ModelDeleteDialog.propTypes = {
    open: PropTypes.bool.isRequired,
    setOpen: PropTypes.func.isRequired,
    modelToDelete: PropTypes.object,
    cacheDir: PropTypes.string,
    homeDir: PropTypes.string,
    onSuccess: PropTypes.func.isRequired,
    onError: PropTypes.func.isRequired,
};

export default ModelDeleteDialog;
