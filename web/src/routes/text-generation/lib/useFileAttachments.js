import { useState, useCallback } from "react";
import { readFileAsText, fetchRemoteText } from "./fileUtils";

/**
 * Custom hook for managing file attachments in text generation.
 * Handles browser uploads, remote file selection, removal, and errors.
 * @returns {object} File attachment state and handlers.
 */
export function useFileAttachments() {
  const [attachedFiles, setAttachedFiles] = useState([]);
  const [fileBrowserOpen, setFileBrowserOpen] = useState(false);
  const [fileError, setFileError] = useState(null);

  /**
   * Handle file upload from browser file picker.
   * @param {File[]} files - Array of File objects from input.
   */
  const handleFileBrowserUpload = useCallback(async (files) => {
    for (const file of files) {
      try {
        const content = await readFileAsText(file);
        setAttachedFiles((prev) => [
          ...prev,
          {
            source: "browser",
            file: file,
            name: file.name,
            content: content,
          },
        ]);
      } catch (error) {
        console.error("Failed to read file:", error);
        setFileError({ fileName: file.name, message: "Failed to read file" });
        setTimeout(() => setFileError(null), 5000);
      }
    }
  }, []);

  /**
   * Handle file selection from remote file browser.
   * @param {object} fileInfo - Object with path and profile properties.
   */
  const handleFileRemoteSelect = useCallback(async (fileInfo) => {
    try {
      const content = await fetchRemoteText(fileInfo.path, fileInfo.profile);
      const fileName = fileInfo.path.split("/").pop();
      setAttachedFiles((prev) => [
        ...prev,
        {
          source: "remote",
          path: fileInfo.path,
          profile: fileInfo.profile,
          name: fileName,
          content: content,
        },
      ]);
    } catch (error) {
      console.error("Failed to fetch remote file:", error);
      const fileName = fileInfo.path.split("/").pop();
      setFileError({ fileName, message: error.message });
      setTimeout(() => setFileError(null), 5000);
    }
  }, []);

  /**
   * Remove a file attachment by index.
   * @param {number} index - Index of file to remove.
   */
  const handleRemoveFile = useCallback((index) => {
    setAttachedFiles((prev) => prev.filter((_, i) => i !== index));
  }, []);

  /**
   * Handle file validation errors from AttachmentMenu.
   * @param {string} fileName - Name of the file that failed.
   * @param {string} errorMessage - Error message to display.
   */
  const handleFileError = useCallback((fileName, errorMessage) => {
    setFileError({ fileName, message: errorMessage });
    setTimeout(() => setFileError(null), 5000);
  }, []);

  /**
   * Clear all attached files (e.g., after submission).
   */
  const clearFiles = useCallback(() => {
    setAttachedFiles([]);
  }, []);

  return {
    attachedFiles,
    fileBrowserOpen,
    setFileBrowserOpen,
    fileError,
    setFileError,
    handleFileBrowserUpload,
    handleFileRemoteSelect,
    handleRemoveFile,
    handleFileError,
    clearFiles,
  };
}
