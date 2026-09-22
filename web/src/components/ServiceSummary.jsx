import React from "react";
import {
  InformationCircleIcon,
  HeartIcon,
  ClockIcon,
  CloudIcon,
  CpuChipIcon,
  FireIcon,
  CubeTransparentIcon,
  CircleStackIcon,
  LockClosedIcon,
} from "@heroicons/react/24/outline";
import PropTypes from "prop-types";
import { formattedTimeInterval, isServiceRunning } from "@/lib/util";
import { useServiceApiKeyStatus } from "@/lib/loaders";

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
 * @return {JSX.Element}
 */
/**
 * Access badge: whether a service requires an API key.
 *
 * Amber rather than red for an unprotected service — running one open is a
 * deliberate choice, not a failure, and red here would cry wolf next to the
 * status badge that uses it for real faults.
 * @param {object} options
 * @param {boolean} options.protected
 * @return {JSX.Element}
 */
const AccessBadge = ({ protected: isProtected }) => {
  const colors = isProtected
    ? "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300"
    : "bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300";

  return (
    <span
      className={`text-xs px-1.5 py-0.5 rounded ${colors}`}
      title={
        isProtected
          ? "Requests to this service must carry its API key"
          : "Anyone who can reach this service can use it"
      }
    >
      {isProtected ? "Protected" : "Unprotected"}
    </span>
  );
};

AccessBadge.propTypes = {
  protected: PropTypes.bool,
};

function ServiceSummary({
  service,
  profile,
}) {
  // Declared before the early returns below: hooks must run unconditionally.
  const { configured: apiKeyConfigured } = useServiceApiKeyStatus(service?.id);

  if (profile && !service) {
    return <></>;
  }

  if (!profile) {
    return (
      <div className="flex flex-row justify-start">
        <div className="grow flex flex-col justify-center mt-3 mb-0">
          <div className="mt-2 ml-1 font-light text-sm sm:flex sm:flex-col text-gray-400 dark:text-gray-500">
            <div className="mb-1 ml-0 inline-flex justify-start items-center">
              <InformationCircleIcon className="h-6 w-6 text-gray-300 dark:text-gray-600 mr-1" />
              <div className="grow font-regular text-sm mr-1">Model </div>
              <span className="mr-2">-</span>
            </div>
            <div className="mb-1 ml-0 inline-flex justify-start items-center">
              <CubeTransparentIcon className="h-6 w-6 text-gray-300 dark:text-gray-600 mr-1" />
              <div className="grow font-regular text-sm mr-1">Image </div>
              <span className="mr-2">-</span>
            </div>
            <div className="mb-1 ml-0 inline-flex justify-start items-center capitalize">
              <HeartIcon className="h-6 w-6 text-gray-300 dark:text-gray-600 mr-1" />
              <div className="grow font-regular text-sm mr-1">Status </div>
              <span className="mr-2">-</span>
            </div>
            <div className="mb-1 ml-0 inline-flex items-center">
              <ClockIcon className="h-6 w-6 text-gray-300 dark:text-gray-600 mr-1" />
              <div className="grow font-regular text-sm mr-1">Time </div>
              <span className="mr-2">-</span>
            </div>
            <div className="mb-1 ml-0 inline-flex items-center">
              <CloudIcon className="h-6 w-6 text-gray-300 dark:text-gray-600 mr-1" />
              <div className="grow font-regular text-sm mr-1">Host </div>
              <span className="mr-2">-</span>
            </div>
            <div className="mb-1 ml-0 inline-flex items-center">
              <LockClosedIcon className="h-6 w-6 text-gray-300 dark:text-gray-600 mr-1" />
              <div className="grow font-regular text-sm mr-1">Access </div>
              <span className="mr-2">-</span>
            </div>
            <div className="mb-1 ml-0 inline-flex items-center">
              <CpuChipIcon className="h-6 w-6 text-gray-300 dark:text-gray-600 mr-1" />
              <div className="grow font-regular text-sm mr-1">Cores </div>
              <span className="mr-2">-</span>
            </div>
            <div className="mb-1 ml-0 inline-flex items-center">
              <CircleStackIcon className="h-6 w-6 text-gray-300 dark:text-gray-600 mr-1" />
              <div className="grow font-regular text-sm mr-1">Memory </div>
              <span className="mr-2">-</span>
            </div>
            <div className="mb-1 ml-0 inline-flex items-center">
              <FireIcon className="h-6 w-6 text-gray-300 dark:text-gray-600 mr-1" />
              <div className="grow font-regular text-sm mr-1">GPU </div>
              <span className="mr-2">-</span>
            </div>
          </div>
          <div className="grow text-center mt-2 font-light text-xs mb-4 text-gray-300 dark:text-gray-600">
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
        <div className="mt-2 ml-1 font-light text-sm sm:flex sm:flex-col text-gray-900 dark:text-gray-100">
          <div className="mb-1 ml-0 inline-flex justify-start items-center">
            <InformationCircleIcon className="h-6 w-6 text-gray-600 dark:text-gray-400 mr-1" />
            <div className="grow font-medium text-sm mr-1">Model </div>
            {service?.model
              ? service.model.split("/")[1] || service.model
              : "-"}
          </div>
          <div className="mb-1 ml-0 inline-flex justify-start items-center">
            <CubeTransparentIcon className="h-6 w-6 text-gray-600 dark:text-gray-400 mr-1" />
            <div className="grow font-medium text-sm mr-1">Image </div>
            {/* Show the tag only — a full "repo:tag" overflows this column.
                The complete reference is in the title attribute. */}
            <span className="service-summary__image" title={service?.image_ref || undefined}>
              {service?.image_ref ? service.image_ref.split(":").pop() : "-"}
            </span>
          </div>
          <div className="mb-1 ml-0 inline-flex justify-start items-center capitalize">
            <HeartIcon className="h-6 w-6 text-gray-600 dark:text-gray-400 mr-1" />
            <div className="grow font-medium text-sm mr-1">Status </div>
            <div className="service-summary__status">
              {service?.status ? service.status.toLowerCase() : "-"}
            </div>
          </div>
          <div className="mb-1 ml-0 inline-flex items-center">
            <ClockIcon className="h-6 w-6 text-gray-600 dark:text-gray-400 mr-1" />
            <div className="grow font-medium text-sm mr-1">Time </div>
            {service?.created_at && isServiceRunning(service) ? (
              <Timer refTime={new Date(service.created_at)} />
            ) : (
              "-"
            )}
          </div>
          <div className="mb-1 ml-0 inline-flex items-center">
            <CloudIcon className="h-6 w-6 text-gray-600 dark:text-gray-400 mr-1" />
            <div className="grow font-medium text-sm mr-1">Host </div>
            {service?.host && isServiceRunning(service)
              ? service.port
                ? `${service.host}:${service.port}`
                : service.host
              : "-"}
          </div>
          <div className="mb-1 ml-0 inline-flex items-center">
            <LockClosedIcon className="h-6 w-6 text-gray-600 dark:text-gray-400 mr-1" />
            <div className="grow font-medium text-sm mr-1">Access </div>
            {/* Whether the service requires a key, not which key it is: the
                user set it, and four characters would not remind them. An
                unprotected service says so plainly rather than showing "-",
                since "no key" is a meaningful state, not missing data. */}
            <span className="service-summary__api-key">
              {/* Undefined until the status resolves: say nothing rather than
                  claiming a protected service is open. */}
              {apiKeyConfigured === undefined ? (
                "-"
              ) : (
                <AccessBadge protected={apiKeyConfigured} />
              )}
            </span>
          </div>
          <div className="mb-1 ml-0 inline-flex items-center">
            <CpuChipIcon className="h-6 w-6 text-gray-600 dark:text-gray-400 mr-1" />
            <div className="grow font-medium text-sm mr-1">Cores </div>
            {service?.ntasks_per_node || "-"}
          </div>
          <div className="mb-1 ml-0 inline-flex items-center">
            <CircleStackIcon className="h-6 w-6 text-gray-600 dark:text-gray-400 mr-1" />
            <div className="grow font-medium text-sm mr-1">Memory </div>
            {service?.mem || "-"}
          </div>
          <div className="mb-1 ml-0 inline-flex items-center">
            <FireIcon className="h-6 w-6 text-gray-600 dark:text-gray-400 mr-1" />
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
            <div className="service-summary__updated-at grow text-center mt-2 font-light text-xs mb-4 text-gray-500 dark:text-gray-400">
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
      </div>
    </div>
  );
}

ServiceSummary.propTypes = {
  service: PropTypes.object,
  profile: PropTypes.object,
};

export default ServiceSummary;
