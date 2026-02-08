import { useEffect, useState } from "react";
import { MagnifyingGlassIcon } from "@heroicons/react/24/outline";
import { ExclamationCircleIcon } from "@heroicons/react/20/solid";
import PropTypes from "prop-types";

/**
 * Directory Input component.
 * @param {object} options
 * @param {string} options.root - Initial directory path.
 * @param {string} options.path - Current directory path.
 * @param {Function} options.setPath - React hook to update `path`.
 * @param {boolean} options.disabled - If the inputs are disabled.
 * @param {object} options.error - Error object with message to display.
 * @return {JSX.Element}
 */
function DirectoryInput({ root, path, setPath, disabled, error }) {
  const [input, setInput] = useState(root || "");

  useEffect(() => {
    setInput(path || "");
  }, [path])

  const handleButtonClick = () => {
    // Path validation is handled by the parent component (FileManager)
    setPath(input);
  };

  const hasError = !!error;
  const borderColor = hasError ? "border-red-500" : "border-gray-300 dark:border-gray-600";

  return (
    <div>
      <div className={`mt-2 flex rounded-md border ${borderColor}`}>
        <div className="relative flex flex-grow items-stretch">
          <input
            disabled={disabled}
            id="directory"
            name="directory"
            placeholder={root}
            value={input}
            onKeyUp={(event) => {
              if (event.key === "Enter" && !disabled) {
                handleButtonClick();
              }
            }}
            onChange={(event) => {
              if (!disabled) {
                setInput(event.target.value);
              }
            }}
            className={`block w-full rounded-l-md border-0 py-1.5 pl-3 ${hasError ? "pr-10" : ""} ${disabled ? "bg-gray-100 dark:bg-gray-800 text-gray-400 dark:text-gray-500" : "bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"} placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:outline-none focus:ring-0 sm:text-sm sm:leading-6`}
          />
          {hasError && (
            <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-3">
              <ExclamationCircleIcon className="h-5 w-5 text-red-500" aria-hidden="true" />
            </div>
          )}
        </div>
        <button
          type="button"
          onClick={() => {
            if (!disabled) handleButtonClick();
          }}
          disabled={disabled}
          className="inline-flex items-center gap-x-1.5 rounded-r-md border-l border-gray-300 dark:border-gray-600 px-3 py-2 text-sm font-semibold text-gray-900 dark:text-gray-100 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600"
        >
          <MagnifyingGlassIcon
            aria-hidden="true"
            className="-ml-0.5 h-5 w-5 text-gray-400"
          />
          Search
        </button>
      </div>
      {hasError && error.message && (
        <p className="mt-1 ml-3 text-xs font-light text-red-600 dark:text-red-400">{error.message}</p>
      )}
    </div>
  );
}

DirectoryInput.propTypes = {
  root: PropTypes.string,
  path: PropTypes.string,
  setPath: PropTypes.func,
  disabled: PropTypes.bool,
  error: PropTypes.shape({
    message: PropTypes.string,
  }),
};

export default DirectoryInput;
