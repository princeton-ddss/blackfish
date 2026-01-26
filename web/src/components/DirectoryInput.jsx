import { useEffect, useState } from "react";
import { MagnifyingGlassIcon } from "@heroicons/react/24/outline";
import PropTypes from "prop-types";

/**
 * Directory Input component.
 * @param {object} options
 * @param {string} options.root - Initial directory path.
 * @param {string} options.path - Current directory path.
 * @param {Function} options.setPath - React hook to update `path`.
 * @param {boolean} options.disabled - If the inputs are disabled.
 * @return {JSX.Element}
 */
function DirectoryInput({ root, path, setPath, disabled }) {
  const [input, setInput] = useState(root || "");

  useEffect(() => {
    setInput(path || "");
  }, [path])

  const handleButtonClick = () => {
    // Path validation is handled by the parent component (FileManager)
    setPath(input);
  };

  return (
    <div>
      <div className="mt-2 flex rounded-md">
        <div className="relative flex flex-grow items-stretch focus-within:z-10">
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
            className={`block w-full rounded-none rounded-l-md border-0 py-1.5 pl-3 ${disabled ? "bg-gray-100 text-gray-400" : "text-gray-900"} ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-500 sm:text-sm sm:leading-6`}
          />
        </div>
        <button
          type="button"
          onClick={() => {
            if (!disabled) handleButtonClick();
          }}
          disabled={disabled}
          className="relative -ml-px inline-flex items-center gap-x-1.5 rounded-r-md px-3 py-2 text-sm font-semibold text-gray-900 ring-1 ring-inset ring-gray-300 hover:bg-gray-50"
        >
          <MagnifyingGlassIcon
            aria-hidden="true"
            className="-ml-0.5 h-5 w-5 text-gray-400"
          />
          Search
        </button>
      </div>
    </div>
  );
}

DirectoryInput.propTypes = {
  root: PropTypes.string,
  path: PropTypes.string,
  setPath: PropTypes.func,
  disabled: PropTypes.bool,
};

export default DirectoryInput;
