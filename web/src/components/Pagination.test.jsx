import { render, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { test, expect, vi, describe } from "vitest";
import Pagination, { getPageItems } from "@/components/Pagination";

describe("getPageItems", () => {
  test("returns every page when the range is small", () => {
    expect(getPageItems(1, 5)).toEqual([1, 2, 3, 4, 5]);
    expect(getPageItems(3, 7)).toEqual([1, 2, 3, 4, 5, 6, 7]);
  });

  test("elides with a trailing ellipsis near the start", () => {
    // 20 pages, on page 2: 1 2 3 … 20
    expect(getPageItems(2, 20)).toEqual([1, 2, 3, "…", 20]);
  });

  test("elides with a leading ellipsis near the end", () => {
    // 20 pages, on page 19: 1 … 18 19 20
    expect(getPageItems(19, 20)).toEqual([1, "…", 18, 19, 20]);
  });

  test("elides on both sides in the middle", () => {
    // 20 pages, on page 10: 1 … 9 10 11 … 20
    expect(getPageItems(10, 20)).toEqual([1, "…", 9, 10, 11, "…", 20]);
  });

  test("never duplicates the first/last page as a sibling", () => {
    const items = getPageItems(3, 20);
    expect(items).toEqual([1, 2, 3, 4, "…", 20]);
    expect(items.filter((i) => i === 1)).toHaveLength(1);
    expect(items.filter((i) => i === 20)).toHaveLength(1);
  });

  test("returns empty for a single page or none", () => {
    expect(getPageItems(1, 1)).toEqual([]);
    expect(getPageItems(1, 0)).toEqual([]);
  });
});

test("renders nothing for a single page", () => {
  // totalFiles (5) <= filesPerPage (20) -> one page -> no controls at all.
  const { container } = render(
    <Pagination
      filesPerPage={20}
      totalFiles={5}
      currentPage={1}
      setCurrentPage={(e) => e}
    />
  );
  expect(container).toBeEmptyDOMElement();
});

test("Enabled Pagination", async () => {
  const user = userEvent.setup();
  const {baseElement, getAllByRole} = render(
    <Pagination
      filesPerPage={10}
      totalFiles={100}
      currentPage={2}
      setCurrentPage={(e) => e}
    />
  );
  expect(baseElement).toMatchSnapshot();
  await act(async () => {
    await user.click(getAllByRole("button")[2]);
  });
  expect(baseElement).toMatchSnapshot();
});

test("Disabled Pagination", async () => {
  const user = userEvent.setup();
  const {baseElement, getAllByRole} = render(
    <Pagination
      filesPerPage={10}
      totalFiles={100}
      currentPage={2}
      setCurrentPage={(e) => e}
      disabled={true}
    />
  );
  expect(baseElement).toMatchSnapshot();
  await act(async () => {
    await user.click(getAllByRole("button")[7]);
  });
  expect(baseElement).toMatchSnapshot();
});

test("Pagination with no files", () => {
  const {baseElement} = render(
    <Pagination
      filesPerPage={10}
      totalFiles={0}
      currentPage={1}
      setCurrentPage={(e) => e}
    />
  );
  expect(baseElement).toMatchSnapshot();
});

test("Pagination on first page", async () => {
  const mockSetCurrentPage = vi.fn();
  const user = userEvent.setup();
  const {getAllByRole} = render(
    <Pagination
      filesPerPage={10}
      totalFiles={50}
      currentPage={1}
      setCurrentPage={mockSetCurrentPage}
    />
  );

  // Try to click previous button (should be disabled)
  const prevButton = getAllByRole("button")[0];
  expect(prevButton).toBeDisabled();

  // Click next button
  const nextButton = getAllByRole("button")[getAllByRole("button").length - 1];
  await act(async () => {
    await user.click(nextButton);
  });
  expect(mockSetCurrentPage).toHaveBeenCalled();
});

test("Pagination on last page", async () => {
  const mockSetCurrentPage = vi.fn();
  const user = userEvent.setup();
  const {getAllByRole} = render(
    <Pagination
      filesPerPage={10}
      totalFiles={50}
      currentPage={5}
      setCurrentPage={mockSetCurrentPage}
    />
  );

  // Next button should be disabled on last page
  const nextButton = getAllByRole("button")[getAllByRole("button").length - 1];
  expect(nextButton).toBeDisabled();

  // Click previous button
  const prevButton = getAllByRole("button")[0];
  await act(async () => {
    await user.click(prevButton);
  });
  expect(mockSetCurrentPage).toHaveBeenCalled();
});

test("Pagination click page number", async () => {
  const mockSetCurrentPage = vi.fn();
  const user = userEvent.setup();
  const {getAllByRole} = render(
    <Pagination
      filesPerPage={10}
      totalFiles={30}
      currentPage={1}
      setCurrentPage={mockSetCurrentPage}
    />
  );

  // Click page 2 button
  const page2Button = getAllByRole("button").find(btn => btn.textContent === "2");
  await act(async () => {
    await user.click(page2Button);
  });
  expect(mockSetCurrentPage).toHaveBeenCalledWith(2);
});
