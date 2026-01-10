import React from "react";
import {
  InformationCircleIcon,
  HeartIcon,
  ClockIcon,
  CloudIcon,
  CpuChipIcon,
  FireIcon,
  CubeTransparentIcon,
} from "@heroicons/react/24/outline";
import { deleteService, stopService } from "../lib/requests";
import { ServiceStatus } from "../lib/util";
import { useServices } from "../lib/loaders"
import PropTypes from "prop-types";
import { formattedTimeInterval, isServiceRunning } from "@/app/lib/util";

/**
 * Timer
 * @param {object} options
 * @param {Date} options.refTime
 */
const Timer = ({ refTime }) => {
  const [currentTime, setCurrentTime] = React.useState(new Date());

  React.useEffect(() => {
    const interval = setInterval(() => {
      setCurrentTime(new Date());
    }, 30_000);

    return () => clearInterval(interval);
  }, []);

  return <div>{formattedTimeInterval(refTime, currentTime)}</div>;
};

Timer.propTypes = {
  refTime: PropTypes.object,
};

/**
 * Service Summary component.
 * @param {object} options
 * @param {object} options.service
 * @param {object} options.profile
 * @param {string} options.task
 * @return {JSX.Element}
 */
function ServiceSummary({
  service,
  profile,
  task
}) {
  const { mutate } = useServices(profile, task);
  const [isUpdating, setIsUpdating] = React.useState(false);

  const handleStopService = async () => {
    if (service == null) return;
    setIsUpdating(true);
    try {
      await stopService(service.id);
      await mutate();
    } catch (e) {
      console.error("An error occurred while stopping a service:", e);
    }
    setIsUpdating(false);
  };

  const handleDeleteService = async () => {
    if (service == null) return;
    setIsUpdating(true);
    try {
      await deleteService(service.id);
      await mutate();
    } catch (e) {
      console.error("An error occurred while deleting a service:", e);
    }
    setIsUpdating(false);
  };

  const renderActionButton = () => {
    if (!service) {
      console.warn("Service is missing.")
      return null;
    }
    if (service?.status == null) {
      return null;
    }

    switch (service.status) {
      case ServiceStatus.UNHEALTHY:
      case ServiceStatus.HEALTHY:
        return (
          <button
            type="button"
            className="w-full flex flex-row justify-center gap-x-2 rounded-md
            bg-transparent px-3.5 py-1.5 text-sm font-regular shadow-sm
            hover:bg-slate-50 focus-visible:outline focus-visible:outline-2
            focus-visible:outline-offset-2 border"
            onClick={handleStopService}
          >
            Stop
          </button>
        );
      case ServiceStatus.STARTING:
      case ServiceStatus.PENDING:
      case ServiceStatus.SUBMITTED:
        return (
          <button
            type="button"
            className="w-full flex flex-row justify-center gap-x-2 rounded-md
            bg-transparent px-3.5 py-1.5 text-sm font-regular shadow-sm
            hover:bg-slate-50 focus-visible:outline focus-visible:outline-2
            focus-visible:outline-offset-2 border"
            onClick={handleStopService}
          >
            Cancel
          </button>
        );
      case ServiceStatus.STOPPED:
      case ServiceStatus.EXPIRED:
      case ServiceStatus.TIMEOUT:
      case ServiceStatus.FAILED:
        return (
          <button
            type="button"
            className="w-full flex flex-row justify-center gap-x-2 rounded-md
            bg-transparent px-3.5 py-1.5 text-sm font-regular shadow-sm
            hover:bg-slate-50 focus-visible:outline focus-visible:outline-2
             focus-visible:outline-offset-2 border"
            onClick={handleDeleteService}
          >
            Delete
          </button>
        );
      default:
        return null;
    }
  };

  if (profile && !service) {
    return <></>;
  }

  if (!profile) {
    return (
      <div className="flex flex-row justify-start">
        <div className="grow flex flex-col justify-center mt-3 mb-0">
          <div className="mt-2 ml-1 font-light text-sm sm:flex sm:flex-col text-gray-400">
            <div className="mb-1 ml-0 inline-flex justify-start items-center">
              <InformationCircleIcon className="h-6 w-6 text-gray-300 mr-1" />
              <div className="grow font-regular text-sm mr-1">Model </div>
              <span className="mr-2">-</span>
            </div>
            <div className="mb-1 ml-0 inline-flex justify-start items-center capitalize">
              <HeartIcon className="h-6 w-6 text-gray-300 mr-1" />
              <div className="grow font-regular text-sm mr-1">Status </div>
              <span className="mr-2">-</span>
            </div>
            <div className="mb-1 ml-0 inline-flex items-center">
              <ClockIcon className="h-6 w-6 text-gray-300 mr-1" />
              <div className="grow font-regular text-sm mr-1">Time </div>
              <span className="mr-2">-</span>
            </div>
            <div className="mb-1 ml-0 inline-flex items-center">
              <CloudIcon className="h-6 w-6 text-gray-300 mr-1" />
              <div className="grow font-regular text-sm mr-1">Host </div>
              <span className="mr-2">-</span>
            </div>
            <div className="mb-1 ml-0 inline-flex items-center">
              <CpuChipIcon className="h-6 w-6 text-gray-300 mr-1" />
              <div className="grow font-regular text-sm mr-1">Cores </div>
              <span className="mr-2">-</span>
            </div>
            <div className="mb-1 ml-0 inline-flex items-center">
              <CubeTransparentIcon className="h-6 w-6 text-gray-300 mr-1" />
              <div className="grow font-regular text-sm mr-1">Memory </div>
              <span className="mr-2">-</span>
            </div>
            <div className="mb-1 ml-0 inline-flex items-center">
              <FireIcon className="h-6 w-6 text-gray-300 mr-1" />
              <div className="grow font-regular text-sm mr-1">GPU </div>
              <span className="mr-2">-</span>
            </div>
          </div>
          <div className="grow text-center mt-2 font-light text-xs mb-4 text-gray-300">
            Last updated
            <div>-</div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-row justify-start">
      <div className="grow flex flex-col justify-center mt-3 mb-0">
        <div className="mt-2 ml-1 font-light text-sm sm:flex sm:flex-col">
          <div className="mb-1 ml-0 inline-flex justify-start items-center">
            <InformationCircleIcon className="h-6 w-6 text-gray-600 mr-1" />
            <div className="grow font-medium text-sm mr-1">Model </div>
            {service?.model
              ? service.model.split("/")[1] || service.model
              : "-"}
          </div>
          <div className="mb-1 ml-0 inline-flex justify-start items-center capitalize">
            <HeartIcon className="h-6 w-6 text-gray-600 mr-1" />
            <div className="grow font-medium text-sm mr-1">Status </div>
            {isUpdating ? (
              <div className="service-summary__status--updating service-summary__status bg-gray-300 rounded-md h-4 w-28 animate-pulse"></div>
            ) : (
              <div
                className={`service-summary__status ${service?.status === ServiceStatus.STARTING ? "animate-pulse" : ""}`.trim()}
              >
                {service?.status ? service.status.toLowerCase() : "-"}
              </div>
            )}
          </div>
          <div className="mb-1 ml-0 inline-flex items-center">
            <ClockIcon className="h-6 w-6 text-gray-600 mr-1" />
            <div className="grow font-medium text-sm mr-1">Time </div>
            {service?.created_at && isServiceRunning(service) ? (
              <Timer refTime={new Date(service.created_at)} />
            ) : (
              "-"
            )}
          </div>
          <div className="mb-1 ml-0 inline-flex items-center">
            <CloudIcon className="h-6 w-6 text-gray-600 mr-1" />
            <div className="grow font-medium text-sm mr-1">Host </div>
            {service?.host && isServiceRunning(service)
              ? service.port
                ? `${service.host}:${service.port}`
                : service.host
              : "-"}
          </div>
          <div className="mb-1 ml-0 inline-flex items-center">
            <CpuChipIcon className="h-6 w-6 text-gray-600 mr-1" />
            <div className="grow font-medium text-sm mr-1">Cores </div>
            {service?.ntasks_per_node || "-"}
          </div>
          <div className="mb-1 ml-0 inline-flex items-center">
            <CubeTransparentIcon className="h-6 w-6 text-gray-600 mr-1" />
            <div className="grow font-medium text-sm mr-1">Memory </div>
            {service?.mem || "-"}
          </div>
          <div className="mb-1 ml-0 inline-flex items-center">
            <FireIcon className="h-6 w-6 text-gray-600 mr-1" />
            <div className="grow font-medium text-sm mr-1">GPU </div>
            <span className="gpus-indicator">
              {"gres" in service && !Number.isNaN(service.gres + 0)
                ? service?.gres > 0
                  ? "🔥".repeat(service.gres)
                  : "🧊"
                : "-"}
            </span>
          </div>
          {service?.updated_at ? (
            <div className="service-summary__updated-at grow text-center mt-2 font-light text-xs mb-4">
              Last updated
              <Timer
                refTime={new Date(service.updated_at)}
                currentTime={new Date()}
              />
            </div>
          ) : (
            <div className="service-summary__updated-at--empty service-summary__updated-at grow text-center mt-2 font-light text-xs mb-2">
              <div></div>
            </div>
          )}
        </div>
        {renderActionButton()}
      </div>
    </div>
  );
}

ServiceSummary.propTypes = {
  service: PropTypes.object,
  profile: PropTypes.object,
  task: PropTypes.string,
};

export default ServiceSummary;
