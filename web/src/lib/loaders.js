import { useState, useEffect, useCallback } from "react";
import useSWR from "swr";
import { fetchModels, fetchServices, fetchProfiles, fetchFiles, fetchClusterStatus } from "./requests";
import { ServiceStatus } from "./util";
import { useRemoteFileSystem } from "@/providers/RemoteFileSystemProvider";


export const useModels = (profile, image) => {
  const { data, error, isLoading } = useSWR(`models?profile=${profile ? profile.name : "default"}&image=${image}`, fetchModels);
  return {
    models: data,
    error: error,
    isLoading: isLoading,
  };
};

export const useServices = (profile, image) => {
  const { data, error, isLoading, mutate } = useSWR(() => {
    if (profile) {
      return `services?refresh=true&profile=${profile ? profile.name : null}&image=${image.replace('-', '_')}`
    }
    return false // do not run without profile
  },
  fetchServices,
  {
    refreshInterval: 30_000,
  });

  const statusOrder = [
    ServiceStatus.HEALTHY,
    ServiceStatus.STARTING,
    ServiceStatus.PENDING,
    ServiceStatus.SUBMITTED,
    ServiceStatus.STOPPED,
    ServiceStatus.EXPIRED,
    ServiceStatus.TIMEOUT,
    ServiceStatus.FAILED,
  ];

  const sortedData = data
  ? [...data].sort((a, b) => {
      const statusComparison = statusOrder.indexOf(a.status) - statusOrder.indexOf(b.status);
      if (statusComparison !== 0) {
          return statusComparison;
      }
      return new Date(b.created_at) - new Date(a.created_at);
  })
  : [];

  return {
    services: sortedData,
    error: error,
    isLoading: isLoading,
    mutate: mutate,
  };
};

export const useProfiles = () => {
  const { data, error, isLoading, mutate } = useSWR("profiles", fetchProfiles);
  return {
    profiles: data,
    error: error,
    isLoading: isLoading,
    mutate: mutate,
  };
};

export const useFileSystem = (path, profile = null) => {
  // Determine if this is a remote profile
  const isRemote = profile && profile.schema !== "local";

  // Get remote file system from context
  const remoteFs = useRemoteFileSystem();

  // Local state for remote file listings
  const [remoteFiles, setRemoteFiles] = useState(null);
  const [remoteError, setRemoteError] = useState(null);
  const [remoteLoading, setRemoteLoading] = useState(false);

  // Clear state when profile changes
  useEffect(() => {
    setRemoteFiles(null);
    setRemoteError(null);
    setRemoteLoading(false);
  }, [profile?.name]);

  // Also clear when connection drops
  useEffect(() => {
    if (!isRemote || !remoteFs.isConnected) {
      setRemoteFiles(null);
      setRemoteError(null);
      setRemoteLoading(false);
    }
  }, [isRemote, remoteFs.isConnected]);

  // Fetch remote directory when path or connection changes
  const { isConnected, listDir } = remoteFs;
  useEffect(() => {
    if (!isRemote || !isConnected || path === null) {
      return;
    }

    setRemoteLoading(true);
    setRemoteError(null);

    listDir(path)
      .then((entries) => {
        setRemoteFiles(entries);
        setRemoteError(null);
      })
      .catch((err) => {
        setRemoteError(err);
        setRemoteFiles(null);
      })
      .finally(() => {
        setRemoteLoading(false);
      });
  }, [isRemote, path, isConnected, listDir]);

  // Refresh function for remote
  const refreshRemote = useCallback(() => {
    if (!isRemote || !isConnected || path === null) {
      return Promise.resolve(null);
    }

    setRemoteLoading(true);
    return listDir(path)
      .then((entries) => {
        setRemoteFiles(entries);
        setRemoteError(null);
        return entries;
      })
      .catch((err) => {
        setRemoteError(err);
        throw err;
      })
      .finally(() => {
        setRemoteLoading(false);
      });
  }, [isRemote, path, isConnected, listDir]);

  // SWR hook for local profiles (only runs when not remote)
  // Uses ~ as default to fetch home directory when path is null
  const localKey = !isRemote ? `files?path=${path ?? "~"}` : null;
  const localFs = useSWR(localKey, fetchFiles);

  // Return appropriate source based on profile type
  if (isRemote) {
    return {
      files: remoteFiles,
      error: remoteError || remoteFs.error,
      isLoading: remoteLoading || remoteFs.isConnecting,
      refresh: refreshRemote,
      isConnected: remoteFs.isConnected,
      homeDir: remoteFs.homeDir,
    };
  }

  return {
    files: localFs.data?.files ?? null,
    error: localFs.error,
    isLoading: localFs.isLoading,
    refresh: localFs.mutate,
    isConnected: true, // Local is always "connected"
    homeDir: localFs.data?.path ?? null,
  };
}

export const useClusterStatus = (profile) => {
  // Only fetch for Slurm profiles
  const key = profile?.schema === "slurm" ? `cluster/${profile.name}` : null;
  const { data, error, isLoading, isValidating, mutate } = useSWR(
    key,
    () => fetchClusterStatus(profile.name),
    {
      refreshInterval: 300_000, // refresh every 5 minutes
      revalidateOnFocus: false,
    }
  );
  return {
    status: data,
    error: error,
    isLoading: isLoading,
    isRefreshing: isValidating,
    refresh: mutate,
  };
};
