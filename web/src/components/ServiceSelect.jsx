import { useContext, Fragment } from "react";
import {
  Listbox,
  ListboxButton,
  ListboxOption,
  ListboxOptions,
  Transition,
} from "@headlessui/react";
import {
  CheckIcon,
  ChevronUpDownIcon,
  ExclamationTriangleIcon,
} from "@heroicons/react/20/solid";
import Alert from "@/components/Alert";
import { useServices } from "@/lib/loaders";
import { ServiceStatus, classNames, getStatusDotClasses } from "@/lib/util";
import { ServiceContext } from "@/providers/ServiceProvider";
import PropTypes from "prop-types";


/**
 * Service Select component.
 * @param {object} options
 * @param {object} options.profile
 * @param {string} options.task
 * @return {JSX.Element}
 */
function ServiceSelect({ profile, task, onLaunch }) {

  const { services, error, isLoading } = useServices(profile, task);
  const { selectedService, setSelectedServiceId } = useContext(ServiceContext);

  if (error) {
    return (
      <Alert variant="error" title="Failed to fetch services" className="mt-2 mb-4">
        We ran into an issue while fetching the services available for this profile.
      </Alert>
    );
  }

  if (isLoading) {
    return (
      <div className="animate-pulse rounded-md bg-gray-100 p-4 mt-2 mb-4 h-72">
      </div>
    );
  }

  if (profile && services.length === 0) {
    return (
      <Alert variant="warning" title="No services available" className="mt-2 mb-4">
        <button type="button" onClick={onLaunch} className="underline hover:no-underline">
          Launch a new service
        </button> to get started.
      </Alert>
    );
  }

  return (
    <Listbox value={selectedService} onChange={setSelectedServiceId}>
      {({ open }) => (
        <>
          <div className="relative">
            {
              selectedService
                ? <ListboxButton className="relative w-full cursor-default rounded-md bg-white dark:bg-gray-700 py-1.5 pl-3 pr-10 text-left text-gray-900 dark:text-gray-100 shadow-sm ring-1 ring-inset ring-gray-300 dark:ring-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500 sm:text-sm sm:leading-6">
                  <span className="flex items-center">
                    {
                      selectedService &&
                      <span
                        aria-label={
                          selectedService.status === ServiceStatus.HEALTHY
                            ? "Online"
                            : "Offline"
                        }
                        className={classNames(
                          getStatusDotClasses(selectedService.status),
                          "inline-block h-2 w-2 flex-shrink-0 rounded-full"
                        )}
                      />
                    }
                    <span className="ml-3 block truncate">
                      {selectedService ? selectedService.name : ""}
                    </span>
                  </span>
                  <span className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2">
                    <ChevronUpDownIcon
                      className="h-5 w-5 text-gray-400"
                      aria-hidden="true"
                    />
                  </span>
                </ListboxButton>
                : (
                  profile
                    ? <ListboxButton className="relative w-full cursor-default rounded-md bg-white dark:bg-gray-700 py-1.5 pl-3 pr-10 text-left text-gray-900 dark:text-gray-100 shadow-sm ring-1 ring-inset ring-gray-300 dark:ring-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500 sm:text-sm sm:leading-6">
                      <span className="flex items-center">
                        {
                          selectedService &&
                          <span
                            aria-label={
                              selectedService.status === ServiceStatus.HEALTHY
                                ? "Online"
                                : "Offline"
                            }
                            className={classNames(
                              getStatusDotClasses(selectedService.status),
                              "inline-block h-2 w-2 flex-shrink-0 rounded-full"
                            )}
                          />
                        }
                        <span className="ml-3 block truncate">
                          No service selected
                        </span>
                      </span>
                      <span className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2">
                        <ChevronUpDownIcon
                          className="h-5 w-5 text-gray-400"
                          aria-hidden="true"
                        />
                      </span>
                    </ListboxButton>
                    : <ListboxButton
                      className="relative w-full cursor-default rounded-md bg-gray-50 dark:bg-gray-800 py-1.5 pl-1 pr-10 text-left text-gray-400 dark:text-gray-500 font-light shadow-sm ring-1 ring-inset ring-gray-200 dark:ring-gray-700 focus:outline-none sm:text-sm sm:leading-6"
                      disabled
                    >
                      <span className="flex items-center">
                        <span className="pointer-events-none flex-shrink-0 pl-3">
                          <ExclamationTriangleIcon
                            className="h-5 w-5 text-gray-300"
                            aria-hidden="true"
                          />
                        </span>
                        <span className="ml-3 block truncate">
                          {"No profile selected"}
                        </span>
                        <span className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2">
                          <ChevronUpDownIcon
                            className="h-5 w-5 text-gray-300"
                            aria-hidden="true"
                          />
                        </span>
                      </span>
                    </ListboxButton>
                )
            }
            <Transition
              show={open}
              as={Fragment}
              leave="transition ease-in duration-100"
              leaveFrom="opacity-100"
              leaveTo="opacity-0"
            >
              <ListboxOptions className="absolute z-10 mt-1 max-h-60 w-full overflow-auto rounded-md bg-white dark:bg-gray-700 py-1 text-base shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none sm:text-sm">
                {services.map((service) => (
                  <ListboxOption
                    key={service.id}
                    className={({ focus }) =>
                      classNames(
                        focus ? "bg-blue-500 text-white" : "text-gray-900 dark:text-gray-100",
                        "relative cursor-default select-none py-2 pl-3 pr-9"
                      )
                    }
                    value={service.id}
                  >
                    {({ selected, focus }) => (
                      <>
                        <div className="flex items-center">
                          <span
                            className={classNames(
                              getStatusDotClasses(service.status),
                              "inline-block h-2 w-2 flex-shrink-0 rounded-full"
                            )}
                            aria-hidden="true"
                          />
                          <span
                            className={classNames(
                              selected ? "font-semibold" : "font-normal",
                              "ml-3 block truncate"
                            )}
                          >
                            {service.name}
                            <span className="sr-only">
                              {" "}
                              is{" "}
                              {service.status === ServiceStatus.HEALTHY
                                ? "online"
                                : "offline"}
                            </span>
                          </span>
                        </div>

                        {selected ? (
                          <span
                            className={classNames(
                              focus ? "text-white" : "text-blue-600",
                              "absolute inset-y-0 right-0 flex items-center pr-4"
                            )}
                          >
                            <CheckIcon className="h-5 w-5" aria-hidden="true" />
                          </span>
                        ) : null}
                      </>
                    )}
                  </ListboxOption>
                ))}
              </ListboxOptions>
            </Transition>
          </div>
        </>
      )}
    </Listbox>
  );
}

ServiceSelect.propTypes = {
  profile: PropTypes.object,
  task: PropTypes.string,
  onLaunch: PropTypes.func,
};

export default ServiceSelect;
