import { useContext, Fragment } from "react";
import {
  Field,
  Listbox,
  ListboxButton,
  ListboxOption,
  ListboxOptions,
  Label,
  Transition,
} from "@headlessui/react";
import {
  CheckIcon,
  ChevronUpDownIcon,
  ExclamationTriangleIcon,
} from "@heroicons/react/20/solid";
import { ExclamationCircleIcon } from "@heroicons/react/24/solid";
import { useServices } from "@/lib/loaders";
import { ServiceStatus, classNames } from "@/lib/util";
import { ServiceContext } from "@/providers/ServiceProvider";
import PropTypes from "prop-types";


const terminalStates = ["stopped", "expired"];


/**
 * Service Select component.
 * @param {object} options
 * @param {object} options.profile
 * @param {string} options.task
 * @return {JSX.Element}
 */
function ServiceSelect({ profile, task }) {

  const { services, error, isLoading } = useServices(profile, task);
  const { selectedService, setSelectedServiceId } = useContext(ServiceContext);

  if (error) {
    return (
      <div className="rounded-md bg-red-50 border-red-100 ring-1 ring-red-300 p-4 mt-2 mb-4">
        <div className="flex">
          <div className="flex-shrink-0">
            <ExclamationCircleIcon
              aria-hidden="true"
              className="size-5 text-red-500"
            />
          </div>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-red-800">
              Failed to fetch services
            </h3>
            <div className="mt-2 font-light text-sm text-red-800">
              <p>We ran into an issue while fetching the services available for this profile.</p>
            </div>
          </div>
        </div>
      </div>
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
      <Field>
        <Label className="pt-2 block text-sm font-medium leading-6 text-gray-900">
          Services
        </Label>
        <div className="rounded-md bg-yellow-50 border-yellow-100 ring-1 ring-yellow-300 p-4 mt-2 mb-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <ExclamationTriangleIcon
                aria-hidden="true"
                className="h-5 w-5 text-yellow-400"
              />
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-yellow-800">
                No services available
              </h3>
              <div className="mt-2 font-light text-sm text-yellow-800">
                <p>Click on the button below to create a new service under the selected profile.</p>
              </div>
            </div>
          </div>
        </div>
      </Field>
    );
  }

  return (
    <Listbox value={selectedService} onChange={setSelectedServiceId}>
      {({ open }) => (
        <>
          <Label className="pt-2 block text-sm font-medium leading-6 text-gray-900">
            Services
          </Label>
          <div className="relative mt-2">
            {
              selectedService
                ? <ListboxButton className="relative w-full cursor-default rounded-md bg-white py-1.5 pl-3 pr-10 text-left text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 sm:text-sm sm:leading-6">
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
                          terminalStates.includes(selectedService.status)
                            ? "bg-gray-200"
                            : selectedService.status === ServiceStatus.HEALTHY
                              ? "bg-green-500"
                              : selectedService.status === ServiceStatus.TIMEOUT ||
                                selectedService.status === ServiceStatus.FAILED
                                ? "bg-red-500"
                                : selectedService.status === ServiceStatus.SUBMITTED
                                  ? "bg-yellow-500"
                                  : selectedService.status === ServiceStatus.STARTING ||
                                    selectedService.status === ServiceStatus.PENDING
                                    ? "animate-pulse bg-green-500"
                                    : "bg-transparent border border-gray-300",
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
                    ? <ListboxButton className="relative w-full cursor-default rounded-md bg-white py-1.5 pl-3 pr-10 text-left text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 sm:text-sm sm:leading-6">
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
                              terminalStates.includes(selectedService.status)
                                ? "bg-gray-200"
                                : selectedService.status === ServiceStatus.HEALTHY
                                  ? "bg-green-500"
                                  : selectedService.status === ServiceStatus.TIMEOUT ||
                                    selectedService.status === ServiceStatus.FAILED
                                    ? "bg-red-500"
                                    : selectedService.status === ServiceStatus.SUBMITTED
                                      ? "bg-yellow-500"
                                      : selectedService.status === ServiceStatus.STARTING ||
                                        selectedService.status === ServiceStatus.PENDING
                                        ? "animate-pulse bg-green-500"
                                        : "bg-transparent border border-gray-300",
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
                      className="relative w-full cursor-default rounded-md bg-gray-50 py-1.5 pl-1 pr-10 text-left text-gray-400 font-light shadow-sm ring-1 ring-inset ring-gray-200 focus:outline-none sm:text-sm sm:leading-6"
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
              <ListboxOptions className="absolute z-10 mt-1 max-h-60 w-full overflow-auto rounded-md bg-white py-1 text-base shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none sm:text-sm">
                {services.map((service) => (
                  <ListboxOption
                    key={service.id}
                    className={({ focus }) =>
                      classNames(
                        focus ? "bg-blue-500 text-white" : "text-gray-900",
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
                              terminalStates.includes(service.status)
                                ? "bg-gray-200"
                                : service.status === ServiceStatus.HEALTHY
                                  ? "bg-green-500"
                                  : service.status === ServiceStatus.TIMEOUT ||
                                    service.status === ServiceStatus.FAILED
                                    ? "bg-red-500"
                                    : service.status === ServiceStatus.SUBMITTED
                                      ? "bg-yellow-500"
                                      : service.status === ServiceStatus.STARTING ||
                                        service.status === ServiceStatus.PENDING
                                        ? "animate-pulse bg-green-500"
                                        : "bg-transparent border border-gray-300",
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
};

export default ServiceSelect;
