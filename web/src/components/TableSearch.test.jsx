import { render, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, test, expect, vi } from "vitest";
import TableSearch from "./TableSearch";

describe("TableSearch", () => {
  test("typing updates the query", async () => {
    const setQuery = vi.fn();
    const { getByLabelText } = render(
      <TableSearch query="" setQuery={setQuery} />,
    );
    await act(async () => {
      await userEvent.type(getByLabelText("Search"), "x");
    });
    expect(setQuery).toHaveBeenCalledWith("x");
  });

  test("clear button empties the query and only shows when non-empty", async () => {
    const setQuery = vi.fn();
    const { getByLabelText, queryByLabelText, rerender } = render(
      <TableSearch query="" setQuery={setQuery} />,
    );
    expect(queryByLabelText("Clear search")).not.toBeInTheDocument();

    rerender(<TableSearch query="foo" setQuery={setQuery} />);
    await act(async () => {
      await userEvent.click(getByLabelText("Clear search"));
    });
    expect(setQuery).toHaveBeenCalledWith("");
  });

  test("renders an attached control passed as children", () => {
    const { getByText } = render(
      <TableSearch query="" setQuery={vi.fn()}>
        <button type="button">Filters</button>
      </TableSearch>,
    );
    expect(getByText("Filters")).toBeInTheDocument();
  });
});
