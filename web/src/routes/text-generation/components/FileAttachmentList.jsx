import { Popover, PopoverButton, PopoverPanel } from "@headlessui/react";
import { DocumentTextIcon, XMarkIcon } from "@heroicons/react/24/outline";
import PropTypes from "prop-types";

/**
 * Single file chip with preview popover.
 * @param {object} props
 * @param {object} props.file - File object with name and content.
 * @param {number} props.index - Index of the file in the list.
 * @param {Function} props.onRemove - Callback to remove the file (optional for read-only display).
 * @param {boolean} props.readOnly - If true, hide the remove button.
 */
function FileChip({ file, index, onRemove, readOnly = false }) {
  const fileName = file.name || (file.file && file.file.name) || "Unknown file";
  const truncatedName = fileName.length > 20 ? fileName.slice(0, 17) + "..." : fileName;

  return (
    <Popover className="relative">
      <div className={`flex items-center gap-1 bg-gray-200 dark:bg-gray-600 rounded-md pl-2 ${readOnly ? 'pr-2' : 'pr-1'} py-1 text-sm text-gray-700 dark:text-gray-300`}>
        <PopoverButton className="flex items-center gap-1.5 hover:text-gray-900 dark:hover:text-gray-100 focus:outline-none">
          <DocumentTextIcon className="size-4 text-gray-500 dark:text-gray-400" />
          <span className="max-w-[150px] truncate" title={fileName}>
            {truncatedName}
          </span>
        </PopoverButton>
        {!readOnly && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onRemove(index);
            }}
            className="ml-1 rounded-full p-0.5 hover:bg-gray-200 dark:hover:bg-gray-600 focus:outline-none"
          >
            <XMarkIcon className="size-3.5 text-gray-500 dark:text-gray-400" />
            <span className="sr-only">Remove {fileName}</span>
          </button>
        )}
      </div>

      <PopoverPanel
        anchor="top"
        className="z-50 w-96 max-h-80 rounded-lg bg-white dark:bg-gray-800 shadow-lg ring-1 ring-black/5 dark:ring-white/10 overflow-hidden mb-2"
      >
        <div className="p-3 border-b border-gray-200 dark:border-gray-700">
          <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate" title={fileName}>
            {fileName}
          </h3>
        </div>
        <div className="p-3 max-h-60 overflow-y-auto">
          <pre className="text-xs text-gray-700 dark:text-gray-300 whitespace-pre-wrap break-words font-mono">
            {file.content || "Loading..."}
          </pre>
        </div>
      </PopoverPanel>
    </Popover>
  );
}

FileChip.propTypes = {
  file: PropTypes.shape({
    source: PropTypes.oneOf(["browser", "remote"]).isRequired,
    file: PropTypes.object,
    path: PropTypes.string,
    name: PropTypes.string,
    content: PropTypes.string,
  }).isRequired,
  index: PropTypes.number.isRequired,
  onRemove: PropTypes.func,
  readOnly: PropTypes.bool,
};

/**
 * Horizontal list of file attachment chips with preview on click.
 * @param {object} props
 * @param {Array} props.files - Array of file objects.
 * @param {Function} props.onRemove - Callback to remove a file by index (optional if readOnly).
 * @param {boolean} props.readOnly - If true, hide remove buttons (for displaying in sent messages).
 */
function FileAttachmentList({ files, onRemove, readOnly = false }) {
  if (!files || files.length === 0) {
    return null;
  }

  return (
    <div className="flex gap-2 flex-wrap py-2">
      {files.map((file, index) => (
        <FileChip
          key={`${file.source}-${file.source === "browser" ? file.file?.name : file.path}-${index}`}
          file={file}
          index={index}
          onRemove={onRemove}
          readOnly={readOnly}
        />
      ))}
    </div>
  );
}

FileAttachmentList.propTypes = {
  files: PropTypes.arrayOf(
    PropTypes.shape({
      source: PropTypes.oneOf(["browser", "remote"]).isRequired,
      file: PropTypes.object,
      path: PropTypes.string,
      name: PropTypes.string,
      content: PropTypes.string,
    })
  ).isRequired,
  onRemove: PropTypes.func,
  readOnly: PropTypes.bool,
};

export default FileAttachmentList;
