import { blackfishApiURL } from "../config";

/* Return a list of local files with resolved path */
export async function fetchFiles(path) {
  const res = await fetch(`${blackfishApiURL}/api/${path}`)
  if (!res.ok) {
    console.debug(`from fetchFiles: failed to fetch files (status=${res.status})`);
    const error = new Error("Failed to fetch files.")
    error.status = res.status
    throw error
  }
  return res.json();
}

/** Return a list of available models. */
export async function fetchModels(path) {
  const res = await fetch(`${blackfishApiURL}/api/${path}`);
  if (!res.ok) {
    console.debug(`from fetchModels: failed to fetch models (status=${res.status})`);
    const error = new Error("Failed to fetch models.");
    error.status = res.status;
    throw error;
  }
  const data = await res.json();
  return data.map((model) => {
    return {
      id: model.id,
      repo_id: model.repo,
      revision: model.revision,
      profile: model.profile,
      image: model.image,
      model_dir: model.model_dir,
      created_at: model.created_at,
      model_size_gb: model.metadata_?.model_size_gb ?? null,
    };
  });
}

/** Return a list of blackfish services. */
export async function fetchServices(path) {
  const res = await fetch(`${blackfishApiURL}/api/${path}`);
  if (!res.ok) {
    console.debug(`from fetchServices: failed to fetch services (status=${res.status})`);
    const error = new Error("Failed to fetch services.");
    error.status = res.status;
    throw error;
  }
  return await res.json();
}

/** Return a list of all profiles. */
export async function fetchProfiles() {
  const res = await fetch(`${blackfishApiURL}/api/profiles`);
  if (!res.ok) {
    console.debug(`from fetchProfiles: failed to fetch profiles (status=${res.status})`);
    const error = new Error("Failed to fetch profiles.");
    error.status = res.status;
    throw error;
  }
  return await res.json();
}

/** Start an service to perform the specified ML/AI pipeline. */
export async function runService(pipeline, model, jobConfig, containerConfig, profile) {
  let body;
  if (profile.schema === "slurm") {
    body = {
      name: jobConfig.name,
      image: pipeline.replace("-", "_"),
      repo_id: model.repo_id,
      profile: profile,
      container_config: {
        ...containerConfig,
        revision: model.revision,
        model_dir: pipeline === "speech-recognition"
          ? dirname(model.model_dir)
          : model.model_dir,
        port: null,
      },
      job_config: jobConfig,
      mount: containerConfig.input_dir,
      grace_period: 180,
    }
  } else if (profile.schema === "local") {
    const res = await fetch(`${blackfishApiURL}/api/ports`)
    if (!res.ok) {
      const error = new Error("Unable to find available local port")
      error.status = res.status
      throw error
    }
    const port = await res.json();
    body = {
      name: jobConfig.name,
      image: pipeline.replace("-", "_"),
      repo_id: model.repo_id,
      profile: profile,
      container_config: {
        ...containerConfig,
        revision: model.revision,
        model_dir: pipeline === "speech-recognition"
          ? dirname(model.model_dir)
          : model.model_dir,
        port: port,
      },
      job_config: {
        gres: jobConfig.gres,
      },
      mount: containerConfig.input_dir,
      grace_period: 180,
    }
  } else {
    throw new Error(`Unsupported job profile type: ${profile.schema}`)
  }
  console.debug("from runService: body =", body)

  const res = await fetch(`${blackfishApiURL}/api/services`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });

  return res
}

function dirname(path) {
  const parts = path.split("/")
  const nparts = parts.length
  return parts.slice(0, nparts - 1).join("/")
}

/** Get details of the given service. */
export async function getServiceDetails(serviceId) {
  const res = await fetch(`${blackfishApiURL}/api/services/${serviceId}?refresh=true`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
    mode: "cors",
  });

  if (!res.ok) {
    // Activates the closest `error.js` Error Boundary
    throw new Error("Failed to get service details.");
  }

  return res.json()
}

/** Stop the given service. */
export async function stopService(serviceId) {
  const body = JSON.stringify({ delay: 0 });
  const res = await fetch(`${blackfishApiURL}/api/services/${serviceId}/stop`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    mode: "cors",
    body: body,
  });

  if (!res.ok) {
    // Activates the closest `error.js` Error Boundary
    throw new Error("Failed to stop the service");
  }

  return res.json()
}

/** Delete the given service. */
export async function deleteService(serviceId) {
  const body = JSON.stringify({ force: false });
  const res = await fetch(`${blackfishApiURL}/api/services/?id=${serviceId}`, {
    method: "DELETE",
    headers: {
      "Content-Type": "application/json",
    },
    mode: "cors",
    body: body,
  });

  if (!res.ok) {
    // Activates the closest `error.js` Error Boundary
    throw new Error("Failed to delete the service");
  }
}

/** Fetch cluster status for a Slurm profile. */
export async function fetchClusterStatus(profileName) {
  const res = await fetch(`${blackfishApiURL}/api/cluster/${profileName}/status`);
  if (!res.ok) {
    console.debug(`from fetchClusterStatus: failed to fetch cluster status (status=${res.status})`);
    // Try to parse error detail from response body
    let message = "Failed to fetch cluster status.";
    try {
      const body = await res.json();
      if (body.detail) {
        message = body.detail;
      }
    } catch {
      // Ignore JSON parse errors, use default message
    }
    const error = new Error(message);
    error.status = res.status;
    throw error;
  }
  return res.json();
}

/** Fetch resource tiers and time constraints for a profile. */
export async function fetchProfileResources(profileName) {
  const res = await fetch(`${blackfishApiURL}/api/profiles/${profileName}/resources`);
  if (!res.ok) {
    console.debug(`from fetchProfileResources: failed to fetch resources (status=${res.status})`);
    return null;
  }
  return res.json();
}

/** Fetch model size from HuggingFace Hub API.
 * @param {string} repoId - The model repo ID (e.g., "meta-llama/Llama-2-7b")
 * @returns {Promise<number|null>} Model size in GB, or null if unavailable
 */
/**
 * Search for models on HuggingFace Hub.
 * Returns array of { id, downloads, likes } or empty array on error.
 */
export async function searchHuggingFaceModels(query, limit = 10) {
  if (!query || query.length < 2) {
    return [];
  }
  try {
    const res = await fetch(
      `https://huggingface.co/api/models?search=${encodeURIComponent(query)}&limit=${limit}&sort=downloads&direction=-1`
    );
    if (!res.ok) {
      return [];
    }
    const data = await res.json();
    return data.map((m) => ({
      id: m.id,
      downloads: m.downloads,
      likes: m.likes,
      pipeline: m.pipeline_tag,
    }));
  } catch {
    return [];
  }
}

/**
 * Fetch model refs (branches/tags) from HuggingFace Hub.
 * Returns { branches: [{name, sha}], tags: [{name, sha}] } or error object.
 */
export async function fetchModelRefs(repoId) {
  if (!repoId || !repoId.includes("/")) {
    return null;
  }
  try {
    const res = await fetch(`https://huggingface.co/api/models/${repoId}/refs`);
    if (!res.ok) {
      if (res.status === 404) {
        return { error: "Model not found", notFound: true };
      }
      return { error: `Failed to fetch refs (${res.status})` };
    }
    const data = await res.json();
    return {
      branches: data.branches?.map((b) => ({ name: b.name, sha: b.targetCommit })) || [],
      tags: data.tags?.map((t) => ({ name: t.name, sha: t.targetCommit })) || [],
    };
  } catch {
    return { error: "Connection failed" };
  }
}

export async function fetchModelSizeFromHub(repoId) {
  console.debug(`[fetchModelSizeFromHub] Fetching size for ${repoId} from HuggingFace Hub`);
  try {
    const res = await fetch(`https://huggingface.co/api/models/${repoId}`);
    if (!res.ok) {
      console.debug(`[fetchModelSizeFromHub] Failed to fetch ${repoId} (status=${res.status})`);
      return null;
    }
    const data = await res.json();
    console.debug(`[fetchModelSizeFromHub] Received data for ${repoId}:`, {
      hasSafetensors: !!data.safetensors,
      safetensorsTotal: data.safetensors?.total,
      siblingsCount: data.siblings?.length,
    });

    let rawSizeGb = null;

    // 1. Try safetensors metadata (most accurate)
    if (data.safetensors?.total) {
      rawSizeGb = data.safetensors.total / (1024 * 1024 * 1024);
      console.debug(`[fetchModelSizeFromHub] ${repoId} raw size from safetensors: ${rawSizeGb.toFixed(2)} GB`);
    }
    // 2. Sum up model weight files from siblings listing
    else if (data.siblings?.length > 0) {
      const modelFiles = data.siblings.filter(f =>
        f.rfilename?.endsWith('.safetensors') ||
        f.rfilename?.endsWith('.bin') ||
        f.rfilename?.endsWith('.pt') ||
        f.rfilename?.endsWith('.pth')
      );
      if (modelFiles.length > 0) {
        const totalBytes = modelFiles.reduce((sum, f) => sum + (f.size || 0), 0);
        if (totalBytes > 0) {
          rawSizeGb = totalBytes / (1024 * 1024 * 1024);
          console.debug(`[fetchModelSizeFromHub] ${repoId} raw size from files (${modelFiles.length} files): ${rawSizeGb.toFixed(2)} GB`);
        }
      }
    }

    if (rawSizeGb !== null) {
      console.debug(`[fetchModelSizeFromHub] ${repoId} model size: ${rawSizeGb.toFixed(2)} GB`);
      return rawSizeGb;
    }

    console.debug(`[fetchModelSizeFromHub] No size data found for ${repoId}`);
    return null;
  } catch (err) {
    console.error(`[fetchModelSizeFromHub] Error fetching ${repoId}:`, err);
    return null;
  }
}

/** Delete a model by its database ID. */
export async function deleteModel(modelId) {
  const res = await fetch(`${blackfishApiURL}/api/models/${modelId}`, {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
  });

  if (!res.ok) {
    let message = "Failed to delete model";
    try {
      const body = await res.json();
      if (body.detail) message = body.detail;
    } catch {
      // Ignore JSON parse errors
    }
    const error = new Error(message);
    error.status = res.status;
    throw error;
  }
}

/** Initiate a model download from Hugging Face. */
export async function downloadModel({ repo_id, profile, revision = null, use_cache = false }) {
  const res = await fetch(`${blackfishApiURL}/api/models/download`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ repo_id, profile, revision, use_cache }),
  });

  if (!res.ok) {
    let message = "Failed to initiate download";
    try {
      const body = await res.json();
      if (body.detail) message = body.detail;
    } catch {
      // Ignore JSON parse errors
    }
    const error = new Error(message);
    error.status = res.status;
    throw error;
  }
  return res.json();
}

/** Get the status of a download task. */
export async function getDownloadStatus(taskId) {
  const res = await fetch(`${blackfishApiURL}/api/models/downloads/${taskId}`);
  if (!res.ok) {
    const error = new Error("Failed to get download status");
    error.status = res.status;
    throw error;
  }
  return res.json();
}

/** List download tasks, optionally filtered by status or profile. */
export async function listDownloads({ status = null, profile = null } = {}) {
  const params = new URLSearchParams();
  if (status) params.append("status", status);
  if (profile) params.append("profile", profile);

  const url = params.toString()
    ? `${blackfishApiURL}/api/models/downloads?${params}`
    : `${blackfishApiURL}/api/models/downloads`;

  const res = await fetch(url);
  if (!res.ok) {
    const error = new Error("Failed to list downloads");
    error.status = res.status;
    throw error;
  }
  return res.json();
}

/** Update a model (check for or download latest revision). */
export async function updateModel(modelId, { checkOnly = false } = {}) {
  const params = new URLSearchParams();
  if (checkOnly) params.append("check_only", "true");

  const res = await fetch(`${blackfishApiURL}/api/models/${modelId}?${params}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
  });

  if (!res.ok) {
    let message = "Failed to update model";
    try {
      const body = await res.json();
      if (body.detail) message = body.detail;
    } catch {
      // Ignore JSON parse errors
    }
    const error = new Error(message);
    error.status = res.status;
    throw error;
  }
  return res.json();
}