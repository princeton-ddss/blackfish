import { useEffect, useState } from "react";
import { Page } from "@/components/Page";
import { TaskContainer } from "@/components/TaskContainer";
import ModelsContainer from "./components/ModelsContainer";

export default function ModelsPage() {
    const [isReady, setIsReady] = useState(false);

    useEffect(() => {
        setIsReady(true);
    }, []);

    if (!isReady) return null;

    return (
        <Page task="models" fullWidth>
            <TaskContainer>
                <ModelsContainer />
            </TaskContainer>
        </Page>
    );
}
