
import { useEffect, useState } from "react";
import { Page } from "@/components/Page";
import { TaskContainer } from "@/components/TaskContainer";
import FileManagerContainer from "./components/FileManagerContainer";

export default function FileManagerPage() {
    const [isReady, setIsReady] = useState(false);

    useEffect(() => {
        setIsReady(true);
    }, []);

    if (!isReady) return null;

    return (
        <Page task="file-manager" fullWidth>
            <TaskContainer>
                <FileManagerContainer />
            </TaskContainer>
        </Page>
    );
}
