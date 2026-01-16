function getConfig() {
  const runtimeConfig =
    typeof window !== "undefined" ? window.__BLACKFISH_CONFIG__ : null;

  return {
    apiUrl:
      runtimeConfig?.apiUrl
        || import.meta.env.VITE_BLACKFISH_URL
        || "http://localhost:8000",
    basePath:
      runtimeConfig?.basePath 
        || import.meta.env.VITE_BLACKFISH_BASE_PATH
        || "",
  };
}

const config = getConfig();

export const blackfishApiURL = config.apiUrl;
export const basePath = config.basePath;


export function assetPath(path) {
    // Convert asset paths to relative paths, e.g., "/path" to "./path" and "path" to "./path"
    return path.startsWith('/') ? `.${path}` : `./${path}`;
}