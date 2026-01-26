import useSWR from "swr";
import { fetchModels, fetchServices, fetchProfiles, fetchFiles } from "./requests";
import { ServiceStatus } from "./util";
import { useRemoteFileSystem } from "../hooks/useRemoteFileSystem";


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

  // WebSocket hook for remote profiles
  const remoteFs = useRemoteFileSystem(
    isRemote ? path : null,
    isRemote ? profile : null
  );

  // SWR hook for local profiles (only runs when not remote)
  // Uses ~ as default to fetch home directory when path is null
  const localKey = !isRemote ? `files?path=${path ?? "~"}` : null;
  const localFs = useSWR(localKey, fetchFiles);

  // Return appropriate source based on profile type
  if (isRemote) {
    return {
      files: remoteFs.files,
      error: remoteFs.error,
      isLoading: remoteFs.isLoading,
      refresh: remoteFs.refresh,
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
