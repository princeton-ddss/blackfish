import { useContext, useEffect, useState } from "react";
import FileManager from "@/components/FileManager";
import FilePreview from "@/components/FilePreview";
import { ProfileContext } from "@/components/ProfileSelect";

function FileManagerContainer() {
    const { profile } = useContext(ProfileContext);
    const [selectedFile, setSelectedFile] = useState(null);

    // Reset selected file when profile changes to avoid stale file references
    useEffect(() => {
        setSelectedFile(null);
    }, [profile?.name]);

    return (
        <div className="bg-white">
            <FileManager
                key={profile?.name ?? "default"}
                root={null}
                onFileSelect={setSelectedFile}
                enableUpload={true}
                enableDelete={true}
                status={{ disabled: false }}
                profile={profile}
            />
            <div className="mt-4">
                <FilePreview
                    file={selectedFile}
                    profile={profile}
                />
            </div>
        </div>
    );
}

export default FileManagerContainer;
