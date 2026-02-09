/**
 * File utility functions for text generation file attachments.
 */

import { blackfishApiURL } from "@/config";

/**
 * Supported text file extensions for attachments.
 */
export const TEXT_FILE_EXTENSIONS = [
  ".txt",
  ".md",
  ".json",
  ".py",
  ".js",
  ".jsx",
  ".ts",
  ".tsx",
  ".html",
  ".css",
  ".sh",
  ".sql",
  ".toml",
  ".yaml",
  ".yml",
  ".log",
  ".csv",
  ".xml",
];

/**
 * Maximum file size for text attachments (100KB).
 */
export const MAX_TEXT_FILE_SIZE = 100 * 1024;

/**
 * Get the accept string for file input.
 * @returns {string} Comma-separated list of accepted extensions.
 */
export function getTextFileAcceptString() {
  return TEXT_FILE_EXTENSIONS.join(",");
}

/**
 * Check if a filename has a supported text extension.
 * @param {string} filename - The filename to check.
 * @returns {boolean} True if supported text file.
 */
export function isTextFile(filename) {
  const lower = filename.toLowerCase();
  return TEXT_FILE_EXTENSIONS.some((ext) => lower.endsWith(ext));
}

/**
 * Read a browser File as text.
 * @param {File} file - The file to read.
 * @returns {Promise<string>} The file content as text.
 */
export function readFileAsText(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsText(file);
  });
}

/**
 * Fetch text content from a remote file.
 * @param {string} path - The file path on the remote server.
 * @param {object} profile - The profile object (for remote servers).
 * @returns {Promise<string>} The file content as text.
 */
export async function fetchRemoteText(path, profile) {
  const profileParam =
    profile && profile.schema !== "local"
      ? `&profile=${encodeURIComponent(profile.name)}`
      : "";
  const url = `${blackfishApiURL}/api/text?path=${encodeURIComponent(path)}${profileParam}`;

  const response = await fetch(url);
  if (!response.ok) {
    const statusMessages = {
      404: "File not found",
      403: "Access denied",
      500: "Server error",
    };
    throw new Error(statusMessages[response.status] || `Error (${response.status})`);
  }

  return response.text();
}

/**
 * Build file context section for prepending to messages.
 * Uses <document> tags to clearly delimit file content.
 * @param {Array} files - Array of file objects with name and content.
 * @returns {string} Formatted file context string.
 */
export function buildFileContext(files) {
  if (!files || files.length === 0) {
    return "";
  }

  return files
    .map((f) => `<document name="${f.name}">\n${f.content}\n</document>`)
    .join("\n\n");
}

/**
 * Prepend file context to a message.
 * @param {string} message - The user's message.
 * @param {Array} files - Array of file objects with name and content.
 * @returns {string} Message with file context prepended.
 */
export function prependFileContext(message, files) {
  const fileContext = buildFileContext(files);
  if (!fileContext) {
    return message;
  }
  return `${fileContext}\n\n${message}`;
}
