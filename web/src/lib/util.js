import PropTypes from "prop-types";

/**
 * Pause execution for the given amount.
 * @param {number} ms - Milliseconds to pause execution.
 * @return {Promise<number>} Resolves to `timeoutID`.
 */
export const sleep = (ms = 0) => new Promise((resolve) => resolve(setTimeout(resolve, ms)));

/**
 * Generate an absolute path from a relative one.
 * @param {string} path - Relative path.
 * @return {string} An absolute path.
 */
export const appendBasePath = (path) => {
  return `${process.env.basePath ? process.env.basePath : ''}${path}`
};

/**
 * Sanitizes class names data for HTML output.
 * @param {string} classes - Each param is a class name. `"one", two", "three"`
 * @return "one two three"
 */
export const classNames = (...classes) => {
  return classes.filter(Boolean).join(" ");
};

/**
 * Enumerates all possible service status.
 */
export const ServiceStatus = Object.freeze({
  SUBMITTED: "submitted",
  PENDING: "pending",
  STARTING: "starting",
  HEALTHY: "healthy",
  UNHEALTHY: "unhealthy",
  TIMEOUT: "timeout",
  STOPPED: "stopped",
  EXPIRED: "expired",
  FAILED: "failed",
});

/**
 * Status color scheme:
 * - green: operational (healthy)
 * - yellow: transitional (starting, pending, submitted) or degraded (unhealthy)
 * - red: error (timeout, failed)
 * - gray: inactive (stopped, expired)
 */

/**
 * Get CSS classes for a status indicator dot.
 * @param {string} status - Service status value.
 * @param {object} options - Optional configuration.
 * @param {boolean} options.pulse - Whether to add pulse animation for transitional states.
 * @return {string} Tailwind CSS classes for the dot.
 */
export function getStatusDotClasses(status, { pulse = true } = {}) {
  switch (status) {
    case ServiceStatus.HEALTHY:
      return "bg-green-500";
    case ServiceStatus.UNHEALTHY:
      return "bg-yellow-500";
    case ServiceStatus.STARTING:
    case ServiceStatus.PENDING:
    case ServiceStatus.SUBMITTED:
      return pulse ? "animate-pulse bg-yellow-500" : "bg-yellow-500";
    case ServiceStatus.TIMEOUT:
    case ServiceStatus.FAILED:
      return "bg-red-500";
    case ServiceStatus.STOPPED:
    case ServiceStatus.EXPIRED:
      return "bg-gray-400";
    default:
      return "bg-gray-300";
  }
}

/**
 * Get CSS classes for a status badge.
 * @param {string} status - Service status value.
 * @return {object} Object with fillColor, bgColor, and textColor classes.
 */
export function getStatusBadgeClasses(status) {
  switch (status) {
    case ServiceStatus.HEALTHY:
      return {
        fillColor: "fill-green-400",
        bgColor: "bg-green-100 dark:bg-green-900/30",
        textColor: "text-green-700 dark:text-green-400",
      };
    case ServiceStatus.UNHEALTHY:
      return {
        fillColor: "fill-yellow-400",
        bgColor: "bg-yellow-100 dark:bg-yellow-900/30",
        textColor: "text-yellow-700 dark:text-yellow-400",
      };
    case ServiceStatus.STARTING:
    case ServiceStatus.PENDING:
    case ServiceStatus.SUBMITTED:
      return {
        fillColor: "fill-yellow-400",
        bgColor: "bg-yellow-100 dark:bg-yellow-900/30",
        textColor: "text-yellow-700 dark:text-yellow-400",
      };
    case ServiceStatus.TIMEOUT:
    case ServiceStatus.FAILED:
      return {
        fillColor: "fill-red-400",
        bgColor: "bg-red-100 dark:bg-red-900/30",
        textColor: "text-red-700 dark:text-red-400",
      };
    case ServiceStatus.STOPPED:
    case ServiceStatus.EXPIRED:
      return {
        fillColor: "fill-gray-400",
        bgColor: "bg-gray-100 dark:bg-gray-700",
        textColor: "text-gray-600 dark:text-gray-400",
      };
    default:
      return {
        fillColor: "fill-gray-400",
        bgColor: "bg-gray-100 dark:bg-gray-700",
        textColor: "text-gray-600 dark:text-gray-400",
      };
  }
}

/**
 * A random integer.
 * @param {number} [min=0] - The lowest possible number to return. Default 0.
 * @param {number} [max=100] - The highest possible number to return. Default 100.
 * @return {number} Random number between `min` and `max`.
 */
export function randomInt(min = 0, max = 100) {
  return Math.floor(Math.random() * (max - min) + min);
}

randomInt.PropTypes = {
  min: PropTypes.number,
  max: PropTypes.number,
};

/**
 * A random integer.
 * Convert bytes to KB, MB, etc.
 * @param {number} bytes - Raw byte count. Will be converted to int.
 * @return {string}
 */
export function fileSize(bytes) {
  if (typeof bytes !== "number") {
    throw new Error(`bytes should be a number (received: "${typeof bytes}").`);
  }
  const n = parseInt(bytes);
  if (Number.isNaN(n)) {
    throw new Error("Cannot parse byte input: wrong type.");
  }
  if (n / 1_000 < 1.0) {
    return `${n} B`;
  } else if (n / 1_000_000 < 1.0) {
    return `${Math.floor(n / 1_000)} KB`;
  } else if (n / 1_000_000_000 < 1.0) {
    return `${Math.floor(n / 1_000_000)} MB`;
  } else if (n / 1_000_000_000_000 < 1.0) {
    return `${Math.floor(n / 1_000_000_000)} GB`;
  } else {
    return `${Math.floor(n / 1_000_000_000_000)} TB`;
  }
}

/**
 * Convert `datetime` string to seconds, minutes, hours, or days ago.
 * @param {string} datetime - Valid `Date` format.
 * @return {string}
 */
export function lastModified(datetime) {
  const date = new Date(datetime);
  const now = new Date();
  const dt = now - date; // milliseconds
  if (Number.isNaN(dt)) {
    throw new Error("Cannot parse date");
  }
  if (dt / 1000 < 60) {
    return `${Math.floor(dt / 1000)} seconds ago`;
  } else if (dt / 1000 / 60 < 60) {
    return `${Math.floor(dt / 1000 / 60)} minutes ago`;
  } else if (dt / 1000 / 3600 < 24) {
    return `${Math.floor(dt / 1000 / 3600)} hours ago`;
  } else {
    return `${Math.floor(dt / 1000 / 3600 / 24)} days ago`;
  }
}

/**
 * Get a list of only unique repo IDs.
 * @param {object} models
 * @param {string} models.repo_id
 * @return {Array<string>} Unique repo IDs.
 */
export function getUniqueRepoIds(models) {
  return models ? models.filter((value, index, array) => {
    return array.map(model => model.repo_id).indexOf(value.repo_id) === index
  }) : [];
}

/**
 * Format time interval.
 * @param {Date} refTime - Time in the past.
 * @param {Date} currentTime - The current time.
 * @return {string} The formatted "ago" time, e.g "2 hr 34 min".
 */
export function formattedTimeInterval(refTime, currentTime) {
  let dt = Math.abs(currentTime - refTime);

  const ms = dt % 1000;
  dt = (dt - ms) / 1000;
  const s = dt % 60;
  dt = (dt - s) / 60;
  const m = dt % 60;
  dt = (dt - m) / 60;
  const h = dt % 24;
  const d = (dt - h) / 24;

  if (d === 1) {
    return `${d} day ${m} min`;
  } else if (d > 0) {
    return `${d} days ${m} min`;
  } else if (h > 0) {
    return `${h} hr ${m} min`;
  } else if (m > 0) {
    return `${m} min ${s} sec`;
  } else {
    return `${s} sec`;
  }
};

/**
 * Whether a profile should be treated as "remote" for file I/O and other
 * non-scheduling purposes. A Slurm profile with host=localhost is scheduled
 * via sbatch but its filesystem is the same as the server's, so it should
 * be treated as local for file access.
 * @param {object|null} profile
 * @return {boolean}
 */
export function isRemoteProfile(profile) {
  return Boolean(
    profile?.schema === "slurm" && profile.host && profile.host !== "localhost"
  );
}

/**
 * Is a service running.
 * @param {object} service
 * @param {string|null} service.status
 * @return {boolean}
 */
export function isServiceRunning({ status } = { status: null }) {
  if (!status) return false;
  if (status === ServiceStatus.UNHEALTHY || status === ServiceStatus.HEALTHY) {
    return true;
  }
  return false;
};

/**
 * Check if all values inside the parameter are empty.
 *
 * Empty is defined as `""`, `null`, `undefined`, an object or array with
 * length 0, or an object or array where all the properties are one of the
 * prior empty values.
 *
 * @param {any} item
 * @return {boolean}
 */
export function isDeepEmpty(item) {
  // Any boolean or number value are considered not empty.
  if (typeof item === "boolean" || typeof item === "number") return false;
  // Handle null, undefined, and a character-less string.
  // Looser type-coersion double equals null handles undefined as well.
  if (item == null || item === "") return true;
  // Handle arrays.
  if (Array.isArray(item) && item.every(isDeepEmpty)) return true;
  // Handle objects.
  if (typeof item === "object") {
    if (item === null) return true;
    if (Object.keys(item).length === 0) return true;
    if (Object.values(item).flat().every(isDeepEmpty)) return true;
  }
  // If non of these checks catch, the item must not be empty.
  return false;
}

/**
 * Select the appropriate resource tier based on model size.
 *
 * Tiers are assumed to be ordered by increasing capacity. Each tier has a
 * `max_model_size_gb` property indicating the maximum model size it can handle.
 * Returns the smallest tier that can accommodate the model size.
 *
 * @param {Array<object>} tiers - Available resource tiers, ordered by capacity.
 * @param {number|null} modelSizeGb - Model size in GB, or null if unknown.
 * @return {string|null} The name of the recommended tier, or null if no match.
 */
export function selectTierByModelSize(tiers, modelSizeGb) {
  if (!tiers || tiers.length === 0) {
    return null;
  }

  // If no model size info, default to first tier
  if (modelSizeGb === null || modelSizeGb === undefined) {
    return tiers[0]?.name ?? null;
  }

  // Find the smallest tier that can fit the model
  for (const tier of tiers) {
    const maxSize = tier.max_model_size_gb;
    // Tier has no size limit or model fits within limit
    if (maxSize === null || maxSize === undefined || modelSizeGb <= maxSize) {
      return tier.name;
    }
  }

  // Model is larger than all tiers, return the largest one
  return tiers[tiers.length - 1]?.name ?? null;
}
