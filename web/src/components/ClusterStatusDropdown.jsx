import { useContext, useState, useEffect } from "react";
import { Popover, PopoverButton, PopoverPanel, Transition } from "@headlessui/react";
import { ServerStackIcon, ChevronRightIcon, ArrowPathIcon } from "@heroicons/react/24/outline";
import { ProfileContext } from "@/components/ProfileSelect";
import { useClusterStatus } from "@/lib/loaders";
import { formattedTimeInterval } from "@/lib/util";
import Alert from "@/components/Alert";
import PropTypes from "prop-types";

/**
 * Timer component that shows time elapsed since refTime.
 */
function Timer({ refTime }) {
  const [currentTime, setCurrentTime] = useState(new Date());

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentTime(new Date());
    }, 30_000);

    return () => clearInterval(interval);
  }, []);

  return <span>{formattedTimeInterval(refTime, currentTime)} ago</span>;
}

Timer.propTypes = {
  refTime: PropTypes.instanceOf(Date).isRequired,
};

/**
 * Status badge component.
 */
function StatusBadge({ state }) {
  const colors = state === "UP"
    ? "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300"
    : "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300";

  return (
    <span className={`text-xs px-1.5 py-0.5 rounded ${colors}`}>
      {state}
    </span>
  );
}

StatusBadge.propTypes = {
  state: PropTypes.string.isRequired,
};

/**
 * GPU availability badge.
 * Green = plenty available, Yellow = limited, Red = none
 */
function GpuAvailabilityBadge({ gpus }) {
  if (!gpus || gpus.length === 0) {
    return <span className="text-xs text-gray-400">-</span>;
  }

  const totalIdle = gpus.reduce((sum, g) => sum + g.idle, 0);

  if (totalIdle === 0) {
    return (
      <span className="text-xs px-1.5 py-0.5 rounded bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300">
        busy
      </span>
    );
  }

  if (totalIdle < 8) {
    return (
      <span className="text-xs px-1.5 py-0.5 rounded bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300">
        limited
      </span>
    );
  }

  return (
    <span className="text-xs px-1.5 py-0.5 rounded bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300">
      available
    </span>
  );
}

GpuAvailabilityBadge.propTypes = {
  gpus: PropTypes.array,
};

/**
 * Progress bar for resource utilization.
 * Bar shows usage, numbers show idle/total.
 */
function ResourceBar({ idle, total, colorClass = "bg-green-500" }) {
  const used = total - idle;
  const percentage = total > 0 ? (used / total) * 100 : 0;

  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-gray-200 dark:bg-gray-600 rounded-full overflow-hidden">
        <div
          className={`h-full ${colorClass} transition-all duration-300`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      <span className="text-xs tabular-nums text-gray-500 dark:text-gray-400 text-right whitespace-nowrap">
        {idle}/{total} idle
      </span>
    </div>
  );
}

ResourceBar.propTypes = {
  idle: PropTypes.number.isRequired,
  total: PropTypes.number.isRequired,
  colorClass: PropTypes.string,
};

/**
 * Loading skeleton for table.
 */
function TableSkeleton() {
  return (
    <div className="animate-pulse">
      {[1, 2, 3].map((i) => (
        <div key={i} className="flex gap-4 py-2 border-b border-gray-100 dark:border-gray-600 last:border-0">
          <div className="h-4 bg-gray-200 dark:bg-gray-600 rounded w-20" />
          <div className="h-4 bg-gray-200 dark:bg-gray-600 rounded w-12 ml-auto" />
          <div className="h-4 bg-gray-200 dark:bg-gray-600 rounded w-16" />
        </div>
      ))}
    </div>
  );
}

/**
 * Expandable partition row.
 */
function PartitionRow({ partition }) {
  const [expanded, setExpanded] = useState(false);
  const hasGpus = partition.gpus && partition.gpus.length > 0;

  return (
    <>
      {/* Summary row */}
      <tr
        className="border-b border-gray-100 dark:border-gray-600 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <td className="py-1.5 pl-3">
          <div className="flex items-center gap-1.5">
            <ChevronRightIcon
              className={`h-3 w-3 text-gray-400 transition-transform flex-shrink-0 ${expanded ? 'rotate-90' : ''}`}
            />
            <span className="font-medium text-gray-900 dark:text-white">
              {partition.name}
            </span>
            {partition.state !== "UP" && <StatusBadge state={partition.state} />}
          </div>
        </td>
        <td className="py-1.5 pr-3 text-right">
          <GpuAvailabilityBadge gpus={partition.gpus} />
        </td>
      </tr>

      {/* Expanded details */}
      {expanded && (
        <tr className="border-b border-gray-100 dark:border-gray-600 bg-gray-50 dark:bg-gray-600/50">
          <td colSpan={2} className="py-2 pl-7 pr-3">
            <div className="space-y-2 text-xs">
              {/* GPUs by type - at the top */}
              {hasGpus && (
                <div className="space-y-1">
                  <div className="text-gray-600 dark:text-gray-400">GPUs</div>
                  {partition.gpus.map((gpu) => (
                    <div key={gpu.gpu_type} className="flex items-center gap-2">
                      <span className="font-mono text-gray-700 dark:text-gray-300 w-16 truncate">
                        {gpu.gpu_type}
                      </span>
                      <div className="flex-1">
                        <ResourceBar
                          idle={gpu.idle}
                          total={gpu.total}
                          colorClass="bg-green-500"
                        />
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Nodes */}
              <div className="space-y-1">
                <div className="text-gray-600 dark:text-gray-400">Nodes</div>
                <ResourceBar
                  idle={partition.nodes_idle}
                  total={partition.nodes_total}
                  colorClass="bg-purple-500"
                />
              </div>

              {/* CPUs */}
              <div className="space-y-1">
                <div className="text-gray-600 dark:text-gray-400">CPUs</div>
                <ResourceBar
                  idle={partition.cpus_idle}
                  total={partition.cpus_total}
                  colorClass="bg-blue-500"
                />
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

PartitionRow.propTypes = {
  partition: PropTypes.shape({
    name: PropTypes.string.isRequired,
    state: PropTypes.string.isRequired,
    nodes_total: PropTypes.number.isRequired,
    nodes_idle: PropTypes.number.isRequired,
    cpus_total: PropTypes.number.isRequired,
    cpus_idle: PropTypes.number.isRequired,
    gpus: PropTypes.array,
  }).isRequired,
};

/**
 * Cluster status dropdown for navbar.
 * Shows partition resources and queue stats for Slurm profiles.
 */
function ClusterStatusDropdown() {
  const { profile } = useContext(ProfileContext);
  const { status, error, isLoading, refresh } = useClusterStatus(profile);

  // Only show for Slurm profiles
  if (!profile || profile.schema !== "slurm") {
    return null;
  }

  const partitions = status?.partitions ? Object.values(status.partitions) : [];
  const hasData = partitions.length > 0;

  return (
    <Popover className="relative">
      <PopoverButton
        className="p-1.5 text-gray-500 hover:text-gray-700 dark:text-gray-300 dark:hover:text-gray-200 focus:outline-none"
        aria-label="Cluster status"
      >
        <ServerStackIcon className="h-5 w-5" />
      </PopoverButton>

      <Transition
        enter="transition ease-out duration-100"
        enterFrom="transform opacity-0 scale-95"
        enterTo="transform opacity-100 scale-100"
        leave="transition ease-in duration-75"
        leaveFrom="transform opacity-100 scale-100"
        leaveTo="transform opacity-0 scale-95"
      >
        <PopoverPanel className="absolute right-0 z-50 mt-1 w-[28rem] origin-top-right rounded-lg bg-white dark:bg-gray-700 shadow-lg ring-1 ring-gray-300 dark:ring-gray-600 focus:outline-none">
          {({ close }) => (
            <>
              {/* Header */}
              <div className="pl-3 pr-3 py-2 border-b border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-800 rounded-t-lg">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
                    Cluster Status
                  </h3>
                  <span className="text-xs text-gray-500 dark:text-gray-400 font-mono">
                    {profile.host}
                  </span>
                </div>
              </div>

              {/* Body */}
              <div className="max-h-96 overflow-y-auto">
                {isLoading && <div className="px-3 py-2"><TableSkeleton /></div>}

                {!isLoading && error && (
                  <div className="px-3 py-3">
                    <Alert variant="error" title="Unable to load cluster status">
                      <p>{error.message || "An unexpected error occurred."}</p>
                      <div className="mt-4">
                        <div className="-mx-2 -my-1.5 flex">
                          <button
                            type="button"
                            onClick={() => refresh()}
                            className="rounded-md bg-red-50 px-2 py-1.5 text-sm font-medium text-red-800 hover:bg-red-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-600 dark:bg-red-500/20 dark:text-red-200 dark:hover:bg-red-500/30"
                          >
                            Retry
                          </button>
                          <button
                            type="button"
                            onClick={close}
                            className="ml-3 rounded-md bg-red-50 px-2 py-1.5 text-sm font-medium text-red-800 hover:bg-red-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-600 dark:bg-red-500/20 dark:text-red-200 dark:hover:bg-red-500/30"
                          >
                            Dismiss
                          </button>
                        </div>
                      </div>
                    </Alert>
                  </div>
                )}

                {!isLoading && !error && !hasData && (
                  <div className="text-sm text-gray-500 dark:text-gray-400 text-center py-4">
                    No partition data available
                  </div>
                )}

                {!isLoading && !error && hasData && (
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="text-left text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-600">
                        <th className="py-1.5 pl-3 font-medium">Partition</th>
                        <th className="py-1.5 pr-3 font-medium text-right">GPUs</th>
                      </tr>
                    </thead>
                    <tbody className="text-gray-700 dark:text-gray-300">
                      {partitions.map((partition) => (
                        <PartitionRow
                          key={partition.name}
                          partition={partition}
                        />
                      ))}
                    </tbody>
                  </table>
                )}
              </div>

              {/* Footer */}
              {status?.timestamp && (
                <div className="px-4 py-2 border-t border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-800 rounded-b-lg">
                  <div className="flex items-center justify-center gap-2 text-xs text-gray-500 dark:text-gray-400">
                    <span>
                      Last updated <Timer refTime={new Date(status.timestamp)} />
                    </span>
                    <button
                      type="button"
                      onClick={() => refresh()}
                      className="p-0.5 rounded hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                      aria-label="Refresh cluster status"
                    >
                      <ArrowPathIcon className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </PopoverPanel>
      </Transition>
    </Popover>
  );
}

export default ClusterStatusDropdown;
