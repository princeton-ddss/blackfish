import {
  ArrowLeftIcon,
  ArrowRightIcon,
} from "@heroicons/react/24/outline";
import PropTypes from "prop-types";

/**
 * Pagination component.
 * @param {object} options
 * @param {number} options.filesPerPage
 * @param {number} options.totalFiles
 * @param {number} options.currentPage
 * @param {Function} options.setCurrentPage - React hook to update `currentPage`.
 * @param {boolean} options.disabled - Disable pagination functionality.
 * @return {JSX.Element}
 */
// Build the list of page items to render: always the first and last page, the
// current page and its neighbours, and "…" placeholders for the gaps between.
// Returns numbers for pages and the string "…" for a collapsed range.
export function getPageItems(currentPage, totalPages, siblings = 1) {
  if (totalPages <= 1) return [];
  // Show every page when the full range is small enough that ellipsis wouldn't
  // save space (first + last + current±siblings + two ellipses).
  const maxPlain = siblings * 2 + 5;
  if (totalPages <= maxPlain) {
    return Array.from({ length: totalPages }, (_, i) => i + 1);
  }

  const left = Math.max(currentPage - siblings, 1);
  const right = Math.min(currentPage + siblings, totalPages);
  const items = [1];
  if (left > 2) items.push("…");
  for (let i = left; i <= right; i++) {
    if (i !== 1 && i !== totalPages) items.push(i);
  }
  if (right < totalPages - 1) items.push("…");
  items.push(totalPages);
  return items;
}

function Pagination({ filesPerPage, totalFiles, currentPage, setCurrentPage, disabled }) {
  const totalPages = Math.ceil(totalFiles / filesPerPage);
  const pageItems = getPageItems(currentPage, totalPages);

  return (
    <div className="flex justify-center py-1">
      <button
        disabled={currentPage === 1 || totalPages === 0 || disabled}
        onClick={() => {
          if (!disabled) setCurrentPage((prevPage) => prevPage - 1);
        }}
        className="text-gray-700 dark:text-gray-300 disabled:text-gray-300 dark:disabled:text-gray-600"
      >
        <ArrowLeftIcon className="w-4 h-4" />
      </button>

      {totalPages === 0 && (
        <button
          key={1}
          disabled
          className="h-8 w-8 px-1 py-1 mx-1 rounded-md text-center sm:text-sm font-light bg-white dark:bg-gray-800 text-gray-300 dark:text-gray-600"
        >
          1
        </button>
      )}

      {pageItems.map((item, index) =>
        item === "…" ? (
          <span
            key={`ellipsis-${index}`}
            className="h-8 w-8 px-1 py-1 mx-1 text-center sm:text-sm font-light text-gray-400 dark:text-gray-500 select-none"
          >
            …
          </span>
        ) : (
          <button
            key={item}
            disabled={item === currentPage || disabled}
            onClick={() => {
              if (!disabled) setCurrentPage(item);
            }}
            className={`h-8 w-8 px-1 py-1 mx-1 rounded-md text-center sm:text-sm text-gray-900 dark:text-gray-100 ${currentPage === item
              ? "font-semibold"
              : "font-light bg-white dark:bg-gray-800 hover:bg-slate-100 dark:hover:bg-gray-700"
              }`}
          >
            {item}
          </button>
        )
      )}

      <button
        disabled={currentPage === totalPages || totalPages === 0}
        className="text-gray-700 dark:text-gray-300 disabled:text-gray-300 dark:disabled:text-gray-600"
        onClick={() => setCurrentPage((prevPage) => prevPage + 1)}
      >
        <ArrowRightIcon className="w-4 h-4" />
      </button>
    </div>
  );
}

Pagination.propTypes = {
  filesPerPage: PropTypes.number,
  totalFiles: PropTypes.number,
  currentPage: PropTypes.number,
  setCurrentPage: PropTypes.func,
  disabled: PropTypes.bool,
};

export default Pagination;
