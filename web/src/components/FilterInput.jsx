import PropTypes from "prop-types";
import { FunnelIcon, XMarkIcon } from "@heroicons/react/24/outline";

/**
 * Filter Input component.
 * @param {object} options
 * @param {string} options.query - Used for `<input>` `id`, `name`, and `value`.
 * @param {Function} options.setQuery - React hook to update `query`.
 * @param {boolean} options.disabled - Disable the `<input>`.
 * @return {JSX.Element}
 */
function FilterInput({ query, setQuery, disabled }) {
  return (
    <div>
      <div className="mt-2 relative rounded-md">
        <input
          id="query"
          name="query"
          placeholder="*"
          disabled={disabled}
          onChange={(event) => {
            if (!disabled) setQuery(event.target.value);
          }}
          onKeyUp={(event) => {
            if (event.key === 'Escape' && !disabled) {
              setQuery("")
            }
          }}
          value={query}
          className={`block w-full rounded-md border-0 py-1.5 pl-3 ${disabled ? "bg-gray-100 dark:bg-gray-800 text-gray-400 dark:text-gray-500" : "bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"} ring-1 ring-inset ring-gray-300 dark:ring-gray-600 placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:ring-2 focus:ring-inset focus:ring-blue-500 sm:text-sm sm:leading-6`}
        />
        {query === "" ? (
          <button
            disabled
            className="absolute inset-y-0 right-0 flex items-center pr-3"
          >
            <FunnelIcon className="h-5 w-5 text-gray-400" />
          </button>
        ) : (
          <button
            onClick={() => setQuery("")}
            className="absolute inset-y-0 right-0 flex items-center pr-3"
          >
            <XMarkIcon className="h-5 w-5 text-gray-400" />
          </button>
        )}
      </div>
    </div>
  );
}

FilterInput.propTypes = {
  query: PropTypes.string,
  setQuery: PropTypes.func,
  disabled: PropTypes.bool,
};

export default FilterInput;
