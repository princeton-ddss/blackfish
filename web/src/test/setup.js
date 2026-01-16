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
