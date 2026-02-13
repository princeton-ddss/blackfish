import { useState, useEffect } from "react";
import {
    ArrowPathIcon,
    TrashIcon,
    ClipboardDocumentIcon,
    CheckIcon,
} from "@heroicons/react/24/outline";
import { lastModified } from "@/lib/util";
import Pagination from "@/components/Pagination";
import PropTypes from "prop-types";

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

function CopyableLocation({ path }) {
    const [copied, setCopied] = useState(false);

    if (!path) {
        return <span className="text-gray-500 dark:text-gray-400">-</span>;
    }

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
        <div className="flex items-center gap-1 min-w-0">
            <span className="font-mono text-xs truncate" title={path}>
                {path}
            </span>
            <button
                onClick={handleCopy}
                className="flex-shrink-0 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                title="Copy path"
            >
                {copied ? (
                    <CheckIcon className="h-3.5 w-3.5 text-green-500" />
                ) : (
                    <ClipboardDocumentIcon className="h-3.5 w-3.5" />
                )}
            </button>
        </div>
    );
}

CopyableLocation.propTypes = {
    path: PropTypes.string,
};

function LastUpdatedFooter({ lastFetchedAt, onRefresh, isLoading }) {
    const [, setTick] = useState(0);

    useEffect(() => {
        const interval = setInterval(() => {
            setTick((t) => t + 1);
        }, 30_000);
        return () => clearInterval(interval);
    }, []);

    return (
        <div className="flex items-center justify-center gap-2 mt-2 text-xs text-gray-500 dark:text-gray-400">
            <span>
                {lastFetchedAt
                    ? `Last updated ${lastModified(lastFetchedAt.toISOString())}`
                    : "Last updated -"}
            </span>
            <button
                onClick={onRefresh}
                title="Refresh"
                className="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
            >
                <ArrowPathIcon
                    className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`}
                />
            </button>
        </div>
    );
}

LastUpdatedFooter.propTypes = {
    lastFetchedAt: PropTypes.instanceOf(Date),
    onRefresh: PropTypes.func.isRequired,
    isLoading: PropTypes.bool,
};

function ModelsTable({
    models,
    onDeleteClick,
    isLoading = false,
    onRefresh,
    isLocalProfile = true,
    lastFetchedAt = null,
}) {
    const [currentPage, setCurrentPage] = useState(1);
    const modelsPerPage = 20;

    const indexOfLastModel = currentPage * modelsPerPage;
    const indexOfFirstModel = indexOfLastModel - modelsPerPage;

    const sortedModels = [...models].sort((a, b) =>
        a.repo_id.toLowerCase().localeCompare(b.repo_id.toLowerCase())
    );

    const currentModels = sortedModels.slice(indexOfFirstModel, indexOfLastModel);
    const heightClass = "lg:h-[calc(100vh-11rem)]";

    return (
        <div id="models-table" name="models-table" className={`flex-none ${heightClass}`}>
            <div className="flex items-center justify-between mb-2 h-9">
                <label className="font-medium text-sm leading-6 text-gray-900 dark:text-gray-100">
                    Models
                </label>
            </div>
            <div className="flow-root">
                <div className="-my-2 overflow-x-auto sm:-mx-6 lg:-mx-8">
                    <div className="inline-block min-w-full py-2 align-middle sm:px-6 lg:px-8">
                        <div className={`ring-1 ring-gray-300 dark:ring-gray-600 sm:rounded-lg ${heightClass} overflow-y-auto`}>
                            <table className="divide-y divide-gray-300 dark:divide-gray-600 table-fixed w-full">
                                <thead>
                                    <tr>
                                        <th
                                            scope="col"
                                            className="sticky top-0 z-10 py-3.5 pl-4 pr-3 text-left text-sm font-semibold text-gray-900 dark:text-gray-100 sm:pl-6 w-[30%] backdrop-blur bg-gray-50 dark:bg-gray-800"
                                        >
                                            Model
                                        </th>
                                        <th
                                            scope="col"
                                            className="sticky top-0 z-10 px-3 py-3.5 text-left text-sm font-semibold text-gray-900 dark:text-gray-100 w-36 backdrop-blur bg-gray-50 dark:bg-gray-800"
                                        >
                                            Task
                                        </th>
                                        <th
                                            scope="col"
                                            className="sticky top-0 z-10 px-3 py-3.5 text-left text-sm font-semibold text-gray-900 dark:text-gray-100 w-24 backdrop-blur bg-gray-50 dark:bg-gray-800"
                                        >
                                            Revision
                                        </th>
                                        <th
                                            scope="col"
                                            className="sticky top-0 z-10 px-3 py-3.5 text-left text-sm font-semibold text-gray-900 dark:text-gray-100 w-28 backdrop-blur bg-gray-50 dark:bg-gray-800"
                                        >
                                            Added
                                        </th>
                                        <th
                                            scope="col"
                                            className="sticky top-0 z-10 px-3 py-3.5 text-left text-sm font-semibold text-gray-900 dark:text-gray-100 backdrop-blur bg-gray-50 dark:bg-gray-800"
                                        >
                                            Location
                                        </th>
                                        <th
                                            scope="col"
                                            className="sticky top-0 z-10 px-3 py-3.5 text-right text-sm font-semibold text-gray-900 dark:text-gray-100 w-14 backdrop-blur bg-gray-50 dark:bg-gray-800"
                                        >
                                        </th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-gray-200 dark:divide-gray-700 bg-white dark:bg-gray-800">
                                    {isLoading ? (
                                        <>
                                            {Array.from({ length: 5 }).map((_, i) => (
                                                <tr key={i}>
                                                    <td colSpan={6} className="relative whitespace-nowrap py-3 px-5 animate-pulse">
                                                        <div className="bg-gray-100 dark:bg-gray-700 h-9 rounded-md"></div>
                                                    </td>
                                                </tr>
                                            ))}
                                        </>
                                    ) : models.length === 0 ? (
                                        <tr>
                                            <td colSpan={6} className="h-64">
                                                <div className="font-light sm:text-sm text-center align-middle text-gray-600 dark:text-gray-400">
                                                    No models found
                                                </div>
                                            </td>
                                        </tr>
                                    ) : (
                                        currentModels.map((model) => (
                                            <tr
                                                key={model.id}
                                                className="bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700"
                                            >
                                                <td className="whitespace-nowrap py-3 pl-4 pr-3 text-left text-sm sm:pl-6">
                                                    <a
                                                        href={`https://huggingface.co/${model.repo_id}`}
                                                        target="_blank"
                                                        rel="noopener noreferrer"
                                                        className="text-blue-600 dark:text-blue-400 hover:underline"
                                                    >
                                                        {model.repo_id}
                                                    </a>
                                                </td>
                                                <td className="whitespace-nowrap py-3 px-3 text-left text-sm">
                                                    <TaskBadge task={model.image} />
                                                </td>
                                                <td className="whitespace-nowrap py-3 px-3 text-left text-sm text-gray-500 dark:text-gray-400 font-mono text-xs">
                                                    {model.revision?.slice(0, 7)}
                                                </td>
                                                <td className="whitespace-nowrap py-3 px-3 text-left text-sm text-gray-500 dark:text-gray-400">
                                                    {model.created_at ? lastModified(model.created_at) : "-"}
                                                </td>
                                                <td className="py-3 px-3 text-left text-sm max-w-0">
                                                    <CopyableLocation path={model.model_dir} />
                                                </td>
                                                <td className="whitespace-nowrap py-3 px-3 text-right">
                                                    <button
                                                        onClick={() => onDeleteClick(model)}
                                                        className="text-gray-500 dark:text-gray-400 hover:text-red-600 dark:hover:text-red-400"
                                                        title="Delete model"
                                                    >
                                                        <TrashIcon className="h-4 w-4" />
                                                    </button>
                                                </td>
                                            </tr>
                                        ))
                                    )}
                                    <tr className="bg-white dark:bg-gray-800">
                                        <td className="whitespace-nowrap h-16"></td>
                                        <td className="whitespace-nowrap h-16"></td>
                                        <td className="whitespace-nowrap h-16"></td>
                                        <td className="whitespace-nowrap h-16"></td>
                                        <td className="whitespace-nowrap h-16"></td>
                                        <td className="whitespace-nowrap h-16"></td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
            <Pagination
                filesPerPage={modelsPerPage}
                totalFiles={sortedModels.length}
                currentPage={currentPage}
                setCurrentPage={setCurrentPage}
                disabled={false}
            />
            <LastUpdatedFooter
                lastFetchedAt={lastFetchedAt}
                onRefresh={onRefresh}
                isLoading={isLoading}
            />
        </div>
    );
}

ModelsTable.propTypes = {
    models: PropTypes.array.isRequired,
    onDeleteClick: PropTypes.func.isRequired,
    isLoading: PropTypes.bool,
    onRefresh: PropTypes.func.isRequired,
    isLocalProfile: PropTypes.bool,
    lastFetchedAt: PropTypes.instanceOf(Date),
};

export default ModelsTable;
