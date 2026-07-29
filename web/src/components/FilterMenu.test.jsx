import { render, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, test, expect, vi } from "vitest";
import FilterMenu from "./FilterMenu";

const sections = [
  {
    title: "Show",
    filterKey: "filter",
    mode: "single",
    options: [
      { value: "active", label: "Active jobs" },
      { value: "inactive", label: "Inactive jobs" },
    ],
  },
  {
    title: "Tasks",
    filterKey: "task",
    mode: "multi",
    options: [
      { value: "transcribe", label: "Transcription" },
      { value: "translate", label: "Translation" },
    ],
  },
];

function renderMenu(props) {
  return render(
    <FilterMenu
      label="Filters"
      sections={sections}
      query=""
      setQuery={vi.fn()}
      {...props}
    />,
  );
}

async function openMenu(getByRole) {
  await act(async () => {
    await userEvent.click(getByRole("button", { name: /filters/i }));
  });
}

describe("FilterMenu", () => {
  test("a single-select section sets its key (replacing any prior value)", async () => {
    const setQuery = vi.fn();
    const { getByRole, getByText } = renderMenu({ query: "filter:active", setQuery });
    await openMenu(getByRole);
    await act(async () => {
      await userEvent.click(getByText("Inactive jobs"));
    });
    expect(setQuery).toHaveBeenCalledWith("filter:inactive");
  });

  test("re-picking the selected single option toggles it off", async () => {
    const setQuery = vi.fn();
    const { getByRole, getByText } = renderMenu({ query: "filter:active", setQuery });
    await openMenu(getByRole);
    await act(async () => {
      await userEvent.click(getByText("Active jobs"));
    });
    expect(setQuery).toHaveBeenCalledWith("");
  });

  test("a multi-select section toggles values, keeping others", async () => {
    const setQuery = vi.fn();
    const { getByRole, getByText } = renderMenu({
      query: "task:transcribe",
      setQuery,
    });
    await openMenu(getByRole);
    await act(async () => {
      await userEvent.click(getByText("Translation"));
    });
    expect(setQuery).toHaveBeenCalledWith("task:transcribe task:translate");
  });

  test("shows a total selected count on the button", async () => {
    const { getByRole } = renderMenu({
      query: "filter:active task:transcribe task:translate",
    });
    // 1 (single) + 2 (multi) = 3
    expect(getByRole("button", { name: /filters.*3/i })).toBeInTheDocument();
  });

  test("Clear filters removes every section's values", async () => {
    const setQuery = vi.fn();
    const { getByRole, getByText } = renderMenu({
      query: "keep filter:active task:transcribe",
      setQuery,
    });
    await openMenu(getByRole);
    await act(async () => {
      await userEvent.click(getByText("Clear filters"));
    });
    expect(setQuery).toHaveBeenCalledWith("keep");
  });

  test("no Clear filters entry when nothing is selected", async () => {
    const { getByRole, queryByText } = renderMenu({ query: "" });
    await openMenu(getByRole);
    expect(queryByText("Clear filters")).not.toBeInTheDocument();
  });
});
