
import { useState, useEffect, useCallback, useRef } from "react";
import { blackfishApiURL } from "@/config";

/**
 * Hook for WebSocket-based remote file system operations.
 * @param {string} path - Current directory path
 * @param {Object} profile - Remote profile configuration
 * @param {Object} options - Optional configuration
 * @param {number} options.timeout - Request timeout in ms (default: 60000)
 * @param {boolean} options.autoReconnect - Enable auto-reconnection (default: true)
 */
export function useRemoteFileSystem(path, profile, options = {}) {
    const {
        timeout = 60000,
        autoReconnect = true,
    } = options;

    const [files, setFiles] = useState(null);
    const [error, setError] = useState(null);
    const [isLoading, setIsLoading] = useState(false);
    const [isConnected, setIsConnected] = useState(false);
    const [homeDir, setHomeDir] = useState(null);

    const wsRef = useRef(null);
    const pendingRequests = useRef(new Map());
    const currentPathRef = useRef(path);
    const reconnectAttempts = useRef(0);
    const reconnectTimeoutRef = useRef(null);
    const shouldReconnect = useRef(true);

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

            // Prevent unbounded memory growth by rejecting if too many pending
            if (pendingRequests.current.size >= 100) {
                reject(new Error("Too many pending requests"));
                return;
            }

            const id = generateId();
            const fullMessage = { ...message, id };

            // Store timeout ID to clear it when response arrives (prevents race condition)
            const timeoutId = setTimeout(() => {
                if (pendingRequests.current.has(id)) {
                    pendingRequests.current.delete(id);
                    reject(new Error("Request timeout"));
                }
            }, timeout);

            pendingRequests.current.set(id, { resolve, reject, timeoutId });
            wsRef.current.send(JSON.stringify(fullMessage));
        });
    }, [generateId, timeout]);

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

        // Reset state on new profile
        shouldReconnect.current = true;
        reconnectAttempts.current = 0;
        setHomeDir(null);
        setFiles(null);

        const wsProtocol = blackfishApiURL.startsWith("https") ? "wss" : "ws";
        const wsHost = blackfishApiURL.replace(/^https?:\/\//, "");
        const wsUrl = `${wsProtocol}://${wsHost}/ws/files/${encodeURIComponent(profile.name)}`;

        const connect = () => {
            const ws = new WebSocket(wsUrl);
            wsRef.current = ws;

            ws.onopen = () => {
                // Reset reconnection attempts on successful connection
                reconnectAttempts.current = 0;
            };

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
                        const { resolve, reject, timeoutId } = pendingRequests.current.get(response.id);
                        // Clear timeout to prevent race condition
                        clearTimeout(timeoutId);
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

            ws.onclose = (event) => {
                setIsConnected(false);

                // Clear pending requests with timeouts
                for (const [id, { reject, timeoutId }] of pendingRequests.current) {
                    clearTimeout(timeoutId);
                    reject(new Error("WebSocket connection closed"));
                    pendingRequests.current.delete(id);
                }

                // Attempt reconnection for transient failures
                // Don't reconnect for policy violations (code 1008) or intentional closes
                const isTransientFailure = event.code !== 1000 && event.code !== 1008;
                if (
                    autoReconnect &&
                    shouldReconnect.current &&
                    isTransientFailure &&
                    reconnectAttempts.current < 2
                ) {
                    reconnectAttempts.current += 1;
                    console.log(`WebSocket closed, reconnecting in 2s (attempt ${reconnectAttempts.current}/2)`);

                    reconnectTimeoutRef.current = setTimeout(() => {
                        if (shouldReconnect.current) {
                            connect();
                        }
                    }, 2000);
                } else if (reconnectAttempts.current >= 2) {
                    setError({
                        message: "Connection failed after maximum retry attempts",
                        code: "MAX_RETRIES_EXCEEDED"
                    });
                }
            };
        };

        connect();

        return () => {
            // Prevent reconnection on cleanup
            shouldReconnect.current = false;
            if (reconnectTimeoutRef.current) {
                clearTimeout(reconnectTimeoutRef.current);
                reconnectTimeoutRef.current = null;
            }
            if (wsRef.current) {
                if (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING) {
                    wsRef.current.close();
                }
                wsRef.current = null;
            }
            pendingRequests.current.clear();
        };
    }, [profile, autoReconnect]);

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
