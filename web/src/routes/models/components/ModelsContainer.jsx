import { useContext, useState, useEffect, useCallback, useMemo } from "react";
import { ProfileContext } from "@/components/ProfileSelect";
import { useModels } from "@/lib/loaders";
import { getDownloadStatus, updateModel } from "@/lib/requests";
import ModelsTable from "./ModelsTable";
import ModelDeleteDialog from "./ModelDeleteDialog";
import ModelDownloadDialog from "./ModelDownloadDialog";
import Notification from "@/components/Notification";

function ModelsContainer() {
    const { profile } = useContext(ProfileContext);
    const { models, isLoading, isRefreshing, mutate } = useModels(profile, null);

    // Remote profiles don't support CRUD operations yet
    const isRemote = profile?.schema === "slurm" &&
                     profile?.host &&
                     profile.host !== "localhost";

    const [modelToDelete, setModelToDelete] = useState(null);
    const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
    const [downloadDialogOpen, setDownloadDialogOpen] = useState(false);
    const [activeDownloads, setActiveDownloads] = useState([]);
    const [updatingModel, setUpdatingModel] = useState(null);
    const [operationSuccess, setOperationSuccess] = useState(null);
    const [operationError, setOperationError] = useState(null);
    const [modelsWithUpdates, setModelsWithUpdates] = useState(new Set());
    const [checkingUpdates, setCheckingUpdates] = useState(false);
    const [selectedModel, setSelectedModel] = useState(null);

    // Get unique repos with one model ID each for update checking
    const reposToCheck = useMemo(() => {
        if (!models || models.length === 0) return [];
        const seen = new Map();
        for (const model of models) {
            if (!seen.has(model.repo_id)) {
                seen.set(model.repo_id, model.id);
            }
        }
        return Array.from(seen.entries()); // [[repo_id, model_id], ...]
    }, [models]);

    // Check for updates when models change (and not remote)
    useEffect(() => {
        if (isRemote || reposToCheck.length === 0) {
            setModelsWithUpdates(new Set());
            return;
        }

        const checkAllUpdates = async () => {
            setCheckingUpdates(true);
            const updatesAvailable = new Set();

            // Check each repo in parallel
            const results = await Promise.allSettled(
                reposToCheck.map(async ([repoId, modelId]) => {
                    try {
                        const result = await updateModel(modelId, { checkOnly: true });
                        if (result.status === "update_available") {
                            return repoId;
                        }
                    } catch {
                        // Ignore errors for individual checks
                    }
                    return null;
                })
            );

            for (const result of results) {
                if (result.status === "fulfilled" && result.value) {
                    updatesAvailable.add(result.value);
                }
            }

            setModelsWithUpdates(updatesAvailable);
            setCheckingUpdates(false);
        };

        checkAllUpdates();
    }, [reposToCheck, isRemote]);

    const handleDeleteClick = (model) => {
        setModelToDelete(model);
        setDeleteDialogOpen(true);
    };

    const handleUpdateClick = async (model) => {
        // Get the most recent revision to update
        if (!model.revisions || model.revisions.length === 0) {
            setOperationError("No revisions found for this model");
            return;
        }

        const revision = model.revisions[0];
        setUpdatingModel(model.repo_id);

        try {
            const result = await updateModel(revision.id);

            if (result.status === "updated") {
                setOperationSuccess(
                    `Updated ${model.repo_id} to ${result.new_revision?.slice(0, 7)}`
                );
                // Remove from updates available set
                setModelsWithUpdates((prev) => {
                    const next = new Set(prev);
                    next.delete(model.repo_id);
                    return next;
                });
                mutate();
            } else if (result.status === "up_to_date") {
                setOperationSuccess(`${model.repo_id} is already up to date`);
                // Remove from updates available set (shouldn't have been there)
                setModelsWithUpdates((prev) => {
                    const next = new Set(prev);
                    next.delete(model.repo_id);
                    return next;
                });
            } else if (result.status === "error") {
                setOperationError(result.message || "Failed to update model");
            }
        } catch (err) {
            setOperationError(err.message || "Failed to update model");
        } finally {
            setUpdatingModel(null);
        }
    };

    const handleDownloadClick = () => {
        setDownloadDialogOpen(true);
    };

    const handleDownloadSuccess = (result) => {
        const newDownload = {
            task_id: result.task_id,
            repo_id: result.repo_id,
            status: "pending",
        };
        setActiveDownloads((prev) => [...prev, newDownload]);
        // Select the downloading model to show progress in revisions table
        setSelectedModel({
            repo_id: result.repo_id,
            isDownloading: true,
            downloadStatus: "pending",
            revisions: [],
        });
        setOperationSuccess(`Download started for ${result.repo_id}`);
        setOperationError(null);
    };

    // Poll for active download status
    const checkDownloadStatus = useCallback(async () => {
        if (activeDownloads.length === 0) return;

        const updatedDownloads = [];
        for (const download of activeDownloads) {
            // Skip already failed downloads (they stay in UI until dismissed)
            if (download.status === "failed") {
                updatedDownloads.push(download);
                continue;
            }

            try {
                const result = await getDownloadStatus(download.task_id);
                if (result.status === "completed") {
                    setOperationSuccess(`Downloaded ${result.repo_id}`);
                    mutate();
                } else if (result.status === "failed") {
                    // Show error toast
                    setOperationError(`Download failed: ${result.error_message || "Unknown error"}`);
                    // Keep failed downloads in UI with error info
                    updatedDownloads.push({
                        ...download,
                        status: "failed",
                        error: result.error_message || "Unknown error",
                    });
                } else {
                    // Still pending or downloading - update status
                    updatedDownloads.push({
                        ...download,
                        status: result.status,
                    });
                }
            } catch {
                // Task not found or error, remove from tracking
                console.debug("Download task not found:", download.task_id);
            }
        }
        setActiveDownloads(updatedDownloads);
    }, [activeDownloads, mutate]);

    const handleDismissDownload = useCallback((taskId) => {
        setActiveDownloads((prev) => prev.filter((d) => d.task_id !== taskId));
    }, []);

    const handleDismissSuccess = useCallback(() => {
        setOperationSuccess(null);
    }, []);

    const handleDismissError = useCallback(() => {
        setOperationError(null);
    }, []);

    useEffect(() => {
        if (activeDownloads.length === 0) return;

        const interval = setInterval(checkDownloadStatus, 3000);
        return () => clearInterval(interval);
    }, [activeDownloads.length, checkDownloadStatus]);

    const handleOperationSuccess = (message) => {
        setOperationSuccess(message);
        setOperationError(null);
        mutate();
    };

    const handleOperationError = (message) => {
        setOperationError(message);
        setOperationSuccess(null);
    };

    const handleRefresh = () => {
        mutate();
    };

    return (
        <>
            <div className="w-full">
                <ModelsTable
                    models={models || []}
                    onDeleteClick={handleDeleteClick}
                    onUpdateClick={handleUpdateClick}
                    onDownloadClick={handleDownloadClick}
                    isLoading={isLoading}
                    isRefreshing={isRefreshing}
                    onRefresh={handleRefresh}
                    cacheDir={profile?.cache_dir}
                    homeDir={profile?.home_dir}
                    activeDownloads={activeDownloads}
                    updatingModel={updatingModel}
                    isRemote={isRemote}
                    modelsWithUpdates={modelsWithUpdates}
                    checkingUpdates={checkingUpdates}
                    selectedModel={selectedModel}
                    onSelectModel={setSelectedModel}
                    onDismissDownload={handleDismissDownload}
                />
            </div>

            {/* Delete Dialog */}
            <ModelDeleteDialog
                open={deleteDialogOpen}
                setOpen={setDeleteDialogOpen}
                modelToDelete={modelToDelete}
                cacheDir={profile?.cache_dir}
                homeDir={profile?.home_dir}
                onSuccess={handleOperationSuccess}
                onError={handleOperationError}
            />

            {/* Download Dialog */}
            <ModelDownloadDialog
                open={downloadDialogOpen}
                setOpen={setDownloadDialogOpen}
                profile={profile}
                onSuccess={handleDownloadSuccess}
                onError={handleOperationError}
            />

            {/* Success Notification */}
            <Notification
                show={!!operationSuccess}
                variant="success"
                message={operationSuccess}
                onDismiss={handleDismissSuccess}
            />

            {/* Error Notification */}
            <Notification
                show={!!operationError}
                variant="error"
                message={operationError}
                onDismiss={handleDismissError}
            />
        </>
    );
}

export default ModelsContainer;
