import { useContext, useState } from "react";
import FileManager from "@/components/FileManager";
import FilePreview from "@/components/FilePreview";
import { ProfileContext } from "@/components/ProfileSelect";

function FileManagerContainer() {
    const { profile } = useContext(ProfileContext);
    const [selectedFile, setSelectedFile] = useState(null);

    // Local profiles start at /tmp; remote profiles ignore this and use homeDir from WebSocket
    const initialPath = "/tmp";

    return (
        <div className="bg-white">
            <FileManager
                root={initialPath}
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
