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
  const res = await fetch(`${blackfishApiURL}/api/${path}&refresh=true`);
  if (!res.ok) {
    console.debug(`from fetchModels: failed to fetch models (status=${res.status})`);
    const error = new Error("Failed to fetch models.");
    error.status = res.status;
    throw error;
  }
  const data = await res.json();
  return data.map(model => {
    return {
      repo_id: model.repo,
      revision: model.revision,
      profile: model.profile,
      image: model.image,
      model_dir: model.model_dir,
    }
  })
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

/** Create a new profile. */
export async function createProfile(profile) {
  const res = await fetch(`${blackfishApiURL}/api/profiles`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(profile),
  });
  if (!res.ok) {
    let message = "Failed to create profile.";
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

/** Update an existing profile. */
export async function updateProfile(name, data) {
  const res = await fetch(`${blackfishApiURL}/api/profiles/${encodeURIComponent(name)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    let message = "Failed to update profile.";
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

/** Delete a profile. */
export async function deleteProfile(name) {
  const res = await fetch(`${blackfishApiURL}/api/profiles/${encodeURIComponent(name)}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    let message = "Failed to delete profile.";
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

/** Fetch recommended tier for a model. */
export async function fetchModelTier(modelId, profileName, partition = null) {
  const params = new URLSearchParams({ profile: profileName });
  if (partition) {
    params.append("partition", partition);
  }
  const res = await fetch(`${blackfishApiURL}/api/models/${modelId}/tier?${params}`);
  if (!res.ok) {
    console.debug(`from fetchModelTier: failed to fetch tier (status=${res.status})`);
    return null;
  }
  return res.json();
}

/** Fetch app info/config. */
export async function fetchAppInfo() {
  const res = await fetch(`${blackfishApiURL}/api/info`);
  if (!res.ok) {
    console.debug(`from fetchAppInfo: failed to fetch info (status=${res.status})`);
    return null;
  }
  return res.json();
}

/** Fetch Hugging Face token status. */
export async function fetchHfTokenStatus() {
  const res = await fetch(`${blackfishApiURL}/api/settings/hf_token`);
  if (!res.ok) {
    console.debug(`from fetchHfTokenStatus: failed to fetch status (status=${res.status})`);
    return { configured: false };
  }
  return res.json();
}

/** Set Hugging Face token. */
export async function setHfToken(token) {
  const res = await fetch(`${blackfishApiURL}/api/settings/hf_token`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token }),
  });
  if (!res.ok) {
    let message = "Failed to set token.";
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

/** Delete Hugging Face token. */
export async function deleteHfToken() {
  const res = await fetch(`${blackfishApiURL}/api/settings/hf_token`, {
    method: "DELETE",
  });
  if (!res.ok) {
    let message = "Failed to delete token.";
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
