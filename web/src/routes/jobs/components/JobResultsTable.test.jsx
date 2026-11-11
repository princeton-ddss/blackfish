import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";
import JobResultsTable from "./JobResultsTable";

function result(id, overrides = {}) {
  return {
    id: `result-${id}`,
    input_file: `/inputs/input-${id}.jpg`,
    output_file: `/outputs/output-${id}.json`,
    success: true,
    started_at: "2026-01-01T00:00:00Z",
    finished_at: "2026-01-01T00:00:01Z",
    ...overrides,
  };
}

function table(results) {
  return <JobResultsTable job={{ name: "Detection job" }} results={results}
    onBack={vi.fn()} onResultSelect={vi.fn()} />;
}

function inputs() {
  return within(screen.getByRole("table")).getAllByRole("row").slice(1)
    .map((row) => within(row).getAllByRole("cell")[0].textContent);
}

async function click(name) {
  await userEvent.click(screen.getByRole("button", { name }));
}

async function typeQuery(query) {
  await userEvent.type(screen.getByRole("textbox", { name: "Search" }), query);
}

describe("JobResultsTable query integration", () => {
  test.each([
    ["Successful", "success", "input-good.jpg"],
    ["Failed", "failed", "input-bad.jpg"],
  ])("Status dropdown filters %s results", async (label, status, filename) => {
    render(table([result("good"), result("bad", { success: false })]));
    await click("Status");
    await click(label);
    expect(screen.getByRole("textbox", { name: "Search" })).toHaveValue(`status:${status}`);
    expect(inputs()).toEqual([filename]);
    expect(screen.getByText("(1 of 2)")).toBeInTheDocument();
  });

  test("status multi-select and clearing preserve the file qualifier", async () => {
    render(table([
      result("good"),
      result("bad", { success: false }),
      result("excluded", { input_file: "/inputs/other.jpg" }),
    ]));
    await typeQuery("file:input-");
    await click("Status");
    await click("Successful");
    expect(inputs()).toEqual(["input-good.jpg"]);
    await click("Failed");
    expect(inputs()).toEqual(["input-good.jpg", "input-bad.jpg"]);
    expect(screen.getByRole("textbox", { name: "Search" })).toHaveValue(
      "file:input- status:success status:failed",
    );
    await click("Successful");
    expect(inputs()).toEqual(["input-bad.jpg"]);
    await click("Clear statuses");
    expect(screen.getByRole("textbox", { name: "Search" })).toHaveValue("file:input-");
    expect(inputs()).toEqual(["input-good.jpg", "input-bad.jpg"]);
  });

  test("filtering from page two shows matching rows from the first page", async () => {
    render(table(Array.from({ length: 101 }, (_, i) => result(i, { success: i >= 51 }))));
    await click("2");
    expect(inputs()).toHaveLength(50);
    expect(inputs()[0]).toBe("input-50.jpg");
    await click("Status");
    await click("Failed");
    expect(inputs()).toHaveLength(50);
    expect(inputs()[0]).toBe("input-0.jpg");
    expect(inputs()[49]).toBe("input-49.jpg");
    expect(screen.getByRole("button", { name: "1" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "2" })).toBeEnabled();
  });

  test("data shrinking under the current page clamps to the last valid page", async () => {
    const results = Array.from({ length: 101 }, (_, i) => result(i));
    const { rerender } = render(table(results));
    await click("3");
    expect(inputs()).toEqual(["input-100.jpg"]);
    rerender(table(results.slice(0, 51)));
    expect(inputs()).toEqual(["input-50.jpg"]);
    expect(screen.getByRole("button", { name: "2" })).toBeDisabled();
    await click("1");
    expect(inputs()).toHaveLength(50);
    expect(inputs()[0]).toBe("input-0.jpg");
  });

  test("distinguishes empty results from a query with no matches and recovers on clear", async () => {
    const { rerender } = render(table([]));
    expect(screen.getByText("No results found")).toBeInTheDocument();
    rerender(table([result("one")]));
    await typeQuery("file:missing");
    expect(screen.getByText("No results match your search")).toBeInTheDocument();
    expect(screen.queryByText("No results found")).not.toBeInTheDocument();
    await click("Clear search");
    expect(inputs()).toEqual(["input-one.jpg"]);
    expect(screen.getByText("(1 results)")).toBeInTheDocument();
  });
});
