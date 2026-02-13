import { useContext, useEffect, useRef, useState } from "react";
import { ProfileContext } from "@/components/ProfileSelect";
import { useModels } from "@/lib/loaders";
import ModelsTable from "./ModelsTable";
import ModelDeleteDialog from "./ModelDeleteDialog";
import Notification from "@/components/Notification";

function ModelsContainer() {
    const { profile } = useContext(ProfileContext);
    const { models, isLoading, mutate } = useModels(profile, null);

    const [modelToDelete, setModelToDelete] = useState(null);
    const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
    const [operationSuccess, setOperationSuccess] = useState(null);
    const [operationError, setOperationError] = useState(null);
    const [lastFetchedAt, setLastFetchedAt] = useState(null);

    const prevLoadingRef = useRef(isLoading);
    useEffect(() => {
        if (prevLoadingRef.current && !isLoading) {
            setLastFetchedAt(new Date());
        }
        prevLoadingRef.current = isLoading;
    }, [isLoading]);

    const handleDeleteClick = (model) => {
        setModelToDelete(model);
        setDeleteDialogOpen(true);
    };

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

    const isLocalProfile = profile?.schema === "local";

    return (
        <>
            <div className="w-full">
                <ModelsTable
                    models={models || []}
                    onDeleteClick={handleDeleteClick}
                    isLoading={isLoading}
                    onRefresh={handleRefresh}
                    isLocalProfile={isLocalProfile}
                    lastFetchedAt={lastFetchedAt}
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
