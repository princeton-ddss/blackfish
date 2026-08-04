import { ChevronUpIcon, ChevronDownIcon } from "@heroicons/react/24/outline";
import PropTypes from "prop-types";

/**
 * A sortable table header cell. Clicking cycles the column's sort direction
 * (asc -> desc -> off) via `onSort`, and shows a chevron for the active column.
 *
 * @param {object} props
 * @param {string} props.label - visible column label
 * @param {string} props.sortKey - this column's sort key
 * @param {string|null} props.activeKey - the currently-sorted key
 * @param {"asc"|"desc"|null} props.direction - active sort direction
 * @param {(key: string) => void} props.onSort
 * @param {string} [props.className] - passed through to the <th>
 * @param {"left"|"right"|"center"} [props.align]
 */
function SortableHeader({
  label,
  sortKey,
  activeKey,
  direction,
  onSort,
  className = "",
  align = "left",
}) {
  const isActive = activeKey === sortKey && direction != null;
  const justify =
    align === "right" ? "justify-end" : align === "center" ? "justify-center" : "justify-start";

  return (
    <th
      scope="col"
      className={`sticky top-0 z-10 py-3.5 text-sm font-semibold text-gray-900 dark:text-gray-100 backdrop-blur bg-gray-50 dark:bg-gray-800 ${className}`}
      aria-sort={
        isActive ? (direction === "asc" ? "ascending" : "descending") : "none"
      }
    >
      <button
        type="button"
        onClick={() => onSort(sortKey)}
        className={`group inline-flex items-center gap-1 ${justify} w-full text-${align} hover:text-gray-600 dark:hover:text-gray-300 focus:outline-none`}
      >
        <span>{label}</span>
        <span className="flex-none">
          {isActive ? (
            direction === "asc" ? (
              <ChevronUpIcon className="h-4 w-4" aria-hidden="true" />
            ) : (
              <ChevronDownIcon className="h-4 w-4" aria-hidden="true" />
            )
          ) : (
            <ChevronDownIcon
              className="h-4 w-4 opacity-0 group-hover:opacity-30"
              aria-hidden="true"
            />
          )}
        </span>
      </button>
    </th>
  );
}

SortableHeader.propTypes = {
  label: PropTypes.string.isRequired,
  sortKey: PropTypes.string.isRequired,
  activeKey: PropTypes.string,
  direction: PropTypes.oneOf(["asc", "desc"]),
  onSort: PropTypes.func.isRequired,
  className: PropTypes.string,
  align: PropTypes.oneOf(["left", "right", "center"]),
};

export default SortableHeader;
