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

    // Reset selected file when path changes
    const handlePathChange = () => {
        setSelectedFile(null);
    };

    return (
        <div className="flex flex-col lg:flex-row lg:items-start gap-8">
            <div className="w-full lg:w-[48rem] lg:flex-shrink-0">
                <FileManager
                    key={profile?.name ?? "default"}
                    root={null}
                    onFileSelect={setSelectedFile}
                    onPathChange={handlePathChange}
                    enableUpload={true}
                    enableDelete={true}
                    status={{ disabled: false }}
                    profile={profile}
                />
            </div>
            <div className="w-full lg:flex-1 lg:min-w-[24rem] mb-2 lg:mr-6">
                <div className="flex items-center justify-between mb-2 h-9">
                    <label className="font-medium text-sm leading-6 text-gray-900 dark:text-gray-100">File Preview</label>
                </div>
                <div className="ring-1 ring-gray-300 dark:ring-gray-600 rounded-lg h-[36rem] overflow-y-auto">
                    <FilePreview
                        file={selectedFile}
                        profile={profile}
                    />
                </div>
            </div>
        </div>
    );
}

export default FileManagerContainer;
