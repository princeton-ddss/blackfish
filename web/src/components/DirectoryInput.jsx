import { MagnifyingGlassIcon } from "@heroicons/react/24/outline";
import { ExclamationCircleIcon } from "@heroicons/react/20/solid";
import PropTypes from "prop-types";

/**
 * Directory Input component. A controlled text input: the parent owns the
 * value and decides what a submit does (navigate, reject, revert). This lets
 * the parent revert the input after a rejected path, which internal state
 * could not do when the target path is unchanged.
 * @param {object} options
 * @param {string} options.root - Root path, shown as placeholder.
 * @param {string} options.value - Current input value (controlled).
 * @param {Function} options.onChange - Called with the new value on edit.
 * @param {Function} options.onSubmit - Called on Enter or Search click.
 * @param {boolean} options.disabled - If the inputs are disabled.
 * @param {object} options.error - Error object with a message to display.
 * @return {JSX.Element}
 */
function DirectoryInput({ root, value, onChange, onSubmit, disabled, error }) {
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
            value={value}
            onKeyUp={(event) => {
              if (event.key === "Enter" && !disabled) {
                onSubmit();
              }
            }}
            onChange={(event) => {
              if (!disabled) {
                onChange(event.target.value);
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
            if (!disabled) onSubmit();
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
  value: PropTypes.string,
  onChange: PropTypes.func,
  onSubmit: PropTypes.func,
  disabled: PropTypes.bool,
  error: PropTypes.shape({
    message: PropTypes.string,
  }),
};

export default DirectoryInput;
