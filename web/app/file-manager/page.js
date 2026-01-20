"use client";

import { useContext, useEffect, useState } from "react";
import { Page } from "../components/Page";
import { TaskContainer } from "../components/TaskContainer";
import FileManagerContainer from "./components/FileManagerContainer";
import ProfileSelect, { ProfileContext } from "../components/ProfileSelect";

export default function FileManagerPage() {
    const [isReady, setIsReady] = useState(false);
    const { profile, setProfile } = useContext(ProfileContext);

    useEffect(() => {
        setIsReady(true);
    }, []);

    if (!isReady) return null;

    return (
        <Page task="file-manager">
            <TaskContainer>
                <FileManagerContainer />
            </TaskContainer>

            {/* Sidebar with Profile Select */}
            <div className="bg-white flex flex-col lg:w-96 lg:p-8 lg:pr-12">
                <ProfileSelect
                    selectedProfile={profile}
                    setSelectedProfile={setProfile}
                />
            </div>
        </Page>
    );
}
