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
import { isRootPath } from "@/lib/pathUtils";
import Pagination from "@/components/Pagination";
import DirectoryInput from "@/components/DirectoryInput";
import FilterInput from "@/components/FilterInput";
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
  filesPerPage,
  setAudioPath,
  query,
  setPath,
  selected,
  setSelected,
  isLoading,
  error,
  refresh,
  status
}) {
  const [currentPage, setCurrentPage] = useState(1);

  const indexOfLastFile = currentPage * filesPerPage;
  const indexOfFirstFile = indexOfLastFile - filesPerPage;
  const filteredContent =
    query === ""
      ? content
      : content?.filter((item) => {
        return item.name.toLowerCase().includes(query.toLowerCase());
      });
  const currentFiles =
    filteredContent === undefined
      ? []
      : filteredContent.slice(indexOfFirstFile, indexOfLastFile);

  return (
    <div
      id="audio-file-browser-table"
      name="audio-file-browser-table"
      className="flex-none h-[26rem]"
    >
      <div className="mt-3 flow-root">
        <div className="-my-2 overflow-x-auto sm:-mx-6 lg:-mx-8">
          <div className="inline-block min-w-full py-2 align-middle sm:px-6 lg:px-8">
            <div className="ring-1 ring-gray-300 sm:rounded-lg h-[26rem] overflow-y-scroll">
              <table className="divide-y divide-gray-300 table-fixed w-full">
                <thead>
                  <tr>
                    <th
                      scope="col"
                      className="sticky top-0 z-10 whitespace-nowrap py-4 text-left text-sm font-medium sm:pr-4 w-24 backdrop-blur bg-gray-50"
                    >
                      <button
                        onClick={() => {
                          const parts = path.split("/").filter(p => p !== "");
                          if (parts.length <= 1) {
                            // Going back to root
                            setPath(path === root || path.startsWith(root) ? root : "/");
                          } else {
                            const newPath = parts.slice(0, parts.length - 1).join("/");
                            setPath(newPath);
                          }
                        }}
                      >
                        {/* Hide back button at root - check for local root match or remote root "/" */}
                        {path !== root && !isRootPath(path) && path !== `${root}/` && (
                          <ChevronLeftIcon className="h-4 w-4 mt-1 ml-4 text-gray-900 hover:text-gray-400" />
                        )}{" "}
                      </button>
                    </th>
                    <th
                      scope="col"
                      className="sticky top-0 z-10 py-3.5 pl-4 pr-3 text-left text-sm font-semibold text-gray-900 sm:pl-6 w-1/2 backdrop-blur bg-gray-50"
                    >
                      Name
                    </th>
                    <th
                      scope="col"
                      className="sticky top-0 z-10 px-3 py-3.5 text-left text-sm font-semibold text-gray-900 w-24 backdrop-blur bg-gray-50"
                    >
                      Size
                    </th>
                    <th
                      scope="col"
                      className="sticky top-0 z-10 px-3 py-3.5 text-left text-sm font-semibold text-gray-900 w-48 backdrop-blur bg-gray-50"
                    >
                      Last Modified
                    </th>
                    <th
                      scope="col"
                      className="sticky top-0 z-10 px-2.5 py-3.5 text-left text-sm font-semibold text-gray-900 w-12 backdrop-blur bg-gray-50"
                    >
                      <button
                        onClick={async () => {
                          refresh();
                        }}
                        disabled={status.disabled}
                      >
                        <ArrowPathIcon
                          className={`h-5 w-5 mt-1 ${status.disabled ? "text-gray-300" : "text-gray-900 hover:text-gray-400"} ${isLoading ? "animate-spin" : ""}`}
                        />
                      </button>
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 bg-white">
                  {status.disabled ? (
                    <tr>
                      <td colSpan={5} className="h-64">
                        <div className="font-light sm:text-sm text-center align-middle">
                          <img
                            className="h-16 ml-auto mr-auto opacity-80 mb-5"
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
                        <div className="font-light sm:text-sm text-center align-middle">
                          <img
                            className="h-16 ml-auto mr-auto opacity-80 mb-5"
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
                            <div className="bg-gray-100 h-9 rounded-md"></div>
                          </td>
                        </tr>
                      ))}
                    </>
                  ) : content?.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="h-64">
                        <div className="font-light sm:text-sm text-center align-middle">
                          <img
                            className="h-16 ml-auto mr-auto opacity-80 mb-5"
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
                        <div className="font-light sm:text-sm text-center align-middle">
                          {"No service selected."}
                        </div>
                      </td>
                    </tr>
                  ) : (
                    currentFiles.map((item) => (
                      <tr key={item.path} className={selected === item.path ? "bg-gray-50" : "bg-white"}>
                        <td className="relative whitespace-nowrap w-24 py-4 px-5 text-gray-700 text-left text-sm font-medium sm:pr-6">
                          <div
                            className={`flex ${item.is_dir || item.path.match(/\.(mp3|wav|flac)$/i) ? "" : "text-gray-300"
                              }`}
                          >
                            {item.is_dir ? (
                              <FolderIcon className="h-7 w-7" />
                            ) : (
                              <DocumentIcon className="h-7 w-7" />
                            )}
                          </div>
                        </td>
                        <td className="whitespace-nowrap w-1/2 py-4 pl-4 pr-3 text-left text-sm text-gray-900">
                          <div
                            className={`overflow-x-scroll ${item.is_dir || item.path.match(/\.(mp3|wav|flac)$/i) ? "" : "text-gray-300"
                              }`}
                          >
                            {item.name}
                          </div>
                        </td>
                        <td className="whitespace-nowrap w-24 py-3.5 px-3 text-left text-sm text-gray-900">
                          <div
                            className={`flex ${item.is_dir || item.path.match(/\.(mp3|wav|flac)$/i) ? "" : "text-gray-300"
                              }`}
                          >
                            {item.is_dir ? "-" : fileSize(item.size)}
                          </div>
                        </td>
                        <td className="whitespace-nowrap w-48 py-4 px-3 text-left text-sm text-gray-900">
                          <div
                            className={`flex ${item.is_dir || item.path.match(/\.(mp3|wav|flac)$/i) ? "" : "text-gray-300"
                              }`}
                          >
                            {lastModified(item.modified_at)}
                          </div>
                        </td>
                        <td className="whitespace-nowrap w-12 py-4 px-3 text-left text-sm text-gray-900">
                          <div
                            className={`flex ${item.is_dir || item.path.match(/\.(mp3|wav|flac)$/i) ? "" : "text-gray-300"
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
                                className={`${status.disabled ? "text-gray-300" : "text-gray-900"}`}
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
                                  className="h-4 w-4 rounded border-gray-300 text-blue-500 focus:ring-blue-600"
                                />
                              )
                            )}
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                  <tr className="bg-white">
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
      <Pagination
        filesPerPage={filesPerPage}
        totalFiles={filteredContent === undefined ? 0 : filteredContent.length}
        currentPage={currentPage}
        setCurrentPage={setCurrentPage}
        disabled={status.disabled}
      />
    </div>
  );
}

AudioFileBrowserTable.propTypes = {
  content: PropTypes.array,
  path: PropTypes.string,
  root: PropTypes.string,
  filesPerPage: PropTypes.number,
  setAudioPath: PropTypes.func,
  query: PropTypes.string,
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
function AudioFileBrowser({ root, setAudioPath, status }) {
  const [path, setPath] = useState(root);
  const [pathError, setPathError] = useState(false);
  const [selected, setSelected] = useState("");
  const [query, setQuery] = useState("");
  const { files, error, isLoading, refresh } = useFileSystem(path); // TODO: only fetch files if !status.disabled

  useEffect(() => {
    setPath(root);
  }, [root]);

  return (
    <div
      id="audio-file-browser"
      name="audio-file-browser"
      className="mt-2 mb-2 w-full max-w-6xl"
    >
      <label className="font-medium text-sm">File Browser</label>
      <DirectoryInput
        root={root}
        path={path}
        setPath={setPath}
        pathError={pathError}
        setPathError={setPathError}
        disabled={status.disabled}
      />

      <FilterInput className="sm:flex-auto" query={query} setQuery={setQuery} disabled={status.disabled} />

      <AudioFileBrowserTable
        content={files}
        path={path}
        root={root}
        filesPerPage={20}
        setAudioPath={setAudioPath}
        query={query}
        setPath={setPath}
        setPathError={setPathError}
        selected={selected}
        setSelected={setSelected}
        isLoading={isLoading}
        error={error}
        refresh={refresh}
        status={status}
      />
    </div>
  );
}

AudioFileBrowser.propTypes = {
  root: PropTypes.string,
  setAudioPath: PropTypes.func,
  status: PropTypes.object,
};

export default AudioFileBrowser;
