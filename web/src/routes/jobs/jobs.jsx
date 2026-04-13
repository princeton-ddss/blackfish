import { useEffect, useState, useContext } from "react";
import { Page } from "@/components/Page";
import { TaskContainer } from "@/components/TaskContainer";
import { ProfileContext } from "@/components/ProfileSelect";
import { Square3Stack3DIcon } from "@heroicons/react/24/outline";
import JobsContainer from "./components/JobsContainer";

export default function JobsPage() {
    const [isReady, setIsReady] = useState(false);
    const { profile } = useContext(ProfileContext);
    const isSlurm = profile?.schema === "slurm";

    useEffect(() => {
        setIsReady(true);
    }, []);

    if (!isReady) return null;

    if (!isSlurm) {
        return (
            <Page task="jobs" fullWidth>
                <TaskContainer>
                    <div className="flex flex-col items-center justify-center h-[60vh] text-center">
                        <Square3Stack3DIcon className="h-16 w-16 text-gray-300 dark:text-gray-600 mb-4" />
                        <h2 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
                            Jobs require a Slurm profile
                        </h2>
                        <p className="text-sm text-gray-500 dark:text-gray-400 max-w-md">
                            Batch jobs are only available when connected to a Slurm cluster.
                            Select a Slurm profile from the dropdown above to access this feature.
                        </p>
                    </div>
                </TaskContainer>
            </Page>
        );
    }

    return (
        <Page task="jobs" fullWidth>
            <TaskContainer>
                <JobsContainer />
            </TaskContainer>
        </Page>
    );
}
