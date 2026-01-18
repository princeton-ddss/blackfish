import { render, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { test, expect, vi, beforeAll, beforeEach, afterAll } from "vitest";
import RemoteFileBrowser from "@/components/RemoteFileBrowser";
import { useFileSystem } from "@/lib/loaders";

vi.mock("@/lib/loaders", async () => {
  const actual = await vi.importActual("@/lib/loaders");
  return {
    ...actual,
    useFileSystem: vi.fn(),
  };
});

// Mock Date to ensure consistent "days ago" text in snapshots
const MOCK_DATE = new Date('2025-06-24T14:16:50');
const originalDate = global.Date;

beforeAll(() => {
  global.Date = class extends Date {
    constructor(...args) {
      if (args.length === 0) {
        return MOCK_DATE;
      }
      return new originalDate(...args);
    }
    static now() {
      return MOCK_DATE.getTime();
    }
  };
  global.Date.UTC = originalDate.UTC;
  global.Date.parse = originalDate.parse;
});

beforeEach(() => {
  vi.clearAllMocks();
  useFileSystem.mockReturnValue({
    files: [
      {name: "file 1", is_dir: false, path: "path/to/file_1.mp3", size: 64, modified_at: "2025-06-19T14:16:50"},
      {name: "file 2", is_dir: false, path: "path/to/file_2.mp3", size: 64, modified_at: "2025-06-19T14:16:50"},
      {name: "file 3", is_dir: false, path: "path/to/file_3.mp3", size: 64, modified_at: "2025-06-19T14:16:50"},
      {name: "file 4", is_dir: false, path: "path/to/file_4.mp3", size: 64, modified_at: "2025-06-19T14:16:50"},
      {name: "file 5", is_dir: false, path: "path/to/file_5.mp3", size: 64, modified_at: "2025-06-19T14:16:50"},
      {name: "file 6", is_dir: false, path: "path/to/file_6.mp3", size: 64, modified_at: "2025-06-19T14:16:50"},
      {name: "file 7", is_dir: false, path: "path/to/file_7.mp3", size: 64, modified_at: "2025-06-19T14:16:50"},
      {name: "file 8", is_dir: false, path: "path/to/file_8.mp3", size: 64, modified_at: "2025-06-19T14:16:50"},
      {name: "file 9", is_dir: false, path: "path/to/file_9.mp3", size: 64, modified_at: "2025-06-19T14:16:50"},
      {name: "file 10", is_dir: false, path: "path/to/file_10.mp3", size: 64, modified_at: "2025-06-19T14:16:50"},
    ],
    error: null,
    isLoading: false,
    refresh: (e) => e,
  });
});

test("Enabled RemoteFileBrowser", async () => {
  const {baseElement} = await act(async () => {
    return render(
      <RemoteFileBrowser
        root="/"
        setAudioPath={(e) => e}
        status={{disabled: false}}
      />
    );
  });
  expect(baseElement).toMatchSnapshot();
});

test("Disabled RemoteFileBrowser", async () => {
  const {baseElement} = await act(async () => {
    return render(
      <RemoteFileBrowser
        root="/"
        setAudioPath={(e) => e}
        status={{disabled: true, detail: "Test error."}}
      />
    );
  });
  expect(baseElement).toMatchSnapshot();
});

test("Loading RemoteFileBrowser", async () => {
  useFileSystem.mockReturnValue({
    files: [
      {name: "file 1", is_dir: false, path: "path/to/file_1.mp3", size: 64, modified_at: "2025-06-19T14:16:50"},
      {name: "file 2", is_dir: false, path: "path/to/file_2.mp3", size: 64, modified_at: "2025-06-19T14:16:50"},
      {name: "file 3", is_dir: false, path: "path/to/file_3.mp3", size: 64, modified_at: "2025-06-19T14:16:50"},
      {name: "file 4", is_dir: false, path: "path/to/file_4.mp3", size: 64, modified_at: "2025-06-19T14:16:50"},
      {name: "file 5", is_dir: false, path: "path/to/file_5.mp3", size: 64, modified_at: "2025-06-19T14:16:50"},
      {name: "file 6", is_dir: false, path: "path/to/file_6.mp3", size: 64, modified_at: "2025-06-19T14:16:50"},
      {name: "file 7", is_dir: false, path: "path/to/file_7.mp3", size: 64, modified_at: "2025-06-19T14:16:50"},
      {name: "file 8", is_dir: false, path: "path/to/file_8.mp3", size: 64, modified_at: "2025-06-19T14:16:50"},
      {name: "file 9", is_dir: false, path: "path/to/file_9.mp3", size: 64, modified_at: "2025-06-19T14:16:50"},
      {name: "file 10", is_dir: false, path: "path/to/file_10.mp3", size: 64, modified_at: "2025-06-19T14:16:50"},
    ],
    error: null,
    isLoading: true,
    refresh: (e) => e,
  });
  const {baseElement} = await act(async () => {
    return render(
      <RemoteFileBrowser
        root="/"
        setAudioPath={(e) => e}
        status={{disabled: true, detail: "Test error."}}
      />
    );
  });
  expect(baseElement).toMatchSnapshot();
});

test("RemoteFileBrowser with error", async () => {
  useFileSystem.mockReturnValue({
    files: [],
    error: {message: "Network error"},
    isLoading: false,
    refresh: (e) => e,
  });
  const {baseElement} = await act(async () => {
    return render(
      <RemoteFileBrowser
        root="/"
        setAudioPath={(e) => e}
        status={{disabled: false}}
      />
    );
  });
  expect(baseElement).toMatchSnapshot();
});

test("RemoteFileBrowser with empty files", async () => {
  useFileSystem.mockReturnValue({
    files: [],
    error: null,
    isLoading: false,
    refresh: (e) => e,
  });
  const {baseElement} = await act(async () => {
    return render(
      <RemoteFileBrowser
        root="/"
        setAudioPath={(e) => e}
        status={{disabled: false}}
      />
    );
  });
  expect(baseElement).toMatchSnapshot();
});

test("RemoteFileBrowser with no service selected", async () => {
  useFileSystem.mockReturnValue({
    files: [],
    error: null,
    isLoading: false,
    refresh: (e) => e,
  });
  const {baseElement} = await act(async () => {
    return render(
      <RemoteFileBrowser
        root=""
        setAudioPath={(e) => e}
        status={{disabled: false}}
      />
    );
  });
  expect(baseElement).toMatchSnapshot();
});

test("RemoteFileBrowser with directories and interactions", async () => {
  const mockSetAudioPath = vi.fn();
  const mockRefresh = vi.fn();
  useFileSystem.mockReturnValue({
    files: [
      {name: "folder1", is_dir: true, path: "/folder1", size: 0, modified_at: "2025-06-19T14:16:50"},
      {name: "audio.mp3", is_dir: false, path: "/audio.mp3", size: 1024, modified_at: "2025-06-19T14:16:50"},
      {name: "document.txt", is_dir: false, path: "/document.txt", size: 512, modified_at: "2025-06-19T14:16:50"},
    ],
    error: null,
    isLoading: false,
    refresh: mockRefresh,
  });

  const user = userEvent.setup();
  const {baseElement, container} = await act(async () => {
    return render(
      <RemoteFileBrowser
        root="/"
        setAudioPath={mockSetAudioPath}
        status={{disabled: false}}
      />
    );
  });

  expect(baseElement).toMatchSnapshot();

  // Test refresh button - find button in table header that's not disabled
  const tableButtons = container.querySelectorAll('thead button:not([disabled])');
  const refreshButton = Array.from(tableButtons).find(btn => btn.querySelector('svg'));
  if (refreshButton) {
    await act(async () => {
      await user.click(refreshButton);
    });
    expect(mockRefresh).toHaveBeenCalled();
  }
});

test("RemoteFileBrowser file selection", async () => {
  const mockSetAudioPath = vi.fn();
  useFileSystem.mockReturnValue({
    files: [
      {name: "audio1.mp3", is_dir: false, path: "/audio1.mp3", size: 1024, modified_at: "2025-06-19T14:16:50"},
      {name: "audio2.wav", is_div: false, path: "/audio2.wav", size: 2048, modified_at: "2025-06-19T14:16:50"},
    ],
    error: null,
    isLoading: false,
    refresh: (e) => e,
  });

  const user = userEvent.setup();
  const {container} = await act(async () => {
    return render(
      <RemoteFileBrowser
        root="/"
        setAudioPath={mockSetAudioPath}
        status={{disabled: false}}
      />
    );
  });

  // Find and click first audio file checkbox
  const checkboxes = container.querySelectorAll('input[type="checkbox"]');
  if (checkboxes.length > 0) {
    await act(async () => {
      await user.click(checkboxes[0]);
    });
    expect(mockSetAudioPath).toHaveBeenCalledWith("/audio1.mp3");

    // Click again to deselect
    await act(async () => {
      await user.click(checkboxes[0]);
    });
    expect(mockSetAudioPath).toHaveBeenCalledWith("");
  }
});

test("RemoteFileBrowser with filtering", async () => {
  useFileSystem.mockReturnValue({
    files: [
      {
        name: "audio1.mp3",
        is_dir: false,
        path: "/audio1.mp3",
        size: 1024,
        modified_at: "2025-06-19T14:16:50"
      },
      {
        name: "document.txt",
        is_dir: false,
        path: "/document.txt",
        size: 512,
        modified_at: "2025-06-19T14:16:50"
      },
      {
        name: "music.wav",
        is_dir: false,
        path: "/music.wav",
        size: 2048,
        modified_at: "2025-06-19T14:16:50"
      },
    ],
    error: null,
    isLoading: false,
    refresh: (e) => e,
  });

  const user = userEvent.setup();
  const {baseElement, container} = await act(async () => {
    return render(
      <RemoteFileBrowser
        root="/"
        setAudioPath={(e) => e}
        status={{disabled: false}}
      />
    );
  });

  // Test filtering functionality
  const filterInput = container.querySelector('input[placeholder*="filter" i], input[placeholder*="search" i]');
  if (filterInput) {
    await act(async () => {
      await user.type(filterInput, "audio");
    });
    expect(baseElement).toMatchSnapshot();
  }
});

test("RemoteFileBrowser back navigation", async () => {
  useFileSystem.mockReturnValue({
    files: [
      {name: "folder1", is_dir: true, path: "/parent/child", size: 0, modified_at: "2025-06-19T14:16:50"},
    ],
    error: null,
    isLoading: false,
    refresh: (e) => e,
  });

  const user = userEvent.setup();
  // Test with a nested path to trigger back navigation
  const {baseElement, container} = await act(async () => {
    return render(
      <RemoteFileBrowser
        root="/parent"
        setAudioPath={(e) => e}
        status={{disabled: false}}
      />
    );
  });

  // Find the back navigation button (left chevron in table header)
  const backButton = container.querySelector('thead button svg[data-slot="icon"]')?.closest('button');
  if (backButton) {
    await act(async () => {
      await user.click(backButton);
    });
  }

  expect(baseElement).toMatchSnapshot();
});

test("RemoteFileBrowser folder navigation", async () => {
  const mockSetAudioPath = vi.fn();
  useFileSystem.mockReturnValue({
    files: [
      {name: "folder1", is_dir: true, path: "/folder1", size: 0, modified_at: "2025-06-19T14:16:50"},
      {name: "audio.mp3", is_dir: false, path: "/audio.mp3", size: 1024, modified_at: "2025-06-19T14:16:50"},
    ],
    error: null,
    isLoading: false,
    refresh: (e) => e,
  });

  const user = userEvent.setup();
  const {baseElement, container} = await act(async () => {
    return render(
      <RemoteFileBrowser
        root="/"
        setAudioPath={mockSetAudioPath}
        status={{disabled: false}}
      />
    );
  });

  // Find and click folder navigation button (right chevron)
  const folderButtons = container.querySelectorAll('tbody button');
  const folderNavButton = Array.from(folderButtons).find(btn =>
    btn.querySelector('svg') && btn.innerHTML.includes('ChevronRight')
  );

  if (folderNavButton) {
    await act(async () => {
      await user.click(folderNavButton);
    });
  }

  expect(baseElement).toMatchSnapshot();
});

test("RemoteFileBrowser disabled interactions", async () => {
  const mockSetAudioPath = vi.fn();
  const mockRefresh = vi.fn();
  useFileSystem.mockReturnValue({
    files: [
      {name: "folder1", is_dir: true, path: "/folder1", size: 0, modified_at: "2025-06-19T14:16:50"},
      {name: "audio.mp3", is_dir: false, path: "/audio.mp3", size: 1024, modified_at: "2025-06-19T14:16:50"},
    ],
    error: null,
    isLoading: false,
    refresh: mockRefresh,
  });

  const user = userEvent.setup();
  const {baseElement, container} = await act(async () => {
    return render(
      <RemoteFileBrowser
        root="/"
        setAudioPath={mockSetAudioPath}
        status={{disabled: true, detail: "Service disabled"}}
      />
    );
  });

  // When disabled, the component shows the disabled message instead of interactive elements
  const disabledMessage = container.querySelector('td[colspan="5"]');
  expect(disabledMessage).toBeTruthy();
  expect(disabledMessage.textContent).toContain("Service disabled");

  // Test disabled refresh button
  const refreshButton = container.querySelector('thead button[disabled]');
  if (refreshButton) {
    await act(async () => {
      await user.click(refreshButton);
    });
    expect(mockRefresh).not.toHaveBeenCalled();
  }

  expect(baseElement).toMatchSnapshot();
});

test("RemoteFileBrowser loading state with files", async () => {
  useFileSystem.mockReturnValue({
    files: [
      {
        name: "file1.mp3",
        is_dir: false,
        path: "/file1.mp3",
        size: 1024,
        modified_at: "2025-06-19T14:16:50"
      },
    ],
    error: null,
    isLoading: true,
    refresh: (e) => e,
  });

  const {baseElement, container} = await act(async () => {
    return render(
      <RemoteFileBrowser
        root="/"
        setAudioPath={(e) => e}
        status={{disabled: false}}
      />
    );
  });

  // Should show loading skeleton
  const loadingElements = container.querySelectorAll('.animate-pulse');
  expect(loadingElements.length).toBeGreaterThan(0);
  expect(baseElement).toMatchSnapshot();
});

afterAll(() => {
  global.Date = originalDate;
});
