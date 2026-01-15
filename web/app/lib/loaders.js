import useSWR from "swr";
import { fetchModels, fetchServices, fetchProfiles, fetchFiles } from "./requests";
import { ServiceStatus } from "./util";


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

export const useFileSystem = (path) => {
  const { data, error, isLoading, mutate } = useSWR(path ? `files?path=${path}` : null, fetchFiles);
  return {
    files: data,
    error: error,
    isLoading: isLoading,
    refresh: mutate,
  }
}
