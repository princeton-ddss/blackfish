import { useContext, useState } from "react";
import { ProfileContext } from "@/components/ProfileSelect";
import { useJobs, useJobResults } from "@/lib/loaders";
import { stopJob, resumeJob, deleteJob } from "@/lib/requests";
import JobsTable from "./JobsTable";
import JobResultsTable from "./JobResultsTable";
import JobDetailsPanel from "./JobDetailsPanel";
import ResultPreview from "./ResultPreview";
import NewJobModal from "./NewJobModal";
import Notification from "@/components/Notification";
import { COLUMN_HEIGHT } from "./layout";

// Mock data for development - matches API BatchJob structure
const MOCK_JOBS = [
    {
        // Just submitted: staged is null until the first observation reports an
        // input count, so progress renders as N/A rather than a collapsed bar.
        id: "job-000c",
        name: "Video Captioning",
        created_at: "2024-01-17T10:00:00Z",
        status: "submitted",
        staged: null,
        finished: 0,
        errored: 0,
        task: "transcribe",
        repo_id: "openai/whisper-large-v3",
        revision: "main",
        input_dir: "/scratch/user/audio/input",
        output_dir: "/scratch/user/audio/output",
    },
    {
        // Terminal: restart budget exhausted with work remaining.
        id: "job-000",
        name: "Meeting Transcription",
        created_at: "2024-01-17T09:00:00Z",
        status: "exhausted",
        staged: 12,
        finished: 48,
        errored: 0,
        restarts: 20,
        max_restarts: 20,
        stalled_restarts: 0,
        max_stalled_restarts: 1,
        processed_highwater: 48,
        task: "transcribe",
        repo_id: "openai/whisper-large-v3",
        revision: "main",
        input_dir: "/scratch/user/audio/input",
        output_dir: "/scratch/user/audio/output",
    },
    {
        // Active (running) but has already restarted: exercises the
        // "Restarted N times" line on a non-terminal job (no red callout).
        id: "job-000a",
        name: "Lecture Transcription",
        created_at: "2024-01-17T08:30:00Z",
        status: "running",
        staged: 30,
        finished: 70,
        errored: 0,
        restarts: 2,
        max_restarts: 20,
        stalled_restarts: 0,
        max_stalled_restarts: 1,
        processed_highwater: 55,
        task: "transcribe",
        repo_id: "openai/whisper-large-v3",
        revision: "main",
        input_dir: "/scratch/user/audio/input",
        output_dir: "/scratch/user/audio/output",
    },
    {
        // Terminal: stalled — no forward progress across restarts.
        id: "job-000b",
        name: "Podcast Transcription",
        created_at: "2024-01-17T08:00:00Z",
        status: "stalled",
        staged: 3,
        finished: 41,
        errored: 0,
        restarts: 6,
        max_restarts: 20,
        stalled_restarts: 1,
        max_stalled_restarts: 1,
        processed_highwater: 41,
        task: "transcribe",
        repo_id: "openai/whisper-large-v3",
        revision: "main",
        input_dir: "/scratch/user/audio/input",
        output_dir: "/scratch/user/audio/output",
    },
    {
        id: "job-001",
        name: "Batch Translation - French",
        created_at: "2024-01-15T10:30:00Z",
        status: "stopped",
        staged: 0,
        finished: 50,
        errored: 2,
        task: "translate",
        repo_id: "meta-llama/Llama-2-7b-chat-hf",
        revision: "main",
        input_dir: "/scratch/user/data/input",
        output_dir: "/scratch/user/data/output",
        resources: {
            memory_gb: 32,
            cpus: 4,
            gpu_count: 1,
            partition: "gpu",
            max_workers: 2,
        },
        params: {
            prompt: "Translate the following text to French:",
            temperature: 0.3,
            max_tokens: 512,
        },
    },
    {
        id: "job-002",
        name: "Audio Transcription",
        created_at: "2024-01-15T14:45:00Z",
        status: "running",
        staged: 77,
        finished: 23,
        errored: 0,
        task: "transcribe",
        repo_id: "openai/whisper-large-v3",
        revision: "main",
        input_dir: "/scratch/user/audio/input",
        output_dir: "/scratch/user/audio/output",
        resources: {
            memory_gb: 16,
            cpus: 2,
            gpu_count: 1,
            partition: "gpu",
            max_workers: 1,
        },
        params: {
            language: "en",
        },
    },
    {
        id: "job-003",
        name: "Document Summarization",
        created_at: "2024-01-14T09:00:00Z",
        status: "stopped",
        staged: 0,
        finished: 15,
        errored: 35,
        task: "summarize",
        repo_id: "mistralai/Mixtral-8x7B-Instruct-v0.1",
        revision: "main",
        input_dir: "/scratch/user/docs/input",
        output_dir: "/scratch/user/docs/output",
        resources: {
            memory_gb: 64,
            cpus: 8,
            gpu_count: 2,
            partition: "gpu-large",
            max_workers: 4,
        },
        params: {
            prompt: "Summarize the following document in 3 sentences:",
            temperature: 0.5,
            max_tokens: 256,
        },
    },
    {
        id: "job-004",
        name: "Code Review Analysis",
        created_at: "2024-01-16T08:00:00Z",
        status: "running",
        staged: 100,
        finished: 0,
        errored: 0,
        task: "review",
        repo_id: "codellama/CodeLlama-34b-Instruct-hf",
        revision: "main",
        input_dir: "/scratch/user/code/input",
        output_dir: "/scratch/user/code/output",
        resources: {
            memory_gb: 32,
            cpus: 4,
            gpu_count: 1,
            partition: "gpu",
            max_workers: 2,
        },
        params: {
            prompt: "Review the following code for potential issues:",
            temperature: 0.1,
            max_tokens: 1024,
        },
    },
];

// Mock results - started_at/finished_at not available from TigerFlow
const MOCK_RESULTS = {
    "job-001": [
        {
            id: "result-001",
            input_file: "document_1.txt",
            output_file: "document_1_fr.txt",
            started_at: null,
            finished_at: null,
            success: true,
        },
        {
            id: "result-002",
            input_file: "document_2.txt",
            output_file: "document_2_fr.txt",
            started_at: null,
            finished_at: null,
            success: true,
        },
        {
            id: "result-003",
            input_file: "document_3.txt",
            output_file: null,
            started_at: null,
            finished_at: null,
            success: false,
            error: "File encoding not supported",
        },
    ],
    "job-002": [
        {
            id: "result-004",
            input_file: "recording_1.mp3",
            output_file: "recording_1.txt",
            started_at: null,
            finished_at: null,
            success: true,
        },
    ],
};

function JobsContainer() {
    const { profile } = useContext(ProfileContext);
    const { jobs: apiJobs, isLoading, isRefreshing, mutate } = useJobs(profile);
    const [useMockData, setUseMockData] = useState(false);
    const [selectedJobId, setSelectedJobId] = useState(null);
    const [selectedResult, setSelectedResult] = useState(null);
    const [viewingResults, setViewingResults] = useState(false);
    const [isNewPipelineModalOpen, setIsNewPipelineModalOpen] = useState(false);
    const [selectedTask, setSelectedTask] = useState(null);
    // job id -> the action in flight for it ("stop" | "resume" | "delete").
    // Keyed by job because actions on different jobs run concurrently: a single
    // scalar let the second action clear the first one's in-flight state, which
    // re-enabled its buttons mid-request.
    const [jobActions, setJobActions] = useState({});
    const [operationSuccess, setOperationSuccess] = useState(null);
    const [operationError, setOperationError] = useState(null);

    const beginJobAction = (jobId, action) => {
        setJobActions((prev) => ({ ...prev, [jobId]: action }));
        // Clear both: a stale success from a previous action would otherwise
        // sit alongside this one's error, each describing a different job.
        setOperationSuccess(null);
        setOperationError(null);
    };

    const endJobAction = (jobId) => {
        setJobActions((prev) => {
            // eslint-disable-next-line no-unused-vars
            const { [jobId]: _finished, ...rest } = prev;
            return rest;
        });
    };

    // Gate mock data on import.meta.env.DEV so Vite can tree-shake MOCK_JOBS
    // out of production builds. In prod this expression simplifies to `apiJobs`.
    const jobs = (import.meta.env.DEV && useMockData) ? MOCK_JOBS : apiJobs;

    // Fetch real results when viewing results for a job (not in mock mode)
    const fetchResultsForJobId = (!useMockData && viewingResults) ? selectedJobId : null;
    const { results: apiResults, error: resultsError, isLoading: isResultsLoading, isRefreshing: isResultsRefreshing, mutate: mutateResults } = useJobResults(fetchResultsForJobId);

    // Derive selectedJob from jobs list - always stays in sync
    const selectedJob = selectedJobId && jobs ? jobs.find(j => j.id === selectedJobId) : null;

    // Click on job row to show details (without drilling in)
    const handleJobClick = (job) => {
        setSelectedJobId(job.id);
        setSelectedResult(null);
    };

    // Click ">" to drill into job results
    const handleJobDrillIn = (job) => {
        setSelectedJobId(job.id);
        setSelectedResult(null);
        setViewingResults(true);
    };

    const handleBackToJobs = () => {
        setViewingResults(false);
        setSelectedResult(null);
    };

    const handleResultSelect = (result) => {
        setSelectedResult(result);
    };

    const handleNewPipelineClick = (task) => {
        setSelectedTask(task);
        setIsNewPipelineModalOpen(true);
    };

    const handleJobCreated = (newJob) => {
        // Optimistic update: immediately add job to cache, then revalidate
        mutate((currentJobs) => [newJob, ...(currentJobs || [])], { revalidate: true });
        // Select the new job
        setSelectedJobId(newJob.id);
    };

    const handleStopJob = async (job) => {
        beginJobAction(job.id, "stop");
        try {
            const updated = await stopJob(job.id);
            // Like resume, a failed stop can answer 200 with the job marked
            // BROKEN (the route maps both a failed scancel and a failed
            // post-stop refresh to BROKEN), so take the status from the body.
            mutate(
                (currentJobs) => currentJobs?.map((j) =>
                    j.id === job.id ? { ...j, ...updated } : j
                ),
                { revalidate: true }
            );
            if (updated?.status === "broken") {
                setOperationError(
                    `Could not stop ${job.name}. The job is now marked broken.`
                );
            } else {
                setOperationSuccess(`Stopped ${job.name}.`);
            }
        } catch (err) {
            console.error("Failed to stop job:", err);
            setOperationError(`Could not stop ${job.name}. ${err.message}`);
        } finally {
            endJobAction(job.id);
        }
    };

    const handleResumeJob = async (job) => {
        beginJobAction(job.id, "resume");
        try {
            const updated = await resumeJob(job.id);
            // A failed resubmit still answers 200: the route catches the
            // TigerFlowError and returns the job marked BROKEN. Take the status
            // from the response rather than assuming RESUBMITTED, or the UI
            // reports success for a resume that didn't happen.
            mutate(
                (currentJobs) => currentJobs?.map((j) =>
                    j.id === job.id ? { ...j, ...updated } : j
                ),
                { revalidate: true }
            );
            if (updated?.status === "broken") {
                setOperationError(
                    `Could not resume ${job.name}. The job could not be resubmitted and is now marked broken.`
                );
            } else {
                setOperationSuccess(`Resumed ${job.name}.`);
            }
        } catch (err) {
            // No rollback needed: the badge still shows the job's real status,
            // since nothing is written until the server answers.
            // The server says why it refused (not resumable, input_dir gone,
            // image unstaged); surface that instead of failing silently.
            console.error("Failed to resume job:", err);
            setOperationError(`Could not resume ${job.name}. ${err.message}`);
        } finally {
            endJobAction(job.id);
        }
    };

    const handleDeleteJob = async (job) => {
        beginJobAction(job.id, "delete");
        try {
            await deleteJob(job.id);
            // Unlike stop/resume this waits for the response before touching
            // the list: a row that vanishes and then comes back on failure is
            // worse than one that lingers for the length of the request.
            if (selectedJobId === job.id) {
                setSelectedJobId(null);
            }
            mutate(
                (currentJobs) => currentJobs?.filter((j) => j.id !== job.id),
                { revalidate: true }
            );
            setOperationSuccess(`Deleted ${job.name}.`);
        } catch (err) {
            console.error("Failed to delete job:", err);
            setOperationError(`Could not delete ${job.name}. ${err.message}`);
        } finally {
            endJobAction(job.id);
        }
    };

    // Map API results to the shape expected by JobResultsTable/ResultPreview.
    // Mock branch is dev-only so MOCK_RESULTS gets tree-shaken from prod builds.
    const jobResults = (import.meta.env.DEV && useMockData)
        ? (selectedJob ? MOCK_RESULTS[selectedJob.id] || [] : [])
        : apiResults.map((r) => ({
            id: `${r.task}/${r.file}`,
            input_file: r.input_file,
            output_file: r.output_file,
            started_at: r.started_at,
            finished_at: r.finished_at,
            success: r.status === "success",
            error: r.error || null,
        }));

    // Determine what to show in right column
    const showResultPreview = selectedResult !== null;

    return (
        <div className="flex flex-col lg:flex-row lg:items-start gap-8">
            <div className="w-full lg:w-[48rem] lg:flex-shrink-0">
                {viewingResults ? (
                    <JobResultsTable
                        job={selectedJob}
                        results={jobResults}
                        onBack={handleBackToJobs}
                        onResultSelect={handleResultSelect}
                        selectedResult={selectedResult}
                        isLoading={!useMockData && isResultsLoading}
                        isRefreshing={!useMockData && isResultsRefreshing}
                        error={!useMockData ? resultsError : null}
                        onRefresh={mutateResults}
                    />
                ) : (
                    <JobsTable
                        jobs={jobs}
                        onJobClick={handleJobClick}
                        onJobDrillIn={handleJobDrillIn}
                        selectedJob={selectedJob}
                        onNewClick={handleNewPipelineClick}
                        profile={profile}
                        isLoading={isLoading}
                        isRefreshing={isRefreshing}
                        onRefresh={() => mutate()}
                        useMockData={useMockData}
                        setUseMockData={setUseMockData}
                        jobActions={jobActions}
                    />
                )}
            </div>
            <div className={`w-full lg:flex-1 lg:min-w-[24rem] lg:flex lg:flex-col ${COLUMN_HEIGHT}`}>
                <div className="flex-none flex items-center justify-between mb-2 h-9">
                    <label className="font-medium text-sm leading-6 text-gray-900 dark:text-gray-100">
                        {showResultPreview ? "Result Preview" : "Job Details"}
                    </label>
                </div>
                <div className="lg:flex-1 lg:min-h-0 ring-1 ring-gray-300 dark:ring-gray-600 rounded-lg overflow-y-auto">
                    {showResultPreview ? (
                        <ResultPreview
                            result={selectedResult}
                            job={selectedJob}
                            profile={profile}
                        />
                    ) : (
                        <JobDetailsPanel
                            job={selectedJob}
                            onStopJob={handleStopJob}
                            onResumeJob={handleResumeJob}
                            onDeleteJob={handleDeleteJob}
                            jobActions={jobActions}
                        />
                    )}
                </div>
            </div>

            <NewJobModal
                open={isNewPipelineModalOpen}
                setOpen={setIsNewPipelineModalOpen}
                profile={profile}
                task={selectedTask}
                onJobCreated={handleJobCreated}
            />

            <Notification
                show={!!operationSuccess}
                variant="success"
                message={operationSuccess}
                onDismiss={() => setOperationSuccess(null)}
            />
            <Notification
                show={!!operationError}
                variant="error"
                message={operationError}
                onDismiss={() => setOperationError(null)}
            />
        </div>
    );
}

export default JobsContainer;
