import '@testing-library/jest-dom';
import { vi } from 'vitest';

// Mock window.__BLACKFISH_CONFIG__ for tests
Object.defineProperty(window, '__BLACKFISH_CONFIG__', {
  value: {
    apiUrl: 'http://localhost:8000',
    basePath: '',
  },
  writable: true,
});

// Mock sessionStorage
const sessionStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
};
Object.defineProperty(window, 'sessionStorage', {
  value: sessionStorageMock,
});

// Mock localStorage with an in-memory store so get/set/clear round-trip works.
// happy-dom's default localStorage doesn't reliably expose `clear` as a
// callable method across versions, so we install a simple Map-backed replacement.
const createStorageMock = () => {
  const store = new Map();
  return {
    getItem: (key) => (store.has(key) ? store.get(key) : null),
    setItem: (key, value) => {
      store.set(key, String(value));
    },
    removeItem: (key) => {
      store.delete(key);
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
Object.defineProperty(window, 'localStorage', {
  value: createStorageMock(),
  writable: true,
});
