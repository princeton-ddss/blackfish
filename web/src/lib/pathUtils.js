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
 * Return the parent directory of a path.
 *
 * Preserves the leading "/" of absolute paths and always returns "/" (never
 * "") when the parent is the filesystem root. Trailing slashes are ignored.
 * @param {string|null} path - Path to get the parent of
 * @returns {string} Parent directory path
 */
export function dirname(path) {
  if (path === "" || path === null || path === undefined) return "/";

  const isAbsolute = path.startsWith("/");
  const parts = path.split("/").filter((p) => p !== "");

  // At (or above) depth 1 the parent is the root.
  if (parts.length <= 1) return isAbsolute ? "/" : ".";

  const parent = parts.slice(0, -1).join("/");
  return isAbsolute ? "/" + parent : parent;
}

/**
 * Check if path represents the filesystem root directory.
 * @param {string|null} path - Path to check
 * @returns {boolean} True if path is filesystem root
 */
export function isFileSystemRoot(path) {
  return path === "/" || path === "" || path === null;
}

/**
 * Check if path is at the security boundary (cannot navigate above `root`).
 * @param {string} path - Current path
 * @param {string|null} root - Security boundary root (null = no boundary)
 * @returns {boolean} True if at boundary
 */
export function isAtSecurityBoundary(path, root) {
  if (root == null) return false;
  return path === root || path === `${root}/`;
}
