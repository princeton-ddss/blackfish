import React from "react";
import Info from "./Info";
import Alert from "@/components/Alert";
import ModelSelect from "@/components/ModelSelect"
import RevisionSelect from "@/components/RevisionSelect"
import TierSelect from "@/components/TierSelect";
import ServiceModalValidatedInput from "@/components/ServiceModalValidatedInput";
import { ChevronDownIcon, ChevronUpIcon } from "@heroicons/react/20/solid";
import { ExclamationTriangleIcon } from "@heroicons/react/24/outline";
import { classNames, selectTierByModelSize } from "@/lib/util";
import { fetchModelSizeFromHub } from "@/lib/requests";
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
  clusterPartitions,
  children
}) {

  const [repoId, setRepoId] = React.useState(null);
  const [modelId, setModelId] = React.useState(null);

  // Tier-based resource selection state
  const [selectedPartition, setSelectedPartition] = React.useState("");
  const [selectedTier, setSelectedTier] = React.useState(null);
  const [recommendedTier, setRecommendedTier] = React.useState(null);
  const [partitionWarning, setPartitionWarning] = React.useState(null);
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


  // Resource spec partitions (for tier matching)
  const specPartitions = React.useMemo(() =>
    resources?.partitions?.length > 0 ? resources.partitions : [],
    [resources?.partitions]
  );

  // Resolve tiers: match typed partition against spec, else use default tiers
  const tiers = React.useMemo(() => {
    if (selectedPartition) {
      const match = specPartitions.find(p => p.name === selectedPartition);
      if (match) return match.tiers;
    }
    // Fall back: use default spec partition's tiers if available, else default tiers
    const defaultSpec = specPartitions.find(p => p.default) || specPartitions[0];
    return defaultSpec?.tiers || defaultTiers;
  }, [selectedPartition, specPartitions, defaultTiers]);

  const timeConfig = resources?.time || { default: 30, max: 180 };

  // Select recommended tier based on model size
  // Priority: 1. model override, 2. client-side data, 3. HuggingFace Hub, 4. no auto-selection
  React.useEffect(() => {
    if (!modelId || tiers.length === 0) return;

    const selectedModel = models?.find(m => m.id === modelId);
    const repoId = selectedModel?.repo_id;
    const cachedSizeGb = selectedModel?.model_size_gb ?? null;
    // Model overrides from resource specs (e.g., "meta-llama/Llama-2-70b": "gpu.Large")
    const modelOverrides = resources?.models || {};

    console.debug(`[TierSelect] Model ${repoId} (${modelId}): cached size = ${cachedSizeGb}`);

    // 1. Check for model override first
    if (repoId && modelOverrides[repoId]) {
      const override = modelOverrides[repoId];
      // Override format: "partition.tier" or just "tier"
      if (override.includes('.')) {
        const [partitionName, tierName] = override.split('.');
        console.debug(`[TierSelect] Using override for ${repoId}: partition=${partitionName}, tier=${tierName}`);
        setSelectedPartition(partitionName);
        setRecommendedTier(tierName);
        setSelectedTier(tierName);
      } else {
        console.debug(`[TierSelect] Using override for ${repoId}: tier=${override}`);
        setRecommendedTier(override);
        setSelectedTier(override);
      }
      return;
    }

    // 2. Try client-side cached data
    if (cachedSizeGb !== null) {
      console.debug(`[TierSelect] Using cached size for ${repoId}: ${cachedSizeGb} GB`);
      const tierName = selectTierByModelSize(tiers, cachedSizeGb);
      if (tierName) {
        console.debug(`[TierSelect] Selected tier for ${repoId}: ${tierName}`);
        setRecommendedTier(tierName);
        setSelectedTier(tierName);
      }
      return;
    }

    // 3. Fetch from HuggingFace Hub
    if (repoId) {
      console.debug(`[TierSelect] No cached size for ${repoId}, fetching from HuggingFace Hub`);
      fetchModelSizeFromHub(repoId)
        .then(sizeGb => {
          if (sizeGb !== null) {
            console.debug(`[TierSelect] Got size from Hub for ${repoId}: ${sizeGb.toFixed(2)} GB`);
            const tierName = selectTierByModelSize(tiers, sizeGb);
            if (tierName) {
              console.debug(`[TierSelect] Selected tier for ${repoId}: ${tierName}`);
              setRecommendedTier(tierName);
              setSelectedTier(tierName);
            }
          } else {
            // 4. No size available - don't auto-select, let user decide
            console.debug(`[TierSelect] No size data for ${repoId}, skipping auto-selection`);
            setRecommendedTier(null);
          }
        })
        .catch(err => {
          console.error(`[TierSelect] Error fetching size for ${repoId}:`, err);
          setRecommendedTier(null);
        });
    } else {
      console.debug(`[TierSelect] No repo_id for model ${modelId}, skipping tier selection`);
    }
  }, [modelId, tiers, selectedPartition, models, resources?.models]);

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
          partition: selectedPartition || null,
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
      <Alert variant="warning" title="No models are available" className="mt-2 mb-4">
        Switch profiles or download a {taskName} model from <a className="underline" href={taskURL}>Hugging Face</a>.
      </Alert>
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
              setModelId={setModelId}
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
            {/* Partition input */}
            <fieldset>
              <label htmlFor="partition" className="block text-sm font-semibold leading-6 text-gray-900 dark:text-gray-100 mb-2">
                Partition
              </label>
              <div className="relative mt-2 rounded-md shadow-sm">
                <input
                  type="text"
                  id="partition"
                  name="partition"
                  placeholder="Default"
                  value={selectedPartition}
                  onChange={(e) => {
                    setSelectedPartition(e.target.value);
                    setPartitionWarning(null);
                    // Reset tier selection when partition changes
                    setSelectedTier(null);
                    setRecommendedTier(null);
                  }}
                  onBlur={() => {
                    if (selectedPartition && clusterPartitions && !clusterPartitions.includes(selectedPartition)) {
                      setPartitionWarning(`Partition "${selectedPartition}" was not found on the cluster.`);
                    } else {
                      setPartitionWarning(null);
                    }
                  }}
                  disabled={disabled}
                  className={classNames(
                    partitionWarning
                      ? "ring-yellow-400 dark:ring-yellow-500 focus:ring-yellow-500"
                      : "ring-gray-300 dark:ring-gray-600 focus:ring-blue-500",
                    "block w-full rounded-md border-0 py-1.5 pr-10 ring-1 ring-inset focus:ring-2 focus:ring-inset sm:text-sm sm:leading-6 disabled:bg-gray-100 dark:disabled:bg-gray-800 disabled:ring-1 disabled:ring-gray-300 dark:disabled:ring-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                  )}
                />
                {partitionWarning && (
                  <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-3">
                    <ExclamationTriangleIcon
                      className="h-5 w-5 text-yellow-500"
                      aria-hidden="true"
                    />
                  </div>
                )}
              </div>
              {partitionWarning ? (
                <p className="mt-2 text-sm text-yellow-700 dark:text-yellow-300">
                  {partitionWarning}
                </p>
              ) : (
                <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                  Specify a SLURM partition, or leave empty to use the cluster default.
                </p>
              )}
            </fieldset>

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
    models: PropTypes.objectOf(PropTypes.string),
  }),
  clusterPartitions: PropTypes.arrayOf(PropTypes.string),
  children: PropTypes.node,
};

export default ServiceModalForm;
