import { render, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, test, expect, vi } from "vitest";
import FilterHeader from "./FilterHeader";

const options = [
  { value: "running", label: "Running" },
  { value: "stopped", label: "Stopped" },
];

function renderHeader(props) {
  // A <th> must live inside a table row for valid DOM.
  return render(
    <table>
      <thead>
        <tr>
          <FilterHeader
            label="Status"
            filterKey="status"
            options={options}
            query=""
            setQuery={vi.fn()}
            {...props}
          />
        </tr>
      </thead>
    </table>,
  );
}

describe("FilterHeader", () => {
  test("toggling an option adds its filterKey:value to the query", async () => {
    const setQuery = vi.fn();
    const { getByRole, getByText } = renderHeader({ query: "foo", setQuery });
    await act(async () => {
      await userEvent.click(getByRole("button", { name: /status/i }));
    });
    await act(async () => {
      await userEvent.click(getByText("Running"));
    });
    expect(setQuery).toHaveBeenCalledWith("foo status:running");
  });

  test("toggling an already-selected option removes just that value", async () => {
    const setQuery = vi.fn();
    const { getByRole, getByText } = renderHeader({
      query: "status:running status:stopped",
      setQuery,
    });
    await act(async () => {
      await userEvent.click(getByRole("button", { name: /status/i }));
    });
    await act(async () => {
      await userEvent.click(getByText("Running"));
    });
    // stopped is preserved; only running is removed.
    expect(setQuery).toHaveBeenCalledWith("status:stopped");
  });

  test("selecting a second option keeps the first (multi-select)", async () => {
    const setQuery = vi.fn();
    const { getByRole, getByText } = renderHeader({
      query: "status:running",
      setQuery,
    });
    await act(async () => {
      await userEvent.click(getByRole("button", { name: /status/i }));
    });
    await act(async () => {
      await userEvent.click(getByText("Stopped"));
    });
    expect(setQuery).toHaveBeenCalledWith("status:running status:stopped");
  });

  test("clear removes all of the column's values, keeping other tokens", async () => {
    const setQuery = vi.fn();
    const { getByRole, getByText } = renderHeader({
      query: "keep status:running status:stopped",
      setQuery,
      clearLabel: "Clear statuses",
    });
    await act(async () => {
      await userEvent.click(getByRole("button", { name: /status/i }));
    });
    await act(async () => {
      await userEvent.click(getByText("Clear statuses"));
    });
    expect(setQuery).toHaveBeenCalledWith("keep");
  });

  test("shows a count when filters are active", () => {
    const { getByRole } = renderHeader({ query: "status:running status:stopped" });
    // The header button's accessible name includes the active count.
    expect(getByRole("button", { name: /status.*2/i })).toBeInTheDocument();
  });
});
