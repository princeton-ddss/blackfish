import { useRef } from "react";
import { Menu, MenuButton, MenuItem, MenuItems } from "@headlessui/react";
import {
  PaperClipIcon,
  ComputerDesktopIcon,
  ServerIcon,
} from "@heroicons/react/24/outline";
import PropTypes from "prop-types";

const DEFAULT_MAX_FILE_SIZE = 5 * 1024 * 1024; // 5MB

/**
 * Format bytes into a human-readable string.
 * @param {number} bytes
 * @return {string}
 */
function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes}B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)}KB`;
  return `${Math.round(bytes / (1024 * 1024))}MB`;
}

/**
 * Dropdown menu for attaching files (browser upload or remote selection).
 * Configurable for different file types (images, text files, etc.).
 * @param {object} props
 * @param {string} props.accept - File types to accept (e.g., "image/*" or ".txt,.md,.py").
 * @param {number} props.maxFileSize - Maximum file size in bytes.
 * @param {React.ElementType} props.icon - Icon component to display.
 * @param {string} props.label - Screen reader label for the button.
 * @param {object|null} props.profile - Current profile to determine remote availability.
 * @param {Function} props.onBrowserUpload - Callback when browser files are selected.
 * @param {Function} props.onRemoteSelect - Callback to open remote file browser.
 * @param {Function} props.onError - Callback when file validation fails.
 */
function AttachmentMenu({
  accept,
  maxFileSize = DEFAULT_MAX_FILE_SIZE,
  icon: Icon = PaperClipIcon,
  label = "Attach a file",
  profile,
  onBrowserUpload,
  onRemoteSelect,
  onError,
}) {
  const fileInputRef = useRef(null);
  const hasServerFiles = profile?.schema === "slurm";

  const handleFileInputChange = (event) => {
    const files = Array.from(event.target.files || []);
    const validFiles = [];

    for (const file of files) {
      if (file.size > maxFileSize) {
        if (onError) {
          onError(file.name, `File exceeds ${formatBytes(maxFileSize)} limit`);
        }
      } else {
        validFiles.push(file);
      }
    }

    if (validFiles.length > 0) {
      onBrowserUpload(validFiles);
    }
    // Reset input so the same file can be selected again
    event.target.value = "";
  };

  const handleBrowserUploadClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <>
      <input
        ref={fileInputRef}
        type="file"
        accept={accept}
        multiple
        onChange={handleFileInputChange}
        className="hidden"
      />

      <Menu as="div" className="relative inline-block text-left">
        <MenuButton className="-m-2.5 flex size-10 items-center justify-center rounded-full text-gray-400 hover:text-gray-500 dark:hover:text-gray-300 focus:outline-none">
          <Icon aria-hidden="true" className="size-5" />
          <span className="sr-only">{label}</span>
        </MenuButton>

        <MenuItems
          anchor="top start"
          className="absolute z-10 mb-2 ml-2 w-48 rounded-md bg-white dark:bg-gray-700 shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none"
        >
          <div>
            <MenuItem>
              {({ active }) => (
                <button
                  type="button"
                  onClick={handleBrowserUploadClick}
                  className={`${
                    active
                      ? "bg-gray-100 dark:bg-gray-600 text-gray-900 dark:text-gray-100"
                      : "text-gray-700 dark:text-gray-200"
                  } group flex w-full items-center px-2 py-1.5 text-sm font-light`}
                >
                  <ComputerDesktopIcon
                    className="mr-2 h-4 w-4 text-gray-400 dark:text-gray-500 group-hover:text-gray-500 dark:group-hover:text-gray-400"
                    aria-hidden="true"
                  />
                  Upload from computer
                </button>
              )}
            </MenuItem>

            {hasServerFiles && (
              <MenuItem>
                {({ active }) => (
                  <button
                    type="button"
                    onClick={onRemoteSelect}
                    className={`${
                      active
                        ? "bg-gray-100 dark:bg-gray-600 text-gray-900 dark:text-gray-100"
                        : "text-gray-700 dark:text-gray-200"
                    } group flex w-full items-center px-2 py-1.5 text-sm font-light`}
                  >
                    <ServerIcon
                      className="mr-2 h-4 w-4 text-gray-400 dark:text-gray-500 group-hover:text-gray-500 dark:group-hover:text-gray-400"
                      aria-hidden="true"
                    />
                    Select from server
                  </button>
                )}
              </MenuItem>
            )}
          </div>
        </MenuItems>
      </Menu>
    </>
  );
}

AttachmentMenu.propTypes = {
  accept: PropTypes.string,
  maxFileSize: PropTypes.number,
  icon: PropTypes.elementType,
  label: PropTypes.string,
  profile: PropTypes.object,
  onBrowserUpload: PropTypes.func.isRequired,
  onRemoteSelect: PropTypes.func.isRequired,
  onError: PropTypes.func,
};

export default AttachmentMenu;
