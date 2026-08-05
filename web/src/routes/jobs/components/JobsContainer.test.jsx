import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, test, expect, vi, beforeEach } from "vitest";

import { ProfileContext } from "@/components/ProfileSelect";
import { useJobs, useJobResults } from "@/lib/loaders";
import { stopJob, resumeJob, deleteJob } from "@/lib/requests";
import JobsContainer from "./JobsContainer";

vi.mock("@/lib/loaders");
vi.mock("@/lib/requests");
// The modal needs RemoteFileSystemProvider, which is irrelevant here. JobsTable
// imports TASKS from the same module, so the stub has to keep exporting it.
vi.mock("./NewJobModal", () => ({
  default: () => null,
  TASKS: [
    { id: "transcribe", name: "Transcribe", description: "Speech to text" },
    { id: "translate", name: "Translate", description: "Translate text" },
  ],
}));

const STOPPED_JOB = {
  id: "job-001",
  name: "Batch Translation",
  status: "stopped",
  created_at: "2024-01-15T10:30:00Z",
  finished: 50,
  staged: 10,
  errored: 0,
  restarts: 3,
  stalled_restarts: 0,
  task: "translate",
};

const mutate = vi.fn();

function renderContainer(jobs = [STOPPED_JOB]) {
  useJobs.mockReturnValue({
    jobs,
    error: null,
    isLoading: false,
    isRefreshing: false,
    mutate,
  });
  useJobResults.mockReturnValue({
    results: [],
    error: null,
    isLoading: false,
    isRefreshing: false,
    mutate: vi.fn(),
  });
  return render(
    <ProfileContext.Provider value={{ profile: { name: "adroit", schema: "slurm" } }}>
      <JobsContainer />
    </ProfileContext.Provider>,
  );
}

// Select the job so JobDetailsPanel (which owns the action buttons) renders it.
async function selectJobAndResume(user) {
  await user.click(screen.getByText("Batch Translation"));
  await user.click(await screen.findByLabelText("Resume job"));
}

describe("JobsContainer resume outcomes", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test("reports a 200 that comes back BROKEN as a failure, not a success", async () => {
    // The route catches a failed resubmit and answers 200 with the job marked
    // BROKEN — the case this feature is built around. Resolving is not success.
    resumeJob.mockResolvedValue({ id: "job-001", status: "broken" });
    const user = userEvent.setup();
    renderContainer();

    await selectJobAndResume(user);

    expect(await screen.findByText(/marked broken/i)).toBeInTheDocument();
    expect(screen.queryByText(/^Resumed/)).not.toBeInTheDocument();
  });

  test("reports a genuine resume as a success", async () => {
    resumeJob.mockResolvedValue({ id: "job-001", status: "resubmitted" });
    const user = userEvent.setup();
    renderContainer();

    await selectJobAndResume(user);

    expect(
      await screen.findByText("Resumed Batch Translation."),
    ).toBeInTheDocument();
  });

  test("surfaces the server's reason when the request is refused", async () => {
    resumeJob.mockRejectedValue(
      new Error("Input directory does not exist on adroit: /scratch/gone"),
    );
    const user = userEvent.setup();
    renderContainer();

    await selectJobAndResume(user);

    expect(
      await screen.findByText(/Input directory does not exist/),
    ).toBeInTheDocument();
  });

  test("does not leave a previous success showing when a later action fails", async () => {
    resumeJob
      .mockResolvedValueOnce({ id: "job-001", status: "resubmitted" })
      .mockRejectedValueOnce(new Error("Job job-001 is not resumable"));
    const user = userEvent.setup();
    renderContainer();

    await selectJobAndResume(user);
    expect(
      await screen.findByText("Resumed Batch Translation."),
    ).toBeInTheDocument();

    await user.click(screen.getByLabelText("Resume job"));

    expect(await screen.findByText(/is not resumable/)).toBeInTheDocument();
    await waitFor(() =>
      expect(
        screen.queryByText("Resumed Batch Translation."),
      ).not.toBeInTheDocument(),
    );
  });
});

describe("JobsContainer concurrent actions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // Regression test for #443: in-flight state used to be a single job id, so
  // starting an action on a second job cleared the first job's, un-pulsing its
  // badge and re-enabling its buttons while its request was still outstanding.
  test("keeps a job's in-flight state when another job's action starts", async () => {
    const jobA = { ...STOPPED_JOB, id: "job-A", name: "Job A" };
    const jobB = { ...STOPPED_JOB, id: "job-B", name: "Job B" };

    let finishA;
    resumeJob
      .mockImplementationOnce(() => new Promise((resolve) => { finishA = resolve; }))
      .mockResolvedValueOnce({ id: "job-B", status: "resubmitted" });

    const user = userEvent.setup();
    renderContainer([jobA, jobB]);

    // The selected job's name also appears in the details panel, so scope row
    // lookups to the table.
    const rowFor = (name) =>
      within(screen.getByRole("table")).getByText(name).closest("tr");
    const badgeFor = (name) => within(rowFor(name)).getByText("Stopped");

    // Start A's resume; it stays pending.
    await user.click(rowFor("Job A"));
    await user.click(await screen.findByLabelText("Resume job"));
    expect(badgeFor("Job A")).toHaveClass("animate-pulse");

    // Start B's resume and let it finish.
    await user.click(rowFor("Job B"));
    await user.click(await screen.findByLabelText("Resume job"));
    expect(await screen.findByText("Resumed Job B.")).toBeInTheDocument();

    // A is still waiting, so its badge must still say so.
    expect(badgeFor("Job A")).toHaveClass("animate-pulse");

    finishA({ id: "job-A", status: "resubmitted" });
    await waitFor(() =>
      expect(badgeFor("Job A")).not.toHaveClass("animate-pulse"),
    );
  });
});

describe("JobsContainer stop and delete outcomes", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test("reports a stop that comes back BROKEN as a failure", async () => {
    // stop_job maps a failed scancel and a failed post-stop refresh to BROKEN,
    // so it has the same 200-with-BROKEN shape as resume.
    stopJob.mockResolvedValue({ id: "job-002", status: "broken" });
    const user = userEvent.setup();
    renderContainer([{ ...STOPPED_JOB, id: "job-002", status: "running" }]);

    await user.click(screen.getByText("Batch Translation"));
    await user.click(await screen.findByLabelText("Stop job"));

    expect(await screen.findByText(/marked broken/i)).toBeInTheDocument();
    expect(screen.queryByText(/^Stopped/)).not.toBeInTheDocument();
  });

  test("reports a successful delete", async () => {
    deleteJob.mockResolvedValue({});
    const user = userEvent.setup();
    renderContainer();

    await user.click(screen.getByText("Batch Translation"));
    await user.click(await screen.findByLabelText("Delete job"));

    expect(
      await screen.findByText("Deleted Batch Translation."),
    ).toBeInTheDocument();
  });
});
