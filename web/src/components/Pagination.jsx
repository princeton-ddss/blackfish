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
function Pagination({ filesPerPage, totalFiles, currentPage, setCurrentPage, disabled }) {
  const pageNumbers = [];

  for (let i = 1; i <= Math.ceil(totalFiles / filesPerPage); i++) {
    pageNumbers.push(i);
  }

  return (
    <div className="flex justify-center py-1">
      <button
        disabled={currentPage === 1 || pageNumbers.length === 0 || disabled}
        onClick={() => {
          if (!disabled) setCurrentPage((prevPage) => prevPage - 1);
        }}
        className="text-gray-700 dark:text-gray-300 disabled:text-gray-300 dark:disabled:text-gray-600"
      >
        <ArrowLeftIcon className="w-4 h-4" />
      </button>

      {pageNumbers.length === 0 && (
        <button
          key={1}
          disabled
          className="h-8 w-8 px-1 py-1 mx-1 rounded-md text-center sm:text-sm font-light bg-white dark:bg-gray-800 text-gray-300 dark:text-gray-600"
        >
          1
        </button>
      )}

      {pageNumbers.map((number) => (
        <button
          key={number}
          disabled={number === currentPage || disabled}
          onClick={() => {
            if (!disabled) setCurrentPage(number);
          }}
          className={`h-8 w-8 px-1 py-1 mx-1 rounded-md text-center sm:text-sm text-gray-900 dark:text-gray-100 ${currentPage === number
            ? "font-semibold"
            : "font-light bg-white dark:bg-gray-800 hover:bg-slate-100 dark:hover:bg-gray-700"
            }`}
        >
          {number}
        </button>
      ))}

      <button
        disabled={currentPage == pageNumbers.length || pageNumbers.length === 0}
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
