import { Fragment, useRef, useState, useEffect, useMemo } from "react";
import {
  Dialog,
  DialogPanel,
  DialogTitle,
  Transition,
  TransitionChild,
  Listbox,
  ListboxButton,
  ListboxOption,
  ListboxOptions,
} from "@headlessui/react";
import {
  ChevronUpDownIcon,
  CheckIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  ArrowLeftIcon,
  ArrowRightIcon,
} from "@heroicons/react/24/outline";
import ModelSelect from "@/components/ModelSelect";
import RevisionSelect from "@/components/RevisionSelect";
import PartitionSelect from "@/components/PartitionSelect";
import TierSelect from "@/components/TierSelect";
import Alert from "@/components/Alert";
import Stepper from "@/components/Stepper";
import DirectoryBrowser from "@/components/DirectoryBrowser";
import { useModels } from "@/lib/loaders";
import { useRemoteFileSystem } from "@/providers/RemoteFileSystemProvider";
import { fetchProfileResources, fetchModelTier } from "@/lib/requests";
import PropTypes from "prop-types";

// Task definitions - each task maps to a service type
export const TASKS = [
  {
    id: "ocr",
    name: "OCR",
    description: "Extract text from images",
    service: "text-generation", // Uses vLLM with vision models
    defaultPrompt: "Extract all text from this image. Preserve the original formatting and structure as much as possible.",
    params: [
      {
        name: "language",
        type: "string",
        required: false,
        label: "Language",
        placeholder: "e.g., english",
        help: "Expected language in the images",
      },
      {
        name: "output_format",
        type: "select",
        required: false,
        label: "Output Format",
        options: [
          { value: "plain", label: "Plain (.txt)" },
          { value: "markdown", label: "Markdown (.md)" },
          { value: "json", label: "JSON (.json)" },
        ],
        default: "plain",
      },
    ],
  },
  {
    id: "transcription",
    name: "Transcription",
    description: "Convert audio to text",
    service: "speech-recognition", // Uses Whisper models
    defaultPrompt: null, // Whisper doesn't use prompts
    params: [
      {
        name: "language",
        type: "string",
        required: false,
        label: "Language",
        placeholder: "e.g., english (auto-detect if empty)",
        help: "Language spoken in the audio. Leave empty to auto-detect.",
      },
      {
        name: "output_format",
        type: "select",
        required: false,
        label: "Output Format",
        options: [
          { value: "plain", label: "Plain (.txt)" },
          { value: "srt", label: "Subtitles (.srt)" },
          { value: "vtt", label: "WebVTT (.vtt)" },
          { value: "json", label: "JSON (.json)" },
        ],
        default: "plain",
      },
    ],
  },
  {
    id: "translation",
    name: "Translation",
    description: "Translate text between languages",
    service: "text-generation", // Uses LLM models
    defaultPrompt: "Translate the following text to {target_language}. Preserve the original formatting.",
    params: [
      {
        name: "target_language",
        type: "string",
        required: true,
        label: "Target Language",
        placeholder: "e.g., Spanish, French, German",
        help: "The language to translate into",
      },
      {
        name: "output_format",
        type: "select",
        required: false,
        label: "Output Format",
        options: [
          { value: "plain", label: "Plain (.txt)" },
          { value: "json", label: "JSON (.json)" },
        ],
        default: "plain",
      },
    ],
  },
];

// Default tiers when API doesn't return data (matching ServiceModalForm)
const DEFAULT_TIERS = [
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
];

const DEFAULT_PARTITIONS = [
  { name: "default", default: true, tiers: DEFAULT_TIERS }
];

// Step definitions
const STEPS = [
  { id: "model", name: "Model", description: "Select model and revision" },
  { id: "options", name: "Task", description: "Configure task parameters" },
  { id: "paths", name: "Data", description: "Choose data directories" },
  { id: "resources", name: "Compute", description: "Assign compute resources" },
];

// Steps for non-Slurm profiles (no resources step)
const STEPS_LOCAL = [
  { id: "model", name: "Model", description: "Select model and revision" },
  { id: "options", name: "Task", description: "Configure task parameters" },
  { id: "paths", name: "Data", description: "Choose data directories" },
];

function NewJobModal({ open, setOpen, profile, task, onJobCreated }) {
  const cancelButtonRef = useRef(null);

  // Remote file system connection state
  const { isConnected, error: connectionError } = useRemoteFileSystem();
  const isRemote = profile && profile.schema !== "local";

  // Stepper state
  const [currentStep, setCurrentStep] = useState(0);
  const [visitedSteps, setVisitedSteps] = useState(new Set([0]));

  // Model selection - fetch models for the task's service type
  const { models, isLoading: modelsLoading, error: modelsError } = useModels(profile, task?.service);
  const [repoId, setRepoId] = useState(null);
  const [model, setModel] = useState(null);

  // Paths
  const [inputDir, setInputDir] = useState("");
  const [outputDir, setOutputDir] = useState("");

  // Task-specific parameters
  const [taskParams, setTaskParams] = useState({});

  // Resource selection (matching ServiceModalForm pattern)
  const [resources, setResources] = useState(null);
  const [selectedPartition, setSelectedPartition] = useState(null);
  const [selectedTier, setSelectedTier] = useState(null);
  const [recommendedTier, setRecommendedTier] = useState(null);
  const [maxWorkers, setMaxWorkers] = useState(1);

  // Advanced options
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [account, setAccount] = useState("");
  const [workerTimeout, setWorkerTimeout] = useState("");
  const [clientTimeout, setClientTimeout] = useState("");
  const contentRef = useRef(null);

  // Submission state
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);

  // Determine which steps to use based on profile type
  const steps = profile?.schema === "slurm" ? STEPS : STEPS_LOCAL;
  const isLastStep = currentStep === steps.length - 1;

  // Compute partitions and tiers
  const partitions = useMemo(() =>
    resources?.partitions?.length > 0 ? resources.partitions : DEFAULT_PARTITIONS,
    [resources?.partitions]
  );

  const currentPartition = useMemo(() =>
    partitions.find(p => p.name === selectedPartition) ||
    partitions.find(p => p.default) ||
    partitions[0],
    [partitions, selectedPartition]
  );

  const tiers = useMemo(() => currentPartition?.tiers || DEFAULT_TIERS, [currentPartition?.tiers]);

  // Fetch resources when profile changes
  useEffect(() => {
    if (profile && profile.schema === "slurm") {
      fetchProfileResources(profile.name)
        .then(data => setResources(data))
        .catch(err => {
          console.debug("NewJobModal: failed to fetch resources", err);
          setResources(null);
        });
    } else {
      setResources(null);
    }
  }, [profile]);

  // Initialize partition when resources load
  useEffect(() => {
    if (partitions.length > 0 && !selectedPartition) {
      const defaultPartition = partitions.find(p => p.default) || partitions[0];
      setSelectedPartition(defaultPartition.name);
    }
  }, [partitions, selectedPartition]);

  // Fetch recommended tier when model or partition changes
  useEffect(() => {
    if (repoId && profile && selectedPartition) {
      fetchModelTier(encodeURIComponent(repoId), profile.name, selectedPartition)
        .then(data => {
          if (data && data.tier) {
            setRecommendedTier(data.tier);
            setSelectedTier(data.tier);
          }
        })
        .catch(err => {
          console.debug("NewJobModal: failed to fetch model tier", err);
          if (tiers.length > 0 && !selectedTier) {
            setSelectedTier(tiers[0].name);
          }
        });
    }
  }, [repoId, profile, selectedPartition, tiers, selectedTier]);

  // Reset form on open
  useEffect(() => {
    if (open) {
      setCurrentStep(0);
      setVisitedSteps(new Set([0]));
      setRepoId(null);
      setModel(null);
      setInputDir("");
      setOutputDir("");
      setTaskParams({});
      setSelectedPartition(null);
      setSelectedTier(null);
      setRecommendedTier(null);
      setMaxWorkers(1);
      setShowAdvanced(false);
      setAccount("");
      setWorkerTimeout("");
      setClientTimeout("");
      setIsSubmitting(false);
      setSubmitError(null);
    }
  }, [open]);

  // Initialize task params when task changes
  useEffect(() => {
    if (!task) return;
    const defaults = {};
    task.params.forEach((param) => {
      if (param.default !== undefined) {
        defaults[param.name] = param.default;
      }
    });
    setTaskParams(defaults);
  }, [task]);

  // Initialize model when models load
  useEffect(() => {
    if (models && models.length > 0 && !repoId) {
      setRepoId(models[0].repo_id);
    }
  }, [models, repoId]);

  // Auto-scroll to bottom when advanced options opens
  useEffect(() => {
    if (showAdvanced && contentRef.current) {
      setTimeout(() => {
        contentRef.current.scrollTo({
          top: contentRef.current.scrollHeight,
          behavior: "smooth"
        });
      }, 50);
    }
  }, [showAdvanced]);

  const handleTaskParamChange = (paramName, value) => {
    setTaskParams((prev) => ({ ...prev, [paramName]: value }));
  };

  const handleNext = () => {
    if (currentStep < steps.length - 1) {
      const nextStep = currentStep + 1;
      setCurrentStep(nextStep);
      setVisitedSteps(prev => new Set([...prev, nextStep]));
    }
  };

  const handleBack = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleStepClick = (stepIndex) => {
    setCurrentStep(stepIndex);
    setVisitedSteps(prev => new Set([...prev, stepIndex]));
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);
    setSubmitError(null);

    try {
      // TODO: Replace with actual API call when backend is ready
      await new Promise((resolve) => setTimeout(resolve, 2000));

      const newJob = {
        id: `job-${Date.now()}`,
        name: `${task.name} - ${model?.repo_id || repoId}`,
        task: task.id,
        model: model?.repo_id || repoId,
        revision: model?.revision,
        input_dir: inputDir,
        output_dir: outputDir,
        tier: selectedTier,
        max_workers: maxWorkers,
        params: taskParams,
        status: "submitted",
        submitted_at: new Date().toISOString(),
      };

      console.debug("Job created:", newJob);
      onJobCreated?.(newJob);
      setOpen(false);
    } catch (error) {
      console.error("Failed to create job:", error);
      setSubmitError(error);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Validation for each step
  const isStepValid = (stepId) => {
    switch (stepId) {
      case "model":
        return repoId && !modelsLoading;
      case "options":
        // Check required params
        if (!task) return false;
        for (const param of task.params) {
          if (param.required && !taskParams[param.name]) {
            return false;
          }
        }
        return true;
      case "paths":
        return inputDir.trim() !== "" && outputDir.trim() !== "";
      case "resources":
        return selectedTier !== null;
      default:
        return true;
    }
  };

  const currentStepId = steps[currentStep]?.id;

  // Modal width based on current step - Data step needs more room for side-by-side browsers
  const modalMaxWidth = currentStepId === "paths" ? "sm:max-w-7xl" : "sm:max-w-4xl";

  // Check if a step is complete (for stepper checkmarks)
  // Only show checkmark if step has been visited AND is valid
  const checkStepComplete = (stepIndex) => {
    if (!visitedSteps.has(stepIndex)) return false;
    const stepId = steps[stepIndex]?.id;
    return isStepValid(stepId);
  };

  // Form is valid when all steps are complete
  const isFormValid = steps.every((_, index) => checkStepComplete(index));

  if (!profile || !task) {
    return null;
  }

  // Render step content
  const renderStepContent = () => {
    switch (currentStepId) {
      case "model":
        return (
          <div className="space-y-4">
            {modelsError ? (
              <Alert variant="error" title="Failed to load models">
                {modelsError.message || "Could not fetch models from the server."}
              </Alert>
            ) : !modelsLoading && (!models || models.length === 0) ? (
              <Alert variant="warning" title="No models available">
                Switch profiles or download a model from{" "}
                <a className="underline" href="https://huggingface.co/models?pipeline_tag=text-generation&sort=trending">
                  Hugging Face
                </a>.
              </Alert>
            ) : (
              <>
                <fieldset>
                  <ModelSelect
                    models={models || []}
                    repoId={repoId}
                    setRepoId={setRepoId}
                    disabled={isSubmitting || modelsLoading}
                  />
                </fieldset>
                <fieldset>
                  <RevisionSelect
                    models={models || []}
                    repoId={repoId}
                    setModel={setModel}
                    disabled={isSubmitting || modelsLoading}
                  />
                </fieldset>
                {modelsLoading && (
                  <p className="text-xs text-gray-500 dark:text-gray-400">Loading models...</p>
                )}
              </>
            )}
          </div>
        );

      case "options":
        return (
          <div className="space-y-4">
            {task.params.map((param) => (
              <fieldset key={param.name}>
                <label className="block text-sm font-medium leading-6 text-gray-900 dark:text-gray-100 mb-1">
                  {param.label}
                  {param.required && <span className="text-red-500 ml-1">*</span>}
                </label>
                {param.type === "select" ? (
                  <Listbox
                    value={taskParams[param.name] || param.default || param.options[0]?.value}
                    onChange={(value) => handleTaskParamChange(param.name, value)}
                    disabled={isSubmitting}
                  >
                    <div className="relative">
                      <ListboxButton className="relative w-full cursor-default rounded-md bg-white dark:bg-gray-700 py-1.5 pl-3 pr-10 text-left text-gray-900 dark:text-gray-100 shadow-sm ring-1 ring-inset ring-gray-300 dark:ring-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500 sm:text-sm sm:leading-6 disabled:bg-gray-100 dark:disabled:bg-gray-800">
                        <span className="block truncate">
                          {param.options.find(o => o.value === (taskParams[param.name] || param.default))?.label || param.options[0]?.label}
                        </span>
                        <span className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2">
                          <ChevronUpDownIcon className="h-5 w-5 text-gray-400" aria-hidden="true" />
                        </span>
                      </ListboxButton>
                      <ListboxOptions className="absolute z-10 mt-1 max-h-60 w-full overflow-auto rounded-md bg-white dark:bg-gray-700 py-1 text-base shadow-lg ring-1 ring-black dark:ring-gray-600 ring-opacity-5 focus:outline-none sm:text-sm">
                        {param.options.map((opt) => (
                          <ListboxOption
                            key={opt.value}
                            value={opt.value}
                            className={({ focus }) =>
                              `relative cursor-default select-none py-2 pl-3 pr-9 ${
                                focus ? "bg-blue-500 text-white" : "text-gray-900 dark:text-gray-100"
                              }`
                            }
                          >
                            {({ selected, focus }) => (
                              <>
                                <span className={`block truncate ${selected ? "font-semibold" : "font-normal"}`}>
                                  {opt.label}
                                </span>
                                {selected && (
                                  <span className={`absolute inset-y-0 right-0 flex items-center pr-4 ${focus ? "text-white" : "text-blue-600"}`}>
                                    <CheckIcon className="h-5 w-5" aria-hidden="true" />
                                  </span>
                                )}
                              </>
                            )}
                          </ListboxOption>
                        ))}
                      </ListboxOptions>
                    </div>
                  </Listbox>
                ) : (
                  <input
                    type="text"
                    value={taskParams[param.name] || ""}
                    onChange={(e) => handleTaskParamChange(param.name, e.target.value)}
                    placeholder={param.placeholder}
                    disabled={isSubmitting}
                    className="block w-full rounded-md border-0 py-1.5 px-3 text-gray-900 dark:text-gray-100 bg-white dark:bg-gray-700 shadow-sm ring-1 ring-inset ring-gray-300 dark:ring-gray-600 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-500 sm:text-sm sm:leading-6 disabled:bg-gray-100 dark:disabled:bg-gray-800"
                  />
                )}
                {param.help && (
                  <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">{param.help}</p>
                )}
              </fieldset>
            ))}

            {/* Prompt field - only show for tasks that use prompts */}
            {task.defaultPrompt && (
              <fieldset>
                <label className="block text-sm font-medium leading-6 text-gray-900 dark:text-gray-100 mb-1">
                  Prompt
                </label>
                <textarea
                  value={taskParams.prompt || ""}
                  onChange={(e) => handleTaskParamChange("prompt", e.target.value)}
                  placeholder={task.defaultPrompt}
                  disabled={isSubmitting}
                  rows={3}
                  className="block w-full rounded-md border-0 py-1.5 px-3 text-gray-900 dark:text-gray-100 bg-white dark:bg-gray-700 shadow-sm ring-1 ring-inset ring-gray-300 dark:ring-gray-600 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-500 sm:text-sm sm:leading-6 disabled:bg-gray-100 dark:disabled:bg-gray-800"
                />
                <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                  Leave empty to use the default prompt shown above.
                </p>
              </fieldset>
            )}

            {task.params.length === 0 && !task.defaultPrompt && (
              <p className="text-sm text-gray-500 dark:text-gray-400">
                No additional options for this task.
              </p>
            )}
          </div>
        );

      case "paths":
        return (
          <div>
            <div className="grid grid-cols-2 gap-6">
              <DirectoryBrowser
                label="Input Directory"
                value={inputDir}
                onChange={setInputDir}
                profile={profile}
                disabled={isSubmitting}
              />
              <DirectoryBrowser
                label="Output Directory"
                value={outputDir}
                onChange={setOutputDir}
                profile={profile}
                disabled={isSubmitting}
              />
            </div>

            {/* Connection status indicator for remote profiles */}
            {isRemote && (
              <div className="flex items-center justify-center gap-2 text-sm text-gray-500 dark:text-gray-400 mt-8">
                <span
                  className={`inline-block h-2 w-2 flex-shrink-0 rounded-full ${
                    isConnected
                      ? "bg-green-500"
                      : connectionError
                        ? "bg-red-500"
                        : "animate-pulse bg-yellow-500"
                  }`}
                />
                <span>
                  {isConnected
                    ? `Connected to ${profile?.name}`
                    : connectionError
                      ? "Connection failed"
                      : "Connecting..."}
                </span>
              </div>
            )}
          </div>
        );

      case "resources":
        return (
          <div className="space-y-4">
            {/* Partition selector - only show if multiple partitions */}
            {partitions.length > 1 && (
              <fieldset>
                <label className="block text-sm font-medium leading-6 text-gray-900 dark:text-gray-100 mb-2">
                  Partition
                </label>
                <PartitionSelect
                  partitions={partitions}
                  selectedPartition={selectedPartition}
                  setSelectedPartition={(name) => {
                    setSelectedPartition(name);
                    setSelectedTier(null);
                    setRecommendedTier(null);
                  }}
                  disabled={isSubmitting}
                />
              </fieldset>
            )}

            {/* Tier selection */}
            <div>
              <label className="block text-sm font-medium leading-6 text-gray-900 dark:text-gray-100 mb-2">
                Compute Tier
              </label>
              <TierSelect
                tiers={tiers}
                selectedTier={selectedTier}
                recommendedTier={recommendedTier}
                setSelectedTier={setSelectedTier}
                disabled={isSubmitting}
              />
            </div>

            <fieldset>
              <label className="block text-sm font-medium leading-6 text-gray-900 dark:text-gray-100 mb-1">
                Max Workers
              </label>
              <input
                type="number"
                min={1}
                max={10}
                value={maxWorkers}
                onChange={(e) => setMaxWorkers(parseInt(e.target.value) || 1)}
                disabled={isSubmitting}
                className="block w-full rounded-md border-0 py-1.5 px-3 text-gray-900 dark:text-gray-100 bg-white dark:bg-gray-700 shadow-sm ring-1 ring-inset ring-gray-300 dark:ring-gray-600 focus:ring-2 focus:ring-inset focus:ring-blue-500 sm:text-sm sm:leading-6 disabled:bg-gray-100 dark:disabled:bg-gray-800"
              />
              <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                Maximum number of concurrent Slurm jobs. TigerFlow scales automatically.
              </p>
            </fieldset>

            {/* Advanced Options */}
            <fieldset>
              <button
                type="button"
                onClick={() => setShowAdvanced(!showAdvanced)}
                className="flex items-center gap-2 w-full text-left"
              >
                <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                  Advanced Options
                </span>
                {showAdvanced ? (
                  <ChevronUpIcon className="h-4 w-4 text-gray-500" />
                ) : (
                  <ChevronDownIcon className="h-4 w-4 text-gray-500" />
                )}
              </button>
              {showAdvanced && (
                <div className="mt-3 space-y-4 pl-0">
                  <div>
                    <label htmlFor="account" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                      Account
                    </label>
                    <input
                      type="text"
                      id="account"
                      value={account}
                      onChange={(e) => setAccount(e.target.value)}
                      disabled={isSubmitting}
                      className="mt-1 block w-full rounded-md border-0 py-1.5 px-3 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm ring-1 ring-inset ring-gray-300 dark:ring-gray-600 focus:ring-2 focus:ring-blue-500 sm:text-sm disabled:bg-gray-100 dark:disabled:bg-gray-800"
                    />
                    <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                      Leave empty to use your default account.
                    </p>
                  </div>
                  <div>
                    <label htmlFor="worker-timeout" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                      Worker Timeout
                    </label>
                    <input
                      type="text"
                      id="worker-timeout"
                      value={workerTimeout}
                      onChange={(e) => setWorkerTimeout(e.target.value)}
                      placeholder="e.g., 01:00:00"
                      disabled={isSubmitting}
                      className="mt-1 block w-full rounded-md border-0 py-1.5 px-3 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm ring-1 ring-inset ring-gray-300 dark:ring-gray-600 focus:ring-2 focus:ring-blue-500 sm:text-sm disabled:bg-gray-100 dark:disabled:bg-gray-800"
                    />
                    <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                      Time limit for each worker job (HH:MM:SS).
                    </p>
                  </div>
                  <div>
                    <label htmlFor="client-timeout" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                      Client Timeout
                    </label>
                    <input
                      type="text"
                      id="client-timeout"
                      value={clientTimeout}
                      onChange={(e) => setClientTimeout(e.target.value)}
                      placeholder="e.g., 300"
                      disabled={isSubmitting}
                      className="mt-1 block w-full rounded-md border-0 py-1.5 px-3 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm ring-1 ring-inset ring-gray-300 dark:ring-gray-600 focus:ring-2 focus:ring-blue-500 sm:text-sm disabled:bg-gray-100 dark:disabled:bg-gray-800"
                    />
                    <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                      Timeout in seconds for client connections.
                    </p>
                  </div>
                </div>
              )}
            </fieldset>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <Transition show={open} as={Fragment}>
      <Dialog
        as="div"
        className="relative z-[60]"
        initialFocus={cancelButtonRef}
        onClose={() => setOpen(false)}
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
              <DialogPanel className={`relative transform rounded-lg bg-white dark:bg-gray-800 text-left shadow-xl transition-all sm:mt-4 sm:mb-8 sm:w-full ${modalMaxWidth} sm:mx-4 max-h-[90vh] flex flex-col`}>
                {/* Header */}
                <div className="px-4 pt-5 sm:px-6 sm:pt-6">
                  <DialogTitle
                    as="h3"
                    className="text-lg font-semibold leading-6 text-gray-900 dark:text-gray-100"
                  >
                    New {task?.name} Job
                  </DialogTitle>
                  <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                    {task?.description}
                  </p>

                  {/* Stepper */}
                  <div className="mt-6 -mx-4 sm:-mx-6 border-t border-b border-gray-200 dark:border-gray-600">
                    <Stepper
                      steps={steps}
                      currentStep={currentStep}
                      isStepComplete={checkStepComplete}
                      onStepClick={handleStepClick}
                    />
                  </div>
                </div>

                {/* Scrollable content area */}
                <div ref={contentRef} className="flex-1 overflow-y-auto px-4 py-6 sm:px-6">
                  {submitError && (
                    <Alert variant="error" title="Failed to create job" className="mb-4">
                      {submitError.message || "An unexpected error occurred"}
                    </Alert>
                  )}

                  <Transition
                    key={currentStepId}
                    appear
                    show={true}
                    enter="transition-opacity duration-200"
                    enterFrom="opacity-0"
                    enterTo="opacity-100"
                  >
                    {renderStepContent()}
                  </Transition>
                </div>

                {/* Footer with navigation buttons */}
                <div className="flex-shrink-0 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 px-4 sm:px-6 py-3 rounded-b-lg">
                  <div className="flex justify-between">
                    <div>
                      {currentStep > 0 && (
                        <button
                          type="button"
                          className="inline-flex items-center gap-1.5 text-sm font-medium text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 px-3 py-2"
                          onClick={handleBack}
                          disabled={isSubmitting}
                        >
                          <ArrowLeftIcon className="h-4 w-4" />
                          Back
                        </button>
                      )}
                    </div>
                    <div className="flex gap-3">
                      <button
                        type="button"
                        className="text-sm font-medium text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 px-3 py-2"
                        onClick={() => setOpen(false)}
                        ref={cancelButtonRef}
                      >
                        Cancel
                      </button>
                      {isLastStep ? (
                        <button
                          type="button"
                          className="w-28 inline-flex justify-center items-center gap-2 rounded-md bg-blue-500 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-400 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-500 disabled:bg-gray-300 dark:disabled:bg-gray-600 disabled:cursor-not-allowed"
                          onClick={handleSubmit}
                          disabled={!isFormValid || isSubmitting}
                        >
                          {isSubmitting ? (
                            <>
                              <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                              </svg>
                              Submitting
                            </>
                          ) : (
                            "Submit"
                          )}
                        </button>
                      ) : (
                        <button
                          type="button"
                          className="inline-flex items-center gap-1.5 rounded-md bg-blue-500 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-400 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-500"
                          onClick={handleNext}
                        >
                          Next
                          <ArrowRightIcon className="h-4 w-4" />
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              </DialogPanel>
            </TransitionChild>
          </div>
        </div>
      </Dialog>
    </Transition>
  );
}

NewJobModal.propTypes = {
  open: PropTypes.bool.isRequired,
  setOpen: PropTypes.func.isRequired,
  profile: PropTypes.object,
  task: PropTypes.object,
  onJobCreated: PropTypes.func,
};

export default NewJobModal;
