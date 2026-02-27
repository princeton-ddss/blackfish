import { useContext, useState } from "react";
import { ProfileContext } from "@/components/ProfileSelect";
import { useJobs } from "@/lib/loaders";
import { stopJob, deleteJob } from "@/lib/requests";
import JobsTable from "./JobsTable";
import JobResultsTable from "./JobResultsTable";
import JobDetailsPanel from "./JobDetailsPanel";
import ResultPreview from "./ResultPreview";
import NewJobModal from "./NewJobModal";

// Mock data for development - matches API BatchJob structure
const MOCK_JOBS = [
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
    const { jobs: apiJobs, isLoading, mutate } = useJobs(profile);
    const [useMockData, setUseMockData] = useState(false);
    const [selectedJobId, setSelectedJobId] = useState(null);
    const [selectedResult, setSelectedResult] = useState(null);
    const [viewingResults, setViewingResults] = useState(false);
    const [isNewPipelineModalOpen, setIsNewPipelineModalOpen] = useState(false);
    const [selectedTask, setSelectedTask] = useState(null);
    const [jobActionInProgress, setJobActionInProgress] = useState(null); // job id being stopped/deleted

    const jobs = useMockData ? MOCK_JOBS : apiJobs;

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

    const handleJobCreated = () => {
        // Refetch jobs from API
        mutate();
    };

    const handleStopJob = async (job) => {
        setJobActionInProgress(job.id);
        try {
            await stopJob(job.id);
            mutate();
        } catch (err) {
            console.error("Failed to stop job:", err);
        } finally {
            setJobActionInProgress(null);
        }
    };

    const handleDeleteJob = async (job) => {
        setJobActionInProgress(job.id);
        try {
            await deleteJob(job.id);
            // Clear selection if deleted job was selected
            if (selectedJobId === job.id) {
                setSelectedJobId(null);
            }
            mutate();
        } catch (err) {
            console.error("Failed to delete job:", err);
        } finally {
            setJobActionInProgress(null);
        }
    };

    const jobResults = selectedJob ? MOCK_RESULTS[selectedJob.id] || [] : [];

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
                        useMockData={useMockData}
                        setUseMockData={setUseMockData}
                    />
                )}
            </div>
            <div className="w-full lg:flex-1 lg:min-w-[24rem] mb-2">
                <div className="flex items-center justify-between mb-2 h-9">
                    <label className="font-medium text-sm leading-6 text-gray-900 dark:text-gray-100">
                        {showResultPreview ? "Result Preview" : "Job Details"}
                    </label>
                </div>
                <div className="ring-1 ring-gray-300 dark:ring-gray-600 rounded-lg lg:h-[calc(100vh-11rem)] overflow-y-auto">
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
                            onDeleteJob={handleDeleteJob}
                            jobActionInProgress={jobActionInProgress}
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
        </div>
    );
}

export default JobsContainer;
