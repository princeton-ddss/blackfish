import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, test, expect, vi } from "vitest";

import JobDetailsPanel, {
  formatParamLabel,
  formatParamValue,
  terminalReason,
} from "./JobDetailsPanel";

describe("formatParamLabel", () => {
  test("uses friendly labels for known params", () => {
    expect(formatParamLabel("overlap_s")).toBe("Window overlap (s)");
    expect(formatParamLabel("batch_size")).toBe("Batch size");
    expect(formatParamLabel("sample_fps")).toBe("Sample FPS");
    expect(formatParamLabel("target_lang")).toBe("Target language");
  });

  test("title-cases unknown snake_case keys", () => {
    expect(formatParamLabel("windowing")).toBe("Windowing");
    expect(formatParamLabel("some_new_param")).toBe("Some new param");
  });
});

describe("formatParamValue", () => {
  test("renders booleans as Yes/No", () => {
    expect(formatParamValue("raw", true)).toBe("Yes");
    expect(formatParamValue("raw", false)).toBe("No");
  });

  test("renders an empty transcribe language as Auto-detect", () => {
    expect(formatParamValue("language", "")).toBe("Auto-detect");
  });

  test("stringifies other values", () => {
    expect(formatParamValue("batch_size", 16)).toBe("16");
    expect(formatParamValue("windowing", "batched")).toBe("batched");
  });
});

describe("terminalReason", () => {
  test("returns null for non-terminal and unhandled statuses", () => {
    expect(terminalReason(null)).toBeNull();
    expect(terminalReason({ status: "running" })).toBeNull();
    expect(terminalReason({ status: "stopped" })).toBeNull();
    expect(terminalReason({ status: "broken" })).toBeNull();
  });

  test("explains EXHAUSTED with budget and remaining count", () => {
    const r = terminalReason({
      status: "exhausted",
      finished: 48,
      staged: 12,
      errored: 0,
      max_restarts: 20,
      processed_highwater: 48,
    });
    expect(r.headline).toBe("Exhausted restart budget");
    expect(r.detail).toContain("all 20 restarts");
    expect(r.detail).toContain("12 files still unprocessed");
  });

  test("avoids the '0 files unprocessed' non-sequitur for EXHAUSTED", () => {
    const r = terminalReason({
      status: "exhausted",
      finished: 60,
      staged: 0,
      errored: 0,
      max_restarts: 20,
      processed_highwater: 60,
    });
    expect(r.detail).toContain("all 20 restarts");
    expect(r.detail).not.toContain("0 files");
    expect(r.detail).toContain("before finishing");
  });

  test("singularizes a single remaining file", () => {
    const r = terminalReason({
      status: "exhausted",
      finished: 59,
      staged: 1,
      errored: 0,
      max_restarts: 20,
      processed_highwater: 59,
    });
    expect(r.detail).toContain("1 file still unprocessed");
    expect(r.detail).not.toContain("1 files");
  });

  test("explains STALLED with restart count and high-water mark", () => {
    const r = terminalReason({
      status: "stalled",
      finished: 41,
      staged: 3,
      errored: 0,
      stalled_restarts: 1,
      processed_highwater: 41,
    });
    expect(r.headline).toBe("No forward progress");
    expect(r.detail).toContain("across 1 restart");
    expect(r.detail).toContain("stopped at 41/44");
    expect(r.detail).toContain("failing repeatedly");
    // Warns the user to fix the input before resuming (else it re-stalls).
    expect(r.detail).toContain("before");
    expect(r.detail).toContain("resuming");
  });

  test("omits the total when staged is unknown (between allocations)", () => {
    const r = terminalReason({
      status: "stalled",
      finished: 41,
      staged: null,
      errored: 0,
      stalled_restarts: 2,
      processed_highwater: 41,
    });
    expect(r.detail).toContain("across 2 restarts");
    expect(r.detail).not.toContain("stopped at");
  });
});

describe("JobDetailsPanel resume action", () => {
  const job = (status) => ({
    id: "job-001",
    name: "Batch Translation",
    status,
    finished: 10,
    staged: 5,
    errored: 0,
  });

  function renderPanel(status, props = {}) {
    return render(
      <JobDetailsPanel
        job={job(status)}
        onResumeJob={vi.fn()}
        onStopJob={vi.fn()}
        onDeleteJob={vi.fn()}
        {...props}
      />,
    );
  }

  test.each(["stopped", "stalled", "exhausted"])(
    "offers Resume for a %s job",
    (status) => {
      renderPanel(status);
      expect(screen.getByLabelText("Resume job")).toBeInTheDocument();
    },
  );

  test.each(["broken", "running", "pending", "submitted", "resubmitted"])(
    "does not offer Resume for a %s job",
    (status) => {
      renderPanel(status);
      expect(screen.queryByLabelText("Resume job")).not.toBeInTheDocument();
    },
  );

  test("calls onResumeJob with the job", async () => {
    const onResumeJob = vi.fn();
    renderPanel("exhausted", { onResumeJob });

    await userEvent.click(screen.getByLabelText("Resume job"));

    expect(onResumeJob).toHaveBeenCalledTimes(1);
    expect(onResumeJob.mock.calls[0][0].id).toBe("job-001");
  });

  test("disables Resume while an action is in flight for that job", () => {
    renderPanel("stopped", { jobActions: { "job-001": "resume" } });
    expect(screen.getByLabelText("Resume job")).toBeDisabled();
  });

  test("stays enabled while a different job's action is in flight", () => {
    renderPanel("stopped", { jobActions: { "job-002": "stop" } });
    expect(screen.getByLabelText("Resume job")).toBeEnabled();
  });

  test("omits Resume when no handler is supplied", () => {
    render(<JobDetailsPanel job={job("stopped")} />);
    expect(screen.queryByLabelText("Resume job")).not.toBeInTheDocument();
  });
});
