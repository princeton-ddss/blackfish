import React from "react";
import Info from "./Info";
import ModelSelect from "@/components/ModelSelect"
import RevisionSelect from "@/components/RevisionSelect"
import PartitionSelect from "@/components/PartitionSelect";
import TierSelect from "@/components/TierSelect";
import ServiceModalValidatedInput from "@/components/ServiceModalValidatedInput";
import { ExclamationTriangleIcon, ChevronDownIcon, ChevronUpIcon } from "@heroicons/react/20/solid";
import { fetchModelTier } from "@/lib/requests";
import PropTypes from "prop-types";


/** Convert time string "HH:MM:SS" to minutes (ignoring seconds). */
const parseTime = (time) => {
  if (time === "") {
    return "";
  }
  let [hr, min] = time.split(":").map((val) => Number.parseInt(val));
  return hr * 60 + min;
};


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
  resources,
  children
}) {

  const [repoId, setRepoId] = React.useState(null);

  // Tier-based resource selection state
  const [selectedPartition, setSelectedPartition] = React.useState(null);
  const [selectedTier, setSelectedTier] = React.useState(null);
  const [recommendedTier, setRecommendedTier] = React.useState(null);
  const [showAdvanced, setShowAdvanced] = React.useState(false);
  const [account, setAccount] = React.useState("");

  // Default tiers when API doesn't return data
  const defaultTiers = React.useMemo(() => [
    {
      name: "CPU Only",
      description: "For testing or CPU-only models",
      gpu_count: 0,
      gpu_type: null,
      cpu_cores: 2,
      memory_gb: 4,
    },
    {
      name: "Small",
      description: "Small GPU models (up to 32GB)",
      gpu_count: 1,
      gpu_type: null,
      cpu_cores: 4,
      memory_gb: 8,
    },
    {
      name: "Medium",
      description: "Medium models (up to 128GB)",
      gpu_count: 2,
      gpu_type: null,
      cpu_cores: 6,
      memory_gb: 16,
    },
    {
      name: "Large",
      description: "Large models (128GB+)",
      gpu_count: 4,
      gpu_type: null,
      cpu_cores: 8,
      memory_gb: 32,
    },
  ], []);

  const defaultPartitions = React.useMemo(() => [
    { name: "default", default: true, tiers: defaultTiers }
  ], [defaultTiers]);

  // Memoize partitions and tiers to avoid re-renders
  const partitions = React.useMemo(() =>
    resources?.partitions?.length > 0 ? resources.partitions : defaultPartitions,
    [resources?.partitions, defaultPartitions]
  );
  const currentPartition = React.useMemo(() =>
    partitions.find(p => p.name === selectedPartition) ||
    partitions.find(p => p.default) ||
    partitions[0],
    [partitions, selectedPartition]
  );
  const tiers = React.useMemo(() => currentPartition?.tiers || [], [currentPartition?.tiers]);
  const timeConfig = resources?.time || { default: 30, max: 180 };

  // Initialize selected partition when resources load
  React.useEffect(() => {
    if (partitions.length > 0 && !selectedPartition) {
      const defaultPartition = partitions.find(p => p.default) || partitions[0];
      setSelectedPartition(defaultPartition.name);
    }
  }, [partitions, selectedPartition]);

  // Fetch recommended tier when model or partition changes
  React.useEffect(() => {
    if (repoId && profile && selectedPartition) {
      fetchModelTier(encodeURIComponent(repoId), profile.name, selectedPartition)
        .then(data => {
          if (data && data.tier) {
            setRecommendedTier(data.tier);
            // Auto-select the recommended tier
            setSelectedTier(data.tier);
          }
        })
        .catch(err => {
          console.debug("from ServiceModalForm: failed to fetch model tier", err);
          // Fallback to first tier
          if (tiers.length > 0) {
            setSelectedTier(tiers[0].name);
          }
        });
    }
  }, [repoId, profile, selectedPartition, tiers]);

  // Update jobOptions when tier selection changes
  React.useEffect(() => {
    if (selectedTier && tiers.length > 0) {
      const tier = tiers.find(t => t.name === selectedTier);
      if (tier) {
        setJobOptions(prevJobOptions => ({
          ...prevJobOptions,
          ntasks_per_node: tier.cpu_cores,
          mem: tier.memory_gb,
          gres: tier.gpu_count,
          partition: selectedPartition,
          constraint: tier.slurm?.constraint || null,
          account: account || null,
        }));
      }
    }
  }, [selectedTier, selectedPartition, account, tiers, setJobOptions]);

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
    const trimmed = String(value).trim();
    const maxTime = timeConfig.max;

    // Allow empty - will use default
    if (trimmed === "") {
      setValidationErrors((prevValidationErrors) => {
        return {
          ...prevValidationErrors,
          time: null,
        }
      })
      return { ok: true };
    }

    const time = Number(trimmed);

    if (!Number.isInteger(time) || time < 1) {
      const error = {
        message: "Time should be a positive integer.",
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
    else if (time > maxTime) {
      const error = {
        message: `Time should be ${maxTime} minutes or less.`,
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
    <div className="space-y-6">

      <fieldset>
        <ServiceModalValidatedInput
          type="text"
          label="Name"
          help="Give your service a name (or use our suggestion)."
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

      {models && models.length ? (
        <div className="space-y-3">
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
        </div>
      ) : warnIfNoModels()}

      {profile.schema === "slurm"
        ? (
          <>
            {/* Partition selector - only show if multiple partitions */}
            {partitions.length > 1 && (
              <fieldset>
                <label className="block text-sm font-semibold leading-6 text-gray-900 dark:text-gray-100 mb-2">
                  Partition
                </label>
                <PartitionSelect
                  partitions={partitions}
                  selectedPartition={selectedPartition}
                  setSelectedPartition={(name) => {
                    setSelectedPartition(name);
                    // Reset tier selection when partition changes
                    setSelectedTier(null);
                    setRecommendedTier(null);
                  }}
                  disabled={disabled}
                />
              </fieldset>
            )}

            {/* Resources selector */}
            <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4 -mx-1 space-y-4">
              <div>
                <h3 className="text-sm font-semibold leading-6 text-gray-900 dark:text-gray-100">
                  Resources
                </h3>
                <p className="mt-1 mb-3 text-sm text-gray-600 dark:text-gray-400">
                  Select a compute tier for your model.
                </p>
                <TierSelect
                  tiers={tiers}
                  selectedTier={selectedTier}
                  recommendedTier={recommendedTier}
                  setSelectedTier={setSelectedTier}
                  disabled={disabled}
                />
              </div>

              <ServiceModalValidatedInput
                type="number"
                label="Time"
                placeholder={String(timeConfig.default)}
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

            {/* Advanced options (collapsed by default) */}
            <fieldset>
              <button
                type="button"
                onClick={() => setShowAdvanced(!showAdvanced)}
                className="flex items-center gap-2 w-full text-left"
              >
                <legend className="text-sm font-semibold leading-6 text-gray-900 dark:text-gray-100">
                  Advanced Options
                </legend>
                {showAdvanced ? (
                  <ChevronUpIcon className="h-4 w-4 text-gray-500" />
                ) : (
                  <ChevronDownIcon className="h-4 w-4 text-gray-500" />
                )}
              </button>
              {showAdvanced && (
                <div className="mt-3">
                  <label htmlFor="account" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                    Account
                  </label>
                  <input
                    type="text"
                    id="account"
                    name="account"
                    value={account}
                    onChange={(e) => setAccount(e.target.value)}
                    disabled={disabled}
                    className="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm disabled:bg-gray-100 dark:disabled:bg-gray-800 disabled:cursor-not-allowed"
                  />
                  <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                    Leave empty to use your default account.
                  </p>
                </div>
              )}
            </fieldset>
          </>
        )
        : (
          <>
            <fieldset>
              <legend className="text-sm font-semibold leading-6 text-gray-900 dark:text-gray-100">
                Resources
              </legend>
              <p className="mt-1 text-sm leading-6 text-gray-600 dark:text-gray-400">
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
                      className="h-4 w-4 rounded border-gray-300 dark:border-gray-600 text-blue-500 focus:ring-blue-500 disabled:bg-gray-100 dark:disabled:bg-gray-700 dark:bg-gray-700"
                    />
                  </div>
                  <div className="text-sm leading-6">
                    <label htmlFor="offers" className="font-medium text-gray-900 dark:text-gray-100">
                      Accelerate
                    </label>
                    <p className="text-gray-500 dark:text-gray-400">
                      Use available GPUs to speed up inference. Requires an Nvidia GPU.
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
  resources: PropTypes.shape({
    time: PropTypes.shape({
      default: PropTypes.number,
      max: PropTypes.number,
    }),
    partitions: PropTypes.arrayOf(
      PropTypes.shape({
        name: PropTypes.string.isRequired,
        default: PropTypes.bool,
        tiers: PropTypes.array,
      })
    ),
  }),
  children: PropTypes.node,
};

export default ServiceModalForm;
