import {
    DocumentIcon,
    CpuChipIcon,
    ServerIcon,
    FolderIcon,
} from "@heroicons/react/24/outline";
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

function ProgressBar({ finished, staged, errored }) {
    const done = finished ?? 0;
    const pending = staged ?? 0;
    const failed = errored ?? 0;
    const total = done + pending + failed;
    if (total === 0) return null;

    const donePct = (done / total) * 100;
    const failedPct = (failed / total) * 100;

    return (
        <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 overflow-hidden">
            <div className="h-full flex">
                <div
                    className="bg-green-500 h-full"
                    style={{ width: `${donePct}%` }}
                />
                <div
                    className="bg-red-500 h-full"
                    style={{ width: `${failedPct}%` }}
                />
            </div>
        </div>
    );
}

ProgressBar.propTypes = {
    finished: PropTypes.number,
    staged: PropTypes.number,
    errored: PropTypes.number,
};

function JobDetailsPanel({ job }) {
    if (!job) {
        return (
            <div className="bg-white dark:bg-gray-800 p-6 h-full flex flex-col justify-center">
                <div className="text-center">
                    <DocumentIcon className="mx-auto h-12 w-12 text-gray-400" />
                    <p className="mt-4 text-sm font-semibold text-gray-700 dark:text-gray-300">
                        No job selected
                    </p>
                    <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                        Click on a job to view its configuration
                    </p>
                </div>
            </div>
        );
    }

    const done = job.finished ?? 0;
    const pending = job.staged ?? 0;
    const failed = job.errored ?? 0;
    const total = done + pending + failed;

    return (
        <div className="bg-white dark:bg-gray-800 p-6">
            {/* Header */}
            <div className="flex items-start justify-between mb-4">
                <div>
                    <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100">
                        {job.name}
                    </h3>
                    <p className="text-xs text-gray-500 dark:text-gray-400 font-mono mt-1">
                        {job.id}
                    </p>
                </div>
                <StatusBadge displayStatus={deriveDisplayStatus(job)} />
            </div>

            {/* Progress Section */}
            <div className="mb-4">
                <div className="flex items-center justify-between text-sm mb-2">
                    <span className="text-gray-500 dark:text-gray-400">Progress</span>
                    <div className="flex items-center gap-3 text-xs">
                        <span className="text-green-600 dark:text-green-400">{done} done</span>
                        <span className="text-gray-500 dark:text-gray-400">{pending} pending</span>
                        {failed > 0 && (
                            <span className="text-red-600 dark:text-red-400">{failed} failed</span>
                        )}
                    </div>
                </div>
                <ProgressBar
                    finished={job.finished}
                    staged={job.staged}
                    errored={job.errored}
                />
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 text-right">
                    {total} total
                </p>
            </div>

            {/* Data Paths Section */}
            {(job.input_dir || job.output_dir) && (
                <div className="border-t border-gray-200 dark:border-gray-700 pt-4 mb-4">
                    <div className="flex items-center gap-2 mb-3">
                        <FolderIcon className="h-4 w-4 text-gray-500 dark:text-gray-400" />
                        <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100">
                            Data Paths
                        </h4>
                    </div>
                    <div className="space-y-2 text-sm">
                        {job.input_dir && (
                            <div>
                                <span className="text-gray-500 dark:text-gray-400">Input:</span>
                                <span className="text-gray-900 dark:text-gray-100 text-xs font-mono ml-2 break-all">
                                    {job.input_dir}
                                </span>
                            </div>
                        )}
                        {job.output_dir && (
                            <div>
                                <span className="text-gray-500 dark:text-gray-400">Output:</span>
                                <span className="text-gray-900 dark:text-gray-100 text-xs font-mono ml-2 break-all">
                                    {job.output_dir}
                                </span>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Resource Config Section */}
            {job.resources && (
                <div className="border-t border-gray-200 dark:border-gray-700 pt-4 mb-4">
                    <div className="flex items-center gap-2 mb-3">
                        <ServerIcon className="h-4 w-4 text-gray-500 dark:text-gray-400" />
                        <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100">
                            Resource Config
                        </h4>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-sm">
                        {job.resources.memory_gb != null && (
                            <div className="flex justify-between">
                                <span className="text-gray-500 dark:text-gray-400">Memory:</span>
                                <span className="text-gray-900 dark:text-gray-100">{job.resources.memory_gb} GB</span>
                            </div>
                        )}
                        {job.resources.cpus != null && (
                            <div className="flex justify-between">
                                <span className="text-gray-500 dark:text-gray-400">CPUs:</span>
                                <span className="text-gray-900 dark:text-gray-100">{job.resources.cpus}</span>
                            </div>
                        )}
                        {job.resources.gpu_count != null && (
                            <div className="flex justify-between">
                                <span className="text-gray-500 dark:text-gray-400">GPUs:</span>
                                <span className="text-gray-900 dark:text-gray-100">{job.resources.gpu_count}</span>
                            </div>
                        )}
                        {job.resources.partition && (
                            <div className="flex justify-between">
                                <span className="text-gray-500 dark:text-gray-400">Partition:</span>
                                <span className="text-gray-900 dark:text-gray-100">{job.resources.partition}</span>
                            </div>
                        )}
                        {job.resources.max_workers != null && (
                            <div className="flex justify-between">
                                <span className="text-gray-500 dark:text-gray-400">Max Workers:</span>
                                <span className="text-gray-900 dark:text-gray-100">{job.resources.max_workers}</span>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Task Config Section */}
            {(job.task || job.repo_id) && (
                <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
                    <div className="flex items-center gap-2 mb-3">
                        <CpuChipIcon className="h-4 w-4 text-gray-500 dark:text-gray-400" />
                        <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100">
                            Task Config
                        </h4>
                    </div>
                    <div className="space-y-2 text-sm">
                        {job.task && (
                            <div className="flex justify-between">
                                <span className="text-gray-500 dark:text-gray-400">Task:</span>
                                <span className="text-gray-900 dark:text-gray-100">{job.task}</span>
                            </div>
                        )}
                        {job.repo_id && (
                            <div className="flex justify-between">
                                <span className="text-gray-500 dark:text-gray-400">Model:</span>
                                <span className="text-gray-900 dark:text-gray-100 text-xs font-mono truncate ml-2 max-w-[200px]" title={job.repo_id}>
                                    {job.repo_id}
                                </span>
                            </div>
                        )}
                        {job.revision && (
                            <div className="flex justify-between">
                                <span className="text-gray-500 dark:text-gray-400">Revision:</span>
                                <span className="text-gray-900 dark:text-gray-100">{job.revision}</span>
                            </div>
                        )}
                        {job.params && Object.keys(job.params).length > 0 && (
                            <>
                                {Object.entries(job.params).map(([key, value]) => (
                                    key === "prompt" ? (
                                        <div key={key}>
                                            <span className="text-gray-500 dark:text-gray-400 block mb-1">Prompt:</span>
                                            <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-3">
                                                <pre className="text-xs text-gray-900 dark:text-gray-100 whitespace-pre-wrap font-mono">
                                                    {value}
                                                </pre>
                                            </div>
                                        </div>
                                    ) : (
                                        <div key={key} className="flex justify-between">
                                            <span className="text-gray-500 dark:text-gray-400 capitalize">{key.replace(/_/g, " ")}:</span>
                                            <span className="text-gray-900 dark:text-gray-100">{String(value)}</span>
                                        </div>
                                    )
                                ))}
                            </>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}

JobDetailsPanel.propTypes = {
    job: PropTypes.shape({
        id: PropTypes.string,
        name: PropTypes.string,
        status: PropTypes.string,
        staged: PropTypes.number,
        finished: PropTypes.number,
        errored: PropTypes.number,
        task: PropTypes.string,
        repo_id: PropTypes.string,
        revision: PropTypes.string,
        input_dir: PropTypes.string,
        output_dir: PropTypes.string,
        resources: PropTypes.shape({
            memory_gb: PropTypes.number,
            cpus: PropTypes.number,
            gpu_count: PropTypes.number,
            partition: PropTypes.string,
            max_workers: PropTypes.number,
        }),
        params: PropTypes.object,
    }),
};

export default JobDetailsPanel;
