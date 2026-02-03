import { useContext } from "react";
import { Popover, PopoverButton, PopoverPanel, Transition, Disclosure, DisclosureButton, DisclosurePanel } from "@headlessui/react";
import { ServerStackIcon, ChevronRightIcon } from "@heroicons/react/24/outline";
import { ProfileContext } from "@/components/ProfileSelect";
import { useClusterStatus } from "@/lib/loaders";
import Alert from "@/components/Alert";
import PropTypes from "prop-types";

/**
 * Progress bar component for resource utilization.
 */
function ResourceBar({ used, total, label, colorClass = "bg-blue-500" }) {
  const percentage = total > 0 ? (used / total) * 100 : 0;
  const idle = total - used;

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs text-gray-600 dark:text-gray-400">
        <span>{label}</span>
        <span>{idle.toLocaleString()} / {total.toLocaleString()} idle</span>
      </div>
      <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
        <div
          className={`h-full ${colorClass} transition-all duration-300`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}

ResourceBar.propTypes = {
  used: PropTypes.number.isRequired,
  total: PropTypes.number.isRequired,
  label: PropTypes.string.isRequired,
  colorClass: PropTypes.string,
};

/**
 * GPU availability display.
 */
function GpuList({ gpus }) {
  if (!gpus || gpus.length === 0) return null;

  return (
    <div className="space-y-1">
      <div className="text-xs text-gray-600 dark:text-gray-400">GPUs</div>
      <div className="grid grid-cols-2 gap-1">
        {gpus.map((gpu) => (
          <div
            key={gpu.gpu_type}
            className="flex items-center justify-between text-xs bg-gray-100 dark:bg-gray-700 rounded px-2 py-1"
          >
            <span className="font-mono text-gray-700 dark:text-gray-300">
              {gpu.gpu_type}
            </span>
            <span className={gpu.idle > 0 ? "text-green-600 dark:text-green-400 font-medium" : "text-gray-500"}>
              {gpu.idle}/{gpu.total}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

GpuList.propTypes = {
  gpus: PropTypes.arrayOf(
    PropTypes.shape({
      gpu_type: PropTypes.string.isRequired,
      total: PropTypes.number.isRequired,
      used: PropTypes.number.isRequired,
      idle: PropTypes.number.isRequired,
    })
  ),
};

/**
 * Queue stats display.
 */
function QueueStats({ queue }) {
  if (!queue) return null;

  return (
    <div className="flex items-center gap-3 text-xs">
      <span className="text-gray-500 dark:text-gray-400">Queue:</span>
      <span className="text-green-600 dark:text-green-400">{queue.running} running</span>
      <span className="text-yellow-600 dark:text-yellow-400">{queue.pending} pending</span>
    </div>
  );
}

QueueStats.propTypes = {
  queue: PropTypes.shape({
    running: PropTypes.number,
    pending: PropTypes.number,
    pending_reasons: PropTypes.object,
  }),
};

/**
 * Collapsible partition card.
 */
function PartitionCard({ partition, queue }) {
  const stateColor = partition.state === "UP"
    ? "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300"
    : "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300";

  return (
    <Disclosure>
      {({ open }) => (
        <div className="border border-gray-200 dark:border-gray-600 rounded-lg overflow-hidden">
          <DisclosureButton className="w-full flex items-center justify-between py-2 px-3 hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors">
            <div className="flex items-center gap-2">
              <ChevronRightIcon
                className={`h-3 w-3 text-gray-500 dark:text-gray-400 transition-transform ${open ? 'rotate-90' : ''}`}
              />
              <span className="font-medium text-sm text-gray-900 dark:text-white">
                {partition.name}
              </span>
            </div>
            <span className={`text-xs px-1.5 py-0.5 rounded ${stateColor}`}>
              {partition.state}
            </span>
          </DisclosureButton>
          <DisclosurePanel className="px-3 pt-3 pb-3 space-y-2">
            <ResourceBar
              used={partition.cpus_allocated}
              total={partition.cpus_total}
              label="CPUs"
              colorClass="bg-blue-500"
            />

            <ResourceBar
              used={partition.nodes_allocated}
              total={partition.nodes_total}
              label="Nodes"
              colorClass="bg-purple-500"
            />

            <GpuList gpus={partition.gpus} />

            <QueueStats queue={queue} />
          </DisclosurePanel>
        </div>
      )}
    </Disclosure>
  );
}

PartitionCard.propTypes = {
  partition: PropTypes.shape({
    name: PropTypes.string.isRequired,
    state: PropTypes.string.isRequired,
    cpus_total: PropTypes.number.isRequired,
    cpus_idle: PropTypes.number.isRequired,
    cpus_allocated: PropTypes.number.isRequired,
    nodes_total: PropTypes.number.isRequired,
    nodes_idle: PropTypes.number.isRequired,
    nodes_allocated: PropTypes.number.isRequired,
    gpus: PropTypes.array,
  }).isRequired,
  queue: PropTypes.object,
};

/**
 * Loading skeleton for partition cards.
 */
function LoadingSkeleton() {
  return (
    <div className="space-y-1.5 animate-pulse">
      {[1, 2].map((i) => (
        <div key={i} className="border border-gray-200 dark:border-gray-600 rounded-lg p-3 space-y-2">
          <div className="flex justify-between">
            <div className="h-4 bg-gray-200 dark:bg-gray-600 rounded w-20" />
            <div className="h-4 bg-gray-200 dark:bg-gray-600 rounded w-8" />
          </div>
          <div className="h-2 bg-gray-200 dark:bg-gray-600 rounded" />
          <div className="h-2 bg-gray-200 dark:bg-gray-600 rounded" />
        </div>
      ))}
    </div>
  );
}

/**
 * Cluster status dropdown for navbar.
 * Shows partition resources and queue stats for Slurm profiles.
 */
function ClusterStatusDropdown() {
  const { profile } = useContext(ProfileContext);
  const { status, error, isLoading } = useClusterStatus(profile);

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
        <PopoverPanel className="absolute right-0 z-50 mt-1 w-80 origin-top-right rounded-lg bg-white dark:bg-gray-700 shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none">
          <div className="p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
                Cluster Status
              </h3>
              {status?.timestamp && (
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  {new Date(status.timestamp).toLocaleTimeString()}
                </span>
              )}
            </div>

            {isLoading && <LoadingSkeleton />}

            {error && (
              <Alert variant="error">
                Failed to load cluster status
              </Alert>
            )}

            {!isLoading && !error && !hasData && (
              <div className="text-sm text-gray-500 dark:text-gray-400 text-center py-4">
                No partition data available
              </div>
            )}

            {!isLoading && !error && hasData && (
              <div className="space-y-1.5 max-h-96 overflow-y-auto">
                {partitions.map((partition) => (
                  <PartitionCard
                    key={partition.name}
                    partition={partition}
                    queue={status.queue?.[partition.name]}
                  />
                ))}
              </div>
            )}
          </div>
        </PopoverPanel>
      </Transition>
    </Popover>
  );
}

export default ClusterStatusDropdown;
