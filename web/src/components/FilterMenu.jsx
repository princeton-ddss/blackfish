import { Popover, PopoverButton, PopoverPanel, Portal } from "@headlessui/react";
import { ChevronDownIcon, CheckIcon } from "@heroicons/react/24/outline";
import {
  getQueryFilter,
  getQueryFilters,
  setQueryFilter,
  toggleQueryFilter,
  setQueryFilters,
} from "@/lib/tableQuery";
import PropTypes from "prop-types";

// Count of currently-selected options across all sections, for the button badge.
function countSelected(query, sections) {
  return sections.reduce((n, s) => {
    if (s.mode === "multi") return n + getQueryFilters(query, s.filterKey).length;
    return n + (getQueryFilter(query, s.filterKey) != null ? 1 : 0);
  }, 0);
}

/**
 * A dropdown of grouped filter sections that edit the canonical query string.
 * Each section targets its own query key and chooses its selection mode:
 *   - "single": radio-like; picking an option replaces that key (mutually
 *     exclusive options, e.g. active vs inactive).
 *   - "multi": checkboxes; toggling adds/removes values for that key (ORed by
 *     applyQuery), e.g. task types.
 * The panel stays open across clicks so multi-select is usable.
 *
 * @param {object} props
 * @param {string} props.label - button label when nothing is selected
 * @param {Array<{ title: string, filterKey: string, mode: "single"|"multi",
 *   options: Array<{ value: string, label: string }> }>} props.sections
 * @param {string} props.query
 * @param {(q: string) => void} props.setQuery
 */
function FilterMenu({ label, sections, query, setQuery }) {
  const count = countSelected(query, sections);
  const active = count > 0;

  const clearAll = () => {
    let next = query;
    for (const s of sections) next = setQueryFilters(next, s.filterKey, []);
    setQuery(next);
  };

  return (
    <Popover className="relative flex-none">
      {/* -ml-px collapses the shared border seam with the search input; the left
          side is square and only the right is rounded so it reads as attached. */}
      <PopoverButton className="inline-flex items-center gap-1 -ml-px rounded-r-md bg-gray-50 dark:bg-gray-800 px-2.5 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-200 ring-1 ring-inset ring-gray-300 dark:ring-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 focus:z-10 focus:outline-none">
        <span className={active ? "text-blue-600 dark:text-blue-400" : ""}>
          {label}
        </span>
        {active && (
          <span className="text-xs font-medium text-blue-600 dark:text-blue-400">
            {count}
          </span>
        )}
        <ChevronDownIcon className="h-4 w-4 text-gray-500 dark:text-gray-400" />
      </PopoverButton>
      <Portal>
        <PopoverPanel
          anchor="bottom end"
          className="z-50 mt-1 w-56 rounded-md bg-white dark:bg-gray-700 shadow-lg ring-1 ring-black/5 dark:ring-gray-600 focus:outline-none"
        >
          <div className="py-1">
            {sections.map((section, si) => (
              <div key={section.filterKey}>
                {si > 0 && (
                  <div className="my-1 border-t border-gray-200 dark:border-gray-600" />
                )}
                <div className="px-3 pt-1.5 pb-1 text-xs font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500">
                  {section.title}
                </div>
                {section.options.map((opt) => {
                  const checked =
                    section.mode === "multi"
                      ? getQueryFilters(query, section.filterKey).includes(
                          opt.value.toLowerCase(),
                        )
                      : getQueryFilter(query, section.filterKey) ===
                        opt.value.toLowerCase();
                  const isMulti = section.mode === "multi";
                  return (
                    <button
                      key={opt.value}
                      type="button"
                      aria-pressed={checked}
                      onClick={() => {
                        if (isMulti) {
                          setQuery(
                            toggleQueryFilter(query, section.filterKey, opt.value),
                          );
                        } else {
                          // Single-select: toggle off if re-picked, else set.
                          setQuery(
                            setQueryFilter(
                              query,
                              section.filterKey,
                              checked ? null : opt.value,
                            ),
                          );
                        }
                      }}
                      className={`flex w-full items-center px-3 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-600 focus:outline-none ${
                        isMulti ? "gap-2" : "justify-between gap-2"
                      }`}
                    >
                      {/* Multi: leading checkbox. Single: bold label + trailing
                          check, matching the app's Listbox single-select style. */}
                      {isMulti && (
                        <span className="flex h-4 w-4 flex-none items-center justify-center rounded border border-gray-300 dark:border-gray-500">
                          {checked && (
                            <CheckIcon className="h-3.5 w-3.5 text-blue-600 dark:text-blue-400" />
                          )}
                        </span>
                      )}
                      <span
                        className={
                          checked
                            ? "font-semibold text-gray-900 dark:text-gray-100"
                            : "font-normal"
                        }
                      >
                        {opt.label}
                      </span>
                      {!isMulti && checked && (
                        <CheckIcon
                          className="h-4 w-4 flex-none text-blue-600 dark:text-blue-400"
                          aria-hidden="true"
                        />
                      )}
                    </button>
                  );
                })}
              </div>
            ))}
            {active && (
              <>
                <div className="my-1 border-t border-gray-200 dark:border-gray-600" />
                <button
                  type="button"
                  onClick={clearAll}
                  className="block w-full px-3 py-2 text-left text-sm text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-600 focus:outline-none"
                >
                  Clear filters
                </button>
              </>
            )}
          </div>
        </PopoverPanel>
      </Portal>
    </Popover>
  );
}

FilterMenu.propTypes = {
  label: PropTypes.string.isRequired,
  sections: PropTypes.arrayOf(
    PropTypes.shape({
      title: PropTypes.string.isRequired,
      filterKey: PropTypes.string.isRequired,
      mode: PropTypes.oneOf(["single", "multi"]).isRequired,
      options: PropTypes.arrayOf(
        PropTypes.shape({
          value: PropTypes.string.isRequired,
          label: PropTypes.string.isRequired,
        }),
      ).isRequired,
    }),
  ).isRequired,
  query: PropTypes.string.isRequired,
  setQuery: PropTypes.func.isRequired,
};

export default FilterMenu;
