import { useEffect, useState } from "react";
import { Page } from "@/components/Page";
import { TaskContainer } from "@/components/TaskContainer";
import JobsContainer from "./components/JobsContainer";

export default function JobsPage() {
    const [isReady, setIsReady] = useState(false);

    useEffect(() => {
        setIsReady(true);
    }, []);

    if (!isReady) return null;

    return (
        <Page task="jobs" fullWidth>
            <TaskContainer>
                <JobsContainer />
            </TaskContainer>
        </Page>
    );
}
