
import { useState, useEffect, useCallback, useRef } from "react";
import { blackfishApiURL } from "@/config";

/** Hook for WebSocket-based remote file system operations. */
export function useRemoteFileSystem(path, profile) {
    const [files, setFiles] = useState(null);
    const [error, setError] = useState(null);
    const [isLoading, setIsLoading] = useState(false);
    const [isConnected, setIsConnected] = useState(false);
    const [homeDir, setHomeDir] = useState(null);

    const wsRef = useRef(null);
    const pendingRequests = useRef(new Map());
    const currentPathRef = useRef(path);

    useEffect(() => {
        currentPathRef.current = path;
    }, [path]);

    const generateId = useCallback(() => {
        return `${Date.now()}-${Math.random().toString(36).substring(2, 11)}`;
    }, []);

    const sendMessage = useCallback((message) => {
        return new Promise((resolve, reject) => {
            if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
                reject(new Error("WebSocket not connected"));
                return;
            }

            const id = generateId();
            const fullMessage = { ...message, id };

            pendingRequests.current.set(id, { resolve, reject });
            wsRef.current.send(JSON.stringify(fullMessage));

            setTimeout(() => {
                if (pendingRequests.current.has(id)) {
                    pendingRequests.current.delete(id);
                    reject(new Error("Request timeout"));
                }
            }, 30000);
        });
    }, [generateId]);

    const listDir = useCallback(async (dirPath, showHidden = false) => {
        setIsLoading(true);
        setError(null);

        try {
            const response = await sendMessage({
                action: "list",
                path: dirPath,
                show_hidden: showHidden,
            });

            if (response.status === "ok") {
                setFiles(response.entries);
                return response.entries;
            } else {
                const err = new Error(response.error?.message || "Failed to list directory");
                err.code = response.error?.code;
                throw err;
            }
        } catch (err) {
            setError(err);
            setFiles(null);
            throw err;
        } finally {
            setIsLoading(false);
        }
    }, [sendMessage]);

    const refresh = useCallback(() => {
        if (currentPathRef.current !== null && isConnected) {
            return listDir(currentPathRef.current);
        }
        return Promise.resolve(null);
    }, [isConnected, listDir]);

    useEffect(() => {
        if (!profile || profile.schema === "local") {
            setIsConnected(false);
            setFiles(null);
            setHomeDir(null);
            return;
        }

        const wsProtocol = blackfishApiURL.startsWith("https") ? "wss" : "ws";
        const wsHost = blackfishApiURL.replace(/^https?:\/\//, "");
        const wsUrl = `${wsProtocol}://${wsHost}/ws/files/${encodeURIComponent(profile.name)}`;

        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {};

        ws.onmessage = (event) => {
            try {
                const response = JSON.parse(event.data);

                if (response.status === "connected") {
                    setIsConnected(true);
                    setHomeDir(response.home_dir);
                    setError(null);
                    return;
                }

                if (response.id && pendingRequests.current.has(response.id)) {
                    const { resolve, reject } = pendingRequests.current.get(response.id);
                    pendingRequests.current.delete(response.id);

                    if (response.status === "ok") {
                        resolve(response);
                    } else {
                        const err = new Error(response.error?.message || "Unknown error");
                        err.code = response.error?.code;
                        reject(err);
                    }
                }
            } catch (parseError) {
                console.error("Failed to parse WebSocket message:", parseError);
            }
        };

        ws.onerror = () => {
            setError({ message: "WebSocket connection error", code: "CONNECTION_ERROR" });
            setIsConnected(false);
        };

        ws.onclose = () => {
            setIsConnected(false);
            for (const [id, { reject }] of pendingRequests.current) {
                reject(new Error("WebSocket connection closed"));
                pendingRequests.current.delete(id);
            }
        };

        return () => {
            if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
                ws.close();
            }
            wsRef.current = null;
            pendingRequests.current.clear();
        };
    }, [profile]);

    useEffect(() => {
        if (isConnected && path !== null) {
            listDir(path).catch(() => {});
        }
    }, [path, isConnected, listDir]);

    return {
        files,
        error,
        isLoading,
        isConnected,
        homeDir,
        refresh,
        listDir,
    };
}

export default useRemoteFileSystem;
