import { render, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { test, expect, vi } from "vitest";
import FileManagerTable from "@/components/FileManagerTable";

const FILES_PER_PAGE = 10;

function makeFiles(n, dir = "/root") {
  return Array.from({ length: n }, (_, i) => ({
    name: `file ${i}`,
    is_dir: false,
    path: `${dir}/file_${i}.txt`,
    size: 64,
    modified_at: "2025-06-19T14:16:50",
  }));
}

function renderTable(props = {}) {
  return render(
    <FileManagerTable
      content={makeFiles(30)}
      path="/root"
      root="/root"
      filesPerPage={FILES_PER_PAGE}
      query=""
      setPath={vi.fn()}
      isLoading={false}
      error={null}
      refresh={vi.fn()}
      status={{ disabled: false }}
      {...props}
    />
  );
}

test("resets to the first page when the directory changes", async () => {
  const user = userEvent.setup();
  const { getByText, queryByText, rerender } = renderTable();

  // 30 files / 10 per page -> 3 pages. Navigate to page 3.
  await act(async () => {
    await user.click(getByText("3"));
  });
  expect(getByText("file 20")).toBeInTheDocument();

  // Navigating to a new directory with fewer files should reset to page 1
  // rather than leaving an out-of-range page.
  await act(async () => {
    rerender(
      <FileManagerTable
        content={makeFiles(5, "/root/sub")}
        path="/root/sub"
        root="/root"
        filesPerPage={FILES_PER_PAGE}
        query=""
        setPath={vi.fn()}
        isLoading={false}
        error={null}
        refresh={vi.fn()}
        status={{ disabled: false }}
      />
    );
  });

  expect(getByText("file 0")).toBeInTheDocument();
  expect(queryByText("3")).not.toBeInTheDocument();
});

test("resets to the first page when the filter changes", async () => {
  const user = userEvent.setup();
  const { getByText, queryByText, rerender } = renderTable();

  await act(async () => {
    await user.click(getByText("3"));
  });
  expect(getByText("file 20")).toBeInTheDocument();

  await act(async () => {
    rerender(
      <FileManagerTable
        content={makeFiles(30)}
        path="/root"
        root="/root"
        filesPerPage={FILES_PER_PAGE}
        query="file 1"
        setPath={vi.fn()}
        isLoading={false}
        error={null}
        refresh={vi.fn()}
        status={{ disabled: false }}
      />
    );
  });

  // "file 1" matches file 1 and file 10-19 -> 11 results, 2 pages, page 1.
  expect(getByText("file 1")).toBeInTheDocument();
  expect(queryByText("3")).not.toBeInTheDocument();
});

test("falls back to a valid page when the content shrinks in place", async () => {
  const user = userEvent.setup();
  const { getByText, queryByText, rerender } = renderTable();

  // 30 files / 10 per page -> 3 pages. Navigate to page 3.
  await act(async () => {
    await user.click(getByText("3"));
  });
  expect(getByText("file 20")).toBeInTheDocument();

  // Deleting the files on the last page shrinks `content` without changing
  // `path` or `query`, so the reset effect doesn't fire. The visible page
  // should still fall back to the new last page rather than render blank.
  await act(async () => {
    rerender(
      <FileManagerTable
        content={makeFiles(20)}
        path="/root"
        root="/root"
        filesPerPage={FILES_PER_PAGE}
        query=""
        setPath={vi.fn()}
        isLoading={false}
        error={null}
        refresh={vi.fn()}
        status={{ disabled: false }}
      />
    );
  });

  expect(getByText("file 10")).toBeInTheDocument();
  expect(getByText("file 19")).toBeInTheDocument();
  expect(queryByText("3")).not.toBeInTheDocument();
});

test("does not jump back to a stale page when the content grows again", async () => {
  const user = userEvent.setup();
  const { getByText, rerender } = renderTable();

  // Page 3 of 30 files, then a delete drops the list to 2 pages.
  await act(async () => {
    await user.click(getByText("3"));
  });
  await act(async () => {
    rerender(
      <FileManagerTable
        content={makeFiles(20)}
        path="/root"
        root="/root"
        filesPerPage={FILES_PER_PAGE}
        query=""
        setPath={vi.fn()}
        isLoading={false}
        error={null}
        refresh={vi.fn()}
        status={{ disabled: false }}
      />
    );
  });
  expect(getByText("file 10")).toBeInTheDocument();

  // An upload (or a refresh that restores rows) brings page 3 back. The user
  // should stay on the page they're looking at rather than being moved to the
  // page they were clamped off of.
  await act(async () => {
    rerender(
      <FileManagerTable
        content={makeFiles(30)}
        path="/root"
        root="/root"
        filesPerPage={FILES_PER_PAGE}
        query=""
        setPath={vi.fn()}
        isLoading={false}
        error={null}
        refresh={vi.fn()}
        status={{ disabled: false }}
      />
    );
  });

  expect(getByText("file 10")).toBeInTheDocument();
  expect(getByText("file 19")).toBeInTheDocument();
});
