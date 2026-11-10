import '@testing-library/jest-dom';
import { beforeEach } from 'vitest';

// Mock window.__BLACKFISH_CONFIG__ for tests
Object.defineProperty(window, '__BLACKFISH_CONFIG__', {
  value: {
    apiUrl: 'http://localhost:8000',
    basePath: '',
  },
  writable: true,
});

// Use independent in-memory stores so get/set/clear round-trip works.
// happy-dom's default localStorage doesn't reliably expose `clear` as a
// callable method across versions, so we install a simple Map-backed replacement.
const createStorageMock = () => {
  const store = new Map();
  return {
    getItem: (key) => (store.has(String(key)) ? store.get(String(key)) : null),
    setItem: (key, value) => {
      store.set(String(key), String(value));
    },
    removeItem: (key) => {
      store.delete(String(key));
    },
    clear: () => {
      store.clear();
    },
    key: (index) => Array.from(store.keys())[index] ?? null,
    get length() {
      return store.size;
    },
  };
};
for (const area of ['localStorage', 'sessionStorage']) {
  Object.defineProperty(window, area, {
    value: createStorageMock(),
    writable: true,
    configurable: true,
  });
}

beforeEach(() => {
  localStorage.clear();
  sessionStorage.clear();
});
