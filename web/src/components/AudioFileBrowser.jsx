import { useEffect, useState } from "react";
import {
  ChevronLeftIcon,
  ChevronRightIcon,
  FolderIcon,
  DocumentIcon,
  ArrowPathIcon,
} from "@heroicons/react/24/outline";
import { useFileSystem } from "@/lib/loaders";
import { assetPath } from "@/config";
import { fileSize, lastModified } from "@/lib/util";
import { dirname, clampToRoot, normalizePath, isWithinRoot, isFileSystemRoot, isAtSecurityBoundary } from "@/lib/pathUtils";
import Pagination from "@/components/Pagination";
import DirectoryInput from "@/components/DirectoryInput";
import FilterInput from "@/components/FilterInput";
import Notification from "@/components/Notification";
import PropTypes from "prop-types";

/**
 * Audio File Picker Table component.
 * @param {object} options
 * @param {Array.<Object>} options.content
 * @param {string} options.path
 * @param {string} options.root
 * @param {number} options.filesPerPage
 * @param {Function} options.setAudioPath - React hook to set audio path.
 * @param {string} options.query
 * @param {Function} options.setPath
 * @param {string} options.selected
 * @param {Function} options.setSelected - React hook to update `selected`.
 * @param {boolean} options.isLoading
 * @param {Object} options.error
 * @param {Function} options.refresh - Function to refetch the content.
 * @param {Object} options.status
 * @return {JSX.Element}
 */
function AudioFileBrowserTable({
  content,
  path,
  root,
  setAudioPath,
  setPath,
  selected,
  setSelected,
  isLoading,
  error,
  refresh,
  status
}) {
  // `content` is the already-filtered, already-paginated page of files.
  const currentFiles = content ?? [];

  return (
    <div
      id="audio-file-browser-table"
      name="audio-file-browser-table"
      className="flex-none h-[26rem]"
    >
      <div className="mt-3 flow-root">
        <div className="-my-2 overflow-x-auto sm:-mx-6 lg:-mx-8">
          <div className="inline-block min-w-full py-2 align-middle sm:px-6 lg:px-8">
            <div className="ring-1 ring-gray-300 dark:ring-gray-600 sm:rounded-lg h-[26rem] overflow-y-scroll">
              <table className="divide-y divide-gray-300 dark:divide-gray-600 table-fixed w-full">
                <thead>
                  <tr>
                    <th
                      scope="col"
                      className="sticky top-0 z-10 whitespace-nowrap py-4 text-left text-sm font-medium sm:pr-4 w-24 backdrop-blur bg-gray-50 dark:bg-gray-800"
                    >
                      <button
                        onClick={() => {
                          // Never navigate above the security root.
                          setPath(clampToRoot(dirname(path), root));
                        }}
                      >
                        {/* Hide back button at filesystem root or security boundary */}
                        {!isFileSystemRoot(path) && !isAtSecurityBoundary(path, root) && (
                          <ChevronLeftIcon className="h-4 w-4 mt-1 ml-4 text-gray-900 dark:text-gray-100 hover:text-gray-400" />
                        )}{" "}
                      </button>
                    </th>
                    <th
                      scope="col"
                      className="sticky top-0 z-10 py-3.5 pl-4 pr-3 text-left text-sm font-semibold text-gray-900 dark:text-gray-100 sm:pl-6 w-1/2 backdrop-blur bg-gray-50 dark:bg-gray-800"
                    >
                      Name
                    </th>
                    <th
                      scope="col"
                      className="sticky top-0 z-10 px-3 py-3.5 text-left text-sm font-semibold text-gray-900 dark:text-gray-100 w-24 backdrop-blur bg-gray-50 dark:bg-gray-800"
                    >
                      Size
                    </th>
                    <th
                      scope="col"
                      className="sticky top-0 z-10 px-3 py-3.5 text-left text-sm font-semibold text-gray-900 dark:text-gray-100 w-48 backdrop-blur bg-gray-50 dark:bg-gray-800"
                    >
                      Last Modified
                    </th>
                    <th
                      scope="col"
                      className="sticky top-0 z-10 px-2.5 py-3.5 text-left text-sm font-semibold text-gray-900 dark:text-gray-100 w-12 backdrop-blur bg-gray-50 dark:bg-gray-800"
                    >
                      <button
                        onClick={async () => {
                          refresh();
                        }}
                        disabled={status.disabled}
                      >
                        <ArrowPathIcon
                          className={`h-5 w-5 mt-1 ${status.disabled ? "text-gray-300 dark:text-gray-600" : "text-gray-900 dark:text-gray-100 hover:text-gray-400"} ${isLoading ? "animate-spin" : ""}`}
                        />
                      </button>
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-700 bg-white dark:bg-gray-800">
                  {status.disabled ? (
                    <tr>
                      <td colSpan={5} className="h-64">
                        <div className="font-light sm:text-sm text-center align-middle text-gray-600 dark:text-gray-400">
                          <img
                            className="h-16 ml-auto mr-auto opacity-80 mb-5 dark:invert"
                            height="56"
                            width="56"
                            src={assetPath("/img/dead-fish.png")}
                            alt="File browser disabled"
                          />
                          {status.detail || "Oops! Something went wrong."}
                        </div>
                      </td>
                    </tr>
                  ) : error ? (
                    <tr>
                      <td colSpan={5} className="h-64">
                        <div className="font-light sm:text-sm text-center align-middle text-gray-600 dark:text-gray-400">
                          <img
                            className="h-16 ml-auto mr-auto opacity-80 mb-5 dark:invert"
                            height="56"
                            width="56"
                            src={assetPath("/img/dead-fish.png")}
                            alt="Loading error."
                          />
                          Oops! There seems to be a problem here...
                        </div>
                      </td>
                    </tr>
                  ) : isLoading ? (
                    <>
                      {Array.from({ length: 5 }).map((_, i) => (
                        <tr key={i}>
                          <td colSpan={5} className="relative whitespace-nowrap py-3 px-5 animate-pulse">
                            <div className="bg-gray-100 dark:bg-gray-700 h-9 rounded-md"></div>
                          </td>
                        </tr>
                      ))}
                    </>
                  ) : content?.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="h-64">
                        <div className="font-light sm:text-sm text-center align-middle text-gray-600 dark:text-gray-400">
                          <img
                            className="h-16 ml-auto mr-auto opacity-80 mb-5 dark:invert"
                            height="56"
                            width="56"
                            src={assetPath("/img/question-mark.png")}
                            alt="No files found."
                          />
                          {"Hmm. There don't seem to be any files here..."}
                        </div>
                      </td>
                    </tr>
                  ) : root === "" ? (
                    <tr>
                      <td colSpan={5} className="h-64">
                        <div className="font-light sm:text-sm text-center align-middle text-gray-600 dark:text-gray-400">
                          {"No service selected."}
                        </div>
                      </td>
                    </tr>
                  ) : (
                    currentFiles.map((item) => (
                      <tr key={item.path} className={selected === item.path ? "bg-gray-50 dark:bg-gray-700" : "bg-white dark:bg-gray-800"}>
                        <td className="relative whitespace-nowrap w-24 py-4 px-5 text-gray-700 dark:text-gray-300 text-left text-sm font-medium sm:pr-6">
                          <div
                            className={`flex ${item.is_dir || item.path.match(/\.(mp3|wav|flac)$/i) ? "" : "text-gray-300 dark:text-gray-600"
                              }`}
                          >
                            {item.is_dir ? (
                              <FolderIcon className="h-7 w-7" />
                            ) : (
                              <DocumentIcon className="h-7 w-7" />
                            )}
                          </div>
                        </td>
                        <td className="whitespace-nowrap w-1/2 py-4 pl-4 pr-3 text-left text-sm text-gray-900 dark:text-gray-100">
                          <div
                            className={`overflow-x-scroll ${item.is_dir || item.path.match(/\.(mp3|wav|flac)$/i) ? "" : "text-gray-300 dark:text-gray-600"
                              }`}
                          >
                            {item.name}
                          </div>
                        </td>
                        <td className="whitespace-nowrap w-24 py-3.5 px-3 text-left text-sm text-gray-900 dark:text-gray-100">
                          <div
                            className={`flex ${item.is_dir || item.path.match(/\.(mp3|wav|flac)$/i) ? "" : "text-gray-300 dark:text-gray-600"
                              }`}
                          >
                            {item.is_dir ? "-" : fileSize(item.size)}
                          </div>
                        </td>
                        <td className="whitespace-nowrap w-48 py-4 px-3 text-left text-sm text-gray-900 dark:text-gray-100">
                          <div
                            className={`flex ${item.is_dir || item.path.match(/\.(mp3|wav|flac)$/i) ? "" : "text-gray-300 dark:text-gray-600"
                              }`}
                          >
                            {lastModified(item.modified_at)}
                          </div>
                        </td>
                        <td className="whitespace-nowrap w-12 py-4 px-3 text-left text-sm text-gray-900 dark:text-gray-100">
                          <div
                            className={`flex ${item.is_dir || item.path.match(/\.(mp3|wav|flac)$/i) ? "" : "text-gray-300 dark:text-gray-600"
                              }`}
                          >
                            {item.is_dir ? (
                              <button
                                onClick={() => {
                                  if (!status.disabled) {
                                    setPath(item.path);
                                  }
                                }}
                                disabled={status.disabled}
                                className={`${status.disabled ? "text-gray-300 dark:text-gray-600" : "text-gray-900 dark:text-gray-100"}`}
                              >
                                <ChevronRightIcon className="h-4 w-4 mt-1 hover:text-gray-400" />
                              </button>
                            ) : (
                              item.path.match(/\.(mp3|wav|flac)$/i) && (
                                <input
                                  type="checkbox"
                                  checked={selected === item.path}
                                  disabled={status.disabled}
                                  onChange={() => {
                                    if (status.disabled) return;
                                    if (selected === item.path) {
                                      setSelected("");
                                      setAudioPath("");
                                    } else {
                                      setSelected(item.path);
                                      setAudioPath(item.path);
                                    }
                                  }}
                                  className="h-4 w-4 rounded border-gray-300 dark:border-gray-600 text-blue-500 focus:ring-blue-600 dark:bg-gray-700"
                                />
                              )
                            )}
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                  <tr className="bg-white dark:bg-gray-800">
                    <td className="whitespace-nowrap h-16"></td>
                    <td className="whitespace-nowrap h-16"></td>
                    <td className="whitespace-nowrap h-16"></td>
                    <td className="whitespace-nowrap h-16"></td>
                    <td className="whitespace-nowrap h-16"></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

AudioFileBrowserTable.propTypes = {
  content: PropTypes.array,
  path: PropTypes.string,
  root: PropTypes.string,
  setAudioPath: PropTypes.func,
  setPath: PropTypes.func,
  selected: PropTypes.string,
  setSelected: PropTypes.func,
  isLoading: PropTypes.bool,
  error: PropTypes.object,
  refresh: PropTypes.func,
  status: PropTypes.object,
};

/**
 * Audio File Picker component for selecting audio files (mp3, wav, flac).
 * @param {object} options
 * @param {string} options.root - File browser root path.
 * @param {Function} options.setAudioPath - React hook to update audio path.
 * @param {Object} options.status - Health of file browser connection.
 * @return {JSX.Element}
 */
const FILES_PER_PAGE = 20;

function AudioFileBrowser({ root, setAudioPath, status, profile = null, children }) {
  const [path, setPath] = useState(root);
  const [operationError, setOperationError] = useState(null);
  const [selected, setSelected] = useState("");
  const [query, setQuery] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [inputValue, setInputValue] = useState(root ?? "");
  // A remote profile lists over the SFTP WebSocket; a local/null profile uses
  // the REST path. useFileSystem branches internally on isRemoteProfile.
  const { files, error, isLoading, refresh } = useFileSystem(path, profile);

  useEffect(() => {
    setPath(root);
    setOperationError(null);
  }, [root]);

  // Keep the controlled input in sync with the current path as navigation
  // changes it (folder clicks, back button, root/service switch).
  useEffect(() => {
    setInputValue(path ?? "");
  }, [path]);

  // Auto-dismiss the boundary-error toast after 5s, mirroring FileManager.
  useEffect(() => {
    if (!operationError) return undefined;
    const id = setTimeout(() => setOperationError(null), 5000);
    return () => clearTimeout(id);
  }, [operationError]);

  // Confine navigation to the service mount. A path that escapes `root` (e.g.
  // via ".." or an absolute path typed into the search bar) is refused with a
  // toast instead of navigating. Normalizing first resolves "." / ".." so a
  // traversal can't slip past the boundary check — and an in-root path with
  // such segments navigates to (and displays) its clean resolved form.
  const handlePathChange = (next) => {
    const normalized = normalizePath(next);
    if (!isWithinRoot(normalized, root)) {
      setOperationError(`Only files within ${root} are accessible.`);
      // Revert the input to the last valid path so a rejected (un-navigable)
      // string doesn't linger in the box.
      setInputValue(path ?? "");
      return;
    }
    setOperationError(null);
    // Sync the input to the resolved path directly. When the resolved path
    // equals the current one (e.g. "/mount/.." back to "/mount") no re-render
    // fires, so set it here too to clear any raw "." / ".." the user typed.
    setInputValue(normalized ?? "");
    setPath(normalized);
  };

  // Filter and paginate here so the footer (below) can host the pagination
  // alongside the submit control passed in as `children`.
  const filteredContent =
    query === ""
      ? files
      : files?.filter((item) => item.name.toLowerCase().includes(query.toLowerCase()));
  const totalFiles = filteredContent ? filteredContent.length : 0;
  const indexOfLastFile = currentPage * FILES_PER_PAGE;
  const currentFiles = filteredContent
    ? filteredContent.slice(indexOfLastFile - FILES_PER_PAGE, indexOfLastFile)
    : [];

  // Reset to the first page when the directory or filter changes.
  useEffect(() => {
    setCurrentPage(1);
  }, [path, query]);

  // Inline path error for the search input, derived from the fetch state.
  // Gated on !isLoading so a stale error from the previous path doesn't paint
  // while the new listing is still in flight (e.g. right after a service
  // switch seeds a new mount). isLoading includes the remote connecting state.
  const inputError =
    isLoading
      ? null
      : error?.status === 403 || error?.code === "permission_denied"
        ? { message: "Access denied" }
        : error?.status === 404 || error?.code === "not_found"
          ? { message: "Path not found" }
          : null;

  return (
    <div
      id="audio-file-browser"
      name="audio-file-browser"
      className="mb-2 w-full max-w-6xl"
    >
      <label className="font-medium text-sm leading-6 text-gray-900 dark:text-gray-100">File Browser</label>
      <DirectoryInput
        root={root}
        value={inputValue}
        onChange={setInputValue}
        // Route typed/searched paths through the boundary check so an
        // out-of-mount path is refused (via toast) rather than navigating.
        onSubmit={() => handlePathChange(inputValue)}
        disabled={status.disabled}
        // Surface a missing/forbidden in-root path inline on the input,
        // mirroring FileManager, instead of the generic table error panel.
        error={inputError}
      />

      <FilterInput className="sm:flex-auto" query={query} setQuery={setQuery} disabled={status.disabled} />

      <AudioFileBrowserTable
        content={currentFiles}
        path={path}
        root={root}
        setAudioPath={setAudioPath}
        setPath={setPath}
        selected={selected}
        setSelected={setSelected}
        isLoading={isLoading}
        // 403/404 are shown inline on the input above; keep the table clean
        // for those and reserve its error panel for real/unknown failures.
        error={
          error?.status === 403 || error?.status === 404 || error?.code === "permission_denied" || error?.code === "not_found"
            ? null
            : error
        }
        refresh={refresh}
        status={status}
      />

      {/* Bare row below the table (matching the File Manager's pagination
          style): centered pagination with the submit control (children) on
          the right. Fixed height so the layout doesn't shift when pagination
          is hidden (single page). */}
      <div className="relative flex items-center justify-center h-12 mt-2">
        <Pagination
          filesPerPage={FILES_PER_PAGE}
          totalFiles={totalFiles}
          currentPage={currentPage}
          setCurrentPage={setCurrentPage}
          disabled={status.disabled}
        />
        <div className="absolute right-0">{children}</div>
      </div>

      <Notification
        show={!!operationError}
        variant="error"
        message={operationError || ""}
        onDismiss={() => setOperationError(null)}
      />
    </div>
  );
}

AudioFileBrowser.propTypes = {
  root: PropTypes.string,
  setAudioPath: PropTypes.func,
  status: PropTypes.object,
  profile: PropTypes.object,
  children: PropTypes.node,
};

export default AudioFileBrowser;
