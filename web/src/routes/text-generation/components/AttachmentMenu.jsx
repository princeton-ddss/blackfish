import { useRef } from "react";
import { Menu, MenuButton, MenuItem, MenuItems } from "@headlessui/react";
import {
  PaperClipIcon,
  ComputerDesktopIcon,
  ServerIcon,
} from "@heroicons/react/24/outline";
import PropTypes from "prop-types";

/**
 * Dropdown menu for attaching files (browser upload or remote selection).
 * @param {object} props
 * @param {object|null} props.profile - Current profile to determine remote availability.
 * @param {Function} props.onBrowserUpload - Callback when browser files are selected.
 * @param {Function} props.onRemoteSelect - Callback to open remote file browser.
 */
function AttachmentMenu({ profile, onBrowserUpload, onRemoteSelect }) {
  const fileInputRef = useRef(null);
  const isRemote = profile && profile.schema !== "local";

  const handleFileInputChange = (event) => {
    const files = Array.from(event.target.files || []);
    if (files.length > 0) {
      onBrowserUpload(files);
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
        accept="image/*"
        multiple
        onChange={handleFileInputChange}
        className="hidden"
      />

      <Menu as="div" className="relative inline-block text-left">
        <MenuButton className="-m-2.5 flex size-10 items-center justify-center rounded-full text-gray-400 hover:text-gray-500 dark:hover:text-gray-300 focus:outline-none">
          <PaperClipIcon aria-hidden="true" className="size-5" />
          <span className="sr-only">Attach a file</span>
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

            {isRemote && (
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
                    Select from remote
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
  profile: PropTypes.object,
  onBrowserUpload: PropTypes.func.isRequired,
  onRemoteSelect: PropTypes.func.isRequired,
};

export default AttachmentMenu;
