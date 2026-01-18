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
