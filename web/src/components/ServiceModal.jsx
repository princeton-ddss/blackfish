import React, { useContext } from "react";
import { Fragment, useRef, useState, useEffect } from "react";
import {
  Dialog,
  DialogPanel,
  DialogTitle,
  Transition,
  TransitionChild,
} from "@headlessui/react";
import ServiceSummary from "@/components/ServiceSummary";
import ServiceModalForm from "@/components/ServiceModalForm";
import ServiceLaunchErrorAlert from "@/components/ServiceLaunchErrorAlert";
import { ServiceContext } from "@/providers/ServiceProvider";
import { runService } from "@/lib/requests";
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

  const defaultJobOptions = React.useMemo(() => {
    return {
      name: randomName(),
      time: "00:30:00",
      ntasks_per_node: 8,
      mem: 16,
      gres: 1,
      partition: null,
      constraint: null,
    }
  }, [])

  const maxAttempts = 3;
  const waitPeriod = 5_000;

  const {
    services,
    mutate: mutateServices
  } = useServices(profile, task);
  const {
    models,
  } = useModels(profile, task);

  const { selectedService, setSelectedServiceId } = useContext(ServiceContext);


  const [jobOptions, setJobOptions] = React.useState({ ...defaultJobOptions, name: randomName() });
  const [model, setModel] = useState(null);


  // initialize on model refresh
  useEffect(() => {
    if (models && models.length > 0) {
      setModel(models[0])
    }
  }, [models])

  // reset on open
  useEffect(() => {
    if (open) {
      setJobOptions({ ...defaultJobOptions, name: randomName() })
      setContainerOptions({ ...defaultContainerOptions })
      setLaunchSuccess(false)
      setIsLaunching(false)
      setLaunchError(null)
      setValidationErrors({})
    }
  }, [
    open,
    setContainerOptions,
    defaultJobOptions,
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
        className="relative z-10"
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
          <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" />
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
              <DialogPanel className="relative transform overflow-hidden rounded-lg bg-white px-4 pb-4 pt-5 text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-4xl sm:p-6 sm:pl-6">
                <div>
                  <div>
                    <DialogTitle
                      as="h3"
                      className="text-base font-semibold leading-6 text-gray-900"
                    ></DialogTitle>

                    {launchError &&
                      <ServiceLaunchErrorAlert error={launchError} onClick={() => setLaunchError(null)} />
                    }

                    <form className="mt-2">
                      <div className="space-y-4">
                        <div className="grid grid-cols-1 gap-x-12 gap-y-10 border-b border-gray-900/10 pb-12 md:grid-cols-3">
                          <div>
                            <h2 className="text-base font-semibold leading-7 text-gray-900">
                              Summary
                            </h2>
                            {isLaunching ? (
                              <div aria-label="Services are loading" className="flex justify-center items-center h-48">
                                <span className="relative flex h-5 w-5">
                                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                                  <span className="relative inline-flex rounded-full h-5 w-5 bg-blue-500"></span>
                                </span>
                              </div>
                            ) : (
                              <ServiceSummary
                                service={
                                  launchSuccess
                                    ? selectedService
                                    : {
                                      model: model ? model.repo_id : null,
                                      name: jobOptions.name,
                                      status: null,
                                      created_at: null,
                                      updated_at: null,
                                      host: profile ? (profile.schema === "local" ? "localhost" : profile.host) : null,
                                      port: null,
                                      ntasks_per_node: profile ? (profile.schema === "local" ? null : jobOptions.ntasks_per_node) : null,
                                      mem: profile ? (profile.schema === "local" ? null : jobOptions.mem) : null,
                                      gres: jobOptions.gres,
                                    }
                                }
                                profile={profile}
                              />
                            )}
                          </div>
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
                          >
                            { children }
                          </ServiceModalForm>
                        </div>
                      </div>
                    </form>
                  </div>
                </div>

                {launchSuccess ? (
                  <div className="mt-5 sm:mt-6 sm:grid sm:grid-flow-row-dense sm:grid-cols-2 sm:gap-3">
                    <button
                      type="button"
                      className="mt-3 inline-flex w-full justify-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 sm:col-start-1 sm:col-span-2 sm:mt-0"
                      onClick={() => {
                        setOpen(false);
                      }}
                      ref={cancelButtonRef}
                    >
                      Close
                    </button>
                  </div>
                ) : (
                  <div className="mt-5 sm:mt-6 sm:grid sm:grid-flow-row-dense sm:grid-cols-2 sm:gap-3">
                    <button
                      type="button"
                      className="inline-flex w-full justify-center rounded-md bg-blue-500 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-400 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-500 sm:col-start-2 disabled:bg-blue-200"
                      onClick={handleFormSubmit}
                      disabled={!isDeepEmpty(validationErrors) || isLaunching}
                    >
                      Launch
                    </button>
                    <button
                      type="button"
                      className="mt-3 inline-flex w-full justify-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 sm:col-start-1 sm:mt-0"
                      // TODO: this should actually cancel the request. If the service is launching, then this
                      // button would issue a stop request. Then, it should turn to a close button.
                      onClick={() => setOpen(false)}
                      ref={cancelButtonRef}
                    >
                      Cancel
                    </button>
                  </div>
                )}
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
