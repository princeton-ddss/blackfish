import { useState } from "react";
import { Menu, MenuButton, MenuItem, MenuItems, Portal } from "@headlessui/react";
import {
    ChevronRightIcon,
    ArrowPathIcon,
    ChevronDownIcon,
} from "@heroicons/react/24/outline";
import { lastModified, batchProgress, isBatchJobActive, BatchJobStatus } from "@/lib/util";
import Pagination from "@/components/Pagination";
import SortableHeader from "@/components/SortableHeader";
import FilterHeader from "@/components/FilterHeader";
import FilterMenu from "@/components/FilterMenu";
import TableSearch from "@/components/TableSearch";
import { useTableControls } from "@/lib/useTableControls";
import { COLUMN_HEIGHT } from "./layout";
import { TASKS } from "./NewJobModal";
import StatusBadge from "./StatusBadge";
import PropTypes from "prop-types";

const RECENT_WINDOW_MS = 7 * 24 * 60 * 60 * 1000;

// Typed field qualifiers (substring match); see applyQuery.
const JOB_FILTER_FIELDS = {
    name: (j) => j.name,
    status: (j) => j.status,
    task: (j) => j.task,
    id: (j) => j.id,
};

// status is dropdown-driven and enum-valued; match it exactly so filtering
// "submitted" doesn't also catch "resubmitted" (substring collision).
const JOB_EXACT_FILTER_FIELDS = ["status"];

// Only columns with a meaningful ordering are sortable. Status and Progress are
// categorical/bucketed — they're filtered via dropdowns, not sorted.
const JOB_SORT_FIELDS = {
    name: (j) => j.name,
    id: (j) => j.id,
    created_at: (j) => j.created_at,
};

// Dropdown-backed predicate groups (see useTableControls.predicateFilters).
// Keyed by the query key each dropdown writes, then option value -> predicate.
const JOB_PREDICATE_FILTERS = {
    // "Filters": intent awkward to type as raw qualifiers.
    filter: {
        active: (j) => isBatchJobActive(j.status),
        inactive: (j) => !isBatchJobActive(j.status),
        failed: (j) => (Number(j.errored) || 0) > 0,
        recent: (j) => {
            const t = Date.parse(j.created_at);
            // Compared against render time; a few seconds' drift is immaterial
            // for a 7-day window.
            return !Number.isNaN(t) && Date.now() - t < RECENT_WINDOW_MS;
        },
    },
    // "Progress": completion state, derived from batchProgress.
    progress: {
        "not-started": (j) => batchProgress(j).done === 0,
        "in-progress": (j) => {
            const { done, total } = batchProgress(j);
            return total != null && done > 0 && done < total;
        },
        complete: (j) => {
            const { done, total } = batchProgress(j);
            return total != null && done >= total;
        },
        failures: (j) => (Number(j.errored) || 0) > 0,
    },
};

// The single "Filters" dropdown attached to the search bar: a "Show" section
// (single-select shortcuts) and a "Tasks" section (multi-select task types).
const JOB_FILTER_SECTIONS = [
    {
        title: "Show",
        filterKey: "filter",
        mode: "single",
        options: [
            { value: "active", label: "Active jobs" },
            { value: "inactive", label: "Inactive jobs" },
            { value: "failed", label: "Jobs with failures" },
            { value: "recent", label: "Recent jobs (< 7 days)" },
        ],
    },
    {
        title: "Tasks",
        filterKey: "task",
        mode: "multi",
        options: TASKS.map((t) => ({ value: t.id, label: t.name })),
    },
];

// Column-header filter menus (Status, Progress). Each writes its own query key.
const STATUS_OPTIONS = Object.values(BatchJobStatus).map((s) => ({
    value: s,
    label: s.charAt(0).toUpperCase() + s.slice(1),
}));

const PROGRESS_OPTIONS = [
    { value: "not-started", label: "Not started" },
    { value: "in-progress", label: "In progress" },
    { value: "complete", label: "Complete" },
    { value: "failures", label: "With failures" },
];

function ProgressDisplay({ finished, staged, errored }) {
    const { done, failed, total } = batchProgress({ finished, staged, errored });
    // total is null before a job's first observation: no denominator to show.
    if (total === null) {
        return <span className="text-xs text-gray-400 dark:text-gray-500">N/A</span>;
    }
    const pending = total - done - failed;
    return (
        <div className="flex items-center gap-1.5 text-xs">
            <span className="text-green-600 dark:text-green-400">{done}</span>
            <span className="text-gray-400">/</span>
            <span className="text-gray-900 dark:text-gray-100">{total}</span>
            {(pending > 0 || failed > 0) && (
                <span className="text-gray-400 dark:text-gray-500">
                    ({pending > 0 && <>{pending} staged</>}
                    {pending > 0 && failed > 0 && ", "}
                    {failed > 0 && <span className="text-red-600 dark:text-red-400">{failed} failed</span>})
                </span>
            )}
        </div>
    );
}

ProgressDisplay.propTypes = {
    finished: PropTypes.number,
    staged: PropTypes.number,
    errored: PropTypes.number,
};

function JobsTable({ jobs, onJobClick, onJobDrillIn, selectedJob, isLoading = false, isRefreshing = false, onRefresh, onNewClick, profile, useMockData, setUseMockData }) {
    const isSlurm = profile?.schema === "slurm";
    const [currentPage, setCurrentPage] = useState(1);
    const jobsPerPage = 20;

    const {
        query,
        setQuery,
        sortKey,
        sortDir,
        toggleSort,
        rows: visibleJobs,
    } = useTableControls(jobs, {
        filterFields: JOB_FILTER_FIELDS,
        exactFilterFields: JOB_EXACT_FILTER_FIELDS,
        predicateFilters: JOB_PREDICATE_FILTERS,
        sortFields: JOB_SORT_FIELDS,
        defaultSort: { key: "created_at", dir: "desc" },
    });

    // Filtering can shrink the list under the current page; clamp to a valid page.
    const pageCount = Math.max(1, Math.ceil(visibleJobs.length / jobsPerPage));
    const page = Math.min(currentPage, pageCount);
    const indexOfLastJob = page * jobsPerPage;
    const indexOfFirstJob = indexOfLastJob - jobsPerPage;

    const currentJobs = visibleJobs.slice(indexOfFirstJob, indexOfLastJob);

    const handleQueryChange = (q) => {
        setQuery(q);
        setCurrentPage(1);
    };

    return (
        <div
            id="jobs-table"
            name="jobs-table"
            className={`flex-none lg:flex lg:flex-col ${COLUMN_HEIGHT}`}
        >
            <div className="flex-none flex items-center justify-between mb-2 h-9">
                <label className="font-medium text-sm leading-6 text-gray-900 dark:text-gray-100">
                    Jobs
                </label>
                <div className="flex items-center gap-2">
                    {import.meta.env.DEV && (
                        <button
                            onClick={() => setUseMockData(!useMockData)}
                            className={`text-xs px-2 py-1 rounded ${useMockData ? "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200" : "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400"}`}
                        >
                            {useMockData ? "Mock" : "API"}
                        </button>
                    )}
                    {isSlurm && (
                        <Menu as="div" className="relative">
                            <MenuButton className="inline-flex items-center gap-1 rounded-md bg-white dark:bg-gray-700 px-2.5 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-200 shadow ring-1 ring-inset ring-gray-300 dark:ring-gray-500 dark:shadow-gray-900/50 hover:shadow-md hover:bg-gray-50 dark:hover:bg-gray-600 transition-shadow focus:outline-none">
                                New Job
                                <ChevronDownIcon className="h-4 w-4 text-gray-500 dark:text-gray-400" />
                            </MenuButton>
                            <Portal>
                                <MenuItems
                                    anchor="bottom end"
                                    className="z-50 w-56 rounded-md bg-white dark:bg-gray-700 shadow-lg ring-1 ring-black dark:ring-gray-600 ring-opacity-5 focus:outline-none"
                                >
                                    <div className="py-1">
                                        {TASKS.map((task) => (
                                            <MenuItem key={task.id}>
                                                <button
                                                    onClick={() => onNewClick(task)}
                                                    className="block w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-200 data-[focus]:bg-blue-500 data-[focus]:text-white"
                                                >
                                                    <div className="font-medium">{task.name}</div>
                                                    <div className="text-xs opacity-75">
                                                        {task.description}
                                                    </div>
                                                </button>
                                            </MenuItem>
                                        ))}
                                    </div>
                                </MenuItems>
                            </Portal>
                        </Menu>
                    )}
                </div>
            </div>
            <div className="flex-none mb-4">
                <TableSearch query={query} setQuery={handleQueryChange}>
                    <FilterMenu
                        label="Filters"
                        sections={JOB_FILTER_SECTIONS}
                        query={query}
                        setQuery={handleQueryChange}
                    />
                </TableSearch>
            </div>
            {/* Pagination lives inside the bordered box so the box's bottom edge
                is the column's bottom edge, aligned with the details panel. */}
            <div className="flex flex-col lg:flex-1 lg:min-h-0 ring-1 ring-gray-300 dark:ring-gray-600 sm:rounded-lg overflow-hidden">
                <div className="lg:flex-1 lg:min-h-0 overflow-auto relative z-0">
                <table className="divide-y divide-gray-300 dark:divide-gray-600 table-fixed w-full">
                    <thead>
                        <tr>
                            <SortableHeader
                                label="Name"
                                sortKey="name"
                                activeKey={sortKey}
                                direction={sortDir}
                                onSort={toggleSort}
                                className="pl-4 pr-3 sm:pl-6 w-1/4"
                            />
                            <SortableHeader
                                label="ID"
                                sortKey="id"
                                activeKey={sortKey}
                                direction={sortDir}
                                onSort={toggleSort}
                                className="px-3 w-24"
                            />
                            <SortableHeader
                                label="Submitted"
                                sortKey="created_at"
                                activeKey={sortKey}
                                direction={sortDir}
                                onSort={toggleSort}
                                className="px-3 w-36"
                            />
                            {/* Status & Progress headers are filter
                                dropdowns, not sortable columns. */}
                            <FilterHeader
                                label="Status"
                                filterKey="status"
                                options={STATUS_OPTIONS}
                                clearLabel="Clear statuses"
                                query={query}
                                setQuery={handleQueryChange}
                                className="px-3 text-left w-24"
                            />
                            <FilterHeader
                                label="Progress"
                                filterKey="progress"
                                options={PROGRESS_OPTIONS}
                                clearLabel="Clear"
                                query={query}
                                setQuery={handleQueryChange}
                                className="px-3 text-left w-32"
                            />
                            <th
                                scope="col"
                                className="sticky top-0 z-10 px-3 py-3.5 text-right text-sm font-semibold text-gray-900 dark:text-gray-100 w-20 backdrop-blur bg-gray-50 dark:bg-gray-800"
                            >
                                <div className="flex gap-2 justify-end">
                                    <button
                                        onClick={onRefresh}
                                        disabled={isRefreshing}
                                        title="Refresh"
                                        className="text-gray-900 dark:text-gray-100 hover:text-gray-400 disabled:opacity-50"
                                    >
                                        <ArrowPathIcon
                                            className={`h-5 w-5 ${isRefreshing ? "animate-spin" : ""}`}
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
                        ) : visibleJobs.length === 0 ? (
                            <tr>
                                <td colSpan={6} className="h-64">
                                    <div className="font-light sm:text-sm text-center align-middle text-gray-600 dark:text-gray-400">
                                        {jobs.length === 0
                                            ? "No jobs found"
                                            : "No jobs match your search"}
                                    </div>
                                </td>
                            </tr>
                        ) : (
                            currentJobs.map((job) => (
                                <tr
                                    key={job.id}
                                    onClick={() => onJobClick(job)}
                                    className={`cursor-pointer ${
                                        selectedJob?.id === job.id
                                            ? "bg-blue-50 dark:bg-blue-900/20"
                                            : "bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700"
                                    }`}
                                >
                                    <td className="whitespace-nowrap py-3 pl-4 pr-3 text-left text-sm text-gray-900 dark:text-gray-100 sm:pl-6">
                                        <div className="overflow-x-scroll">{job.name}</div>
                                    </td>
                                    <td className="whitespace-nowrap py-3 px-3 text-left text-sm text-gray-500 dark:text-gray-400 font-mono text-xs" title={job.id}>
                                        {job.id?.slice(0, 8)}
                                    </td>
                                    <td className="whitespace-nowrap py-3 px-3 text-left text-sm text-gray-900 dark:text-gray-100">
                                        {lastModified(job.created_at)}
                                    </td>
                                    <td className="whitespace-nowrap py-3 px-3 text-left text-sm">
                                        <StatusBadge status={job.status} errored={job.errored} />
                                    </td>
                                    <td className="whitespace-nowrap py-3 px-3 text-left text-sm text-gray-900 dark:text-gray-100">
                                        <ProgressDisplay
                                            finished={job.finished}
                                            staged={job.staged}
                                            errored={job.errored}
                                        />
                                    </td>
                                    <td className="whitespace-nowrap py-3 px-3 text-right">
                                        <button
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                onJobDrillIn(job);
                                            }}
                                            className="text-gray-900 dark:text-gray-100 hover:text-gray-400"
                                        >
                                            <ChevronRightIcon className="h-4 w-4" />
                                        </button>
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
                            filesPerPage={jobsPerPage}
                            totalFiles={visibleJobs.length}
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

JobsTable.propTypes = {
    jobs: PropTypes.array.isRequired,
    onJobClick: PropTypes.func.isRequired,
    onJobDrillIn: PropTypes.func.isRequired,
    selectedJob: PropTypes.object,
    isLoading: PropTypes.bool,
    isRefreshing: PropTypes.bool,
    onRefresh: PropTypes.func,
    onNewClick: PropTypes.func,
    profile: PropTypes.object,
    useMockData: PropTypes.bool,
    setUseMockData: PropTypes.func,
};

export default JobsTable;
