import { Popover, PopoverButton, PopoverPanel, Portal } from "@headlessui/react";
import { FunnelIcon, CheckIcon } from "@heroicons/react/24/outline";
import { FunnelIcon as FunnelSolidIcon } from "@heroicons/react/24/solid";
import { getQueryFilters, toggleQueryFilter, setQueryFilters } from "@/lib/tableQuery";
import PropTypes from "prop-types";

/**
 * A table header cell that is itself a multi-select filter dropdown. Clicking
 * the label opens a checkbox menu; toggling options adds/removes
 * `filterKey:value` tokens in the canonical query (values for one key are ORed
 * by applyQuery). A funnel icon fills in when any option is selected.
 *
 * @param {object} props
 * @param {string} props.label - column label
 * @param {string} props.filterKey - query key this column writes (e.g. "status")
 * @param {Array<{ value: string, label: string }>} props.options
 * @param {string} props.query - canonical query string
 * @param {(q: string) => void} props.setQuery
 * @param {string} [props.clearLabel] - reset entry text (default "Clear")
 * @param {string} [props.className] - passed through to the <th>
 */
function FilterHeader({
  label,
  filterKey,
  options,
  query,
  setQuery,
  clearLabel = "Clear",
  className = "",
}) {
  const selected = getQueryFilters(query, filterKey);
  const active = selected.length > 0;

  return (
    <th
      scope="col"
      className={`sticky top-0 z-10 py-3.5 text-sm font-semibold text-gray-900 dark:text-gray-100 backdrop-blur bg-gray-50 dark:bg-gray-800 ${className}`}
    >
      <Popover className="relative inline-block text-left">
        <PopoverButton className="group inline-flex items-center gap-1 hover:text-gray-600 dark:hover:text-gray-300 focus:outline-none">
          <span className={active ? "text-blue-600 dark:text-blue-400" : ""}>
            {label}
          </span>
          {active ? (
            <span className="inline-flex items-center gap-0.5 text-blue-600 dark:text-blue-400">
              <FunnelSolidIcon className="h-3.5 w-3.5" aria-hidden="true" />
              <span className="text-xs font-medium">{selected.length}</span>
            </span>
          ) : (
            <FunnelIcon
              className="h-3.5 w-3.5 opacity-0 group-hover:opacity-40"
              aria-hidden="true"
            />
          )}
        </PopoverButton>
        <Portal>
          <PopoverPanel
            anchor="bottom start"
            className="z-50 mt-1 w-48 rounded-md bg-white dark:bg-gray-700 shadow-lg ring-1 ring-black/5 dark:ring-gray-600 focus:outline-none"
          >
            <div className="py-1">
              {options.map((opt) => {
                const checked = selected.includes(opt.value.toLowerCase());
                return (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() =>
                      setQuery(toggleQueryFilter(query, filterKey, opt.value))
                    }
                    aria-pressed={checked}
                    className="flex w-full items-center gap-2 px-3 py-2 text-sm font-normal text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-600 focus:outline-none"
                  >
                    <span className="flex h-4 w-4 flex-none items-center justify-center rounded border border-gray-300 dark:border-gray-500">
                      {checked && (
                        <CheckIcon className="h-3.5 w-3.5 text-blue-600 dark:text-blue-400" />
                      )}
                    </span>
                    <span className={checked ? "font-medium text-gray-900 dark:text-gray-100" : ""}>
                      {opt.label}
                    </span>
                  </button>
                );
              })}
              {active && (
                <>
                  <div className="my-1 border-t border-gray-200 dark:border-gray-600" />
                  <button
                    type="button"
                    onClick={() => setQuery(setQueryFilters(query, filterKey, []))}
                    className="block w-full px-3 py-2 text-left text-sm text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-600 focus:outline-none"
                  >
                    {clearLabel}
                  </button>
                </>
              )}
            </div>
          </PopoverPanel>
        </Portal>
      </Popover>
    </th>
  );
}

FilterHeader.propTypes = {
  label: PropTypes.string.isRequired,
  filterKey: PropTypes.string.isRequired,
  options: PropTypes.arrayOf(
    PropTypes.shape({
      value: PropTypes.string.isRequired,
      label: PropTypes.string.isRequired,
    }),
  ).isRequired,
  query: PropTypes.string.isRequired,
  setQuery: PropTypes.func.isRequired,
  clearLabel: PropTypes.string,
  className: PropTypes.string,
};

export default FilterHeader;
