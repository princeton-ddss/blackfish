import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";
import { BatchJobStatus } from "@/lib/util";
import JobsTable from "./JobsTable";

function job(id, overrides = {}) {
  return {
    id: `job-${id}`,
    name: `Job ${id}`,
    status: BatchJobStatus.SUBMITTED,
    task: "detect",
    created_at: "2026-01-01T00:00:00Z",
    finished: 0,
    staged: 10,
    errored: 0,
    ...overrides,
  };
}

function table(jobs) {
  return <JobsTable jobs={jobs} onJobClick={vi.fn()} onJobDrillIn={vi.fn()} />;
}

function names() {
  return within(screen.getByRole("table")).getAllByRole("row").slice(1)
    .map((row) => within(row).getAllByRole("cell")[0].textContent);
}

async function click(name, pressed) {
  await userEvent.click(screen.getByRole("button", { name, pressed }));
}

async function typeQuery(query) {
  await userEvent.type(screen.getByRole("textbox", { name: "Search" }), query);
}

describe("JobsTable query integration", () => {
  test.each(Object.values(BatchJobStatus))("Status dropdown selects exactly %s", async (status) => {
    render(table(Object.values(BatchJobStatus).map((value) => job(value, { status: value }))));

    await click("Status");
    await click(status.charAt(0).toUpperCase() + status.slice(1), false);

    expect(screen.getByRole("textbox", { name: "Search" })).toHaveValue(`status:${status}`);
    expect(names()).toEqual([`Job ${status}`]);
  });

  test("status multi-select, deselection, and clearing preserve another qualifier", async () => {
    render(table([
      job("submitted"),
      job("resubmitted", { status: BatchJobStatus.RESUBMITTED }),
      job("other", { name: "Excluded item" }),
    ]));
    await typeQuery("name:Job");
    await click("Status");
    await click("Submitted", false);
    await click("Resubmitted");
    expect(names()).toEqual(["Job submitted", "Job resubmitted"]);
    expect(screen.getByRole("textbox", { name: "Search" })).toHaveValue(
      "name:Job status:submitted status:resubmitted",
    );

    await click("Submitted", true);
    expect(names()).toEqual(["Job resubmitted"]);
    await click("Clear statuses");
    expect(screen.getByRole("textbox", { name: "Search" })).toHaveValue("name:Job");
    expect(names()).toEqual(["Job submitted", "Job resubmitted"]);
  });

  test("Progress dropdown filters rows and combines with the Status dropdown", async () => {
    render(table([
      job("untouched"),
      job("partial", { finished: 2, staged: 8 }),
      job("complete", { finished: 10, staged: 0 }),
      job("retry", { status: BatchJobStatus.RESUBMITTED, finished: 2, staged: 8 }),
    ]));
    await click("Progress");
    await click("In progress");
    expect(names()).toEqual(["Job partial", "Job retry"]);
    await click("Status");
    await click("Submitted", false);
    expect(screen.getByRole("textbox", { name: "Search" })).toHaveValue(
      "progress:in-progress status:submitted",
    );
    expect(names()).toEqual(["Job partial"]);
  });

  test("Filters shortcut combines with a header filter and clears independently", async () => {
    render(table([
      job("failed", { errored: 1 }),
      job("healthy"),
      job("stopped", { status: BatchJobStatus.STOPPED, errored: 1 }),
    ]));
    await click("Status");
    await click("Submitted", false);
    await click("Filters");
    await click("Jobs with failures");
    expect(screen.getByRole("textbox", { name: "Search" })).toHaveValue(
      "status:submitted filter:failed",
    );
    expect(names()).toEqual(["Job failed"]);
    await click("Clear filters");
    expect(screen.getByRole("textbox", { name: "Search" })).toHaveValue("status:submitted");
    expect(names()).toEqual(["Job failed", "Job healthy"]);
  });

  test("filtering from page two shows matching rows from the first page", async () => {
    render(table(Array.from({ length: 101 }, (_, i) => job(i, {
      status: i < 51 ? BatchJobStatus.STOPPED : BatchJobStatus.SUBMITTED,
    }))));
    await click("2");
    expect(names()).toHaveLength(50);
    expect(names()[0]).toBe("Job 50");
    await click("Status");
    await click("Stopped");
    expect(names()).toHaveLength(50);
    expect(names()[0]).toBe("Job 0");
    expect(names()[49]).toBe("Job 49");
    expect(screen.getByRole("button", { name: "1" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "2" })).toBeEnabled();
  });

  test("data shrinking under the current page clamps to the last valid page", async () => {
    const jobs = Array.from({ length: 101 }, (_, i) => job(i));
    const { rerender } = render(table(jobs));
    await click("3");
    expect(names()).toEqual(["Job 100"]);
    rerender(table(jobs.slice(0, 51)));
    expect(names()).toEqual(["Job 50"]);
    expect(screen.getByRole("button", { name: "2" })).toBeDisabled();
    await click("1");
    expect(names()).toHaveLength(50);
    expect(names()[0]).toBe("Job 0");
  });

  test("distinguishes an empty source from a query with no matches and recovers on clear", async () => {
    const { rerender } = render(table([]));
    expect(screen.getByText("No jobs found")).toBeInTheDocument();
    rerender(table([job("one")]));
    await typeQuery("name:missing");
    expect(screen.getByText("No jobs match your search")).toBeInTheDocument();
    expect(screen.queryByText("No jobs found")).not.toBeInTheDocument();
    await click("Clear search");
    expect(names()).toEqual(["Job one"]);
  });
});
