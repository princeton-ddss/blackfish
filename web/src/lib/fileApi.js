import { blackfishApiURL } from "@/config";

export const FILE_TYPE_CONFIG = {
    image: {
        extensions: [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp"],
        endpoint: "/api/image",
    },
    text: {
        extensions: [".txt", ".md", ".json", ".csv", ".xml", ".yaml", ".yml", ".log"],
        endpoint: "/api/text",
    },
    audio: {
        extensions: [".wav", ".mp3"],
        endpoint: "/api/audio",
    },
};

export function getFileType(filename) {
    if (!filename) return null;

    const ext = filename.toLowerCase().match(/\.[^.]+$/)?.[0];
    if (!ext) return null;

    for (const [type, config] of Object.entries(FILE_TYPE_CONFIG)) {
        if (config.extensions.includes(ext)) {
            return type;
        }
    }

    return null;
}

export function getUploadEndpoint(fileType) {
    return FILE_TYPE_CONFIG[fileType]?.endpoint;
}

export function validateFileForUpload(file, destinationPath) {
    const errors = [];
    if (!file) {
        errors.push("No file selected");
        return errors;
    }

    const fileType = getFileType(file.name);
    if (!fileType) errors.push(`Unsupported file type: ${file.name}`);

    const MAX_FILE_SIZE = 100 * 1024 * 1024;
    if (file.size > MAX_FILE_SIZE) {
        errors.push(`File too large: ${(file.size / (1024 * 1024)).toFixed(2)}MB (max: 100MB)`);
    }

    if (!destinationPath || destinationPath.trim() === "") {
        errors.push("Destination path is required");
    }

    return errors;
}

export async function uploadFile(filePath, file, profile = null) {
    const fileType = getFileType(file.name);
    if (!fileType) throw new Error(`Unsupported file type: ${file.name}`);

    const endpoint = getUploadEndpoint(fileType);
    const formData = new FormData();
    formData.append("path", filePath);
    formData.append("file", file);

    let url = `${blackfishApiURL}${endpoint}`;
    if (profile && profile.schema !== "local") {
        url += `?profile=${encodeURIComponent(profile.name)}`;
    }

    const res = await fetch(url, { method: "POST", body: formData });
    if (!res.ok) throw new Error(`Upload failed: ${await res.text()}`);
    return res.json();
}

export async function replaceFile(filePath, newFile, profile = null) {
    const fileType = getFileType(filePath);
    if (!fileType) throw new Error(`Unsupported file type: ${filePath}`);

    const originalExt = filePath.toLowerCase().match(/\.[^.]+$/)?.[0];
    const newFileExt = newFile.name.toLowerCase().match(/\.[^.]+$/)?.[0];
    if (originalExt !== newFileExt) {
        throw new Error(`File type mismatch: expected ${originalExt}, got ${newFileExt}`);
    }

    const endpoint = getUploadEndpoint(fileType);
    const formData = new FormData();
    formData.append("path", filePath);
    formData.append("file", newFile);

    let url = `${blackfishApiURL}${endpoint}`;
    if (profile && profile.schema !== "local") {
        url += `?profile=${encodeURIComponent(profile.name)}`;
    }

    const res = await fetch(url, { method: "PUT", body: formData });
    if (!res.ok) throw new Error(`Replace failed: ${await res.text()}`);
    return res.json();
}

export async function deleteFile(filePath, profile = null) {
    const fileType = getFileType(filePath);
    if (!fileType) throw new Error(`Unsupported file type: ${filePath}`);

    const endpoint = getUploadEndpoint(fileType);
    let url = `${blackfishApiURL}${endpoint}?path=${encodeURIComponent(filePath)}`;
    if (profile && profile.schema !== "local") {
        url += `&profile=${encodeURIComponent(profile.name)}`;
    }

    const res = await fetch(url, { method: "DELETE" });
    if (!res.ok) throw new Error(`Delete failed: ${await res.text()}`);
    return res.text();
}
