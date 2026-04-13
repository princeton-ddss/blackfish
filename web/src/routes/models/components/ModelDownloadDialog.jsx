import { Fragment, useState, useEffect, useCallback } from "react";

// Search configuration
const MIN_SEARCH_LENGTH = 2;
const SEARCH_DEBOUNCE_MS = 300;
const REFS_DEBOUNCE_MS = 500;
import {
    Dialog,
    DialogPanel,
    DialogTitle,
    Transition,
    TransitionChild,
    Combobox,
    ComboboxInput,
    ComboboxOptions,
    ComboboxOption,
    Listbox,
    ListboxButton,
    ListboxOptions,
    ListboxOption,
} from "@headlessui/react";
import { ArrowPathIcon, ExclamationTriangleIcon, MagnifyingGlassIcon } from "@heroicons/react/24/outline";
import { CheckIcon, ChevronUpDownIcon } from "@heroicons/react/20/solid";
import Alert from "@/components/Alert";
import { downloadModel, fetchModelRefs, searchHuggingFaceModels } from "@/lib/requests";
import PropTypes from "prop-types";

function ModelDownloadDialog({
    open,
    setOpen,
    profile,
    onSuccess,
    onError,
}) {
    const [repoId, setRepoId] = useState("");
    const [searchQuery, setSearchQuery] = useState("");
    const [searchResults, setSearchResults] = useState([]);
    const [searchLoading, setSearchLoading] = useState(false);
    const [revision, setRevision] = useState("");
    const [customRevision, setCustomRevision] = useState("");
    const [useCustomRevision, setUseCustomRevision] = useState(false);
    const [revisions, setRevisions] = useState({ branches: [], tags: [] });
    const [loadingRefs, setLoadingRefs] = useState(false);
    const [refsError, setRefsError] = useState(null);
    const [useCache, setUseCache] = useState(false);
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState(null);

    // Debounced search for models
    useEffect(() => {
        const query = searchQuery.trim();

        if (!query || query.length < MIN_SEARCH_LENGTH) {
            setSearchResults([]);
            return;
        }

        const timeoutId = setTimeout(async () => {
            setSearchLoading(true);
            const results = await searchHuggingFaceModels(query);
            setSearchResults(results);
            setSearchLoading(false);
        }, SEARCH_DEBOUNCE_MS);

        return () => clearTimeout(timeoutId);
    }, [searchQuery]);

    // Debounced fetch of revisions when repo_id changes
    useEffect(() => {
        const trimmedRepoId = repoId.trim();

        // Reset state when repo_id is cleared or invalid
        if (!trimmedRepoId || !trimmedRepoId.includes("/")) {
            setRevisions({ branches: [], tags: [] });
            setRevision("");
            setRefsError(null);
            return;
        }

        // Debounce the API call
        const timeoutId = setTimeout(async () => {
            setLoadingRefs(true);
            setRefsError(null);

            const result = await fetchModelRefs(trimmedRepoId);

            if (result?.error) {
                setRefsError(result.error);
                setRevisions({ branches: [], tags: [] });
                setRevision("");
            } else if (result) {
                setRevisions(result);
                setRefsError(null);
                // Auto-select "main" if available
                const mainBranch = result.branches?.find(b => b.name === "main");
                if (mainBranch) {
                    setRevision(mainBranch.sha);
                } else if (result.branches?.length > 0) {
                    setRevision(result.branches[0].sha);
                } else if (result.tags?.length > 0) {
                    setRevision(result.tags[0].sha);
                } else {
                    setRevision("");
                }
            }

            setLoadingRefs(false);
        }, REFS_DEBOUNCE_MS);

        return () => clearTimeout(timeoutId);
    }, [repoId]);

    const handleClose = useCallback(() => {
        if (!submitting) {
            setError(null);
            setRepoId("");
            setSearchQuery("");
            setSearchResults([]);
            setRevision("");
            setCustomRevision("");
            setUseCustomRevision(false);
            setRevisions({ branches: [], tags: [] });
            setRefsError(null);
            setUseCache(false);
            setOpen(false);
        }
    }, [submitting, setOpen]);

    const handleSubmit = async (e) => {
        e.preventDefault();

        const modelId = (repoId || searchQuery).trim();
        if (!modelId) {
            setError("Please enter a model repository ID");
            return;
        }

        if (!profile) {
            setError("No profile selected");
            return;
        }

        setSubmitting(true);
        setError(null);

        const selectedRevision = useCustomRevision ? customRevision.trim() : revision;

        try {
            const result = await downloadModel({
                repo_id: modelId,
                profile: profile.name,
                revision: selectedRevision || null,
                use_cache: useCache,
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

    const hasRevisions = revisions.branches.length > 0 || revisions.tags.length > 0;
    const inputValue = repoId || searchQuery;
    const validRepoId = inputValue.trim() && inputValue.includes("/");

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
                                        </p>

                                        <div className="mt-4">
                                            <label
                                                htmlFor="repo-id"
                                                className="block text-sm font-medium text-gray-700 dark:text-gray-300"
                                            >
                                                Model
                                                {searchLoading && (
                                                    <ArrowPathIcon className="inline-block ml-2 h-3.5 w-3.5 animate-spin text-gray-400" />
                                                )}
                                            </label>
                                            <Combobox
                                                value={inputValue}
                                                onChange={(value) => {
                                                    if (value) {
                                                        setRepoId(value);
                                                        setSearchResults([]);
                                                    }
                                                }}
                                                disabled={submitting}
                                                immediate
                                            >
                                                <div className="relative mt-1">
                                                    <div className="relative">
                                                        <MagnifyingGlassIcon className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                                                        <ComboboxInput
                                                            id="repo-id"
                                                            className="block w-full rounded-md border-0 py-1.5 pl-9 pr-3 text-gray-900 dark:text-gray-100 shadow-sm ring-1 ring-inset ring-gray-300 dark:ring-gray-600 placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:ring-2 focus:ring-inset focus:ring-blue-600 dark:focus:ring-blue-500 sm:text-sm sm:leading-6 bg-white dark:bg-gray-700"
                                                            placeholder="Search models..."
                                                            onChange={(e) => {
                                                                setRepoId("");
                                                                setSearchQuery(e.target.value);
                                                            }}
                                                            autoComplete="off"
                                                        />
                                                    </div>
                                                    {searchResults.length > 0 && (
                                                        <ComboboxOptions
                                                            static
                                                            className="absolute z-[100] w-full mt-1 max-h-60 overflow-auto rounded-md bg-white dark:bg-gray-700 py-1 text-base shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none sm:text-sm"
                                                        >
                                                            {searchResults.map((model) => (
                                                                <ComboboxOption
                                                                    key={model.id}
                                                                    value={model.id}
                                                                    className="group relative cursor-pointer select-none py-2 px-3 text-gray-900 dark:text-gray-100 data-[focus]:bg-blue-600 data-[focus]:text-white"
                                                                >
                                                                    <div className="flex items-center justify-between">
                                                                        <span className="truncate font-medium">
                                                                            {model.id}
                                                                        </span>
                                                                        <span className="ml-2 text-xs text-gray-500 dark:text-gray-400 group-data-[focus]:text-blue-100 flex-shrink-0">
                                                                            {model.downloads?.toLocaleString()} ↓
                                                                        </span>
                                                                    </div>
                                                                    {model.pipeline && (
                                                                        <span className="text-xs text-gray-500 dark:text-gray-400 group-data-[focus]:text-blue-200">
                                                                            {model.pipeline}
                                                                        </span>
                                                                    )}
                                                                </ComboboxOption>
                                                            ))}
                                                        </ComboboxOptions>
                                                    )}
                                                </div>
                                            </Combobox>
                                            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                                                Search or enter a model ID (e.g., openai/whisper-large-v3)
                                            </p>
                                        </div>

                                        {/* Revision selector */}
                                        <div className="mt-4">
                                            <div className="flex items-center justify-between">
                                                <label
                                                    htmlFor="revision"
                                                    className={`block text-sm font-medium ${
                                                        validRepoId
                                                            ? "text-gray-700 dark:text-gray-300"
                                                            : "text-gray-400 dark:text-gray-500"
                                                    }`}
                                                >
                                                    Revision
                                                    {loadingRefs && (
                                                        <ArrowPathIcon className="inline-block ml-2 h-3.5 w-3.5 animate-spin text-gray-400" />
                                                    )}
                                                </label>
                                                {validRepoId && hasRevisions && !refsError && (
                                                    <button
                                                        type="button"
                                                        onClick={() => setUseCustomRevision(!useCustomRevision)}
                                                        className="text-xs text-blue-500 dark:text-blue-400 hover:underline"
                                                    >
                                                        {useCustomRevision ? "Select from list" : "Enter custom SHA"}
                                                    </button>
                                                )}
                                            </div>
                                            <div className="mt-1">
                                                {!validRepoId ? (
                                                    <div className="relative w-full rounded-md bg-gray-100 dark:bg-gray-700/50 py-1.5 pl-3 pr-10 text-left text-gray-400 dark:text-gray-500 shadow-sm ring-1 ring-inset ring-gray-200 dark:ring-gray-600 sm:text-sm sm:leading-6 cursor-not-allowed">
                                                        <span className="block truncate">main</span>
                                                        <span className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2">
                                                            <ChevronUpDownIcon className="h-5 w-5 text-gray-300 dark:text-gray-600" aria-hidden="true" />
                                                        </span>
                                                    </div>
                                                ) : refsError ? (
                                                    <div className="flex items-center gap-2 text-sm text-amber-600 dark:text-amber-400 py-1.5">
                                                        <ExclamationTriangleIcon className="h-4 w-4 flex-shrink-0" />
                                                        <span>{refsError}</span>
                                                    </div>
                                                ) : loadingRefs ? (
                                                    <p className="text-sm text-gray-400 dark:text-gray-500 py-1.5">
                                                        Loading revisions...
                                                    </p>
                                                ) : useCustomRevision ? (
                                                    <input
                                                        type="text"
                                                        id="custom-revision"
                                                        value={customRevision}
                                                        onChange={(e) => setCustomRevision(e.target.value)}
                                                        placeholder="e.g., a1b2c3d4e5f6..."
                                                        className="block w-full rounded-md border-0 py-1.5 px-3 text-gray-900 dark:text-gray-100 shadow-sm ring-1 ring-inset ring-gray-300 dark:ring-gray-600 placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:ring-2 focus:ring-inset focus:ring-blue-500 dark:focus:ring-blue-500 sm:text-sm sm:leading-6 bg-white dark:bg-gray-700 font-mono"
                                                        disabled={submitting}
                                                    />
                                                ) : hasRevisions ? (
                                                    <Listbox value={revision} onChange={setRevision} disabled={submitting}>
                                                        <div className="relative">
                                                            <ListboxButton className="relative w-full cursor-default rounded-md bg-white dark:bg-gray-700 py-1.5 pl-3 pr-10 text-left text-gray-900 dark:text-gray-100 shadow-sm ring-1 ring-inset ring-gray-300 dark:ring-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500 sm:text-sm sm:leading-6">
                                                                <span className="block truncate">
                                                                    {(() => {
                                                                        const branch = revisions.branches.find(b => b.sha === revision);
                                                                        const tag = revisions.tags.find(t => t.sha === revision);
                                                                        if (branch) return `${branch.name} (${branch.sha.slice(0, 7)})`;
                                                                        if (tag) return `${tag.name} (${tag.sha.slice(0, 7)})`;
                                                                        return "Select revision";
                                                                    })()}
                                                                </span>
                                                                <span className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2">
                                                                    <ChevronUpDownIcon className="h-5 w-5 text-gray-400" aria-hidden="true" />
                                                                </span>
                                                            </ListboxButton>
                                                            <ListboxOptions className="absolute z-[100] mt-1 max-h-60 w-full overflow-auto rounded-md bg-white dark:bg-gray-700 py-1 text-base shadow-lg ring-1 ring-black ring-opacity-5 dark:ring-gray-600 focus:outline-none sm:text-sm">
                                                                {revisions.branches.length > 0 && (
                                                                    <>
                                                                        <div className="px-3 py-1 text-xs font-semibold text-gray-500 dark:text-gray-400">
                                                                            Branches
                                                                        </div>
                                                                        {revisions.branches.map((branch) => (
                                                                            <ListboxOption
                                                                                key={`branch-${branch.sha}`}
                                                                                value={branch.sha}
                                                                                className="group relative cursor-default select-none py-2 pl-3 pr-9 text-gray-900 dark:text-gray-100 data-[focus]:bg-blue-500 data-[focus]:text-white"
                                                                            >
                                                                                <span className="block truncate font-normal group-data-[selected]:font-semibold">
                                                                                    {branch.name} ({branch.sha.slice(0, 7)})
                                                                                </span>
                                                                                <span className="absolute inset-y-0 right-0 flex items-center pr-4 text-blue-600 group-data-[focus]:text-white [.group:not([data-selected])_&]:hidden">
                                                                                    <CheckIcon className="h-5 w-5" aria-hidden="true" />
                                                                                </span>
                                                                            </ListboxOption>
                                                                        ))}
                                                                    </>
                                                                )}
                                                                {revisions.tags.length > 0 && (
                                                                    <>
                                                                        <div className="px-3 py-1 text-xs font-semibold text-gray-500 dark:text-gray-400">
                                                                            Tags
                                                                        </div>
                                                                        {revisions.tags.map((tag) => (
                                                                            <ListboxOption
                                                                                key={`tag-${tag.sha}`}
                                                                                value={tag.sha}
                                                                                className="group relative cursor-default select-none py-2 pl-3 pr-9 text-gray-900 dark:text-gray-100 data-[focus]:bg-blue-500 data-[focus]:text-white"
                                                                            >
                                                                                <span className="block truncate font-normal group-data-[selected]:font-semibold">
                                                                                    {tag.name} ({tag.sha.slice(0, 7)})
                                                                                </span>
                                                                                <span className="absolute inset-y-0 right-0 flex items-center pr-4 text-blue-600 group-data-[focus]:text-white [.group:not([data-selected])_&]:hidden">
                                                                                    <CheckIcon className="h-5 w-5" aria-hidden="true" />
                                                                                </span>
                                                                            </ListboxOption>
                                                                        ))}
                                                                    </>
                                                                )}
                                                            </ListboxOptions>
                                                        </div>
                                                    </Listbox>
                                                ) : (
                                                    <p className="text-sm text-gray-400 dark:text-gray-500 py-1.5">
                                                        No revisions found
                                                    </p>
                                                )}
                                            </div>
                                        </div>

                                        {/* Save location toggle */}
                                        <div className="mt-4">
                                            <div className="flex items-center gap-3">
                                                <button
                                                    type="button"
                                                    role="switch"
                                                    aria-checked={useCache}
                                                    onClick={() => setUseCache(!useCache)}
                                                    disabled={submitting}
                                                    className={`relative inline-flex h-6 w-11 shrink-0 rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed ${
                                                        useCache
                                                            ? "bg-blue-500"
                                                            : "bg-gray-200 dark:bg-gray-600"
                                                    }`}
                                                >
                                                    <span
                                                        className={`pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow ring-0 transition-transform duration-200 ease-in-out ${
                                                            useCache ? "translate-x-5" : "translate-x-0"
                                                        }`}
                                                    />
                                                </button>
                                                <span className="text-sm text-gray-700 dark:text-gray-300">
                                                    Use cache directory
                                                </span>
                                            </div>
                                            <p className="mt-2 ml-14 text-xs text-gray-500 dark:text-gray-400">
                                                Model will be saved to{" "}
                                                <code className="font-mono text-gray-600 dark:text-gray-300">
                                                    {useCache
                                                        ? profile?.cache_dir || "~/.cache/huggingface/hub"
                                                        : profile?.home_dir || "~"}
                                                </code>
                                            </p>
                                        </div>

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
                                            disabled={!inputValue.trim() || submitting}
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
