import { MagnifyingGlassIcon, XMarkIcon } from "@heroicons/react/24/outline";
import PropTypes from "prop-types";

/**
 * Search bar for client-side tables. A single text input holds the canonical
 * query (free text + `key:value` qualifiers). An optional attached control
 * (e.g. a sectioned FilterMenu) is rendered via `children` and forms one
 * rounded group with the input.
 *
 * @param {object} props
 * @param {string} props.query
 * @param {(q: string) => void} props.setQuery
 * @param {string} [props.placeholder]
 * @param {React.ReactNode} [props.children] - control attached after the input;
 *   handles its own seam styling (-ml-px, rounded-r-md).
 */
function TableSearch({ query, setQuery, placeholder = "", children }) {
  const hasAttached = children != null;

  return (
    <div className="flex items-center">
      <div className="relative flex-1">
        <MagnifyingGlassIcon
          className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400"
          aria-hidden="true"
        />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={placeholder}
          aria-label="Search"
          className={`w-full border-0 bg-white dark:bg-gray-700 py-1.5 pl-8 pr-8 text-sm text-gray-900 dark:text-gray-100 ring-1 ring-inset ring-gray-300 dark:ring-gray-600 placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:z-10 focus:ring-2 focus:ring-inset focus:ring-blue-500 ${
            hasAttached ? "rounded-l-md" : "rounded-md"
          }`}
        />
        {query !== "" && (
          <button
            type="button"
            onClick={() => setQuery("")}
            aria-label="Clear search"
            className="absolute right-2 top-1/2 z-10 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          >
            <XMarkIcon className="h-4 w-4" />
          </button>
        )}
      </div>
      {children}
    </div>
  );
}

TableSearch.propTypes = {
  query: PropTypes.string.isRequired,
  setQuery: PropTypes.func.isRequired,
  placeholder: PropTypes.string,
  children: PropTypes.node,
};

export default TableSearch;
