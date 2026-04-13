import { useEffect, useState } from "react";
import {
    ArrowPathIcon,
    ArrowUpTrayIcon,
} from "@heroicons/react/24/outline";
import { useFileSystem } from "@/lib/loaders";
import { useRemoteFileSystem } from "@/providers/RemoteFileSystemProvider";
import Notification from "@/components/Notification";
import FileManagerTable from "@/components/FileManagerTable";
import DirectoryInput from "@/components/DirectoryInput";
import FilterInput from "@/components/FilterInput";
import FileUploadDialog from "@/components/FileUploadDialog";
import FileDeleteDialog from "@/components/FileDeleteDialog";
import { getFileType } from "@/lib/fileApi";
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
    const isRemote = profile && profile.schema !== "local";
    const { reconnect, isConnecting, error: connectionError } = useRemoteFileSystem();
    const [path, setPath] = useState(null);
    const [query, setQuery] = useState("");
    const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
    const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
    const [selectedFile, setSelectedFile] = useState(null);
    const [operationInProgress, setOperationInProgress] = useState(false);
    const [operationSuccess, setOperationSuccess] = useState(null);
    const [operationError, setOperationError] = useState(null);

    const { files, error, isLoading, refresh, isConnected, homeDir } = useFileSystem(path, profile);

    // Update path when home directory changes
    useEffect(() => {
        setPath(homeDir);
    }, [homeDir]);

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

    const handlePathChange = (newPath) => {
        // Only enforce path boundary if root is an explicit path (not ~)
        if (!isRemote && root?.startsWith("/") && !newPath.startsWith(root)) {
            setOperationError(`Path must be within ${root}`);
            return;
        }
        setPath(newPath);
        if (onPathChange) onPathChange(newPath);
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
                        {isRemote && profile && (
                            <div className="flex items-center gap-1.5">
                                <span
                                    className={`inline-block h-2 w-2 flex-shrink-0 rounded-full ${
                                        isConnected
                                            ? "bg-green-500"
                                            : connectionError
                                                ? "bg-red-500"
                                                : "animate-pulse bg-yellow-500"
                                    }`}
                                />
                                <span className="text-sm text-gray-600 dark:text-gray-400">
                                    {isConnected
                                        ? `Connected to ${profile.user}@${profile.host}`
                                        : connectionError
                                            ? "Disconnected"
                                            : "Connecting..."}
                                </span>
                                {connectionError && (
                                    <button
                                        onClick={reconnect}
                                        disabled={isConnecting}
                                        className="ml-1 p-1 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 disabled:opacity-50 focus:outline-none"
                                        aria-label="Reconnect"
                                    >
                                        <ArrowPathIcon className={`h-4 w-4 ${isConnecting ? "animate-spin" : ""}`} />
                                    </button>
                                )}
                            </div>
                        )}
                    </div>
                    {enableUpload && isRemote ? (
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
                path={path}
                setPath={handlePathChange}
                disabled={status.disabled || operationInProgress}
                error={
                    error?.status === 403 || error?.code === "permission_denied"
                        ? { message: "Access denied" }
                        : error?.status === 404 || error?.code === "not_found"
                            ? { message: "Path not found" }
                            : null
                }
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
