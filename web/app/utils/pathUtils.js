/**
 * Path utilities for consistent handling across file management.
 *
 * Path Contract:
 * - Remote profiles: Use relative paths (e.g., "/", "data", "data/models")
 * - Local profiles: Use absolute paths (e.g., "/home/user/data")
 * - Root representation: Forward slash "/" (never "" or null for connected state)
 */

/**
 * Join path parts, handling root "/" and avoiding double slashes.
 * @param {...string} parts - Path segments to join
 * @returns {string} Joined path
 */
export function joinPath(...parts) {
  // Filter out empty/null parts, but keep "/" if it's the only part
  const filtered = parts.filter(
    (p) => p !== "" && p !== null && p !== undefined
  );
  if (filtered.length === 0) return "/";

  // If first part is "/" (root), join remaining parts
  if (filtered[0] === "/") {
    if (filtered.length === 1) return "/";
    return "/" + filtered.slice(1).join("/").replace(/\/+/g, "/");
  }

  return filtered.join("/").replace(/\/+/g, "/");
}

/**
 * Check if path represents the root directory.
 * @param {string|null} path - Path to check
 * @returns {boolean} True if path is root
 */
export function isRootPath(path) {
  return path === "/" || path === "" || path === null;
}

/**
 * Normalize a relative path: remove leading/trailing slashes, collapse doubles.
 * @param {string} path - Path to normalize
 * @returns {string} Normalized path
 */
export function normalizeRelativePath(path) {
  if (!path) return "";
  return path.replace(/^\/+|\/+$/g, "").replace(/\/+/g, "/");
}

/**
 * Convert absolute path to relative (for remote profiles).
 * @param {string} absolutePath - Absolute path to convert
 * @param {string} homeDir - Home directory base
 * @returns {string|null} Relative path ("/" for root), or null if outside homeDir
 */
export function toRelativePath(absolutePath, homeDir) {
  if (!absolutePath || !homeDir) return "/";
  if (absolutePath === homeDir || absolutePath === homeDir + "/") return "/";
  if (absolutePath.startsWith(homeDir + "/")) {
    return absolutePath.slice(homeDir.length + 1);
  }
  return null; // Path outside homeDir
}
