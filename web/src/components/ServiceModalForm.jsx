import React from "react";
import Warning from "./Warning";
import Info from "./Info";
import ModelSelect from "@/components/ModelSelect"
import RevisionSelect from "@/components/RevisionSelect"
import ServiceModalValidatedInput from "@/components/ServiceModalValidatedInput";
import { ExclamationTriangleIcon } from "@heroicons/react/20/solid";
import PropTypes from "prop-types";


/** Convert time string "HH:MM:SS" to minutes (ignoring seconds). */
const parseTime = (time) => {
  if (time === "") {
    return "";
  }
  let [hr, min] = time.split(":").map((val) => Number.parseInt(val));
  return hr * 60 + min;
};

/** Della-specific calculation of GPU memory requirements. */
const calculateGres = (mem) => {
  return Math.min(Math.max(Math.ceil(mem / 36), 1), 4); // 36 = 90% of 40GB card
}

function ServiceModalForm({
  models,
  services,
  setModel,
  jobOptions,
  setJobOptions,
  setValidationErrors,
  disabled,
  profile,
  task,
  children
}) {

  const [repoId, setRepoId] = React.useState(null);

  function validateName(name, services) {
    if (services.map(service => service.name).includes(name)) {
      const error = {
        message: "Name is already in use by another service.",
        ok: false,
      }
      setValidationErrors((prevValidationErrors) => {
        return {
          ...prevValidationErrors,
          name: error,
        }
      })
      return error
    }

    setValidationErrors((prevValidationErrors) => {
      return {
        ...prevValidationErrors,
        name: null,
      }
    })
    return { ok: true }
  }

  function validateTime(value) {
    const time = Number(String(value).trim())

    if (!Number.isInteger(time) || time === "") {
      const error = {
        message: "Time should be a valid positive integer.",
        ok: false,
      };
      setValidationErrors((prevValidationErrors) => {
        return {
          ...prevValidationErrors,
          time: error,
        }
      })
      return error
    }
    else if (time < 1) {
      const error = {
        message: "Time should be greater than or equal to 1.",
        ok: false,
      };
      setValidationErrors((prevValidationErrors) => {
        return {
          ...prevValidationErrors,
          time: error,
        }
      })
      return error
    }
    else if (time > 180) {
      const error = {
        message: "Time should be less than 180.",
        ok: false,
      };
      setValidationErrors((prevValidationErrors) => {
        return {
          ...prevValidationErrors,
          time: error,
        }
      })
      return error
    }

    setValidationErrors((prevValidationErrors) => {
      return {
        ...prevValidationErrors,
        time: null,
      }
    })
    return { ok: true };
  }

  function validateCPUs(value) {
    const cpus = Number(String(value).trim())

    if (!Number.isInteger(cpus)) {
      const error = {
        message: "CPU cores should be a valid integer.",
        ok: false,
      };
      setValidationErrors((prevValidationErrors) => {
        return {
          ...prevValidationErrors,
          cpus: error,
        }
      })
      return error
    }
    else if (cpus < 8) {
      const error = {
        message: "CPU cores should be greater than or equal to 8.",
        ok: false,
      };
      setValidationErrors((prevValidationErrors) => {
        return {
          ...prevValidationErrors,
          cpus: error,
        }
      })
      return error
    }
    else if (cpus > 128) {
      const error = {
        message: "CPU cores should be less than 128.",
        ok: false,
      };
      setValidationErrors((prevValidationErrors) => {
        return {
          ...prevValidationErrors,
          cpus: error,
        }
      })
      return error
    }

    setValidationErrors((prevValidationErrors) => {
      return {
        ...prevValidationErrors,
        cpus: null,
      }
    })
    return { ok: true };
  }

  function validateMemory(value) {
    const mem = Number(String(value).trim())

    if (!Number.isInteger(mem)) {
      const error = {
        message: "Memory should be a valid integer.",
        ok: false,
      };
      setValidationErrors((prevValidationErrors) => {
        return {
          ...prevValidationErrors,
          mem: error,
        }
      })
      return error
    }
    else if (mem < 8) {
      const error = {
        message: "Memory should be greater than or equal to 8 GB.",
        ok: false,
      };
      setValidationErrors((prevValidationErrors) => {
        return {
          ...prevValidationErrors,
          mem: error,
        }
      })
      return error
    }
    else if (mem > 256) {
      const error = {
        message: "Memory should be less than 256.",
        ok: false,
      };
      setValidationErrors((prevValidationErrors) => {
        return {
          ...prevValidationErrors,
          mem: error,
        }
      })
      return error
    }

    setValidationErrors((prevValidationErrors) => {
      return {
        ...prevValidationErrors,
        mem: null,
      }
    })

    return { ok: true };
  }

  const huggingFaceTaskMap = new Map([
    ['text-generation', 'text-generation'],
    ['speech-recognition', 'automatic-speech-recognition'],
  ]);

  function warnIfNoModels() {
    const taskName = task.replaceAll('-', ' ');
    const taskURL = `https://huggingface.co/models?pipeline_tag=${huggingFaceTaskMap.get(task)}&sort=trending`;
    return (
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
              No models are available
            </h3>
            <div className="mt-2 font-light text-sm text-yellow-800">
              <p>Switch profiles or download a {taskName} model from <a className="underline" href={taskURL}>Hugging Face</a>.</p>
            </div>
          </div>
        </div>
      </div>
    );
  }


  // TODO: move to the launcher--no button should show up if there is no profile selected,
  // or the button should be disabled to avoid the modal opening.
  if (!profile) {
    return <></>
  }

  return (
    <div className="max-w-2xl space-y-6 md:col-span-2">

      <fieldset>
        <ServiceModalValidatedInput
          type="text"
          label="Name"
          help="Give your service a name (or use our wonderful suggestion)."
          value={jobOptions.name}
          setValue={(value) => {
            setJobOptions((prevJobOptions) => {
              return {
                ...prevJobOptions,
                name: value,
              }
            })
          }}
          validate={(value) => validateName(value, services)}
          disabled={disabled}
        />
      </fieldset>

      {models && models.length ? (<>
        <fieldset>
          <ModelSelect
            models={models}
            repoId={repoId}
            setRepoId={setRepoId}
            disabled={disabled}
          />
        </fieldset>

        <fieldset>
          <RevisionSelect
            models={models}
            repoId={repoId}
            setModel={setModel}
            disabled={disabled}
          />
        </fieldset>
      </>) : warnIfNoModels()}

      {profile.schema === "slurm"
        ? (
          <>
            <fieldset>
              <legend className="text-sm font-semibold leading-6 text-gray-900">
                Time
              </legend>
              <p className="mt-1 text-sm leading-6 text-gray-600">
                How long would you like to run this model?
              </p>
              <div className="mt-3 space-y-3">
                <ServiceModalValidatedInput
                  type="number"
                  units="minutes"
                  disabled={disabled}
                  value={parseTime(jobOptions.time)}
                  setValue={(value) => {
                    setJobOptions({
                      ...jobOptions,
                      time:
                        value === ""
                          ? value
                          : `00:${String(value).padStart(2, "0")}:00`,
                    });
                  }}
                  validate={validateTime}
                />
              </div>
            </fieldset>

            <fieldset>
              <legend className="text-sm font-semibold leading-6 text-gray-900">
                Resources
              </legend>
              <p className="mt-1 text-sm leading-6 text-gray-600">
                Request resources for the model.
              </p>
              <div className="mt-2 text-sm font-medium inline-flex">
                <Warning
                  header="Warning"
                  message="Changing the settings below may cause your service to fail or over utilize resources."
                />
              </div>
              <div className="mt-6 space-y-3">
                <ServiceModalValidatedInput
                  type="number"
                  disabled={disabled}
                  label="CPU"
                  units="cores"
                  value={jobOptions.ntasks_per_node}
                  setValue={(value) => {
                    setJobOptions((prevJobOptions) => {
                      return {
                        ...prevJobOptions,
                        ntasks_per_node: value,
                      }
                    });
                  }}
                  validate={validateCPUs}
                />
                <ServiceModalValidatedInput
                  type="number"
                  disabled={disabled}
                  label="Memory"
                  units="GB"
                  value={jobOptions.mem}
                  setValue={(value) => {
                    setJobOptions((prevJobOptions) => {
                      return {
                        ...prevJobOptions,
                        mem: value,
                        gres: prevJobOptions.gres > 0 ? calculateGres(value) : 0,
                      }
                    });
                  }}
                  validate={validateMemory}
                />
                <div className="relative flex gap-x-3">
                  <div className="flex h-6 items-center">
                    <input
                      id="gpu-checkbox"
                      name="gpu-checkbox"
                      type="checkbox"
                      disabled={disabled}
                      checked={jobOptions.gres > 0}
                      onChange={() => {
                        if (jobOptions.gres > 0) {
                          setJobOptions((prevJobOptions) => {
                            return {
                              ...prevJobOptions,
                              gres: 0,
                            }
                          });
                        } else {
                          setJobOptions((prevJobOptions) => {
                            return {
                              ...prevJobOptions,
                              gres: calculateGres(prevJobOptions.mem),
                            }
                          });
                        }
                      }}
                      className="h-4 w-4 rounded border-gray-300 text-blue-500 focus:ring-blue-500 disabled:bg-gray-100"
                    />
                  </div>
                  <div className="text-sm leading-6">
                    <label htmlFor="offers" className="font-medium text-gray-900">
                      Accelerate
                    </label>
                    <p className="text-gray-500">
                      Use GPUs to accelerate inference. Recommended for most models.
                    </p>
                  </div>
                </div>
              </div>
            </fieldset>
          </>
        )
        : (
          <>
            <fieldset>
              <legend className="text-sm font-semibold leading-6 text-gray-900">
                Resources
              </legend>
              <p className="mt-1 text-sm leading-6 text-gray-600">
                Request resources for the model.
              </p>
              <div className="mt-2 text-sm font-medium inline-flex">
                <Info
                  header="Note"
                  message="Services running locally can utilize all CPU, memory and GPU resources made available through the container provider and will run until stopped."
                />
              </div>
              <div className="mt-6 space-y-3">
                <div className="relative flex gap-x-3">
                  <div className="flex h-6 items-center">
                    <input
                      id="gpu-checkbox"
                      name="gpu-checkbox"
                      type="checkbox"
                      disabled={disabled}
                      checked={jobOptions.gres > 0}
                      onChange={() => {
                        if (jobOptions.gres > 0) {
                          setJobOptions((prevJobOptions) => {
                            return {
                              ...prevJobOptions,
                              gres: 0,
                            }
                          });
                        } else {
                          setJobOptions((prevJobOptions) => {
                            return {
                              ...prevJobOptions,
                              gres: 1, // local => binary
                            }
                          });
                        }
                      }}
                      className="h-4 w-4 rounded border-gray-300 text-blue-500 focus:ring-blue-500 disabled:bg-gray-100"
                    />
                  </div>
                  <div className="text-sm leading-6">
                    <label htmlFor="offers" className="font-medium text-gray-900">
                      Accelerate
                    </label>
                    <p className="text-gray-500">
                      Use GPUs to accelerate inference. Recommended for most models.
                    </p>
                  </div>
                </div>
              </div>
            </fieldset>
          </>
        )
      }

      {children}

    </div>
  );
}

ServiceModalForm.propTypes = {
  models: PropTypes.array,
  services: PropTypes.array,
  setModel: PropTypes.func,
  jobOptions: PropTypes.object,
  setJobOptions: PropTypes.func,
  setValidationErrors: PropTypes.func,
  disabled: PropTypes.bool,
  profile: PropTypes.object,
  task: PropTypes.string,
  children: PropTypes.node,
};

export default ServiceModalForm;
