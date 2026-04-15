import { useState, useEffect } from "react";
import { FolderIcon } from "@heroicons/react/24/outline";
import { useFileSystem } from "@/lib/loaders";
import DirectoryInput from "@/components/DirectoryInput";
import FilterInput from "@/components/FilterInput";
import FileManagerTable from "@/components/FileManagerTable";
import { isRemoteProfile } from "@/lib/util";
import PropTypes from "prop-types";

/**
 * Inline directory browser for selecting a directory.
 * @param {object} props
 * @param {string} props.label - Label for the browser.
 * @param {string} props.value - Current selected path.
 * @param {Function} props.onChange - Callback when directory changes.
 * @param {object} props.profile - The remote profile to use.
 * @param {boolean} props.disabled - Whether the browser is disabled.
 */
function DirectoryBrowser({
  label,
  value,
  onChange,
  profile,
  disabled = false,
}) {
  const [query, setQuery] = useState("");

  const { files, error: fsError, isLoading, refresh, homeDir, isConnected } = useFileSystem(value, profile);

  // Determine if this is a remote profile
  const isRemote = isRemoteProfile(profile);

  // Set path to homeDir when it becomes available (if no value)
  useEffect(() => {
    if (homeDir && !value) {
      onChange(homeDir);
    }
  }, [homeDir, value, onChange]);

  const handlePathChange = (newPath) => {
    onChange(newPath);
  };

  // Pass all files - FileManagerTable will handle graying out non-directories
  const allFiles = files || null;

  // Status object required by FileManagerTable
  // Show disabled state with message when remote but not connected
  const notConnected = isRemote && !isConnected && !isLoading;
  const status = {
    disabled: disabled || notConnected,
    detail: notConnected ? "Not connected to cluster" : undefined,
  };

  const displayRoot = homeDir ?? "~";
  const displayPath = value || displayRoot;

  return (
    <div className="flex flex-col h-full">
      {/* Header with label */}
      <div className="flex items-center gap-2 mb-2">
        <FolderIcon className="h-4 w-4 text-gray-500 dark:text-gray-400" />
        <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
          {label}
        </span>
      </div>

      {/* Path input */}
      <DirectoryInput
        root={displayRoot}
        path={value}
        setPath={handlePathChange}
        disabled={disabled}
      />

      {/* Search filter */}
      <FilterInput
        query={query}
        setQuery={setQuery}
        disabled={disabled}
      />

      {/* Directory listing */}
      <div className="mt-2 flex-1 min-h-0">
        <FileManagerTable
          content={allFiles}
          path={value}
          root={null}
          filesPerPage={8}
          query={query}
          setPath={handlePathChange}
          isLoading={isLoading}
          error={fsError}
          refresh={refresh}
          status={status}
          onFileClick={null}
          onDeleteClick={null}
          operationInProgress={false}
          heightClass="h-[14rem]"
          showBottomSpacer={false}
          showPagination={false}
          compact
          directorySelectionMode
        />
      </div>

      {/* Current selection */}
      <div className="mt-2 px-2 py-1.5 bg-gray-100 dark:bg-gray-700 rounded border border-gray-300 dark:border-gray-600">
        <p className="text-xs text-gray-700 dark:text-gray-300 truncate" title={displayPath}>
          {displayPath}
        </p>
      </div>
    </div>
  );
}

DirectoryBrowser.propTypes = {
  label: PropTypes.string.isRequired,
  value: PropTypes.string,
  onChange: PropTypes.func.isRequired,
  profile: PropTypes.object,
  disabled: PropTypes.bool,
};

export default DirectoryBrowser;
