import { useContext, useState } from "react";
import { Popover, PopoverButton, PopoverPanel } from "@headlessui/react";
import {
  AdjustmentsHorizontalIcon,
  StopIcon,
  TrashIcon,
  XMarkIcon,
} from "@heroicons/react/24/outline";
import ServiceSelect from "./ServiceSelect";
import ServiceSummary from "./ServiceSummary";
import ServiceLauncher from "./ServiceLauncher";
import { ServiceContext } from "@/providers/ServiceProvider";
import { useServices } from "@/lib/loaders";
import { deleteService, stopService } from "@/lib/requests";
import { getStatusBadgeClasses } from "@/lib/util";
import PropTypes from "prop-types";

const terminalStates = ["stopped", "expired", "timeout", "failed"];

/**
 * Status Badge component.
 * @param {object} options
 * @param {string} options.status
 * @return {JSX.Element}
 */
function StatusBadge({ status }) {
  const { fillColor, bgColor, textColor } = getStatusBadgeClasses(status);

  return (
    <span className={`inline-flex items-center gap-x-1.5 rounded-md px-2 py-1 text-xs font-medium ${bgColor} ${textColor}`}>
      <svg viewBox="0 0 6 6" aria-hidden="true" className={`size-1.5 ${fillColor}`}>
        <circle r={3} cx={3} cy={3} />
      </svg>
      {status ? status.charAt(0).toUpperCase() + status.slice(1).toLowerCase() : "None"}
    </span>
  );
}

StatusBadge.propTypes = {
  status: PropTypes.string,
};

/**
 * Service Container component.
 * @param {object} options
 * @param {object} options.profile
 * @param {string} options.task
 * @param {object} options.defaultContainerOptions
 * @param {JSX.Element} options.ContainerOptionsFormComponent
 * @param {JSX.Element} options.ParametersFormComponent
 * @param {object} options.parametersFormProps
 * @return {JSX.Element}
 */
function ServiceContainer({
  profile,
  task,
  defaultContainerOptions,
  ContainerOptionsFormComponent,
  ParametersFormComponent,
  parametersFormProps,
}) {
  const { selectedService } = useContext(ServiceContext);
  const { mutate } = useServices(profile, task);
  const [isUpdating, setIsUpdating] = useState(false);
  const [launchOpen, setLaunchOpen] = useState(false);

  const handleStopService = async () => {
    if (selectedService == null) return;
    setIsUpdating(true);
    try {
      await stopService(selectedService.id);
      await mutate();
    } catch (e) {
      console.error("An error occurred while stopping a service:", e);
    }
    setIsUpdating(false);
  };

  const handleDeleteService = async () => {
    if (selectedService == null) return;
    setIsUpdating(true);
    try {
      await deleteService(selectedService.id);
      await mutate();
    } catch (e) {
      console.error("An error occurred while deleting a service:", e);
    }
    setIsUpdating(false);
  };

  const isRunning = selectedService && !terminalStates.includes(selectedService.status);
  const canDelete = selectedService && terminalStates.includes(selectedService.status);

  return (
    <div>
      {/* Header row */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-900 dark:text-gray-100">Service</span>
          {selectedService && <StatusBadge status={selectedService.status} />}
        </div>
        <div className="flex items-center gap-1">
          {/* Settings button with dropdown */}
          {ParametersFormComponent && (
            <Popover className="relative">
              <PopoverButton
                disabled={!selectedService}
                className="p-1.5 rounded-md text-gray-500 hover:text-gray-700 hover:bg-gray-100 dark:text-gray-400 dark:hover:text-gray-200 dark:hover:bg-gray-700 disabled:text-gray-300 dark:disabled:text-gray-600 disabled:hover:bg-transparent disabled:cursor-not-allowed focus:outline-none"
              >
                <AdjustmentsHorizontalIcon className="h-5 w-5" />
              </PopoverButton>
              <PopoverPanel
                anchor="bottom end"
                className="z-50 mt-2 w-80 rounded-lg bg-white dark:bg-gray-800 shadow-lg ring-1 ring-gray-200 dark:ring-gray-700 p-4"
              >
                {({ close }) => (
                  <div>
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-sm font-medium text-gray-900 dark:text-gray-100">Parameters</span>
                      <button
                        onClick={close}
                        className="p-1 rounded-md text-gray-400 hover:text-gray-500 dark:hover:text-gray-300 focus:outline-none"
                      >
                        <XMarkIcon className="h-4 w-4" />
                      </button>
                    </div>
                    <ParametersFormComponent {...parametersFormProps} />
                  </div>
                )}
              </PopoverPanel>
            </Popover>
          )}

          {/* Stop/Delete button */}
          {isRunning && (
            <button
              type="button"
              onClick={handleStopService}
              disabled={isUpdating}
              className="p-1.5 rounded-md text-gray-500 hover:text-red-600 hover:bg-red-50 dark:text-gray-400 dark:hover:text-red-400 dark:hover:bg-red-900/20 disabled:opacity-50 focus:outline-none"
              aria-label="Stop service"
            >
              <StopIcon className="h-5 w-5" />
            </button>
          )}
          {canDelete && (
            <button
              type="button"
              onClick={handleDeleteService}
              disabled={isUpdating}
              className="p-1.5 rounded-md text-gray-500 hover:text-red-600 hover:bg-red-50 dark:text-gray-400 dark:hover:text-red-400 dark:hover:bg-red-900/20 disabled:opacity-50 focus:outline-none"
              aria-label="Delete service"
            >
              <TrashIcon className="h-5 w-5" />
            </button>
          )}

          {/* Launcher button */}
          <ServiceLauncher
            profile={profile}
            task={task}
            defaultContainerOptions={defaultContainerOptions}
            ContainerOptionsFormComponent={ContainerOptionsFormComponent}
            open={launchOpen}
            setOpen={setLaunchOpen}
          />
        </div>
      </div>

      {/* Service select dropdown */}
      <ServiceSelect
        profile={profile}
        task={task}
        onLaunch={() => setLaunchOpen(true)}
      />

      {/* Service details */}
      <ServiceSummary
        service={selectedService}
        profile={profile}
      />
    </div>
  );
}

ServiceContainer.propTypes = {
  profile: PropTypes.object,
  task: PropTypes.string,
  defaultContainerOptions: PropTypes.object,
  ContainerOptionsFormComponent: PropTypes.elementType,
  ParametersFormComponent: PropTypes.elementType,
  parametersFormProps: PropTypes.object,
};

export default ServiceContainer;
