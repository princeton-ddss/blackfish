/**
 * Centralized browser storage keys for the Blackfish frontend.
 *
 * All keys use a `bf:` prefix with topic sub-namespaces (e.g.
 * `bf:tg:chat:messages`) so they don't collide with other apps sharing the
 * origin during development and are self-documenting in devtools. New
 * persisted state should add a key here rather than inlining a string.
 */
export const STORAGE_KEYS = {
  // localStorage
  PROFILE: "bf:profile",
  THEME: "bf:theme",

  // sessionStorage (text-generation)
  TG_CHAT_SYSTEM_MESSAGE: "bf:tg:chat:systemMessage",
  TG_CHAT_USER_MESSAGE: "bf:tg:chat:userMessage",
  TG_CHAT_MESSAGES: "bf:tg:chat:messages",
  TG_COMPLETION_INPUT: "bf:tg:completion:input",
  TG_COMPLETION_OUTPUT: "bf:tg:completion:output",
};

/**
 * One-time mapping from the legacy (un-prefixed) keys to their `bf:`-prefixed
 * replacements. Used by {@link migrateStorageKeys} on app boot.
 */
const LEGACY_KEY_MIGRATIONS = [
  { area: "local", from: "profileName", to: STORAGE_KEYS.PROFILE },
  { area: "local", from: "theme", to: STORAGE_KEYS.THEME },
  { area: "session", from: "tgcc-sm", to: STORAGE_KEYS.TG_CHAT_SYSTEM_MESSAGE },
  { area: "session", from: "tgcc-um", to: STORAGE_KEYS.TG_CHAT_USER_MESSAGE },
  { area: "session", from: "tgcc-ml", to: STORAGE_KEYS.TG_CHAT_MESSAGES },
  { area: "session", from: "tgci", to: STORAGE_KEYS.TG_COMPLETION_INPUT },
  { area: "session", from: "tgco", to: STORAGE_KEYS.TG_COMPLETION_OUTPUT },
];

/**
 * Migrate any legacy storage keys to their `bf:`-prefixed equivalents.
 *
 * For each legacy key, the value is copied to the new key (only if the new key
 * isn't already set, so a re-run never clobbers fresh data) and the legacy key
 * is removed. Safe to call multiple times and a no-op once migration is done.
 */
export function migrateStorageKeys() {
  if (typeof window === "undefined") return;

  for (const { area, from, to } of LEGACY_KEY_MIGRATIONS) {
    const store = area === "local" ? window.localStorage : window.sessionStorage;
    try {
      const oldValue = store.getItem(from);
      if (oldValue === null) continue;
      if (store.getItem(to) === null) {
        store.setItem(to, oldValue);
      }
      store.removeItem(from);
    } catch (error) {
      console.error(`Failed to migrate storage key "${from}" -> "${to}"`, error);
    }
  }
}
