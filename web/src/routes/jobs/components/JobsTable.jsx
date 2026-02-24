import { useState } from "react";
import { Menu, MenuButton, MenuItem, MenuItems, Portal } from "@headlessui/react";
import {
    ChevronRightIcon,
    ArrowPathIcon,
    ChevronDownIcon,
} from "@heroicons/react/24/outline";
import { lastModified } from "@/lib/util";
import Pagination from "@/components/Pagination";
import { TASKS } from "./NewJobModal";
import PropTypes from "prop-types";

// Derive display status from API status and progress fields
function deriveDisplayStatus(job) {
    if (job.status === "running") return "running";
    // status === "stopped"
    if ((job.staged ?? 0) === 0 && (job.errored ?? 0) === 0) return "done";
    if ((job.errored ?? 0) > 0) return "error";
    return "stopped";
}

function StatusBadge({ displayStatus }) {
    const getStatusConfig = () => {
        switch (displayStatus) {
            case "done":
                return {
                    bg: "bg-green-50 dark:bg-green-900/30",
                    text: "text-green-700 dark:text-green-400",
                    ring: "ring-green-600/20 dark:ring-green-500/30",
                    label: "Done",
                };
            case "running":
                return {
                    bg: "bg-yellow-50 dark:bg-yellow-900/30",
                    text: "text-yellow-700 dark:text-yellow-400",
                    ring: "ring-yellow-600/20 dark:ring-yellow-500/30",
                    label: "Running",
                };
            case "error":
                return {
                    bg: "bg-red-50 dark:bg-red-900/30",
                    text: "text-red-700 dark:text-red-400",
                    ring: "ring-red-600/20 dark:ring-red-500/30",
                    label: "Error",
                };
            case "stopped":
            default:
                return {
                    bg: "bg-gray-50 dark:bg-gray-700",
                    text: "text-gray-600 dark:text-gray-400",
                    ring: "ring-gray-500/10 dark:ring-gray-600",
                    label: "Stopped",
                };
        }
    };

    const config = getStatusConfig();

    return (
        <span className={`inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ring-1 ring-inset ${config.bg} ${config.text} ${config.ring}`}>
            {config.label}
        </span>
    );
}

StatusBadge.propTypes = {
    displayStatus: PropTypes.string.isRequired,
};

function ProgressDisplay({ finished, staged, errored }) {
    const done = finished ?? 0;
    const pending = staged ?? 0;
    const failed = errored ?? 0;
    const total = done + pending + failed;
    return (
        <div className="flex items-center gap-2 text-xs">
            <span className="text-green-600 dark:text-green-400">{done}</span>
            <span className="text-gray-400">/</span>
            <span className="text-gray-500 dark:text-gray-400">{pending}</span>
            {failed > 0 && (
                <>
                    <span className="text-gray-400">/</span>
                    <span className="text-red-600 dark:text-red-400">{failed}</span>
                </>
            )}
            <span className="text-gray-400 dark:text-gray-500">({total})</span>
        </div>
    );
}

ProgressDisplay.propTypes = {
    finished: PropTypes.number,
    staged: PropTypes.number,
    errored: PropTypes.number,
};

function JobsTable({ jobs, onJobClick, onJobDrillIn, selectedJob, isLoading = false, onNewClick, profile, useMockData, setUseMockData }) {
    const isSlurm = profile?.schema === "slurm";
    const [currentPage, setCurrentPage] = useState(1);
    const jobsPerPage = 20;

    const indexOfLastJob = currentPage * jobsPerPage;
    const indexOfFirstJob = indexOfLastJob - jobsPerPage;

    const sortedJobs = [...jobs].sort((a, b) =>
        new Date(b.created_at) - new Date(a.created_at)
    );

    const currentJobs = sortedJobs.slice(indexOfFirstJob, indexOfLastJob);
    const heightClass = "lg:h-[calc(100vh-11rem)]";

    return (
        <div id="jobs-table" name="jobs-table" className={`flex-none ${heightClass}`}>
            <div className="flex items-center justify-between mb-2 h-9">
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
            <div className="flow-root">
                <div className="-my-2 overflow-x-auto sm:-mx-6 lg:-mx-8">
                    <div className="inline-block min-w-full py-2 align-middle sm:px-6 lg:px-8">
                        <div className={`ring-1 ring-gray-300 dark:ring-gray-600 sm:rounded-lg ${heightClass} overflow-y-auto relative z-0`}>
                            <table className="divide-y divide-gray-300 dark:divide-gray-600 table-fixed w-full">
                                <thead>
                                    <tr>
                                        <th
                                            scope="col"
                                            className="sticky top-0 z-10 py-3.5 pl-4 pr-3 text-left text-sm font-semibold text-gray-900 dark:text-gray-100 sm:pl-6 w-1/4 backdrop-blur bg-gray-50 dark:bg-gray-800"
                                        >
                                            Name
                                        </th>
                                        <th
                                            scope="col"
                                            className="sticky top-0 z-10 px-3 py-3.5 text-left text-sm font-semibold text-gray-900 dark:text-gray-100 w-24 backdrop-blur bg-gray-50 dark:bg-gray-800"
                                        >
                                            ID
                                        </th>
                                        <th
                                            scope="col"
                                            className="sticky top-0 z-10 px-3 py-3.5 text-left text-sm font-semibold text-gray-900 dark:text-gray-100 w-36 backdrop-blur bg-gray-50 dark:bg-gray-800"
                                        >
                                            Submitted
                                        </th>
                                        <th
                                            scope="col"
                                            className="sticky top-0 z-10 px-3 py-3.5 text-left text-sm font-semibold text-gray-900 dark:text-gray-100 w-24 backdrop-blur bg-gray-50 dark:bg-gray-800"
                                        >
                                            Status
                                        </th>
                                        <th
                                            scope="col"
                                            className="sticky top-0 z-10 px-3 py-3.5 text-left text-sm font-semibold text-gray-900 dark:text-gray-100 w-32 backdrop-blur bg-gray-50 dark:bg-gray-800"
                                        >
                                            Progress
                                        </th>
                                        <th
                                            scope="col"
                                            className="sticky top-0 z-10 px-3 py-3.5 text-right text-sm font-semibold text-gray-900 dark:text-gray-100 w-20 backdrop-blur bg-gray-50 dark:bg-gray-800"
                                        >
                                            <div className="flex gap-2 justify-end">
                                                <button
                                                    onClick={() => {}}
                                                    title="Refresh"
                                                    className="text-gray-900 dark:text-gray-100 hover:text-gray-400"
                                                >
                                                    <ArrowPathIcon
                                                        className={`h-5 w-5 ${isLoading ? "animate-spin" : ""}`}
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
                                    ) : jobs.length === 0 ? (
                                        <tr>
                                            <td colSpan={6} className="h-64">
                                                <div className="font-light sm:text-sm text-center align-middle text-gray-600 dark:text-gray-400">
                                                    No jobs found
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
                                                <td className="whitespace-nowrap py-3 px-3 text-left text-sm text-gray-500 dark:text-gray-400 font-mono text-xs">
                                                    {job.id}
                                                </td>
                                                <td className="whitespace-nowrap py-3 px-3 text-left text-sm text-gray-900 dark:text-gray-100">
                                                    {lastModified(job.created_at)}
                                                </td>
                                                <td className="whitespace-nowrap py-3 px-3 text-left text-sm">
                                                    <StatusBadge displayStatus={deriveDisplayStatus(job)} />
                                                </td>
                                                <td className="whitespace-nowrap py-3 px-3 text-left text-sm text-gray-900 dark:text-gray-100">
                                                    <ProgressDisplay
                                                        finished={job.finished}
                                                        staged={job.staged}
                                                        errored={job.errored}
                                                    />
                                                </td>
                                                <td className="whitespace-nowrap py-3 px-3 text-right">
                                                    <div className="flex gap-2 justify-end">
                                                        <button
                                                            onClick={(e) => {
                                                                e.stopPropagation();
                                                                onJobDrillIn(job);
                                                            }}
                                                            className="text-gray-900 dark:text-gray-100 hover:text-gray-400"
                                                        >
                                                            <ChevronRightIcon className="h-4 w-4" />
                                                        </button>
                                                    </div>
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
                filesPerPage={jobsPerPage}
                totalFiles={sortedJobs.length}
                currentPage={currentPage}
                setCurrentPage={setCurrentPage}
                disabled={false}
            />
        </div>
    );
}

JobsTable.propTypes = {
    jobs: PropTypes.array.isRequired,
    onJobClick: PropTypes.func.isRequired,
    onJobDrillIn: PropTypes.func.isRequired,
    selectedJob: PropTypes.object,
    isLoading: PropTypes.bool,
    onNewClick: PropTypes.func,
    profile: PropTypes.object,
    useMockData: PropTypes.bool,
    setUseMockData: PropTypes.func,
};

export default JobsTable;
