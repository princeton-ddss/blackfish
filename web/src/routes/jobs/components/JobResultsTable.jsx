import { useState } from "react";
import {
    ChevronLeftIcon,
    ArrowPathIcon,
    CheckCircleIcon,
    XCircleIcon,
} from "@heroicons/react/24/outline";
import { lastModified } from "@/lib/util";
import { assetPath } from "@/config";
import Pagination from "@/components/Pagination";
import PropTypes from "prop-types";

function formatElapsedTime(startedAt, finishedAt) {
    if (!startedAt || !finishedAt) return "-";

    const start = new Date(startedAt);
    const end = new Date(finishedAt);
    const diffMs = end - start;

    if (diffMs < 1000) {
        return `${diffMs}ms`;
    } else if (diffMs < 60000) {
        return `${(diffMs / 1000).toFixed(1)}s`;
    } else {
        const minutes = Math.floor(diffMs / 60000);
        const seconds = ((diffMs % 60000) / 1000).toFixed(0);
        return `${minutes}m ${seconds}s`;
    }
}

function StatusIcon({ success }) {
    if (success) {
        return <CheckCircleIcon className="h-5 w-5 text-green-500" />;
    }
    return <XCircleIcon className="h-5 w-5 text-red-500" />;
}

StatusIcon.propTypes = {
    success: PropTypes.bool.isRequired,
};

function JobResultsTable({
    job,
    results,
    onBack,
    onResultSelect,
    selectedResult,
    isLoading = false,
    isRefreshing = false,
    error = null,
    onRefresh = null,
}) {
    const [currentPage, setCurrentPage] = useState(1);
    const resultsPerPage = 20;

    const indexOfLastResult = currentPage * resultsPerPage;
    const indexOfFirstResult = indexOfLastResult - resultsPerPage;

    const currentResults = results.slice(indexOfFirstResult, indexOfLastResult);
    const heightClass = "lg:h-[calc(100vh-11rem)]";

    return (
        <div id="job-results-table" name="job-results-table" className={`flex-none ${heightClass}`}>
            <div className="flex items-center justify-between mb-2 h-9">
                <div className="flex items-center gap-2">
                    <button
                        onClick={onBack}
                        className="p-1 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                    >
                        <ChevronLeftIcon className="h-5 w-5" />
                    </button>
                    <label className="font-medium text-sm leading-6 text-gray-900 dark:text-gray-100">
                        {job.name}
                    </label>
                    <span className="text-sm text-gray-500 dark:text-gray-400">
                        ({results.length} results)
                    </span>
                </div>
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
                                            className="sticky top-0 z-10 py-3.5 pl-4 pr-3 text-left text-sm font-semibold text-gray-900 dark:text-gray-100 sm:pl-6 w-1/4 backdrop-blur bg-gray-50 dark:bg-gray-800"
                                        >
                                            Input File
                                        </th>
                                        <th
                                            scope="col"
                                            className="sticky top-0 z-10 px-3 py-3.5 text-left text-sm font-semibold text-gray-900 dark:text-gray-100 w-36 backdrop-blur bg-gray-50 dark:bg-gray-800"
                                        >
                                            Started
                                        </th>
                                        <th
                                            scope="col"
                                            className="sticky top-0 z-10 px-3 py-3.5 text-left text-sm font-semibold text-gray-900 dark:text-gray-100 w-24 backdrop-blur bg-gray-50 dark:bg-gray-800"
                                        >
                                            Elapsed
                                        </th>
                                        <th
                                            scope="col"
                                            className="sticky top-0 z-10 px-3 py-3.5 text-center text-sm font-semibold text-gray-900 dark:text-gray-100 w-16 backdrop-blur bg-gray-50 dark:bg-gray-800"
                                        >
                                            Status
                                        </th>
                                        <th
                                            scope="col"
                                            className="sticky top-0 z-10 px-3 py-3.5 text-left text-sm font-semibold text-gray-900 dark:text-gray-100 w-1/4 backdrop-blur bg-gray-50 dark:bg-gray-800"
                                        >
                                            Output File
                                        </th>
                                        <th
                                            scope="col"
                                            className="sticky top-0 z-10 px-3 py-3.5 text-right text-sm font-semibold text-gray-900 dark:text-gray-100 w-12 backdrop-blur bg-gray-50 dark:bg-gray-800"
                                        >
                                            <div className="flex gap-2 justify-end">
                                                <button
                                                    onClick={() => onRefresh?.()}
                                                    title="Refresh"
                                                >
                                                    <ArrowPathIcon
                                                        className={`h-5 w-5 text-gray-900 dark:text-gray-100 hover:text-gray-400 ${isLoading || isRefreshing ? "animate-spin" : ""}`}
                                                    />
                                                </button>
                                            </div>
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
                                    ) : error ? (
                                        <tr>
                                            <td colSpan={6} className="h-64">
                                                <div className="font-light sm:text-sm text-center align-middle text-gray-600 dark:text-gray-400">
                                                    <img
                                                        className="h-16 mb-5 w-auto ml-auto mr-auto opacity-80 dark:invert"
                                                        src={assetPath("/img/dead-fish.png")}
                                                        alt="Loading error."
                                                    />
                                                    {error?.message || "Failed to load results."}
                                                </div>
                                            </td>
                                        </tr>
                                    ) : results.length === 0 ? (
                                        <tr>
                                            <td colSpan={6} className="h-64">
                                                <div className="font-light sm:text-sm text-center align-middle text-gray-600 dark:text-gray-400">
                                                    No results found
                                                </div>
                                            </td>
                                        </tr>
                                    ) : (
                                        currentResults.map((result) => (
                                            <tr
                                                key={result.id}
                                                onClick={() => onResultSelect(result)}
                                                className={`cursor-pointer ${
                                                    selectedResult?.id === result.id
                                                        ? "bg-blue-50 dark:bg-blue-900/20"
                                                        : "bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700"
                                                }`}
                                            >
                                                <td className="whitespace-nowrap py-3 pl-4 pr-3 text-left text-sm text-gray-900 dark:text-gray-100 sm:pl-6">
                                                    <div className="overflow-x-scroll">{result.input_file}</div>
                                                </td>
                                                <td className="whitespace-nowrap py-3 px-3 text-left text-sm text-gray-900 dark:text-gray-100">
                                                    {result.started_at ? lastModified(result.started_at) : "-"}
                                                </td>
                                                <td className="whitespace-nowrap py-3 px-3 text-left text-sm text-gray-500 dark:text-gray-400">
                                                    {result.started_at && result.finished_at ? formatElapsedTime(result.started_at, result.finished_at) : "-"}
                                                </td>
                                                <td className="whitespace-nowrap py-3 px-3">
                                                    <div className="flex justify-center">
                                                        <StatusIcon success={result.success} />
                                                    </div>
                                                </td>
                                                <td className="whitespace-nowrap py-3 px-3 text-left text-sm text-gray-900 dark:text-gray-100">
                                                    <div className="overflow-x-scroll">
                                                        {result.output_file ? result.output_file.split("/").pop() : "-"}
                                                    </div>
                                                </td>
                                                <td className="whitespace-nowrap py-3 px-3 text-right">
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
                filesPerPage={resultsPerPage}
                totalFiles={results.length}
                currentPage={currentPage}
                setCurrentPage={setCurrentPage}
                disabled={false}
            />
        </div>
    );
}

JobResultsTable.propTypes = {
    job: PropTypes.object.isRequired,
    results: PropTypes.array.isRequired,
    onBack: PropTypes.func.isRequired,
    onResultSelect: PropTypes.func.isRequired,
    selectedResult: PropTypes.object,
    isLoading: PropTypes.bool,
    isRefreshing: PropTypes.bool,
    error: PropTypes.object,
    onRefresh: PropTypes.func,
};

export default JobResultsTable;
