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
import ServiceModalValidatedInput from "@/components/ServiceModalValidatedInput";
import Alert from "@/components/Alert";
import Stepper from "@/components/Stepper";
import DirectoryBrowser from "@/components/DirectoryBrowser";
import { useModels } from "@/lib/loaders";
import { useRemoteFileSystem } from "@/providers/RemoteFileSystemProvider";
import { fetchProfileResources, fetchModelSizeFromHub, createJob } from "@/lib/requests";
import { selectTierByModelSize, isRemoteProfile } from "@/lib/util";
import PropTypes from "prop-types";

// Task definitions - each task maps to a TigerFlow task type
// id must match backend SUPPORTED_TASKS keys (detect, ocr, transcribe, translate)
// service can be a string or array of strings for tasks that support multiple model types
export const TASKS = [
  {
    id: "detect",
    name: "Object Detection",
    description: "Detect objects in images or videos",
    service: "object-detection", // Backend COMPATIBLE_PIPELINES includes zero-shot-object-detection
    defaultInputExt: ".jpg",
    defaultPrompt: null,
    inputExtOptions: [
      { value: ".jpg", label: "JPEG (.jpg)" },
      { value: ".jpeg", label: "JPEG (.jpeg)" },
      { value: ".png", label: "PNG (.png)" },
      { value: ".tiff", label: "TIFF (.tiff)" },
      { value: ".mp4", label: "MP4 (.mp4)" },
      { value: ".avi", label: "AVI (.avi)" },
      { value: ".mov", label: "MOV (.mov)" },
      { value: ".mkv", label: "MKV (.mkv)" },
      { value: ".webm", label: "WebM (.webm)" },
    ],
    params: [
      {
        name: "labels",
        type: "text",
        required: false, // Dynamically required for zero-shot models
        label: "Labels",
        help: "Comma-separated labels to detect (e.g., \"cat,dog,person\").",
        placeholder: "cat,dog,person",
        showWhen: { modelType: "zero-shot-object-detection" },
      },
      {
        name: "threshold",
        type: "text",
        required: false,
        label: "Confidence Threshold",
        help: "Minimum confidence score (0-1). Default: 0.3",
        placeholder: "0.3",
      },
      {
        name: "batch_size",
        type: "text",
        required: false,
        label: "Batch Size",
        help: "Parallel frame processing count. Default: 4",
        placeholder: "4",
      },
      {
        name: "sample_fps",
        type: "text",
        required: false,
        label: "Sample FPS",
        help: "Video sampling rate. Use 0 for all frames. Default: 1.0",
        placeholder: "1.0",
      },
    ],
  },
  {
    id: "ocr",
    name: "OCR",
    description: "Extract text from images",
    service: "image-text-to-text", // Vision models only
    defaultInputExt: ".png",
    defaultPrompt: "Extract all text from this image.",
    inputExtOptions: [
      { value: ".png", label: "PNG (.png)" },
      { value: ".jpg", label: "JPEG (.jpg)" },
      { value: ".jpeg", label: "JPEG (.jpeg)" },
      { value: ".tiff", label: "TIFF (.tiff)" },
      { value: ".pdf", label: "PDF (.pdf)" },
    ],
    params: [
      {
        name: "output_format",
        type: "select",
        required: false,
        label: "Output Format",
        options: [
          { value: "text", label: "Plain text (.txt)" },
          { value: "markdown", label: "Markdown (.md)" },
          { value: "json", label: "JSON (.json)" },
        ],
        default: "text",
      },
    ],
  },
  {
    id: "transcribe",
    name: "Transcription",
    description: "Convert audio to text",
    service: "speech-recognition", // Uses Whisper models
    defaultInputExt: ".wav",
    defaultPrompt: null, // Whisper doesn't use prompts
    inputExtOptions: [
      { value: ".wav", label: "WAV (.wav)" },
      { value: ".mp3", label: "MP3 (.mp3)" },
      { value: ".flac", label: "FLAC (.flac)" },
      { value: ".m4a", label: "M4A (.m4a)" },
      { value: ".ogg", label: "OGG (.ogg)" },
      { value: ".webm", label: "WebM (.webm)" },
    ],
    params: [
      {
        name: "language",
        type: "select",
        required: false,
        label: "Language",
        help: "Language spoken in the audio. Leave empty to auto-detect.",
        options: [
          { value: "", label: "Auto-detect" },
          { value: "en", label: "English" },
          { value: "es", label: "Spanish" },
          { value: "fr", label: "French" },
          { value: "de", label: "German" },
          { value: "it", label: "Italian" },
          { value: "pt", label: "Portuguese" },
          { value: "zh", label: "Chinese" },
          { value: "ja", label: "Japanese" },
          { value: "ko", label: "Korean" },
          { value: "ar", label: "Arabic" },
          { value: "hi", label: "Hindi" },
          { value: "ru", label: "Russian" },
        ],
        default: "",
      },
      {
        name: "output_format",
        type: "select",
        required: false,
        label: "Output Format",
        options: [
          { value: "text", label: "Plain text (.txt)" },
          { value: "srt", label: "Subtitles (.srt)" },
          { value: "json", label: "JSON (.json)" },
        ],
        default: "text",
      },
    ],
  },
  {
    id: "translate",
    name: "Translation",
    description: "Translate text between languages",
    service: "text-generation", // Uses LLM models
    defaultInputExt: ".txt",
    defaultPrompt: "Translate the following text to {target_language}. Preserve the original formatting.",
    params: [
      {
        name: "source_lang",
        type: "select",
        required: true,
        label: "Source Language",
        default: "auto",
        help: "Language of the input text.",
        options: [
          { value: "auto", label: "Auto-detect" },
          { value: "af", label: "Afrikaans" },
          { value: "ar", label: "Arabic" },
          { value: "bg", label: "Bulgarian" },
          { value: "bn", label: "Bengali" },
          { value: "ca", label: "Catalan" },
          { value: "cs", label: "Czech" },
          { value: "cy", label: "Welsh" },
          { value: "da", label: "Danish" },
          { value: "de", label: "German" },
          { value: "el", label: "Greek" },
          { value: "en", label: "English" },
          { value: "es", label: "Spanish" },
          { value: "et", label: "Estonian" },
          { value: "fa", label: "Persian" },
          { value: "fi", label: "Finnish" },
          { value: "fr", label: "French" },
          { value: "gu", label: "Gujarati" },
          { value: "he", label: "Hebrew" },
          { value: "hi", label: "Hindi" },
          { value: "hr", label: "Croatian" },
          { value: "hu", label: "Hungarian" },
          { value: "id", label: "Indonesian" },
          { value: "it", label: "Italian" },
          { value: "ja", label: "Japanese" },
          { value: "kn", label: "Kannada" },
          { value: "ko", label: "Korean" },
          { value: "lt", label: "Lithuanian" },
          { value: "lv", label: "Latvian" },
          { value: "mk", label: "Macedonian" },
          { value: "ml", label: "Malayalam" },
          { value: "mr", label: "Marathi" },
          { value: "ne", label: "Nepali" },
          { value: "nl", label: "Dutch" },
          { value: "no", label: "Norwegian" },
          { value: "pa", label: "Punjabi" },
          { value: "pl", label: "Polish" },
          { value: "pt", label: "Portuguese" },
          { value: "ro", label: "Romanian" },
          { value: "ru", label: "Russian" },
          { value: "sk", label: "Slovak" },
          { value: "sl", label: "Slovenian" },
          { value: "so", label: "Somali" },
          { value: "sq", label: "Albanian" },
          { value: "sv", label: "Swedish" },
          { value: "sw", label: "Swahili" },
          { value: "ta", label: "Tamil" },
          { value: "te", label: "Telugu" },
          { value: "th", label: "Thai" },
          { value: "tl", label: "Tagalog" },
          { value: "tr", label: "Turkish" },
          { value: "uk", label: "Ukrainian" },
          { value: "ur", label: "Urdu" },
          { value: "vi", label: "Vietnamese" },
          { value: "zh-cn", label: "Chinese (Simplified)" },
          { value: "zh-tw", label: "Chinese (Traditional)" },
        ],
      },
      {
        name: "target_lang",
        type: "select",
        required: true,
        label: "Target Language",
        help: "Language to translate into.",
        options: [
          { value: "af", label: "Afrikaans" },
          { value: "ar", label: "Arabic" },
          { value: "bg", label: "Bulgarian" },
          { value: "bn", label: "Bengali" },
          { value: "ca", label: "Catalan" },
          { value: "cs", label: "Czech" },
          { value: "cy", label: "Welsh" },
          { value: "da", label: "Danish" },
          { value: "de", label: "German" },
          { value: "el", label: "Greek" },
          { value: "en", label: "English" },
          { value: "es", label: "Spanish" },
          { value: "et", label: "Estonian" },
          { value: "fa", label: "Persian" },
          { value: "fi", label: "Finnish" },
          { value: "fr", label: "French" },
          { value: "gu", label: "Gujarati" },
          { value: "he", label: "Hebrew" },
          { value: "hi", label: "Hindi" },
          { value: "hr", label: "Croatian" },
          { value: "hu", label: "Hungarian" },
          { value: "id", label: "Indonesian" },
          { value: "it", label: "Italian" },
          { value: "ja", label: "Japanese" },
          { value: "kn", label: "Kannada" },
          { value: "ko", label: "Korean" },
          { value: "lt", label: "Lithuanian" },
          { value: "lv", label: "Latvian" },
          { value: "mk", label: "Macedonian" },
          { value: "ml", label: "Malayalam" },
          { value: "mr", label: "Marathi" },
          { value: "ne", label: "Nepali" },
          { value: "nl", label: "Dutch" },
          { value: "no", label: "Norwegian" },
          { value: "pa", label: "Punjabi" },
          { value: "pl", label: "Polish" },
          { value: "pt", label: "Portuguese" },
          { value: "ro", label: "Romanian" },
          { value: "ru", label: "Russian" },
          { value: "sk", label: "Slovak" },
          { value: "sl", label: "Slovenian" },
          { value: "so", label: "Somali" },
          { value: "sq", label: "Albanian" },
          { value: "sv", label: "Swedish" },
          { value: "sw", label: "Swahili" },
          { value: "ta", label: "Tamil" },
          { value: "te", label: "Telugu" },
          { value: "th", label: "Thai" },
          { value: "tl", label: "Tagalog" },
          { value: "tr", label: "Turkish" },
          { value: "uk", label: "Ukrainian" },
          { value: "ur", label: "Urdu" },
          { value: "vi", label: "Vietnamese" },
          { value: "zh-cn", label: "Chinese (Simplified)" },
          { value: "zh-tw", label: "Chinese (Traditional)" },
        ],
      },
    ],
  },
];

// Map output_format values to file extensions
const OUTPUT_FORMAT_EXT = {
  text: ".txt",
  markdown: ".md",
  json: ".json",
  srt: ".srt",
};

// ISO language codes supported by langdetect
const ISO_LANGUAGE_CODES = new Set([
  "af", "ar", "bg", "bn", "ca", "cs", "cy", "da", "de", "el", "en", "es", "et",
  "fa", "fi", "fr", "gu", "he", "hi", "hr", "hu", "id", "it", "ja", "kn", "ko",
  "lt", "lv", "mk", "ml", "mr", "ne", "nl", "no", "pa", "pl", "pt", "ro", "ru",
  "sk", "sl", "so", "sq", "sv", "sw", "ta", "te", "th", "tl", "tr", "uk", "ur",
  "vi", "zh-cn", "zh-tw", "zh",
]);

/**
 * Extract language pair from model repo_id if present.
 * Matches patterns like: opus-mt-en-de, model_en_to_de, nllb-en-de
 * @returns {[string, string] | null} [source, target] or null if not found
 */
function extractLanguagePair(repoId) {
  if (!repoId) return null;
  const name = repoId.split("/").pop().toLowerCase();

  // Pattern: {src}_to_{tgt} or {src}-to-{tgt}
  const toMatch = name.match(/[_-]([a-z]{2}(?:-[a-z]{2})?)[_-]to[_-]([a-z]{2}(?:-[a-z]{2})?)/);
  if (toMatch) {
    const [, src, tgt] = toMatch;
    if (ISO_LANGUAGE_CODES.has(src) && ISO_LANGUAGE_CODES.has(tgt)) {
      return [src, tgt];
    }
  }

  // Pattern: -{src}-{tgt} or _{src}_{tgt} at end or before version
  const pairMatch = name.match(/[_-]([a-z]{2}(?:-[a-z]{2})?)[_-]([a-z]{2}(?:-[a-z]{2})?)(?:[_-]|$)/);
  if (pairMatch) {
    const [, src, tgt] = pairMatch;
    if (ISO_LANGUAGE_CODES.has(src) && ISO_LANGUAGE_CODES.has(tgt)) {
      return [src, tgt];
    }
  }

  return null;
}

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
  const isRemote = isRemoteProfile(profile);

  // Stepper state
  const [currentStep, setCurrentStep] = useState(0);
  const [visitedSteps, setVisitedSteps] = useState(new Set([0]));

  // Job name
  const [jobName, setJobName] = useState("");

  // Model selection - fetch models for the task's service type(s)
  const { models, isLoading: modelsLoading, error: modelsError } = useModels(profile, task?.service);
  const [repoId, setRepoId] = useState(null);
  const [model, setModel] = useState(null);

  // Derive model type from selected model's image field (e.g., "object-detection", "zero-shot-object-detection")
  const modelType = model?.image || null;

  // Paths
  const [inputDir, setInputDir] = useState("");
  const [outputDir, setOutputDir] = useState("");

  // Task-specific parameters
  const [taskParams, setTaskParams] = useState({});
  const [inputExt, setInputExt] = useState(null);

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
  const [idleTimeout, setIdleTimeout] = useState("");
  const [advancedErrors, setAdvancedErrors] = useState({
    account: null,
    workerTimeout: null,
    idleTimeout: null,
  });
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

  // Select recommended tier based on model size (client-side)
  useEffect(() => {
    if (!repoId || tiers.length === 0) return;

    // Check for model override first
    const modelOverrides = resources?.models || {};
    if (modelOverrides[repoId]) {
      const override = modelOverrides[repoId];
      if (override.includes('.')) {
        const [partitionName, tierName] = override.split('.');
        setSelectedPartition(partitionName);
        setRecommendedTier(tierName);
        setSelectedTier(tierName);
      } else {
        setRecommendedTier(override);
        setSelectedTier(override);
      }
      return;
    }

    // Fetch model size from HuggingFace and select tier
    fetchModelSizeFromHub(repoId)
      .then(sizeGb => {
        if (sizeGb !== null) {
          const tierName = selectTierByModelSize(tiers, sizeGb);
          if (tierName) {
            setRecommendedTier(tierName);
            setSelectedTier(tierName);
          }
        }
      })
      .catch(err => {
        console.debug("NewJobModal: failed to fetch model size", err);
      });
  }, [repoId, tiers, resources?.models]);

  // Reset form on open
  useEffect(() => {
    if (open) {
      setCurrentStep(0);
      setVisitedSteps(new Set([0]));
      setJobName("");
      setRepoId(null);
      setModel(null);
      setInputDir("");
      setOutputDir("");
      setTaskParams({});
      setInputExt(null);
      setSelectedPartition(null);
      setSelectedTier(null);
      setRecommendedTier(null);
      setMaxWorkers(1);
      setShowAdvanced(false);
      setAccount("");
      setWorkerTimeout("");
      setIdleTimeout("");
      setAdvancedErrors({ account: null, workerTimeout: null, idleTimeout: null });
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

  // Auto-detect language pair from model name for translation task
  useEffect(() => {
    if (task?.id !== "translate" || !repoId) return;
    const langPair = extractLanguagePair(repoId);
    if (langPair) {
      const [src, tgt] = langPair;
      setTaskParams(prev => ({
        ...prev,
        source_lang: src,
        target_lang: tgt,
      }));
    }
  }, [task?.id, repoId]);

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

  // Slurm account names: letters, digits, underscore, dash, dot
  const ACCOUNT_PATTERN = /^[A-Za-z0-9_.-]+$/;
  const TIME_PATTERN = /^(\d{1,3}):([0-5]\d):([0-5]\d)$/;
  const WORKER_TIMEOUT_MAX_SECONDS = 7 * 24 * 3600; // 7 days
  const IDLE_TIMEOUT_MAX_SECONDS = 24 * 3600; // 24 hours

  const parseTimeToSeconds = (value) => {
    const match = TIME_PATTERN.exec(String(value).trim());
    if (!match) return null;
    const [, h, m, s] = match;
    return Number(h) * 3600 + Number(m) * 60 + Number(s);
  };

  const formatSecondsAsTime = (totalSeconds) => {
    const h = Math.floor(totalSeconds / 3600);
    const m = Math.floor((totalSeconds % 3600) / 60);
    const s = totalSeconds % 60;
    const pad = (n) => String(n).padStart(2, "0");
    return `${pad(h)}:${pad(m)}:${pad(s)}`;
  };

  const validateAccount = (value) => {
    const trimmed = String(value).trim();
    if (trimmed === "") {
      setAdvancedErrors((prev) => ({ ...prev, account: null }));
      return { ok: true };
    }
    if (!ACCOUNT_PATTERN.test(trimmed)) {
      const error = {
        message: "Account may only contain letters, numbers, '_', '-', and '.'.",
        ok: false,
      };
      setAdvancedErrors((prev) => ({ ...prev, account: error }));
      return error;
    }
    setAdvancedErrors((prev) => ({ ...prev, account: null }));
    return { ok: true };
  };

  const validateHHMMSS = (value, { maxSeconds, fieldKey }) => {
    const trimmed = String(value).trim();
    if (trimmed === "") {
      setAdvancedErrors((prev) => ({ ...prev, [fieldKey]: null }));
      return { ok: true };
    }
    const seconds = parseTimeToSeconds(trimmed);
    if (seconds === null) {
      const error = {
        message: "Time must be in HH:MM:SS format (e.g., 01:00:00).",
        ok: false,
      };
      setAdvancedErrors((prev) => ({ ...prev, [fieldKey]: error }));
      return error;
    }
    if (seconds < 1) {
      const error = {
        message: "Time must be at least 00:00:01.",
        ok: false,
      };
      setAdvancedErrors((prev) => ({ ...prev, [fieldKey]: error }));
      return error;
    }
    if (seconds > maxSeconds) {
      const error = {
        message: `Time must be ${formatSecondsAsTime(maxSeconds)} or less.`,
        ok: false,
      };
      setAdvancedErrors((prev) => ({ ...prev, [fieldKey]: error }));
      return error;
    }
    setAdvancedErrors((prev) => ({ ...prev, [fieldKey]: null }));
    return { ok: true };
  };

  const validateWorkerTimeout = (value) =>
    validateHHMMSS(value, {
      maxSeconds: WORKER_TIMEOUT_MAX_SECONDS,
      fieldKey: "workerTimeout",
    });

  const validateIdleTimeout = (value) =>
    validateHHMMSS(value, {
      maxSeconds: IDLE_TIMEOUT_MAX_SECONDS,
      fieldKey: "idleTimeout",
    });

  const hasAdvancedErrors = Boolean(
    advancedErrors.account || advancedErrors.workerTimeout || advancedErrors.idleTimeout
  );

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
      // Build resources object from selected tier
      const selectedTierObj = tiers.find(t => t.name === selectedTier);
      const jobResources = {};

      // Map tier fields to backend format
      if (selectedTierObj?.cpu_cores) jobResources.cpus = selectedTierObj.cpu_cores;
      if (selectedTierObj?.memory_gb) jobResources.memory = `${selectedTierObj.memory_gb}GB`;
      if (selectedTierObj?.gpu_count) jobResources.gpus = selectedTierObj.gpu_count;

      // Add optional advanced options as sbatch_options
      const sbatchOptions = [];
      if (account) sbatchOptions.push(`--account=${account}`);
      if (workerTimeout) jobResources.time = workerTimeout;
      if (sbatchOptions.length > 0) jobResources.sbatch_options = sbatchOptions;

      // Derive cache_dir from model's model_dir (parent directory)
      const cacheDir = model?.model_dir ? dirname(model.model_dir) : null;

      // Derive output_ext from output_format param if present
      const outputFormat = taskParams.output_format;
      const outputExt = outputFormat ? OUTPUT_FORMAT_EXT[outputFormat] : null;

      // Build job request matching BatchJobRequest schema
      const jobRequest = {
        name: jobName.trim() || `${task.name} - ${model?.repo_id || repoId}`,
        task: task.id,
        repo_id: model?.repo_id || repoId,
        revision: model?.revision || null,
        profile: profile,
        input_dir: inputDir,
        output_dir: outputDir,
        input_ext: inputExt || task.defaultInputExt || null,
        output_ext: outputExt,
        cache_dir: cacheDir,
        params: Object.keys(taskParams).length > 0 ? taskParams : null,
        resources: Object.keys(jobResources).length > 0 ? jobResources : null,
        max_workers: maxWorkers,
        idle_timeout: idleTimeout
          ? Math.max(1, Math.ceil(parseTimeToSeconds(idleTimeout) / 60))
          : undefined,
      };

      console.debug("Submitting job request:", jobRequest);
      const newJob = await createJob(jobRequest);
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

  // Helper to get parent directory
  function dirname(path) {
    if (!path) return null;
    const parts = path.split("/");
    return parts.slice(0, -1).join("/");
  }

  // Validation for each step
  const isStepValid = (stepId) => {
    switch (stepId) {
      case "model":
        return repoId && !modelsLoading;
      case "options":
        // Check required params (including dynamically required ones based on model type)
        if (!task) return false;
        for (const param of task.params) {
          // Skip params that don't apply to current model type
          if (param.showWhen?.modelType && modelType !== param.showWhen.modelType) {
            continue;
          }
          // Params with showWhen are required when shown
          const isRequired = param.showWhen ? true : param.required;
          if (isRequired && !taskParams[param.name]) {
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

  // Form is valid when all steps are complete and no advanced option errors
  const isFormValid =
    steps.every((_, index) => checkStepComplete(index)) && !hasAdvancedErrors;

  if (!profile || !task) {
    return null;
  }

  // Render step content
  const renderStepContent = () => {
    switch (currentStepId) {
      case "model":
        return (
          <div className="space-y-4">
            <fieldset>
              <label className="block text-sm font-medium leading-6 text-gray-900 dark:text-gray-100 mb-1">
                Job Name
              </label>
              <input
                type="text"
                value={jobName}
                onChange={(e) => setJobName(e.target.value)}
                placeholder={`${task?.name || "Job"} - ${repoId || "model"}`}
                disabled={isSubmitting}
                className="block w-full rounded-md border-0 py-1.5 px-3 text-gray-900 dark:text-gray-100 bg-white dark:bg-gray-700 shadow-sm ring-1 ring-inset ring-gray-300 dark:ring-gray-600 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-500 sm:text-sm sm:leading-6 disabled:bg-gray-100 dark:disabled:bg-gray-800"
              />
              <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                Leave empty for auto-generated name.
              </p>
            </fieldset>
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
            {/* Input format - only show for tasks with options */}
            {task.inputExtOptions && (
              <fieldset>
                <label className="block text-sm font-medium leading-6 text-gray-900 dark:text-gray-100 mb-1">
                  Input Format
                </label>
                <Listbox
                  value={inputExt || task.defaultInputExt}
                  onChange={setInputExt}
                  disabled={isSubmitting}
                >
                  <div className="relative">
                    <ListboxButton className="relative w-full cursor-default rounded-md bg-white dark:bg-gray-700 py-1.5 pl-3 pr-10 text-left text-gray-900 dark:text-gray-100 shadow-sm ring-1 ring-inset ring-gray-300 dark:ring-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500 sm:text-sm sm:leading-6 disabled:bg-gray-100 dark:disabled:bg-gray-800">
                      <span className="block truncate">
                        {task.inputExtOptions.find(o => o.value === (inputExt || task.defaultInputExt))?.label || task.defaultInputExt}
                      </span>
                      <span className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2">
                        <ChevronUpDownIcon className="h-5 w-5 text-gray-400" aria-hidden="true" />
                      </span>
                    </ListboxButton>
                    <ListboxOptions
                      anchor="bottom start"
                      className="z-50 mt-1 max-h-60 w-[var(--button-width)] overflow-auto rounded-md bg-white dark:bg-gray-700 py-1 text-base shadow-lg ring-1 ring-black dark:ring-gray-600 ring-opacity-5 focus:outline-none sm:text-sm"
                    >
                      {task.inputExtOptions.map((opt) => (
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
                <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                  File extension to match in the input directory.
                </p>
              </fieldset>
            )}

            {task.params
              .filter((param) => {
                // Filter out params with showWhen conditions that don't match
                if (param.showWhen?.modelType) {
                  return modelType === param.showWhen.modelType;
                }
                return true;
              })
              .map((param) => {
                // Params with showWhen are required when shown
                const isRequired = param.showWhen ? true : param.required;
                return (
              <fieldset key={param.name}>
                <label className="block text-sm font-medium leading-6 text-gray-900 dark:text-gray-100 mb-1">
                  {param.label}
                  {isRequired && <span className="text-red-500 ml-1">*</span>}
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
                      <ListboxOptions
                        anchor="bottom start"
                        className="z-50 mt-1 max-h-60 w-[var(--button-width)] overflow-auto rounded-md bg-white dark:bg-gray-700 py-1 text-base shadow-lg ring-1 ring-black dark:ring-gray-600 ring-opacity-5 focus:outline-none sm:text-sm"
                      >
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
                );
              })}

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
                    ? `Connected to ${profile?.host}`
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
                  <ServiceModalValidatedInput
                    type="text"
                    htmlFor="account"
                    label="Account"
                    help="Leave empty to use your default account."
                    value={account}
                    setValue={setAccount}
                    validate={validateAccount}
                    disabled={isSubmitting}
                  />
                  <ServiceModalValidatedInput
                    type="text"
                    htmlFor="worker-timeout"
                    label="Worker Timeout"
                    placeholder="01:00:00"
                    help="Time limit for each worker job in HH:MM:SS format (max 168:00:00)."
                    value={workerTimeout}
                    setValue={setWorkerTimeout}
                    validate={validateWorkerTimeout}
                    disabled={isSubmitting}
                  />
                  <ServiceModalValidatedInput
                    type="text"
                    htmlFor="idle-timeout"
                    label="Idle Timeout"
                    placeholder="00:10:00"
                    help="Time of inactivity before the job auto-terminates in HH:MM:SS format (max 24:00:00)."
                    value={idleTimeout}
                    setValue={setIdleTimeout}
                    validate={validateIdleTimeout}
                    disabled={isSubmitting}
                  />
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
