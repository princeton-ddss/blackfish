/**
 * Path utilities for consistent handling across file management.
 *
 * Path Contract:
 * - All profiles use absolute paths (e.g., "/home/user/data")
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
 * Check if path represents the filesystem root directory.
 * @param {string|null} path - Path to check
 * @returns {boolean} True if path is filesystem root
 */
export function isFileSystemRoot(path) {
  return path === "/" || path === "" || path === null;
}
