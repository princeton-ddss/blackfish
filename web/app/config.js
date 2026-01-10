export const basePath =
    (typeof window !== 'undefined' && window.__BLACKFISH_CONFIG__?.basePath) ||
    process.env.NEXT_PUBLIC_BASE_PATH ||
    "";

export const blackfishApiURL =
    (typeof window !== 'undefined' && window.__BLACKFISH_CONFIG__?.apiUrl) ||
    process.env.NEXT_PUBLIC_BLACKFISH_URL ||
    "http://localhost:8000";
