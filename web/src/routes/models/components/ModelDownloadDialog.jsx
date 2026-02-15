import { Fragment, useState } from "react";
import {
    Dialog,
    DialogPanel,
    DialogTitle,
    Transition,
    TransitionChild,
} from "@headlessui/react";
import { ArrowDownTrayIcon } from "@heroicons/react/24/outline";
import Alert from "@/components/Alert";
import { downloadModel } from "@/lib/requests";
import PropTypes from "prop-types";

function ModelDownloadDialog({
    open,
    setOpen,
    profile,
    onSuccess,
    onError,
}) {
    const [repoId, setRepoId] = useState("");
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState(null);

    const handleClose = () => {
        if (!submitting) {
            setError(null);
            setRepoId("");
            setOpen(false);
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();

        if (!repoId.trim()) {
            setError("Please enter a model repository ID");
            return;
        }

        if (!profile) {
            setError("No profile selected");
            return;
        }

        setSubmitting(true);
        setError(null);

        try {
            const result = await downloadModel({
                repo_id: repoId.trim(),
                profile: profile.name,
            });
            onSuccess(result);
            handleClose();
        } catch (err) {
            setError(err.message);
            onError(err.message);
        } finally {
            setSubmitting(false);
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
                                <form onSubmit={handleSubmit}>
                                    <div>
                                        <DialogTitle
                                            as="h3"
                                            className="text-base font-semibold leading-6 text-gray-900 dark:text-white"
                                        >
                                            Download Model
                                        </DialogTitle>
                                        <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                                            Enter a Hugging Face model repository ID to download.
                                            The model will be downloaded to your profile&apos;s cache directory.
                                        </p>

                                        <div className="mt-4">
                                            <label
                                                htmlFor="repo-id"
                                                className="block text-sm font-medium text-gray-700 dark:text-gray-300"
                                            >
                                                Model Repository
                                            </label>
                                            <div className="mt-1">
                                                <input
                                                    type="text"
                                                    id="repo-id"
                                                    name="repo-id"
                                                    value={repoId}
                                                    onChange={(e) => setRepoId(e.target.value)}
                                                    placeholder="meta-llama/Llama-2-7b-hf"
                                                    className="block w-full rounded-md border-0 py-1.5 px-3 text-gray-900 dark:text-gray-100 shadow-sm ring-1 ring-inset ring-gray-300 dark:ring-gray-600 placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:ring-2 focus:ring-inset focus:ring-blue-600 dark:focus:ring-blue-500 sm:text-sm sm:leading-6 bg-white dark:bg-gray-700"
                                                    disabled={submitting}
                                                    autoComplete="off"
                                                />
                                            </div>
                                            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                                                e.g., openai/whisper-large-v3, facebook/opt-1.3b
                                            </p>
                                        </div>

                                        {profile && (
                                            <div className="mt-4 rounded-md bg-gray-50 dark:bg-gray-700 px-4 py-3 flex items-center gap-3">
                                                <ArrowDownTrayIcon className="h-5 w-5 text-gray-400 dark:text-gray-500 shrink-0" />
                                                <div className="text-sm">
                                                    <span className="text-gray-500 dark:text-gray-400">Profile: </span>
                                                    <span className="font-medium text-gray-900 dark:text-gray-100">
                                                        {profile.name}
                                                    </span>
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
                                            disabled={submitting}
                                        >
                                            Cancel
                                        </button>
                                        <button
                                            type="submit"
                                            className="w-32 inline-flex justify-center items-center gap-2 rounded-md bg-blue-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:bg-gray-300 dark:disabled:bg-gray-600"
                                            disabled={!repoId.trim() || submitting}
                                        >
                                            {submitting ? (
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
                                                    Starting...
                                                </>
                                            ) : (
                                                "Download"
                                            )}
                                        </button>
                                    </div>
                                </form>
                            </DialogPanel>
                        </TransitionChild>
                    </div>
                </div>
            </Dialog>
        </Transition>
    );
}

ModelDownloadDialog.propTypes = {
    open: PropTypes.bool.isRequired,
    setOpen: PropTypes.func.isRequired,
    profile: PropTypes.object,
    onSuccess: PropTypes.func.isRequired,
    onError: PropTypes.func.isRequired,
};

export default ModelDownloadDialog;
