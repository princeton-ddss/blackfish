import { useState } from "react";
import {
    ChevronLeftIcon,
    ArrowPathIcon,
    CheckCircleIcon,
    XCircleIcon,
} from "@heroicons/react/24/outline";
import { lastModified, elapsedMs, formatElapsed } from "@/lib/util";
import { assetPath } from "@/config";
import Pagination from "@/components/Pagination";
import SortableHeader from "@/components/SortableHeader";
import FilterHeader from "@/components/FilterHeader";
import TableSearch from "@/components/TableSearch";
import { useTableControls } from "@/lib/useTableControls";
import { COLUMN_HEIGHT } from "./layout";
import PropTypes from "prop-types";

// The table shows file basenames (the full paths are in the result preview).
function basename(path) {
    if (!path) return "-";
    return path.split("/").pop();
}

// Typed field qualifiers (substring match); see applyQuery. `status` is also
// driven by the Status header dropdown.
const RESULT_FILTER_FIELDS = {
    status: (r) => (r.success ? "success" : "failed"),
    file: (r) => r.input_file,
    out: (r) => r.output_file,
};

// status is dropdown-driven and enum-valued — match exactly, not by substring.
const RESULT_EXACT_FILTER_FIELDS = ["status"];

// Status is filtered via its header dropdown, not sorted — so it's absent here.
const RESULT_SORT_FIELDS = {
    input_file: (r) => basename(r.input_file),
    started_at: (r) => r.started_at,
    elapsed: (r) => elapsedMs(r.started_at, r.finished_at),
    output_file: (r) => basename(r.output_file),
};

const RESULT_STATUS_OPTIONS = [
    { value: "success", label: "Successful" },
    { value: "failed", label: "Failed" },
];

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
    // Enough rows to overflow a full-height box on any realistic viewport: a
    // page that fits without scrolling reads as "that's everything", which the
    // pager below then contradicts.
    const resultsPerPage = 50;

    const {
        query,
        setQuery,
        sortKey,
        sortDir,
        toggleSort,
        rows: visibleResults,
    } = useTableControls(results, {
        filterFields: RESULT_FILTER_FIELDS,
        exactFilterFields: RESULT_EXACT_FILTER_FIELDS,
        sortFields: RESULT_SORT_FIELDS,
        defaultSort: { key: "started_at", dir: "desc" },
    });

    // Filtering can shrink the list under the current page; clamp to page 1
    // whenever the query changes rather than stranding the user on an empty page.
    const pageCount = Math.max(1, Math.ceil(visibleResults.length / resultsPerPage));
    const page = Math.min(currentPage, pageCount);
    const indexOfLastResult = page * resultsPerPage;
    const indexOfFirstResult = indexOfLastResult - resultsPerPage;

    const currentResults = visibleResults.slice(indexOfFirstResult, indexOfLastResult);

    const handleQueryChange = (q) => {
        setQuery(q);
        setCurrentPage(1);
    };

    return (
        <div
            id="job-results-table"
            name="job-results-table"
            className={`flex-none lg:flex lg:flex-col ${COLUMN_HEIGHT}`}
        >
            <div className="flex-none flex items-center justify-between mb-2 h-9">
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
                        {visibleResults.length === results.length
                            ? `(${results.length} results)`
                            : `(${visibleResults.length} of ${results.length})`}
                    </span>
                </div>
            </div>
            <div className="flex-none mb-4">
                <TableSearch query={query} setQuery={handleQueryChange} />
            </div>
            {/* Pagination lives inside the bordered box so the box's bottom edge
                is the column's bottom edge, aligned with the preview panel. */}
            <div className="flex flex-col lg:flex-1 lg:min-h-0 ring-1 ring-gray-300 dark:ring-gray-600 sm:rounded-lg overflow-hidden">
                <div className="lg:flex-1 lg:min-h-0 overflow-auto">
                <table className="divide-y divide-gray-300 dark:divide-gray-600 table-fixed w-full">
                    <thead>
                        <tr>
                            <SortableHeader
                                label="Input File"
                                sortKey="input_file"
                                activeKey={sortKey}
                                direction={sortDir}
                                onSort={toggleSort}
                                className="pl-4 pr-3 sm:pl-6 w-1/4"
                            />
                            <SortableHeader
                                label="Started"
                                sortKey="started_at"
                                activeKey={sortKey}
                                direction={sortDir}
                                onSort={toggleSort}
                                className="px-3 w-36"
                            />
                            <SortableHeader
                                label="Elapsed"
                                sortKey="elapsed"
                                activeKey={sortKey}
                                direction={sortDir}
                                onSort={toggleSort}
                                className="px-3 w-24"
                            />
                            {/* Status is filtered via its dropdown, not sorted. */}
                            <FilterHeader
                                label="Status"
                                filterKey="status"
                                options={RESULT_STATUS_OPTIONS}
                                clearLabel="Clear statuses"
                                query={query}
                                setQuery={handleQueryChange}
                                className="px-3 text-center w-20"
                            />
                            <SortableHeader
                                label="Output File"
                                sortKey="output_file"
                                activeKey={sortKey}
                                direction={sortDir}
                                onSort={toggleSort}
                                className="px-3 w-1/4"
                            />
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
                        ) : visibleResults.length === 0 ? (
                            <tr>
                                <td colSpan={6} className="h-64">
                                    <div className="font-light sm:text-sm text-center align-middle text-gray-600 dark:text-gray-400">
                                        {results.length === 0
                                            ? "No results found"
                                            : "No results match your search"}
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
                                    <td className="whitespace-nowrap py-3 pl-4 pr-3 text-left text-xs font-mono text-gray-900 dark:text-gray-100 sm:pl-6">
                                        <div className="overflow-x-scroll">{basename(result.input_file)}</div>
                                    </td>
                                    <td className="whitespace-nowrap py-3 px-3 text-left text-sm text-gray-900 dark:text-gray-100">
                                        {result.started_at ? lastModified(result.started_at) : "-"}
                                    </td>
                                    <td className="whitespace-nowrap py-3 px-3 text-left text-sm text-gray-500 dark:text-gray-400">
                                        {formatElapsed(result.started_at, result.finished_at)}
                                    </td>
                                    <td className="whitespace-nowrap py-3 px-3">
                                        <div className="flex justify-center">
                                            <StatusIcon success={result.success} />
                                        </div>
                                    </td>
                                    <td className="whitespace-nowrap py-3 px-3 text-left text-xs font-mono text-gray-900 dark:text-gray-100">
                                        <div className="overflow-x-scroll">
                                            {basename(result.output_file)}
                                        </div>
                                    </td>
                                    <td className="whitespace-nowrap py-3 px-3 text-right">
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
                </div>
                {pageCount > 1 && (
                    <div className="flex-none border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
                        <Pagination
                            filesPerPage={resultsPerPage}
                            totalFiles={visibleResults.length}
                            currentPage={page}
                            setCurrentPage={setCurrentPage}
                            disabled={false}
                        />
                    </div>
                )}
            </div>
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
