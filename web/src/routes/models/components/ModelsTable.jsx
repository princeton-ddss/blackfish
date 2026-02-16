import { useState, useEffect, useMemo } from "react";
import {
    Menu,
    MenuButton,
    MenuItem,
    MenuItems,
} from "@headlessui/react";
import {
    ArrowPathIcon,
    TrashIcon,
    ClipboardDocumentIcon,
    CheckIcon,
    MagnifyingGlassIcon,
    ArrowTopRightOnSquareIcon,
    ChevronDownIcon,
    ChevronRightIcon,
    PlusIcon,
    XMarkIcon,
} from "@heroicons/react/24/outline";
import { ArrowDownCircleIcon, ExclamationCircleIcon as ExclamationCircleIconSolid } from "@heroicons/react/24/solid";
import { lastModified } from "@/lib/util";
import PropTypes from "prop-types";

/**
 * Format size in GB to human-readable form
 */
function formatSizeGB(sizeGB) {
    if (sizeGB == null) return null;
    if (sizeGB >= 1000) {
        return `${(sizeGB / 1000).toFixed(1)} TB`;
    }
    if (sizeGB >= 10) {
        return `${sizeGB.toFixed(0)} GB`;
    }
    return `${sizeGB.toFixed(1)} GB`;
}

/**
 * Format parameter count to human-readable form (e.g., "7B", "405M")
 */
function formatParameters(count) {
    if (count == null) return null;
    const billions = count / 1_000_000_000;
    if (billions >= 1) {
        return `${billions.toFixed(billions >= 10 ? 0 : 1)}B`;
    }
    const millions = count / 1_000_000;
    return `${millions.toFixed(0)}M`;
}

function CopyButton({ text }) {
    const [copied, setCopied] = useState(false);

    const handleCopy = () => {
        navigator.clipboard
            .writeText(text)
            .then(() => {
                setCopied(true);
                setTimeout(() => setCopied(false), 2000);
            })
            .catch((err) => {
                console.error("Failed to copy:", err);
            });
    };

    return (
        <button
            onClick={handleCopy}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            title={copied ? "Copied!" : "Copy"}
        >
            {copied ? (
                <CheckIcon className="h-3.5 w-3.5" />
            ) : (
                <ClipboardDocumentIcon className="h-3.5 w-3.5" />
            )}
        </button>
    );
}

CopyButton.propTypes = {
    text: PropTypes.string.isRequired,
};

function TaskBadge({ task }) {
    if (!task) {
        return <span className="text-sm text-gray-500 dark:text-gray-400">-</span>;
    }
    return (
        <span className="inline-flex items-center rounded-md bg-gray-50 dark:bg-gray-700 px-2 py-1 text-xs font-medium text-gray-600 dark:text-gray-400 ring-1 ring-inset ring-gray-500/10 dark:ring-gray-600">
            {task.replace(/_/g, "-")}
        </span>
    );
}

TaskBadge.propTypes = {
    task: PropTypes.string,
};

function LocationBadge({ path, cacheDir, homeDir }) {
    const [copied, setCopied] = useState(false);

    if (!path) {
        return <span className="text-gray-500 dark:text-gray-400">-</span>;
    }

    // Determine location type by comparing with profile directories
    const isCache = cacheDir && path.startsWith(cacheDir);
    const isHome = homeDir && path.startsWith(homeDir);

    if (!isCache && !isHome) {
        // Path doesn't match either directory - error state
        return (
            <span
                className="inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium ring-1 ring-inset bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-300 ring-red-600/20"
                title={`Unknown location: ${path}`}
            >
                error
            </span>
        );
    }

    const label = isCache ? "cache" : "home";

    const handleCopy = (e) => {
        e.stopPropagation();
        navigator.clipboard
            .writeText(path)
            .then(() => {
                setCopied(true);
                setTimeout(() => setCopied(false), 2000);
            })
            .catch((err) => {
                console.error("Failed to copy path:", err);
            });
    };

    return (
        <button
            onClick={handleCopy}
            className="inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-medium ring-1 ring-inset bg-gray-50 dark:bg-gray-700 text-gray-600 dark:text-gray-400 ring-gray-500/10 dark:ring-gray-600 hover:bg-gray-100 dark:hover:bg-gray-600"
            title={copied ? "Copied!" : path}
        >
            {label}
            {copied ? (
                <CheckIcon className="h-3 w-3" />
            ) : (
                <ClipboardDocumentIcon className="h-3 w-3 opacity-60" />
            )}
        </button>
    );
}

LocationBadge.propTypes = {
    path: PropTypes.string,
    cacheDir: PropTypes.string,
    homeDir: PropTypes.string,
};

function SearchInput({ value, onChange, placeholder = "Search models..." }) {
    return (
        <div className="relative flex rounded-md border border-gray-300 dark:border-gray-600">
            <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
                <MagnifyingGlassIcon className="h-4 w-4 text-gray-400" />
            </div>
            <input
                type="text"
                value={value}
                onChange={(e) => onChange(e.target.value)}
                placeholder={placeholder}
                className="block w-full rounded-md border-0 py-1.5 pl-9 pr-3 text-gray-900 dark:text-gray-100 placeholder:text-gray-400 dark:placeholder:text-gray-500 bg-white dark:bg-gray-700 focus:outline-none focus:ring-0 sm:text-sm sm:leading-6"
            />
        </div>
    );
}

SearchInput.propTypes = {
    value: PropTypes.string.isRequired,
    onChange: PropTypes.func.isRequired,
    placeholder: PropTypes.string,
};

function TaskFilter({ tasks, selectedTask, onTaskChange }) {
    const displayLabel = selectedTask ? selectedTask.replace(/_/g, "-") : "All tasks";

    return (
        <Menu as="div" className="relative">
            <MenuButton className="flex items-center gap-1.5 w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-1.5 sm:text-sm sm:leading-6 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none">
                <span className="flex-1 text-left truncate">{displayLabel}</span>
                <ChevronDownIcon className="h-4 w-4 text-gray-400" aria-hidden="true" />
            </MenuButton>

            <MenuItems
                anchor="bottom end"
                className="absolute right-0 z-50 mt-1 w-48 origin-top-right rounded-md bg-white dark:bg-gray-700 shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none"
            >
                <div className="py-1">
                    <MenuItem>
                        <button
                            onClick={() => onTaskChange("")}
                            className="group flex w-full items-center gap-2 px-4 py-2 text-sm text-gray-700 dark:text-gray-300 data-[focus]:bg-gray-100 data-[focus]:dark:bg-gray-600"
                        >
                            <span className={!selectedTask ? "font-semibold" : "font-normal"}>
                                All tasks
                            </span>
                            {!selectedTask && (
                                <CheckIcon className="ml-auto h-4 w-4 text-blue-600" aria-hidden="true" />
                            )}
                        </button>
                    </MenuItem>
                    {tasks.map((task) => (
                        <MenuItem key={task}>
                            <button
                                onClick={() => onTaskChange(task)}
                                className="group flex w-full items-center gap-2 px-4 py-2 text-sm text-gray-700 dark:text-gray-300 data-[focus]:bg-gray-100 data-[focus]:dark:bg-gray-600"
                            >
                                <span className={selectedTask === task ? "font-semibold" : "font-normal"}>
                                    {task.replace(/_/g, "-")}
                                </span>
                                {selectedTask === task && (
                                    <CheckIcon className="ml-auto h-4 w-4 text-blue-600" aria-hidden="true" />
                                )}
                            </button>
                        </MenuItem>
                    ))}
                </div>
            </MenuItems>
        </Menu>
    );
}

TaskFilter.propTypes = {
    tasks: PropTypes.array.isRequired,
    selectedTask: PropTypes.string.isRequired,
    onTaskChange: PropTypes.func.isRequired,
};

/**
 * Group flat model/revision list by repo_id
 */
function groupModelsByRepo(models) {
    const grouped = {};
    for (const model of models) {
        const repoId = model.repo_id;
        if (!grouped[repoId]) {
            grouped[repoId] = {
                repo_id: repoId,
                image: model.image,
                profile: model.profile,
                model_size_gb: model.model_size_gb,
                parameter_count: model.parameter_count,
                dtype: model.dtype,
                revisions: [],
            };
        }
        grouped[repoId].revisions.push({
            id: model.id,
            revision: model.revision,
            model_dir: model.model_dir,
            created_at: model.created_at,
            repo_id: model.repo_id,
            profile: model.profile,
            model_size_gb: model.model_size_gb,
        });
    }

    // Sort revisions by created_at (most recent first)
    for (const repoId of Object.keys(grouped)) {
        grouped[repoId].revisions.sort((a, b) => {
            if (!a.created_at) return 1;
            if (!b.created_at) return -1;
            return new Date(b.created_at) - new Date(a.created_at);
        });
    }

    return Object.values(grouped);
}

/**
 * Revision rows shown when a model is expanded on mobile.
 * Returns an array of tr elements to be rendered in the parent tbody.
 */
function RevisionRows({ revisions, activeDownload, cacheDir, homeDir, isRemote, onDeleteClick, onDismissDownload }) {
    const isFailed = activeDownload?.status === "failed";
    const rows = [];

    // Header row for revisions - columns must match main table
    // Below md: 4 columns (Chevron, Model, Task, Action)
    // md to xl: 5 columns (Chevron, Model, Task, Size, Action)
    rows.push(
        <tr key="header" className="xl:hidden bg-gray-100 dark:bg-gray-900 border-t border-gray-300 dark:border-gray-600">
            <td className="py-2 pl-4 pr-1 w-8"></td>
            <td className="py-2 pl-2 pr-3 text-xs font-medium text-gray-500 dark:text-gray-400">
                <span className="pl-4">Revision</span>
            </td>
            <td className="py-2 px-3 text-xs font-medium text-gray-500 dark:text-gray-400">
                Location
            </td>
            <td className="hidden md:table-cell py-2 px-3 text-xs font-medium text-gray-500 dark:text-gray-400">
                Added
            </td>
            <td className="py-2 pl-3 pr-4 sm:pr-6"></td>
        </tr>
    );

    // Show downloading row if applicable
    if (activeDownload) {
        rows.push(
            <tr key="downloading" className={`xl:hidden bg-gray-50 dark:bg-gray-900 ${!isFailed ? "animate-pulse" : ""}`}>
                <td className="py-2 pl-4 pr-1 w-8"></td>
                <td className="py-2 pl-2 pr-3 text-sm">
                    <div className="flex items-center gap-1.5 pl-4">
                        {isFailed && (
                            <ExclamationCircleIconSolid
                                className="h-4 w-4 text-red-500 flex-shrink-0"
                                title={activeDownload.error || "Download failed"}
                            />
                        )}
                        <span className="text-gray-500 dark:text-gray-400">
                            {isFailed ? "Failed" : activeDownload.status === "downloading" ? "Downloading..." : "Pending..."}
                        </span>
                    </div>
                </td>
                <td className="py-2 px-3 text-sm text-gray-400">-</td>
                <td className="hidden md:table-cell py-2 px-3 text-sm text-gray-400">-</td>
                <td className="py-2 pl-3 pr-4 sm:pr-6">
                    <div className="flex justify-end">
                        {isFailed ? (
                            <button
                                onClick={() => onDismissDownload(activeDownload.task_id)}
                                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                                title="Dismiss"
                            >
                                <XMarkIcon className="h-4 w-4" />
                            </button>
                        ) : (
                            <ArrowPathIcon className="h-4 w-4 text-gray-400 animate-spin" />
                        )}
                    </div>
                </td>
            </tr>
        );
    }

    // Revision rows
    for (const revision of revisions) {
        rows.push(
            <tr key={revision.revision} className="xl:hidden bg-gray-50 dark:bg-gray-900">
                <td className="py-2 pl-4 pr-1 w-8"></td>
                <td className="py-2 pl-2 pr-3 text-sm">
                    <div className="flex items-center gap-2 pl-4">
                        <span className="font-mono text-xs text-gray-700 dark:text-gray-300" title={revision.revision}>
                            {revision.revision.slice(0, 12)}
                        </span>
                        <CopyButton text={revision.revision} />
                    </div>
                </td>
                <td className="py-2 px-3 text-sm">
                    <LocationBadge path={revision.model_dir} cacheDir={cacheDir} homeDir={homeDir} />
                </td>
                <td className="hidden md:table-cell py-2 px-3 text-xs text-gray-500 dark:text-gray-400">
                    {revision.created_at ? lastModified(revision.created_at) : "-"}
                </td>
                <td className="py-2 pl-3 pr-4 sm:pr-6">
                    <div className="flex justify-end">
                        <button
                            onClick={() => onDeleteClick(revision)}
                            disabled={isRemote}
                            className="text-gray-400 hover:text-red-600 dark:hover:text-red-400 disabled:opacity-50 disabled:cursor-not-allowed"
                            title={isRemote ? "Not available for remote profiles" : "Delete"}
                        >
                            <TrashIcon className="h-4 w-4" />
                        </button>
                    </div>
                </td>
            </tr>
        );
    }

    // Empty state
    if (revisions.length === 0 && !activeDownload) {
        rows.push(
            <tr key="empty" className="xl:hidden bg-gray-50 dark:bg-gray-900">
                <td colSpan={5} className="py-3 text-center text-sm text-gray-400">
                    No revisions
                </td>
            </tr>
        );
    }

    return rows;
}

RevisionRows.propTypes = {
    revisions: PropTypes.array.isRequired,
    activeDownload: PropTypes.object,
    cacheDir: PropTypes.string,
    homeDir: PropTypes.string,
    isRemote: PropTypes.bool,
    onDeleteClick: PropTypes.func.isRequired,
    onDismissDownload: PropTypes.func,
};

function ModelsTable({
    models,
    onDeleteClick,
    onUpdateClick,
    onDownloadClick,
    isLoading = false,
    isRefreshing = false,
    onRefresh,
    cacheDir = null,
    homeDir = null,
    activeDownloads = [],
    updatingModel = null,
    isRemote = false,
    modelsWithUpdates = new Set(),
    checkingUpdates = false,
    selectedModel = null,
    onSelectModel,
    onDismissDownload,
}) {
    const [searchQuery, setSearchQuery] = useState("");
    const [selectedTask, setSelectedTask] = useState("");
    const [expandedModel, setExpandedModel] = useState(null);

    // Get unique tasks for filter dropdown
    const availableTasks = useMemo(() => {
        const tasks = new Set(models.map((m) => m.image).filter(Boolean));
        return Array.from(tasks).sort();
    }, [models]);

    // Group and filter models
    const groupedModels = useMemo(() => {
        let filtered = models;

        // Filter by search query
        if (searchQuery) {
            const query = searchQuery.toLowerCase();
            filtered = filtered.filter((m) =>
                m.repo_id.toLowerCase().includes(query)
            );
        }

        // Filter by task
        if (selectedTask) {
            filtered = filtered.filter((m) => m.image === selectedTask);
        }

        return groupModelsByRepo(filtered);
    }, [models, searchQuery, selectedTask]);

    // Sort by repo_id
    const sortedModels = useMemo(() => {
        return [...groupedModels].sort((a, b) =>
            a.repo_id.toLowerCase().localeCompare(b.repo_id.toLowerCase())
        );
    }, [groupedModels]);

    // Create set of existing repo_ids for quick lookup
    const existingRepoIds = useMemo(() => {
        return new Set(sortedModels.map((m) => m.repo_id));
    }, [sortedModels]);

    // Get active downloads that aren't already in the model list
    const downloadingModels = useMemo(() => {
        return activeDownloads
            .filter((d) => !existingRepoIds.has(d.repo_id))
            .map((d) => ({
                repo_id: d.repo_id,
                task_id: d.task_id,
                isDownloading: true,
                downloadStatus: d.status,
                downloadError: d.error,
                revisions: [],
            }));
    }, [activeDownloads, existingRepoIds]);

    // Combined list: downloading models at top, then sorted models
    const modelsToDisplay = useMemo(() => {
        return [...downloadingModels, ...sortedModels];
    }, [downloadingModels, sortedModels]);

    // Auto-select first model when list changes (for desktop layout)
    useEffect(() => {
        // Check if current selection exists in the combined list (including downloading)
        const selectionExists = modelsToDisplay.find(m => m.repo_id === selectedModel?.repo_id);
        if (!selectionExists && modelsToDisplay.length > 0) {
            onSelectModel(modelsToDisplay[0]);
        } else if (modelsToDisplay.length === 0) {
            onSelectModel(null);
        }
    }, [modelsToDisplay, selectedModel?.repo_id, onSelectModel]);

    const heightClass = "xl:h-[calc(100vh-14rem)]";

    // Toggle expansion for mobile view
    const toggleExpanded = (repoId) => {
        setExpandedModel(expandedModel === repoId ? null : repoId);
    };

    return (
        <div id="models-table" name="models-table" className={`flex-none ${heightClass}`}>
            {/* Main content area */}
            <div className="flex gap-6">
                {/* Models table - full width on mobile, flex-1 on desktop */}
                <div className="flex-1 min-w-0">
                    {/* Header with search and filter */}
                    <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-2 gap-2 sm:gap-4">
                        <label className="font-medium text-sm leading-6 text-gray-900 dark:text-gray-100 flex-shrink-0 flex items-center gap-2">
                            Models
                            {(() => {
                                const activeCount = activeDownloads.filter(d => d.status !== "failed").length;
                                return activeCount > 0 && (
                                    <span className="flex h-5 w-5 items-center justify-center rounded-full bg-blue-500 text-xs font-medium text-white">
                                        {activeCount}
                                    </span>
                                );
                            })()}
                        </label>
                        <div className="flex flex-wrap items-center gap-2 w-full sm:w-auto">
                            <button
                                onClick={onDownloadClick}
                                disabled={isRemote}
                                title={isRemote ? "Not available for remote profiles" : "Add model"}
                                className="p-1 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                <PlusIcon className="h-5 w-5" />
                            </button>
                            <div className="flex-1 sm:flex-none sm:w-48">
                                <SearchInput
                                    value={searchQuery}
                                    onChange={setSearchQuery}
                                    placeholder="Search..."
                                />
                            </div>
                            <div className="w-36 sm:w-48">
                                <TaskFilter
                                    tasks={availableTasks}
                                    selectedTask={selectedTask}
                                    onTaskChange={setSelectedTask}
                                />
                            </div>
                        </div>
                    </div>
                    <div className={`ring-1 ring-gray-300 dark:ring-gray-600 sm:rounded-lg ${heightClass} overflow-y-auto`}>
                        <table className="divide-y divide-gray-300 dark:divide-gray-600 w-full">
                            <thead className="bg-gray-50 dark:bg-gray-800">
                                <tr>
                                    {/* Expand chevron column - mobile only */}
                                    <th
                                        scope="col"
                                        className="xl:hidden sticky top-0 z-10 py-3 pl-4 pr-1 w-8 bg-gray-50 dark:bg-gray-800"
                                    >
                                    </th>
                                    <th
                                        scope="col"
                                        className="sticky top-0 z-10 py-3 pl-2 lg:pl-6 pr-3 text-left text-sm font-semibold text-gray-900 dark:text-gray-100 bg-gray-50 dark:bg-gray-800"
                                    >
                                        Model
                                    </th>
                                    <th
                                        scope="col"
                                        className="sticky top-0 z-10 px-3 py-3 text-left text-sm font-semibold text-gray-900 dark:text-gray-100 w-40 bg-gray-50 dark:bg-gray-800"
                                    >
                                        Task
                                    </th>
                                    <th
                                        scope="col"
                                        className="sticky top-0 z-10 px-3 py-3 text-left text-sm font-semibold text-gray-900 dark:text-gray-100 w-32 bg-gray-50 dark:bg-gray-800 hidden md:table-cell"
                                    >
                                        Size
                                    </th>
                                    <th
                                        scope="col"
                                        className="sticky top-0 z-10 pl-3 pr-4 py-3 text-right text-sm font-semibold text-gray-900 dark:text-gray-100 sm:pr-6 w-20 bg-gray-50 dark:bg-gray-800"
                                    >
                                        <button
                                            onClick={onRefresh}
                                            title="Refresh"
                                            className="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
                                        >
                                            <ArrowPathIcon
                                                className={`h-4 w-4 ${isRefreshing || checkingUpdates ? "animate-spin" : ""}`}
                                            />
                                        </button>
                                    </th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-200 dark:divide-gray-700 bg-white dark:bg-gray-800">
                                {isLoading ? (
                                    <>
                                        {Array.from({ length: 5 }).map((_, i) => (
                                            <tr key={i}>
                                                <td colSpan={5} className="relative whitespace-nowrap py-3 px-5 animate-pulse">
                                                    <div className="bg-gray-100 dark:bg-gray-700 h-9 rounded-md"></div>
                                                </td>
                                            </tr>
                                        ))}
                                    </>
                                ) : modelsToDisplay.length === 0 ? (
                                    <tr>
                                        <td colSpan={5} className="h-64">
                                            <div className="font-light sm:text-sm text-center align-middle text-gray-600 dark:text-gray-400">
                                                {models.length === 0 ? "No models found" : "No models match your filters"}
                                            </div>
                                        </td>
                                    </tr>
                                ) : (
                                    modelsToDisplay.map((model) => {
                                        const isSelected = selectedModel?.repo_id === model.repo_id;
                                        const isExpanded = expandedModel === model.repo_id;
                                        const downloadingForModel = activeDownloads.find(d => d.repo_id === model.repo_id);

                                        // Downloading model placeholder row
                                        if (model.isDownloading) {
                                            const isFailed = model.downloadStatus === "failed";
                                            return (
                                                <tr
                                                    key={`downloading-${model.repo_id}`}
                                                    className={`cursor-pointer ${
                                                        isSelected
                                                            ? "bg-gray-100 dark:bg-gray-700"
                                                            : "bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-750"
                                                    }`}
                                                    onClick={() => onSelectModel(model)}
                                                >
                                                    {/* Chevron column - mobile only */}
                                                    <td className="xl:hidden py-3 pl-4 pr-1 w-8">
                                                        <ChevronRightIcon className="h-4 w-4 text-gray-300" />
                                                    </td>
                                                    <td className="whitespace-nowrap py-3 pl-2 lg:pl-6 pr-3 text-left text-sm">
                                                        <div className={`flex items-center gap-2 ${!isFailed ? "animate-pulse" : ""}`}>
                                                            {isFailed && (
                                                                <span
                                                                    className="text-red-500 dark:text-red-400 flex-shrink-0"
                                                                    title={model.downloadError || "Download failed"}
                                                                >
                                                                    <ExclamationCircleIconSolid className="h-4 w-4" />
                                                                </span>
                                                            )}
                                                            <span className="text-gray-900 dark:text-gray-100 truncate">
                                                                {model.repo_id}
                                                            </span>
                                                            <a
                                                                href={`https://huggingface.co/${model.repo_id}`}
                                                                target="_blank"
                                                                rel="noopener noreferrer"
                                                                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 flex-shrink-0"
                                                                onClick={(e) => e.stopPropagation()}
                                                                title="View on Hugging Face"
                                                            >
                                                                <ArrowTopRightOnSquareIcon className="h-3.5 w-3.5" />
                                                            </a>
                                                        </div>
                                                    </td>
                                                    <td className={`whitespace-nowrap py-3 px-3 text-left text-sm w-40 ${!isFailed ? "animate-pulse" : ""}`}>
                                                        <span className="text-gray-400 dark:text-gray-500">-</span>
                                                    </td>
                                                    <td className={`whitespace-nowrap py-3 px-3 text-left text-sm text-gray-600 dark:text-gray-400 w-32 hidden md:table-cell ${!isFailed ? "animate-pulse" : ""}`}>
                                                        <span className="text-gray-400 dark:text-gray-500">-</span>
                                                    </td>
                                                    <td className="whitespace-nowrap py-3 pl-3 pr-4 sm:pr-6 w-20">
                                                        <div className="flex justify-end">
                                                            {isFailed ? (
                                                                <button
                                                                    onClick={(e) => {
                                                                        e.stopPropagation();
                                                                        onDismissDownload(model.task_id);
                                                                    }}
                                                                    className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                                                                    title="Dismiss"
                                                                >
                                                                    <XMarkIcon className="h-4 w-4" />
                                                                </button>
                                                            ) : (
                                                                <ArrowPathIcon className="h-4 w-4 text-gray-400 animate-spin" />
                                                            )}
                                                        </div>
                                                    </td>
                                                </tr>
                                            );
                                        }

                                        return (
                                            <>
                                                <tr
                                                    key={model.repo_id}
                                                    className={`cursor-pointer ${
                                                        isSelected
                                                            ? "bg-gray-100 dark:bg-gray-700"
                                                            : "bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-750"
                                                    }`}
                                                    onClick={() => {
                                                        // Desktop: select model for right panel
                                                        onSelectModel(model);
                                                        // Mobile: toggle expansion
                                                        toggleExpanded(model.repo_id);
                                                    }}
                                                >
                                                    {/* Chevron column - mobile only */}
                                                    <td className="xl:hidden py-3 pl-4 pr-1 w-8">
                                                        <ChevronRightIcon
                                                            className={`h-4 w-4 text-gray-400 transition-transform ${isExpanded ? "rotate-90" : ""}`}
                                                        />
                                                    </td>
                                                    <td className="whitespace-nowrap py-3 pl-2 lg:pl-6 pr-3 text-left text-sm">
                                                        <div className="flex items-center gap-2">
                                                            <span className="text-gray-900 dark:text-gray-100 truncate">
                                                                {model.repo_id}
                                                            </span>
                                                            <a
                                                                href={`https://huggingface.co/${model.repo_id}`}
                                                                target="_blank"
                                                                rel="noopener noreferrer"
                                                                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 flex-shrink-0"
                                                                onClick={(e) => e.stopPropagation()}
                                                                title="View on Hugging Face"
                                                            >
                                                                <ArrowTopRightOnSquareIcon className="h-3.5 w-3.5" />
                                                            </a>
                                                        </div>
                                                    </td>
                                                    <td className="whitespace-nowrap py-3 px-3 text-left text-sm w-40">
                                                        <TaskBadge task={model.image} />
                                                    </td>
                                                    <td className="whitespace-nowrap py-3 px-3 text-left text-sm text-gray-600 dark:text-gray-400 w-32 hidden md:table-cell">
                                                        {model.model_size_gb || model.parameter_count ? (
                                                            <span title={model.dtype ? `${model.dtype}` : undefined}>
                                                                {model.parameter_count ? formatParameters(model.parameter_count) : null}
                                                                {model.parameter_count && model.model_size_gb ? " · " : null}
                                                                {model.model_size_gb ? formatSizeGB(model.model_size_gb) : null}
                                                            </span>
                                                        ) : (
                                                            <span className="text-gray-400 dark:text-gray-500">-</span>
                                                        )}
                                                    </td>
                                                    <td className="whitespace-nowrap py-3 pl-3 pr-4 sm:pr-6 w-20">
                                                        <div className="flex justify-end">
                                                            {!checkingUpdates && modelsWithUpdates.has(model.repo_id) && !isRemote ? (
                                                                <button
                                                                    onClick={(e) => {
                                                                        e.stopPropagation();
                                                                        onUpdateClick(model);
                                                                    }}
                                                                    className="text-blue-500 hover:text-blue-600 dark:hover:text-blue-400 disabled:opacity-50 disabled:cursor-not-allowed"
                                                                    title="Update available - click to download"
                                                                    disabled={updatingModel === model.repo_id}
                                                                >
                                                                    <ArrowDownCircleIcon
                                                                        className={`h-4 w-4 ${updatingModel === model.repo_id ? "animate-pulse" : ""}`}
                                                                    />
                                                                </button>
                                                            ) : null}
                                                        </div>
                                                    </td>
                                                </tr>
                                                {/* Expanded revision rows - mobile only */}
                                                {isExpanded && (
                                                    <RevisionRows
                                                        revisions={model.revisions}
                                                        activeDownload={downloadingForModel}
                                                        cacheDir={cacheDir}
                                                        homeDir={homeDir}
                                                        isRemote={isRemote}
                                                        onDeleteClick={onDeleteClick}
                                                        onDismissDownload={onDismissDownload}
                                                    />
                                                )}
                                            </>
                                        );
                                    })
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>

                {/* Right panel: Revisions for selected model - desktop only */}
                <div className="w-[400px] 2xl:w-[560px] flex-shrink-0 hidden xl:block">
                    {/* Header */}
                    <div className="flex items-center gap-2 mb-2 h-9">
                        <label className="font-medium text-sm leading-6 text-gray-900 dark:text-gray-100">
                            Revisions
                        </label>
                        {selectedModel && (
                            <span className="font-mono text-xs text-gray-500 dark:text-gray-400">
                                {selectedModel.repo_id}
                            </span>
                        )}
                    </div>
                    <div className={`ring-1 ring-gray-300 dark:ring-gray-600 sm:rounded-lg ${heightClass} overflow-y-auto`}>
                        <table className="divide-y divide-gray-300 dark:divide-gray-600 w-full">
                            <thead className="bg-gray-50 dark:bg-gray-800">
                                <tr>
                                    <th
                                        scope="col"
                                        className="sticky top-0 z-10 py-3 pl-6 pr-4 text-left text-sm font-semibold text-gray-900 dark:text-gray-100 bg-gray-50 dark:bg-gray-800 w-full"
                                    >
                                        Revision
                                    </th>
                                    <th
                                        scope="col"
                                        className="sticky top-0 z-10 py-3 px-4 text-left text-sm font-semibold text-gray-900 dark:text-gray-100 bg-gray-50 dark:bg-gray-800 hidden 2xl:table-cell"
                                    >
                                        Location
                                    </th>
                                    <th
                                        scope="col"
                                        className="sticky top-0 z-10 py-3 px-4 text-left text-sm font-semibold text-gray-900 dark:text-gray-100 bg-gray-50 dark:bg-gray-800 hidden 2xl:table-cell"
                                    >
                                        Added
                                    </th>
                                    <th
                                        scope="col"
                                        className="sticky top-0 z-10 py-3 pl-4 pr-6 text-right text-sm font-semibold text-gray-900 dark:text-gray-100 bg-gray-50 dark:bg-gray-800 w-12"
                                    >
                                    </th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-200 dark:divide-gray-700 bg-white dark:bg-gray-800">
                                {!selectedModel ? (
                                    <tr>
                                        <td colSpan={4} className="h-64">
                                            <div className="font-light sm:text-sm text-center align-middle text-gray-400 dark:text-gray-500">
                                                Select a model
                                            </div>
                                        </td>
                                    </tr>
                                ) : (() => {
                                    // Check if there's an active download for this model
                                    const downloadingForModel = activeDownloads.find(
                                        (d) => d.repo_id === selectedModel.repo_id
                                    );
                                    const hasRevisions = selectedModel.revisions.length > 0;

                                    if (!hasRevisions && !downloadingForModel) {
                                        return (
                                            <tr>
                                                <td colSpan={4} className="h-64">
                                                    <div className="font-light sm:text-sm text-center align-middle text-gray-400 dark:text-gray-500">
                                                        No revisions
                                                    </div>
                                                </td>
                                            </tr>
                                        );
                                    }

                                    return (
                                        <>
                                            {/* Show downloading placeholder if applicable */}
                                            {downloadingForModel && (() => {
                                                const isFailed = downloadingForModel.status === "failed";
                                                return (
                                                    <tr className="bg-white dark:bg-gray-800">
                                                        <td className={`py-3 pl-6 pr-4 text-left text-sm w-full ${!isFailed ? "animate-pulse" : ""}`}>
                                                            <div className="flex items-center gap-1.5">
                                                                {isFailed && (
                                                                    <span
                                                                        className="text-red-500 dark:text-red-400 flex-shrink-0"
                                                                        title={downloadingForModel.error || "Download failed"}
                                                                    >
                                                                        <ExclamationCircleIconSolid className="h-4 w-4" />
                                                                    </span>
                                                                )}
                                                                <span className="text-gray-400 dark:text-gray-500">
                                                                    {isFailed
                                                                        ? "Failed"
                                                                        : downloadingForModel.status === "downloading"
                                                                            ? "Downloading..."
                                                                            : "Pending..."}
                                                                </span>
                                                            </div>
                                                        </td>
                                                        <td className={`whitespace-nowrap py-3 px-4 text-left text-sm hidden 2xl:table-cell ${!isFailed ? "animate-pulse" : ""}`}>
                                                            <span className="text-gray-400 dark:text-gray-500">-</span>
                                                        </td>
                                                        <td className={`whitespace-nowrap py-3 px-4 text-left text-sm text-gray-500 dark:text-gray-400 hidden 2xl:table-cell ${!isFailed ? "animate-pulse" : ""}`}>
                                                            -
                                                        </td>
                                                        <td className="whitespace-nowrap py-3 pl-4 pr-6 w-12">
                                                            <div className="flex justify-end">
                                                                {isFailed ? (
                                                                    <button
                                                                        onClick={() => onDismissDownload(downloadingForModel.task_id)}
                                                                        className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                                                                        title="Dismiss"
                                                                    >
                                                                        <XMarkIcon className="h-4 w-4" />
                                                                    </button>
                                                                ) : (
                                                                    <ArrowPathIcon className="h-4 w-4 text-gray-400 animate-spin" />
                                                                )}
                                                            </div>
                                                        </td>
                                                    </tr>
                                                );
                                            })()}
                                            {selectedModel.revisions.map((revision) => (
                                                <tr key={revision.revision} className="bg-white dark:bg-gray-800">
                                                    <td className="py-3 pl-6 pr-4 text-left text-sm w-full">
                                                        <div className="flex items-center gap-1.5">
                                                            <span
                                                                className="font-mono text-xs text-gray-700 dark:text-gray-300"
                                                                title={revision.revision}
                                                            >
                                                                {revision.revision.slice(0, 12)}
                                                            </span>
                                                            <CopyButton text={revision.revision} />
                                                        </div>
                                                    </td>
                                                    <td className="whitespace-nowrap py-3 px-4 text-left text-sm hidden 2xl:table-cell">
                                                        <LocationBadge path={revision.model_dir} cacheDir={cacheDir} homeDir={homeDir} />
                                                    </td>
                                                    <td className="whitespace-nowrap py-3 px-4 text-left text-sm text-gray-500 dark:text-gray-400 hidden 2xl:table-cell">
                                                        {revision.created_at
                                                            ? lastModified(revision.created_at)
                                                            : "-"}
                                                    </td>
                                                    <td className="whitespace-nowrap py-3 pl-4 pr-6 text-right w-12">
                                                        <button
                                                            onClick={() => onDeleteClick(revision)}
                                                            disabled={isRemote}
                                                            className="text-gray-500 dark:text-gray-400 hover:text-red-600 dark:hover:text-red-400 disabled:opacity-50 disabled:cursor-not-allowed"
                                                            title={isRemote ? "Not available for remote profiles" : "Delete revision"}
                                                        >
                                                            <TrashIcon className="h-4 w-4" />
                                                        </button>
                                                    </td>
                                                </tr>
                                            ))}
                                        </>
                                    );
                                })()}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    );
}

ModelsTable.propTypes = {
    models: PropTypes.array.isRequired,
    onDeleteClick: PropTypes.func.isRequired,
    onUpdateClick: PropTypes.func.isRequired,
    onDownloadClick: PropTypes.func.isRequired,
    isLoading: PropTypes.bool,
    isRefreshing: PropTypes.bool,
    onRefresh: PropTypes.func.isRequired,
    cacheDir: PropTypes.string,
    homeDir: PropTypes.string,
    activeDownloads: PropTypes.array,
    updatingModel: PropTypes.string,
    isRemote: PropTypes.bool,
    modelsWithUpdates: PropTypes.instanceOf(Set),
    checkingUpdates: PropTypes.bool,
    selectedModel: PropTypes.object,
    onSelectModel: PropTypes.func.isRequired,
    onDismissDownload: PropTypes.func,
};

export default ModelsTable;
