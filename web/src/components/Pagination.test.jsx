import { render, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { test, expect, vi } from "vitest";
import Pagination from "@/components/Pagination";

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
