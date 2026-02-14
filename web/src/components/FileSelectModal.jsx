import { Fragment, useEffect, useState } from "react";
import {
  Dialog,
  DialogPanel,
  DialogTitle,
  Transition,
  TransitionChild,
} from "@headlessui/react";
import { XMarkIcon, ArrowPathIcon } from "@heroicons/react/24/outline";
import { useFileSystem } from "@/lib/loaders";
import { useRemoteFileSystem } from "@/providers/RemoteFileSystemProvider";
import DirectoryInput from "@/components/DirectoryInput";
import FilterInput from "@/components/FilterInput";
import FileManagerTable from "@/components/FileManagerTable";
import PropTypes from "prop-types";

/**
 * Check if a file matches the accepted extensions.
 * @param {string} filename - The filename to check.
 * @param {string[]} acceptedExtensions - Array of accepted extensions (e.g., [".png", ".jpg"]).
 * @returns {boolean} True if the file matches.
 */
function matchesExtensions(filename, acceptedExtensions) {
  if (!acceptedExtensions || acceptedExtensions.length === 0) return true;
  const lowerName = filename.toLowerCase();
  return acceptedExtensions.some((ext) => lowerName.endsWith(ext.toLowerCase()));
}

/**
 * Modal dialog for browsing and selecting files from a remote system.
 * @param {object} props
 * @param {boolean} props.open - Whether the modal is open.
 * @param {Function} props.setOpen - Function to set open state.
 * @param {object} props.profile - The remote profile to use.
 * @param {Function} props.onSelect - Callback when a file is selected.
 * @param {string} props.title - Modal title.
 * @param {string[]} props.acceptedExtensions - Array of accepted file extensions (e.g., [".png", ".jpg"]).
 * @param {string} props.extensionErrorMessage - Error message when wrong file type is selected.
 */
function FileSelectModal({
  open,
  setOpen,
  profile,
  onSelect,
  title = "Select File",
  acceptedExtensions = [],
  extensionErrorMessage = "Please select a supported file type.",
}) {
  const [path, setPath] = useState(null);
  const [query, setQuery] = useState("");
  const [selectedFile, setSelectedFile] = useState(null);
  const [error, setError] = useState(null);

  const { reconnect, isConnecting, error: connectionError } = useRemoteFileSystem();
  const { files, error: fsError, isLoading, refresh, isConnected, homeDir } = useFileSystem(path, profile);

  // Set path to homeDir when it becomes available
  useEffect(() => {
    if (homeDir && path === null) setPath(homeDir);
  }, [homeDir, path]);

  const handleClose = () => {
    setSelectedFile(null);
    setError(null);
    setOpen(false);
  };

  const handleFileSelect = (file) => {
    if (file && !file.is_dir) {
      if (matchesExtensions(file.name, acceptedExtensions)) {
        setSelectedFile(file);
        setError(null);
      } else {
        setError(extensionErrorMessage);
        setSelectedFile(null);
      }
    }
  };

  const handleConfirm = () => {
    if (selectedFile) {
      onSelect({
        path: selectedFile.path,
        name: selectedFile.name,
        profile: profile,
      });
      handleClose();
    }
  };

  const handlePathChange = (newPath) => {
    setPath(newPath);
  };

  // Status object required by FileManagerTable
  const status = {
    disabled: false,
  };

  const displayRoot = homeDir ?? "~";

  return (
    <Transition show={open} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={handleClose}>
        <TransitionChild
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-gray-500 dark:bg-gray-900 bg-opacity-75 dark:bg-opacity-75 transition-opacity" />
        </TransitionChild>

        <div className="fixed inset-0 z-10 overflow-y-auto">
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
              <DialogPanel className="relative transform overflow-hidden rounded-lg bg-white dark:bg-gray-800 text-left shadow-2xl ring-1 ring-gray-900/10 dark:ring-white/10 transition-all sm:my-8 sm:w-full sm:max-w-2xl">
                {/* Header */}
                <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700">
                  <DialogTitle
                    as="h3"
                    className="text-sm font-semibold leading-6 text-gray-900 dark:text-gray-100"
                  >
                    {title}
                  </DialogTitle>
                  <button
                    type="button"
                    className="rounded-md text-gray-400 hover:text-gray-500 dark:hover:text-gray-300 focus:outline-none"
                    onClick={handleClose}
                  >
                    <span className="sr-only">Close</span>
                    <XMarkIcon className="h-5 w-5" aria-hidden="true" />
                  </button>
                </div>

                {/* Connection status */}
                {profile && (
                  <div className="px-4 py-2 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
                    <div className="flex items-center gap-1.5">
                      <span
                        className={`inline-block h-2 w-2 flex-shrink-0 rounded-full ${
                          isConnected
                            ? "bg-green-500"
                            : connectionError
                              ? "bg-red-500"
                              : "animate-pulse bg-yellow-500"
                        }`}
                      />
                      <span className="text-xs text-gray-600 dark:text-gray-400">
                        {isConnected
                          ? `Connected to ${profile.user}@${profile.host}`
                          : connectionError
                            ? "Disconnected"
                            : "Connecting..."}
                      </span>
                      {connectionError && (
                        <button
                          onClick={reconnect}
                          disabled={isConnecting}
                          className="ml-1 p-0.5 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 disabled:opacity-50 focus:outline-none"
                          aria-label="Reconnect"
                        >
                          <ArrowPathIcon className={`h-3.5 w-3.5 ${isConnecting ? "animate-spin" : ""}`} />
                        </button>
                      )}
                    </div>
                  </div>
                )}

                {/* Content */}
                <div className="px-4 py-3">
                  <DirectoryInput
                    root={displayRoot}
                    path={path}
                    setPath={handlePathChange}
                    disabled={false}
                  />

                  <FilterInput
                    query={query}
                    setQuery={setQuery}
                    disabled={false}
                  />

                  <div className="mt-2">
                    <FileManagerTable
                      content={files}
                      path={path}
                      root={null}
                      filesPerPage={20}
                      query={query}
                      setPath={handlePathChange}
                      isLoading={isLoading}
                      error={fsError}
                      refresh={refresh}
                      status={status}
                      onFileClick={handleFileSelect}
                      onDeleteClick={null}
                      operationInProgress={false}
                      heightClass="h-[18rem]"
                      showBottomSpacer={false}
                      showPagination={false}
                      selectedFilePath={selectedFile?.path}
                    />
                  </div>

                  {selectedFile && (
                    <div className="mt-3">
                      <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                        Selected: {selectedFile.name}
                      </p>
                      <p className="text-xs font-light text-gray-600 dark:text-gray-400 truncate">
                        {selectedFile.path}
                      </p>
                    </div>
                  )}

                  {error && (
                    <div className="mt-3 p-2 bg-red-50 dark:bg-red-900/30 rounded-md">
                      <p className="text-sm text-red-800 dark:text-red-200">
                        {error}
                      </p>
                    </div>
                  )}
                </div>

                {/* Footer */}
                <div className="flex items-center justify-end gap-3 px-4 py-3 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 shadow-[0_-1px_2px_rgba(0,0,0,0.05)]">
                  <button
                    type="button"
                    className="text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100"
                    onClick={handleClose}
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    className="rounded-md bg-blue-500 px-3 py-1.5 text-sm font-semibold text-white shadow-sm hover:bg-blue-400 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-500 disabled:bg-gray-100 dark:disabled:bg-gray-700 disabled:text-gray-400 dark:disabled:text-gray-500 disabled:cursor-not-allowed"
                    onClick={handleConfirm}
                    disabled={!selectedFile}
                  >
                    Select
                  </button>
                </div>
              </DialogPanel>
            </TransitionChild>
          </div>
        </div>
      </Dialog>
    </Transition>
  );
}

FileSelectModal.propTypes = {
  open: PropTypes.bool.isRequired,
  setOpen: PropTypes.func.isRequired,
  profile: PropTypes.object,
  onSelect: PropTypes.func.isRequired,
  title: PropTypes.string,
  acceptedExtensions: PropTypes.arrayOf(PropTypes.string),
  extensionErrorMessage: PropTypes.string,
};

export default FileSelectModal;
