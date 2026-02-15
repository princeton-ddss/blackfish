import { useContext, useState, useEffect, useCallback } from "react";
import { ProfileContext } from "@/components/ProfileSelect";
import { useModels } from "@/lib/loaders";
import { getDownloadStatus, updateModel } from "@/lib/requests";
import ModelsTable from "./ModelsTable";
import ModelDeleteDialog from "./ModelDeleteDialog";
import ModelDownloadDialog from "./ModelDownloadDialog";
import Notification from "@/components/Notification";

function ModelsContainer() {
    const { profile } = useContext(ProfileContext);
    const { models, isLoading, mutate } = useModels(profile, null);

    const [modelToDelete, setModelToDelete] = useState(null);
    const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
    const [downloadDialogOpen, setDownloadDialogOpen] = useState(false);
    const [activeDownloads, setActiveDownloads] = useState([]);
    const [updatingModel, setUpdatingModel] = useState(null);
    const [operationSuccess, setOperationSuccess] = useState(null);
    const [operationError, setOperationError] = useState(null);

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
                mutate();
            } else if (result.status === "up_to_date") {
                setOperationSuccess(`${model.repo_id} is already up to date`);
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
        setActiveDownloads((prev) => [...prev, result.task_id]);
        setOperationSuccess(`Download started for ${result.repo_id}`);
        setOperationError(null);
    };

    // Poll for active download status
    const checkDownloadStatus = useCallback(async () => {
        if (activeDownloads.length === 0) return;

        const updatedDownloads = [];
        for (const taskId of activeDownloads) {
            try {
                const status = await getDownloadStatus(taskId);
                if (status.status === "completed") {
                    setOperationSuccess(`Downloaded ${status.repo_id}`);
                    mutate();
                } else if (status.status === "failed") {
                    setOperationError(`Download failed: ${status.error_message || "Unknown error"}`);
                } else {
                    // Still pending or downloading
                    updatedDownloads.push(taskId);
                }
            } catch {
                // Task not found or error, remove from tracking
                console.debug("Download task not found:", taskId);
            }
        }
        setActiveDownloads(updatedDownloads);
    }, [activeDownloads, mutate]);

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
                    onRefresh={handleRefresh}
                    cacheDir={profile?.cache_dir}
                    homeDir={profile?.home_dir}
                    hasActiveDownloads={activeDownloads.length > 0}
                    updatingModel={updatingModel}
                />
            </div>

            {/* Delete Dialog */}
            <ModelDeleteDialog
                open={deleteDialogOpen}
                setOpen={setDeleteDialogOpen}
                modelToDelete={modelToDelete}
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
                onDismiss={() => setOperationSuccess(null)}
            />

            {/* Error Notification */}
            <Notification
                show={!!operationError}
                variant="error"
                message={operationError}
                onDismiss={() => setOperationError(null)}
            />
        </>
    );
}

export default ModelsContainer;
