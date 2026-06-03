import { describe, expect, it, beforeEach } from "vitest";
import { STORAGE_KEYS, migrateStorageKeys } from "@/lib/storage";

// Map-backed storage so get/set/remove round-trip in tests (the global
// sessionStorage mock from setup.js is a no-op).
const createStorageMock = () => {
  const store = new Map();
  return {
    getItem: (key) => (store.has(key) ? store.get(key) : null),
    setItem: (key, value) => store.set(key, String(value)),
    removeItem: (key) => store.delete(key),
    clear: () => store.clear(),
  };
};

describe("migrateStorageKeys", () => {
  beforeEach(() => {
    Object.defineProperty(window, "localStorage", {
      value: createStorageMock(),
      writable: true,
    });
    Object.defineProperty(window, "sessionStorage", {
      value: createStorageMock(),
      writable: true,
    });
  });

  it("moves legacy localStorage keys to the bf: scheme", () => {
    localStorage.setItem("profileName", "my-profile");
    localStorage.setItem("theme", "dark");

    migrateStorageKeys();

    expect(localStorage.getItem(STORAGE_KEYS.PROFILE)).toBe("my-profile");
    expect(localStorage.getItem(STORAGE_KEYS.THEME)).toBe("dark");
    expect(localStorage.getItem("profileName")).toBeNull();
    expect(localStorage.getItem("theme")).toBeNull();
  });

  it("moves legacy sessionStorage keys to the bf: scheme", () => {
    sessionStorage.setItem("tgcc-sm", "system");
    sessionStorage.setItem("tgcc-um", "user");
    sessionStorage.setItem("tgcc-ml", "[]");
    sessionStorage.setItem("tgci", "in");
    sessionStorage.setItem("tgco", "out");

    migrateStorageKeys();

    expect(sessionStorage.getItem(STORAGE_KEYS.TG_CHAT_SYSTEM_MESSAGE)).toBe("system");
    expect(sessionStorage.getItem(STORAGE_KEYS.TG_CHAT_USER_MESSAGE)).toBe("user");
    expect(sessionStorage.getItem(STORAGE_KEYS.TG_CHAT_MESSAGES)).toBe("[]");
    expect(sessionStorage.getItem(STORAGE_KEYS.TG_COMPLETION_INPUT)).toBe("in");
    expect(sessionStorage.getItem(STORAGE_KEYS.TG_COMPLETION_OUTPUT)).toBe("out");

    expect(sessionStorage.getItem("tgcc-sm")).toBeNull();
    expect(sessionStorage.getItem("tgci")).toBeNull();
  });

  it("does not clobber an existing new-scheme value", () => {
    localStorage.setItem("theme", "light");
    localStorage.setItem(STORAGE_KEYS.THEME, "dark");

    migrateStorageKeys();

    // The already-migrated value wins; the legacy key is still cleaned up.
    expect(localStorage.getItem(STORAGE_KEYS.THEME)).toBe("dark");
    expect(localStorage.getItem("theme")).toBeNull();
  });

  it("is a no-op when there is nothing to migrate", () => {
    migrateStorageKeys();

    expect(localStorage.getItem(STORAGE_KEYS.PROFILE)).toBeNull();
    expect(sessionStorage.getItem(STORAGE_KEYS.TG_CHAT_MESSAGES)).toBeNull();
  });
});
