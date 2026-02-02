import React, { useContext } from "react";
import { Fragment, useRef, useState, useEffect } from "react";
import {
  Dialog,
  DialogPanel,
  DialogTitle,
  Transition,
  TransitionChild,
} from "@headlessui/react";
import ServiceModalForm from "@/components/ServiceModalForm";
import ServiceLaunchErrorAlert from "@/components/ServiceLaunchErrorAlert";
import { ServiceContext } from "@/providers/ServiceProvider";
import { runService, fetchProfileResources } from "@/lib/requests";
import { useModels, useServices } from "@/lib/loaders";
import { sleep, randomInt, isDeepEmpty } from "@/lib/util";
import PropTypes from "prop-types";

/**
 * Create a default job name with the form "blackfish-N".
 * @return {string}
 */
function randomName() {
  return `blackfish-${randomInt(10_000, 21_000)}`;
}

/**
 * Get default job options based on profile type.
 * @param {object} profile - The selected profile.
 * @return {object} Default job options.
 */
function getDefaultJobOptions(profile) {
  const baseOptions = {
    name: randomName(),
  };

  if (profile?.schema === "slurm") {
    // Slurm: time is user-configurable, resource fields are set by tier selection
    return {
      ...baseOptions,
      time: "00:30:00",
      ntasks_per_node: null,
      mem: null,
      gres: null,
      partition: null,
      constraint: null,
      account: null,
    };
  } else {
    // Local: only gres matters, default to disabled (most users don't have Nvidia GPUs)
    return {
      ...baseOptions,
      gres: 0,
    };
  }
}

/**
 * Service Modal component.
 * @param {object} options
 * @param {string} options.task
 * @param {boolean} options.open
 * @param {Function} options.setOpen
 * @param {object} options.defaultContainerOptions
 * @param {object} options.containerOptions
 * @param {Function} options.setContainerOptions
 * @param {boolean} options.launchSuccess
 * @param {Function} options.setLaunchSuccess
 * @param {boolean} options.isLaunching
 * @param {Function} options.setIsLaunching
 * @param {object} options.launchError
 * @param {Function} options.setLaunchError
 * @param {object} options.validationErrors
 * @param {Function} options.setValidationErrors
 * @param {object} options.profile
 * @param {JSX.Element} options.children
 * @return {JSX.Element}
 */
function ServiceModal({
  task,
  open,
  setOpen,
  defaultContainerOptions,
  containerOptions,
  setContainerOptions,
  launchSuccess,
  setLaunchSuccess,
  isLaunching,
  setIsLaunching,
  launchError,
  setLaunchError,
  validationErrors,
  setValidationErrors,
  profile,
  children
}) {


  const maxAttempts = 3;
  const waitPeriod = 5_000;

  const {
    services,
    mutate: mutateServices
  } = useServices(profile, task);
  const {
    models,
  } = useModels(profile, task);

  const { setSelectedServiceId } = useContext(ServiceContext);


  const [jobOptions, setJobOptions] = React.useState(() => getDefaultJobOptions(profile));
  const [model, setModel] = useState(null);
  const [resources, setResources] = useState(null);

  // Fetch resources when profile changes
  useEffect(() => {
    if (profile && profile.schema === "slurm") {
      fetchProfileResources(profile.name)
        .then(data => setResources(data))
        .catch(err => {
          console.debug("from ServiceModal: failed to fetch resources", err);
          setResources(null);
        });
    } else {
      setResources(null);
    }
  }, [profile]);

  // initialize on model refresh
  useEffect(() => {
    if (models && models.length > 0) {
      setModel(models[0])
    }
  }, [models])

  // reset on open
  useEffect(() => {
    if (open) {
      setJobOptions(getDefaultJobOptions(profile))
      setContainerOptions({ ...defaultContainerOptions })
      setLaunchSuccess(false)
      setIsLaunching(false)
      setLaunchError(null)
      setValidationErrors({})
    }
  }, [
    open,
    profile,
    setContainerOptions,
    defaultContainerOptions,
    setLaunchSuccess,
    setLaunchError,
    setIsLaunching,
    setValidationErrors,
  ])

  const cancelButtonRef = useRef(null);

  const handleFormSubmit = async () => {
    console.debug("from handleFormSubmit: attempting to launch service")
    setIsLaunching(true)
    setLaunchError(null)
    const res = await runService(task, model, jobOptions, containerOptions, profile);
    if (!res.ok) {
      const text = await res.text()
      const error = new Error("A service request failed with message:", text);
      console.error(error);
      setIsLaunching(false);
      setLaunchError(error);
      return // TODO: or throw the error? What handling is more user-friendly and
      // looks nice?
    }
    const data = await res.json();
    console.debug("from handleFormSubmit: received response", data.id);

    console.debug("from handleFormSubmit: attempting to find service");
    for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
      await sleep(waitPeriod);
      const newServices = await mutateServices();
      const matchedIndex = newServices.map(x => x.id).indexOf(data.id)
      if (matchedIndex > -1) {
        const service = newServices[matchedIndex]
        console.debug("from handleFormSubmit: found service", service);
        setSelectedServiceId(service.id);
        setIsLaunching(false);
        setLaunchSuccess(true);
        break;
      } else {
        if (attempt === maxAttempts - 1) {
          const error = new Error(`Maximum wait time (${maxAttempts * waitPeriod / 1_000} seconds) exceeded.`)
          console.error(error)
          setIsLaunching(false);
          setLaunchError(error);
        } else {
          console.debug(
            `from handleFormSubmit: service details not found: re-trying in ${waitPeriod / 1_000} seconds (attempts remaining: ${maxAttempts - attempt})`
          );
        }
      }
    }
  };

  return (
    <Transition show={open} as={Fragment}>
      <Dialog
        as="div"
        className="relative z-[60]"
        initialFocus={cancelButtonRef}
        onClose={() => {
          setOpen(false);
        }}
      >
        <TransitionChild
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-gray-500 dark:bg-gray-900 bg-opacity-75 dark:bg-opacity-80 transition-opacity" />
        </TransitionChild>

        <div className="fixed inset-0 z-10 w-screen overflow-y-auto">
          <div className="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
            <TransitionChild
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
              enterTo="opacity-100 translate-y-0 sm:scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 translate-y-0 sm:scale-100"
              leaveTo="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
            >
              <DialogPanel className="relative transform rounded-lg bg-white dark:bg-gray-800 text-left shadow-xl transition-all sm:mt-4 sm:mb-8 sm:w-full sm:max-w-4xl max-h-[90vh] flex flex-col">
                {/* Scrollable content area */}
                <div className="flex-1 overflow-y-auto px-4 pt-5 sm:p-6 sm:pl-6">
                  <DialogTitle
                    as="h3"
                    className="text-base font-semibold leading-6 text-gray-900 dark:text-gray-100"
                  ></DialogTitle>

                  {launchError &&
                    <ServiceLaunchErrorAlert error={launchError} onClick={() => setLaunchError(null)} />
                  }

                  <form className="mt-2">
                      <ServiceModalForm
                        models={models}
                        services={services}
                        setModel={setModel}
                        jobOptions={jobOptions}
                        setJobOptions={setJobOptions}
                        setValidationErrors={setValidationErrors}
                        disabled={isLaunching || launchError || launchSuccess}
                        profile={profile}
                        task={task}
                        resources={resources}
                      >
                        { children }
                      </ServiceModalForm>
                  </form>
                </div>

                {/* Footer with buttons */}
                <div className="flex-shrink-0 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 px-4 sm:px-6 py-3 rounded-b-lg">
                  {launchSuccess ? (
                    <div className="flex justify-end">
                      <button
                        type="button"
                        className="w-24 inline-flex justify-center rounded-md bg-white dark:bg-gray-700 px-3 py-2 text-sm font-semibold text-gray-900 dark:text-gray-100 shadow-sm ring-1 ring-inset ring-gray-300 dark:ring-gray-600 hover:bg-gray-50 dark:hover:bg-gray-600"
                        onClick={() => setOpen(false)}
                        ref={cancelButtonRef}
                      >
                        Close
                      </button>
                    </div>
                  ) : (
                    <div className="flex justify-end gap-3">
                      <button
                        type="button"
                        className="text-sm font-medium text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 px-3 py-2"
                        onClick={() => setOpen(false)}
                        ref={cancelButtonRef}
                      >
                        Cancel
                      </button>
                      <button
                        type="button"
                        className="w-24 inline-flex justify-center rounded-md bg-blue-500 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-400 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-500 disabled:bg-blue-200 dark:disabled:bg-blue-900"
                        onClick={handleFormSubmit}
                        disabled={!isDeepEmpty(validationErrors) || isLaunching}
                      >
                        Launch
                      </button>
                    </div>
                  )}
                </div>
              </DialogPanel>
            </TransitionChild>
          </div>
        </div>
      </Dialog>
    </Transition>
  );
}

ServiceModal.propTypes = {
  task: PropTypes.string,
  open: PropTypes.bool,
  setOpen: PropTypes.func,
  defaultContainerOptions: PropTypes.object,
  containerOptions: PropTypes.object,
  setContainerOptions: PropTypes.func,
  launchSuccess: PropTypes.bool,
  setLaunchSuccess: PropTypes.func,
  isLaunching: PropTypes.bool,
  setIsLaunching: PropTypes.func,
  launchError: PropTypes.object,
  setLaunchError: PropTypes.func,
  validationErrors: PropTypes.object,
  setValidationErrors: PropTypes.func,
  profile: PropTypes.object,
  children: PropTypes.node,
};

export default ServiceModal;
