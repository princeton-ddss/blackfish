import { useContext, useState } from "react";
import { ProfileContext } from "@/components/ProfileSelect";
import JobsTable from "./JobsTable";
import JobResultsTable from "./JobResultsTable";
import JobDetailsPanel from "./JobDetailsPanel";
import ResultPreview from "./ResultPreview";

// Mock data for development
const mockJobs = [
    {
        id: "job-001",
        name: "Batch Translation - French",
        submitted_at: "2024-01-15T10:30:00Z",
        status: "done",
        completed: 50,
        remaining: 0,
        failed: 2,
        slurm: {
            memory: "32GB",
            cpus: 4,
            gpus: 1,
            partition: "gpu",
            time_limit: "4:00:00",
        },
        task: {
            model: "meta-llama/Llama-2-7b-chat-hf",
            revision: "main",
            prompt: "Translate the following text to French:",
            temperature: 0.3,
            max_tokens: 512,
        },
    },
    {
        id: "job-002",
        name: "Audio Transcription",
        submitted_at: "2024-01-15T14:45:00Z",
        status: "running",
        completed: 23,
        remaining: 77,
        failed: 0,
        slurm: {
            memory: "16GB",
            cpus: 2,
            gpus: 1,
            partition: "gpu",
            time_limit: "2:00:00",
        },
        task: {
            model: "openai/whisper-large-v3",
            revision: "main",
            prompt: "Transcribe the audio file.",
            temperature: 0.0,
            max_tokens: 1024,
        },
    },
    {
        id: "job-003",
        name: "Document Summarization",
        submitted_at: "2024-01-14T09:00:00Z",
        status: "error",
        completed: 15,
        remaining: 0,
        failed: 35,
        slurm: {
            memory: "64GB",
            cpus: 8,
            gpus: 2,
            partition: "gpu-large",
            time_limit: "8:00:00",
        },
        task: {
            model: "mistralai/Mixtral-8x7B-Instruct-v0.1",
            revision: "main",
            prompt: "Summarize the following document in 3 sentences:",
            temperature: 0.5,
            max_tokens: 256,
        },
    },
    {
        id: "job-004",
        name: "Code Review Analysis",
        submitted_at: "2024-01-16T08:00:00Z",
        status: "submitted",
        completed: 0,
        remaining: 100,
        failed: 0,
        slurm: {
            memory: "32GB",
            cpus: 4,
            gpus: 1,
            partition: "gpu",
            time_limit: "4:00:00",
        },
        task: {
            model: "codellama/CodeLlama-34b-Instruct-hf",
            revision: "main",
            prompt: "Review the following code for potential issues:",
            temperature: 0.1,
            max_tokens: 1024,
        },
    },
];

const mockResults = {
    "job-001": [
        {
            id: "result-001",
            input_file: "document_1.txt",
            output_file: "document_1_fr.txt",
            started_at: "2024-01-15T10:30:05Z",
            finished_at: "2024-01-15T10:30:12Z",
            success: true,
        },
        {
            id: "result-002",
            input_file: "document_2.txt",
            output_file: "document_2_fr.txt",
            started_at: "2024-01-15T10:30:12Z",
            finished_at: "2024-01-15T10:30:18Z",
            success: true,
        },
        {
            id: "result-003",
            input_file: "document_3.txt",
            output_file: null,
            started_at: "2024-01-15T10:30:18Z",
            finished_at: "2024-01-15T10:30:25Z",
            success: false,
            error: "File encoding not supported",
        },
    ],
    "job-002": [
        {
            id: "result-004",
            input_file: "recording_1.mp3",
            output_file: "recording_1.txt",
            started_at: "2024-01-15T14:45:05Z",
            finished_at: "2024-01-15T14:46:30Z",
            success: true,
        },
    ],
};

function JobsContainer() {
    const { profile } = useContext(ProfileContext);
    const [selectedJob, setSelectedJob] = useState(null);
    const [selectedResult, setSelectedResult] = useState(null);
    const [viewingResults, setViewingResults] = useState(false);

    // Click on job row to show details (without drilling in)
    const handleJobClick = (job) => {
        setSelectedJob(job);
        setSelectedResult(null);
    };

    // Click ">" to drill into job results
    const handleJobDrillIn = (job) => {
        setSelectedJob(job);
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

    const jobResults = selectedJob ? mockResults[selectedJob.id] || [] : [];

    // Determine what to show in right column
    const showResultPreview = selectedResult !== null;
    const showJobDetails = selectedJob !== null && !showResultPreview;

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
                        jobs={mockJobs}
                        onJobClick={handleJobClick}
                        onJobDrillIn={handleJobDrillIn}
                        selectedJob={selectedJob}
                    />
                )}
            </div>
            <div className="w-full lg:flex-1 lg:min-w-[24rem] mb-2 lg:mr-6">
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
                        <JobDetailsPanel job={selectedJob} />
                    )}
                </div>
            </div>
        </div>
    );
}

export default JobsContainer;
