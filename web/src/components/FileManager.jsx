
import { useEffect, useState } from "react";
import {
    ArrowUpTrayIcon,
    CheckCircleIcon,
    XCircleIcon,
    XMarkIcon,
} from "@heroicons/react/24/outline";
import { useFileSystem } from "@/lib/loaders";
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
    enableUpload = true,
    enableDelete = true,
    status,
    profile = null,
}) {
    const isRemote = profile && profile.schema !== "local";
    const [path, setPath] = useState(null);
    const [query, setQuery] = useState("");
    const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
    const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
    const [selectedFile, setSelectedFile] = useState(null);
    const [operationInProgress, setOperationInProgress] = useState(false);
    const [operationSuccess, setOperationSuccess] = useState(null);
    const [operationError, setOperationError] = useState(null);

    const { files, error, isLoading, refresh, isConnected, homeDir } = useFileSystem(path, profile);

    // Set path to homeDir when it becomes available
    useEffect(() => {
        if (homeDir && path === null) setPath(homeDir);
    }, [homeDir, path]);

    const displayRoot = homeDir ?? root;

    const handlePathChange = (newPath) => {
        // Only enforce path boundary if root is an explicit path (not ~)
        if (!isRemote && root?.startsWith("/") && !newPath.startsWith(root)) {
            setOperationError(`Path must be within ${root}`);
            return;
        }
        setPath(newPath);
    };

    useEffect(() => {
        if (files && files.length > 0 && onFileSelect) {
            const firstFile = files.find(f => !f.is_dir);
            if (firstFile) {
                onFileSelect({
                    path: firstFile.path,
                    name: firstFile.name,
                    type: getFileType(firstFile.name),
                    size: firstFile.size,
                    modified_at: firstFile.modified_at
                });
            }
        }
    }, [files, onFileSelect]);

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
        setTimeout(() => setOperationSuccess(null), 5000);
    };

    const handleDeleteSuccess = async (message) => {
        setOperationSuccess(message);
        setDeleteDialogOpen(false);
        setSelectedFile(null);
        await refresh();
        setTimeout(() => setOperationSuccess(null), 5000);
    };

    const handleOperationError = (message) => {
        setOperationError(message);
        setTimeout(() => setOperationError(null), 5000);
    };

    return (
        <div
            id="file-manager"
            name="file-manager"
            className="mt-2 mb-2 w-full"
        >
            <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-4">
                    <label className="font-medium text-sm">File Manager</label>
                    {isRemote && profile && (
                        <div className="flex items-center gap-1.5">
                            <span
                                className={`inline-block h-2 w-2 flex-shrink-0 rounded-full ${isConnected ? "bg-green-500" : "animate-pulse bg-yellow-500"
                                    }`}
                            />
                            <span className="text-sm text-gray-600">
                                {isConnected ? `Connected to ${profile.host}` : "Connecting..."}
                            </span>
                        </div>
                    )}
                </div>
                {enableUpload && (
                    <button
                        onClick={() => setUploadDialogOpen(true)}
                        disabled={status.disabled || operationInProgress}
                        className="inline-flex items-center gap-x-1.5 rounded-md bg-blue-500 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-400 disabled:bg-blue-200 disabled:cursor-not-allowed"
                    >
                        <ArrowUpTrayIcon className="h-5 w-5" />
                        Upload File
                    </button>
                )}
            </div>

            <DirectoryInput
                root={displayRoot}
                path={path}
                setPath={handlePathChange}
                disabled={status.disabled || operationInProgress}
            />

            {error?.status === 403 && (
                <div className="rounded-md bg-red-50 p-4 mt-2">
                    <div className="flex">
                        <XCircleIcon className="h-5 w-5 text-red-400" />
                        <div className="ml-3">
                            <p className="text-sm font-medium text-red-800">Access Denied</p>
                            <p className="text-sm text-red-700 mt-1">
                                You don&apos;t have permission to access: {path}
                            </p>
                        </div>
                    </div>
                </div>
            )}

            {error?.status === 404 && (
                <div className="rounded-md bg-yellow-50 p-4 mt-2">
                    <div className="flex">
                        <XCircleIcon className="h-5 w-5 text-yellow-400" />
                        <div className="ml-3">
                            <p className="text-sm font-medium text-yellow-800">Path Not Found</p>
                            <p className="text-sm text-yellow-700 mt-1">
                                The path does not exist: {path}
                            </p>
                        </div>
                    </div>
                </div>
            )}

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
                setPath={setPath}
                isLoading={isLoading}
                error={error}
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

            {operationSuccess && (
                <div className="fixed top-4 right-4 z-50 rounded-md bg-green-50 p-4 shadow-lg">
                    <div className="flex">
                        <CheckCircleIcon className="h-5 w-5 text-green-400" />
                        <p className="ml-3 text-sm font-medium text-green-800">
                            {operationSuccess}
                        </p>
                        <button
                            onClick={() => setOperationSuccess(null)}
                            className="ml-auto"
                        >
                            <XMarkIcon className="h-5 w-5 text-green-400" />
                        </button>
                    </div>
                </div>
            )}

            {operationError && (
                <div className="fixed top-4 right-4 z-50 rounded-md bg-red-50 p-4 shadow-lg">
                    <div className="flex">
                        <XCircleIcon className="h-5 w-5 text-red-400" />
                        <p className="ml-3 text-sm font-medium text-red-800">
                            {operationError}
                        </p>
                        <button onClick={() => setOperationError(null)} className="ml-auto">
                            <XMarkIcon className="h-5 w-5 text-red-400" />
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}

FileManager.propTypes = {
    root: PropTypes.string,
    onFileSelect: PropTypes.func,
    enableUpload: PropTypes.bool,
    enableDelete: PropTypes.bool,
    status: PropTypes.object,
    profile: PropTypes.object,
};

export default FileManager;
