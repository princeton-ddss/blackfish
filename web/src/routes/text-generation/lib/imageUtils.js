/**
 * Image utility functions for multimodal text generation.
 */

/**
 * Convert a browser File to base64 data URL.
 * @param {File} file - The file to convert.
 * @returns {Promise<string>} Base64 data URL.
 */
export function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

/**
 * Convert a Blob to base64 data URL.
 * @param {Blob} blob - The blob to convert.
 * @returns {Promise<string>} Base64 data URL.
 */
export function blobToBase64(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

/**
 * Build OpenAI-compatible multimodal content array.
 * @param {string} text - The text content.
 * @param {string[]} imageUrls - Array of image URLs (base64 data URLs or file:// paths).
 * @returns {Array} Content array with text and image_url objects.
 */
export function buildMultimodalContent(text, imageUrls) {
  const content = [];

  // Add images first (common pattern for VLMs)
  for (const url of imageUrls) {
    content.push({
      type: "image_url",
      image_url: { url },
    });
  }

  // Add text
  if (text) {
    content.push({ type: "text", text });
  }

  return content;
}

/**
 * Check if a message content is multimodal (array format).
 * @param {string|Array} content - The message content.
 * @returns {boolean} True if multimodal.
 */
export function isMultimodalContent(content) {
  return Array.isArray(content);
}

/**
 * Extract text from a message content (handles both string and array formats).
 * @param {string|Array} content - The message content.
 * @returns {string} The text content.
 */
export function extractTextFromContent(content) {
  if (typeof content === "string") {
    return content;
  }
  if (Array.isArray(content)) {
    const textPart = content.find((part) => part.type === "text");
    return textPart ? textPart.text : "";
  }
  return "";
}

/**
 * Extract image URLs from a multimodal message content.
 * @param {string|Array} content - The message content.
 * @returns {string[]} Array of image URLs (base64 data URLs).
 */
export function extractImagesFromContent(content) {
  if (!Array.isArray(content)) {
    return [];
  }
  return content
    .filter((part) => part.type === "image_url")
    .map((part) => part.image_url.url);
}

/**
 * Supported image extensions.
 */
export const IMAGE_EXTENSIONS = [
  ".png",
  ".jpg",
  ".jpeg",
  ".gif",
  ".bmp",
  ".tiff",
  ".webp",
];

/**
 * Maximum file size for image attachments (5MB).
 */
export const MAX_IMAGE_FILE_SIZE = 5 * 1024 * 1024;

/**
 * Check if a filename has a supported image extension.
 * @param {string} filename - The filename to check.
 * @returns {boolean} True if supported image file.
 */
export function isImageFile(filename) {
  const lower = filename.toLowerCase();
  return IMAGE_EXTENSIONS.some((ext) => lower.endsWith(ext));
}
