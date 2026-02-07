import {
    DocumentIcon,
    CpuChipIcon,
    ServerIcon,
} from "@heroicons/react/24/outline";
import PropTypes from "prop-types";

function StatusBadge({ status }) {
    const getStatusConfig = () => {
        switch (status) {
            case "done":
                return {
                    bg: "bg-green-50 dark:bg-green-900/30",
                    text: "text-green-700 dark:text-green-400",
                    ring: "ring-green-600/20 dark:ring-green-500/30",
                };
            case "running":
                return {
                    bg: "bg-yellow-50 dark:bg-yellow-900/30",
                    text: "text-yellow-700 dark:text-yellow-400",
                    ring: "ring-yellow-600/20 dark:ring-yellow-500/30",
                };
            case "error":
                return {
                    bg: "bg-red-50 dark:bg-red-900/30",
                    text: "text-red-700 dark:text-red-400",
                    ring: "ring-red-600/20 dark:ring-red-500/30",
                };
            case "submitted":
            default:
                return {
                    bg: "bg-gray-50 dark:bg-gray-700",
                    text: "text-gray-600 dark:text-gray-400",
                    ring: "ring-gray-500/10 dark:ring-gray-600",
                };
        }
    };

    const config = getStatusConfig();
    const label = status.charAt(0).toUpperCase() + status.slice(1);

    return (
        <span className={`inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ring-1 ring-inset ${config.bg} ${config.text} ${config.ring}`}>
            {label}
        </span>
    );
}

StatusBadge.propTypes = {
    status: PropTypes.string.isRequired,
};

function ProgressBar({ completed, remaining, failed }) {
    const total = completed + remaining + failed;
    if (total === 0) return null;

    const completedPct = (completed / total) * 100;
    const failedPct = (failed / total) * 100;

    return (
        <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 overflow-hidden">
            <div className="h-full flex">
                <div
                    className="bg-green-500 h-full"
                    style={{ width: `${completedPct}%` }}
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
    completed: PropTypes.number.isRequired,
    remaining: PropTypes.number.isRequired,
    failed: PropTypes.number.isRequired,
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

    const total = job.completed + job.remaining + job.failed;

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
                <StatusBadge status={job.status} />
            </div>

            {/* Progress Section */}
            <div className="mb-4">
                <div className="flex items-center justify-between text-sm mb-2">
                    <span className="text-gray-500 dark:text-gray-400">Progress</span>
                    <div className="flex items-center gap-3 text-xs">
                        <span className="text-green-600 dark:text-green-400">{job.completed} done</span>
                        <span className="text-gray-500 dark:text-gray-400">{job.remaining} pending</span>
                        {job.failed > 0 && (
                            <span className="text-red-600 dark:text-red-400">{job.failed} failed</span>
                        )}
                    </div>
                </div>
                <ProgressBar
                    completed={job.completed}
                    remaining={job.remaining}
                    failed={job.failed}
                />
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 text-right">
                    {total} total
                </p>
            </div>

            {/* Resource Config Section */}
            {job.slurm && (
                <div className="border-t border-gray-200 dark:border-gray-700 pt-4 mb-4">
                    <div className="flex items-center gap-2 mb-3">
                        <ServerIcon className="h-4 w-4 text-gray-500 dark:text-gray-400" />
                        <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100">
                            Resource Config
                        </h4>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-sm">
                        <div className="flex justify-between">
                            <span className="text-gray-500 dark:text-gray-400">Memory:</span>
                            <span className="text-gray-900 dark:text-gray-100">{job.slurm.memory}</span>
                        </div>
                        <div className="flex justify-between">
                            <span className="text-gray-500 dark:text-gray-400">CPUs:</span>
                            <span className="text-gray-900 dark:text-gray-100">{job.slurm.cpus}</span>
                        </div>
                        <div className="flex justify-between">
                            <span className="text-gray-500 dark:text-gray-400">GPUs:</span>
                            <span className="text-gray-900 dark:text-gray-100">{job.slurm.gpus}</span>
                        </div>
                        <div className="flex justify-between">
                            <span className="text-gray-500 dark:text-gray-400">Partition:</span>
                            <span className="text-gray-900 dark:text-gray-100">{job.slurm.partition}</span>
                        </div>
                        <div className="flex justify-between col-span-2">
                            <span className="text-gray-500 dark:text-gray-400">Time Limit:</span>
                            <span className="text-gray-900 dark:text-gray-100">{job.slurm.time_limit}</span>
                        </div>
                    </div>
                </div>
            )}

            {/* Task Config Section */}
            {job.task && (
                <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
                    <div className="flex items-center gap-2 mb-3">
                        <CpuChipIcon className="h-4 w-4 text-gray-500 dark:text-gray-400" />
                        <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100">
                            Task Config
                        </h4>
                    </div>
                    <div className="space-y-2 text-sm">
                        <div className="flex justify-between">
                            <span className="text-gray-500 dark:text-gray-400">Model:</span>
                            <span className="text-gray-900 dark:text-gray-100 text-xs font-mono truncate ml-2 max-w-[200px]" title={job.task.model}>
                                {job.task.model}
                            </span>
                        </div>
                        <div className="flex justify-between">
                            <span className="text-gray-500 dark:text-gray-400">Revision:</span>
                            <span className="text-gray-900 dark:text-gray-100">{job.task.revision}</span>
                        </div>
                        <div className="flex justify-between">
                            <span className="text-gray-500 dark:text-gray-400">Temperature:</span>
                            <span className="text-gray-900 dark:text-gray-100">{job.task.temperature}</span>
                        </div>
                        <div className="flex justify-between">
                            <span className="text-gray-500 dark:text-gray-400">Max Tokens:</span>
                            <span className="text-gray-900 dark:text-gray-100">{job.task.max_tokens}</span>
                        </div>
                        {job.task.prompt && (
                            <div>
                                <span className="text-gray-500 dark:text-gray-400 block mb-1">Prompt:</span>
                                <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-3">
                                    <pre className="text-xs text-gray-900 dark:text-gray-100 whitespace-pre-wrap font-mono">
                                        {job.task.prompt}
                                    </pre>
                                </div>
                            </div>
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
        completed: PropTypes.number,
        remaining: PropTypes.number,
        failed: PropTypes.number,
        slurm: PropTypes.shape({
            memory: PropTypes.string,
            cpus: PropTypes.number,
            gpus: PropTypes.number,
            partition: PropTypes.string,
            time_limit: PropTypes.string,
        }),
        task: PropTypes.shape({
            model: PropTypes.string,
            revision: PropTypes.string,
            prompt: PropTypes.string,
            temperature: PropTypes.number,
            max_tokens: PropTypes.number,
        }),
    }),
};

export default JobDetailsPanel;
