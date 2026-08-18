import { useEffect, useState } from "react";
import {
    ArrowUpTrayIcon,
} from "@heroicons/react/24/outline";
import { useFileSystem } from "@/lib/loaders";
import { isWithinRoot, normalizePath } from "@/lib/pathUtils";
import { useRemoteFileSystem } from "@/providers/RemoteFileSystemProvider";
import Notification from "@/components/Notification";
import FileManagerTable from "@/components/FileManagerTable";
import DirectoryInput from "@/components/DirectoryInput";
import RemoteConnectionStatus from "@/components/RemoteConnectionStatus";
import FilterInput from "@/components/FilterInput";
import FileUploadDialog from "@/components/FileUploadDialog";
import FileDeleteDialog from "@/components/FileDeleteDialog";
import { getFileType } from "@/lib/fileApi";
import { isRemoteProfile } from "@/lib/util";
import PropTypes from "prop-types";

/** File Manager component with CRUD operations. */
function FileManager({
    root,
    onFileSelect = null,
    onPathChange = null,
    enableUpload = true,
    enableDelete = true,
    showHeader = true,
    status,
    profile = null,
}) {
    const isRemote = isRemoteProfile(profile);
    const { reconnect, isConnecting, error: connectionError } = useRemoteFileSystem();
    const [path, setPath] = useState(null);
    const [query, setQuery] = useState("");
    const [inputValue, setInputValue] = useState("");
    const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
    const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
    const [selectedFile, setSelectedFile] = useState(null);
    const [operationInProgress, setOperationInProgress] = useState(false);
    const [operationSuccess, setOperationSuccess] = useState(null);
    const [operationError, setOperationError] = useState(null);

    const { files, error, isLoading, isFetching, refresh, isConnected, homeDir } = useFileSystem(path, profile);

    // Reset path when profile changes
    useEffect(() => {
        setPath(null);
    }, [profile?.name]);

    // Initialize path from home directory (once per profile)
    useEffect(() => {
        if (homeDir && path === null) {
            setPath(homeDir);
        }
    }, [homeDir, path]);

    // Keep the controlled input in sync with the current path as navigation
    // changes it (folder clicks, homeDir init, profile switch).
    useEffect(() => {
        setInputValue(path ?? "");
    }, [path]);

    // Auto-dismiss success notifications after 5s. The effect cleanup also
    // cancels the timer on unmount and when a new success message arrives
    // before the previous one expires, preventing state updates on an
    // unmounted component.
    useEffect(() => {
        if (!operationSuccess) return undefined;
        const id = setTimeout(() => setOperationSuccess(null), 5000);
        return () => clearTimeout(id);
    }, [operationSuccess]);

    // Auto-dismiss error notifications after 5s.
    useEffect(() => {
        if (!operationError) return undefined;
        const id = setTimeout(() => setOperationError(null), 5000);
        return () => clearTimeout(id);
    }, [operationError]);

    const displayRoot = homeDir ?? root;

    // Inline path error for the search input, derived from the fetch state.
    // Gated on !isFetching so a stale error from the previous path doesn't paint
    // while the new listing is still in flight (covers remote connecting and
    // local background revalidation).
    const inputError =
        isFetching
            ? null
            : error?.status === 403 || error?.code === "permission_denied"
                ? { message: "Access denied" }
                : error?.status === 404 || error?.code === "not_found"
                    ? { message: "Path not found" }
                    : null;

    const handlePathChange = (newPath) => {
        // Normalize absolute paths (resolve "." / "..") so navigation lands on
        // and displays a clean path. "~"-relative input can't be resolved
        // client-side, so leave those (and non-absolute input) untouched.
        const resolved = newPath?.startsWith("/") ? normalizePath(newPath) : newPath;
        // Enforce the mount boundary only when root is an explicit absolute
        // path (not "~"/remote).
        const enforceBoundary = !isRemote && root?.startsWith("/");
        if (enforceBoundary && !isWithinRoot(resolved, root)) {
            setOperationError(`Path must be within ${root}`);
            // Revert the input to the last valid path so a rejected string
            // doesn't linger in the box.
            setInputValue(path ?? "");
            return;
        }
        // Sync the input to the resolved path directly. The [path] effect
        // covers navigation that changes path, but when the resolved path
        // equals the current one (e.g. "/x/.." back to "/x") no re-render
        // fires, so set it here too to clear any raw "." / ".." the user typed.
        setInputValue(resolved ?? "");
        setPath(resolved);
        if (onPathChange) onPathChange(resolved);
    };

    const handleFileClick = (file) => {
        if (onFileSelect && !file.is_dir) {
            onFileSelect({
                path: file.path,
                name: file.name,
                type: getFileType(file.name),
                size: file.size,
                modified_at: file.modified_at
            });
        }
    };

    const handleDeleteClick = (file) => {
        setSelectedFile(file);
        setDeleteDialogOpen(true);
    };

    const handleUploadSuccess = async (message) => {
        setOperationSuccess(message);
        setUploadDialogOpen(false);
        await refresh();
    };

    const handleDeleteSuccess = async (message) => {
        setOperationSuccess(message);
        setDeleteDialogOpen(false);
        setSelectedFile(null);
        if (onFileSelect) onFileSelect(null);
        await refresh();
    };

    const handleOperationError = (message) => {
        setOperationError(message);
    };

    return (
        <div
            id="file-manager"
            name="file-manager"
            className="mb-2 w-full"
        >
            {showHeader && (
                <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-4">
                        <label className="font-medium text-sm leading-6 text-gray-900 dark:text-gray-100">File Manager</label>
                        <RemoteConnectionStatus
                            profile={profile}
                            isConnected={isConnected}
                            isConnecting={isConnecting}
                            connectionError={connectionError}
                            onReconnect={reconnect}
                        />
                    </div>
                    {enableUpload ? (
                        <button
                            onClick={() => setUploadDialogOpen(true)}
                            disabled={status.disabled || operationInProgress}
                            className="p-1.5 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 disabled:text-gray-300 dark:disabled:text-gray-600 disabled:cursor-not-allowed focus:outline-none"
                            aria-label="Upload file"
                        >
                            <ArrowUpTrayIcon className="h-5 w-5" />
                        </button>
                    ) : (
                        <div className="p-1.5">
                            <div className="h-5 w-5" />
                        </div>
                    )}
                </div>
            )}

            <DirectoryInput
                root={displayRoot}
                value={inputValue}
                onChange={setInputValue}
                onSubmit={() => handlePathChange(inputValue)}
                disabled={status.disabled || operationInProgress}
                error={inputError}
            />

            <FilterInput
                className="sm:flex-auto"
                query={query}
                setQuery={setQuery}
                disabled={status.disabled}
            />

            <FileManagerTable
                content={files}
                path={path}
                root={root}
                filesPerPage={20}
                query={query}
                setPath={handlePathChange}
                isLoading={isLoading}
                error={error?.status === 403 || error?.status === 404 || error?.code === "permission_denied" || error?.code === "not_found" ? null : error}
                refresh={refresh}
                status={status}
                onFileClick={handleFileClick}
                onDeleteClick={enableDelete ? handleDeleteClick : null}
                operationInProgress={operationInProgress}
            />

            <FileUploadDialog
                open={uploadDialogOpen}
                setOpen={setUploadDialogOpen}
                currentPath={path}
                profile={profile}
                onSuccess={handleUploadSuccess}
                onError={handleOperationError}
                setOperationInProgress={setOperationInProgress}
            />

            <FileDeleteDialog
                open={deleteDialogOpen}
                setOpen={setDeleteDialogOpen}
                fileToDelete={selectedFile}
                profile={profile}
                onSuccess={handleDeleteSuccess}
                onError={handleOperationError}
                setOperationInProgress={setOperationInProgress}
            />

            <Notification
                show={!!operationSuccess}
                variant="success"
                message={operationSuccess || ""}
                onDismiss={() => setOperationSuccess(null)}
            />

            <Notification
                show={!!operationError}
                variant="error"
                message={operationError || ""}
                onDismiss={() => setOperationError(null)}
            />
        </div>
    );
}

FileManager.propTypes = {
    root: PropTypes.string,
    onFileSelect: PropTypes.func,
    onPathChange: PropTypes.func,
    enableUpload: PropTypes.bool,
    enableDelete: PropTypes.bool,
    showHeader: PropTypes.bool,
    status: PropTypes.object,
    profile: PropTypes.object,
};

export default FileManager;
