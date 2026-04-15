import { createContext, useContext, useState, useEffect, useCallback, useRef } from "react";
import { ProfileContext } from "@/components/ProfileSelect";
import { isRemoteProfile } from "@/lib/util";
import { blackfishApiURL } from "@/config";
import PropTypes from "prop-types";

const RemoteFileSystemContext = createContext(null);

/**
 * Provider for WebSocket-based remote file system operations.
 * Connects when a remote profile is selected, disconnects on local/null.
 */
function RemoteFileSystemProvider({ children }) {
    const { profile } = useContext(ProfileContext);

    // Configuration
    const timeout = 60000;
    const connectionTimeout = 15000; // Timeout for initial connection
    const maxReconnectAttempts = 2;
    const reconnectDelayMs = 2000;

    // State
    const [isConnected, setIsConnected] = useState(false);
    const [isConnecting, setIsConnecting] = useState(false);
    const [error, setError] = useState(null);
    const [homeDir, setHomeDir] = useState(null);

    // Refs
    const wsRef = useRef(null);
    const pendingRequests = useRef(new Map());
    const reconnectAttempts = useRef(0);
    const reconnectTimeoutRef = useRef(null);
    const connectionTimeoutRef = useRef(null);
    const shouldReconnect = useRef(true);
    const currentProfileRef = useRef(null);

    const generateId = useCallback(() => {
        return `${Date.now()}-${Math.random().toString(36).substring(2, 11)}`;
    }, []);

    const sendMessage = useCallback((message) => {
        return new Promise((resolve, reject) => {
            if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
                reject(new Error("WebSocket not connected"));
                return;
            }

            if (pendingRequests.current.size >= 100) {
                reject(new Error("Too many pending requests"));
                return;
            }

            const id = generateId();
            const fullMessage = { ...message, id };

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
        const response = await sendMessage({
            action: "list",
            path: dirPath,
            show_hidden: showHidden,
        });

        if (response.status === "ok") {
            return response.entries;
        } else {
            const err = new Error(response.error?.message || "Failed to list directory");
            err.code = response.error?.code;
            throw err;
        }
    }, [sendMessage]);

    const connect = useCallback(() => {
        const profileToConnect = currentProfileRef.current;
        if (!isRemoteProfile(profileToConnect)) {
            return;
        }

        setIsConnecting(true);
        setError(null);

        const wsProtocol = blackfishApiURL.startsWith("https") ? "wss" : "ws";
        const wsHost = blackfishApiURL.replace(/^https?:\/\//, "");
        const wsUrl = `${wsProtocol}://${wsHost}/ws/files/${encodeURIComponent(profileToConnect.name)}`;

        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        // Set connection timeout - cleared when "connected" message received or socket closes
        connectionTimeoutRef.current = setTimeout(() => {
            if (wsRef.current) {
                setError({ message: "Connection timeout", code: "CONNECTION_TIMEOUT" });
                setIsConnecting(false);
                wsRef.current.close();
            }
        }, connectionTimeout);

        ws.onopen = () => {
            reconnectAttempts.current = 0;
        };

        ws.onmessage = (event) => {
            try {
                const response = JSON.parse(event.data);

                if (response.status === "connected") {
                    if (connectionTimeoutRef.current) {
                        clearTimeout(connectionTimeoutRef.current);
                        connectionTimeoutRef.current = null;
                    }
                    setIsConnected(true);
                    setIsConnecting(false);
                    setHomeDir(response.home_dir);
                    setError(null);
                    return;
                }

                if (response.id && pendingRequests.current.has(response.id)) {
                    const { resolve, reject, timeoutId } = pendingRequests.current.get(response.id);
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
            setIsConnecting(false);
        };

        ws.onclose = (event) => {
            setIsConnected(false);
            setIsConnecting(false);

            // Clear connection timeout
            if (connectionTimeoutRef.current) {
                clearTimeout(connectionTimeoutRef.current);
                connectionTimeoutRef.current = null;
            }

            // Clear pending requests
            for (const [id, { reject, timeoutId }] of pendingRequests.current) {
                clearTimeout(timeoutId);
                reject(new Error("WebSocket connection closed"));
                pendingRequests.current.delete(id);
            }

            // Attempt reconnection for transient failures
            const isTransientFailure = event.code !== 1000 && event.code !== 1008;
            if (
                shouldReconnect.current &&
                isTransientFailure &&
                reconnectAttempts.current < maxReconnectAttempts
            ) {
                reconnectAttempts.current += 1;
                reconnectTimeoutRef.current = setTimeout(() => {
                    if (shouldReconnect.current) {
                        connect();
                    }
                }, reconnectDelayMs);
            } else if (reconnectAttempts.current >= maxReconnectAttempts) {
                setError({
                    message: "Connection failed after maximum retry attempts",
                    code: "MAX_RETRIES_EXCEEDED"
                });
            }
        };
    }, [connectionTimeout, maxReconnectAttempts, reconnectDelayMs]);

    const disconnect = useCallback(() => {
        shouldReconnect.current = false;
        if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
            reconnectTimeoutRef.current = null;
        }
        if (connectionTimeoutRef.current) {
            clearTimeout(connectionTimeoutRef.current);
            connectionTimeoutRef.current = null;
        }
        if (wsRef.current) {
            if (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING) {
                wsRef.current.close();
            }
            wsRef.current = null;
        }
        pendingRequests.current.clear();
        setIsConnected(false);
        setIsConnecting(false);
    }, []);

    const reconnect = useCallback(() => {
        disconnect();
        shouldReconnect.current = true;
        reconnectAttempts.current = 0;
        setError(null);
        connect();
    }, [connect, disconnect]);

    // Handle profile changes
    useEffect(() => {
        // Short-circuit if profile hasn't actually changed
        if (currentProfileRef.current?.name === profile?.name) {
            return;
        }

        const isRemote = isRemoteProfile(profile);
        currentProfileRef.current = profile;

        // Always disconnect first when profile changes
        disconnect();

        if (isRemote) {
            // Connect to new remote profile
            shouldReconnect.current = true;
            reconnectAttempts.current = 0;
            setHomeDir(null);
            setError(null);
            connect();
        } else {
            // Already disconnected above
            setHomeDir(null);
            setError(null);
        }

        return () => {
            disconnect();
        };
    }, [profile, connect, disconnect]);

    const value = {
        // State
        isConnected,
        isConnecting,
        error,
        homeDir,

        // Methods
        listDir,
        reconnect,
        disconnect,
    };

    return (
        <RemoteFileSystemContext.Provider value={value}>
            {children}
        </RemoteFileSystemContext.Provider>
    );
}

RemoteFileSystemProvider.propTypes = {
    children: PropTypes.node,
};

/**
 * Hook to access the remote file system context.
 */
function useRemoteFileSystem() {
    const context = useContext(RemoteFileSystemContext);
    if (!context) {
        throw new Error("useRemoteFileSystem must be used within RemoteFileSystemProvider");
    }
    return context;
}

export { RemoteFileSystemContext, RemoteFileSystemProvider, useRemoteFileSystem };
