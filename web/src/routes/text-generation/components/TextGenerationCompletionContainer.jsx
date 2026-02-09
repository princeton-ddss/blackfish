import { useContext, useState, useCallback } from "react";
import { ServiceContext } from "@/providers/ServiceProvider";
import { ProfileContext } from "@/components/ProfileSelect";
import { streamCompletionInference } from "../lib/requests";
import {
  ArrowPathIcon,
  ClipboardDocumentIcon,
  DocumentTextIcon,
  PaperAirplaneIcon,
} from "@heroicons/react/24/outline";
import {
  readFileAsText,
  fetchRemoteText,
  prependFileContext,
  getTextFileAcceptString,
  MAX_TEXT_FILE_SIZE,
  TEXT_FILE_EXTENSIONS,
} from "../lib/fileUtils";
import AttachmentMenu from "./AttachmentMenu";
import FileAttachmentList from "./FileAttachmentList";
import FileSelectModal from "@/components/FileSelectModal";
import Notification from "@/components/Notification";
import { ServiceStatus } from "@/lib/util";
import PropTypes from "prop-types";


/**
 * Text generation prompt input component.
 * @param {object} options
 * @param {string} options.prompt
 * @param {Function} options.setPrompt
 * @param {Function} options.handleSubmit
 * @param {object} options.selectedService
 * @param {JSX.Element} options.toolbar
 * @param {Array} options.attachedFiles
 * @param {Function} options.onRemoveFile
 * @param {Function} options.onFileError
 * @param {object} options.profile
 * @param {Function} options.onFileBrowserUpload
 * @param {Function} options.onFileRemoteSelect
 * @return {JSX.Element}
 */
function TextGenerationPromptInput({
  prompt,
  setPrompt,
  handleSubmit,
  selectedService,
  toolbar,
  attachedFiles,
  onRemoveFile,
  onFileError,
  profile,
  onFileBrowserUpload,
  onFileRemoteSelect,
}) {
  /**
   * Set input value in React state and session storage.
   * @param {string} value
   */
  function handleChange(value) {
    setPrompt(value || "");
    sessionStorage.setItem("tgci", value || "");
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <label className="block text-sm font-medium leading-6 text-gray-900 dark:text-gray-100">
          Prompt
        </label>
        {toolbar}
      </div>

      <div className="flex items-start space-x-4">
        <div className="min-w-0 flex-1">
          <form action="#" onSubmit={handleSubmit} className="relative">
            <div className="rounded-lg bg-white dark:bg-gray-700 outline outline-1 -outline-offset-1 outline-gray-300 dark:outline-gray-600 shadow-md">
              {/* File attachments preview */}
              {attachedFiles.length > 0 && (
                <div className="px-4 pt-2 border-b border-gray-200 dark:border-gray-600">
                  <FileAttachmentList
                    files={attachedFiles}
                    onRemove={onRemoveFile}
                  />
                </div>
              )}

              <label htmlFor="text-generation-text-input" className="sr-only">
                Prompt anything
              </label>
              <textarea
                id="text-generation-text-input"
                name="text-generation-text-input"
                rows={10}
                placeholder="Orcas are awesome because..."
                value={prompt}
                onChange={(event) => handleChange(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && event.shiftKey) {
                    // Allow new line
                    return;
                  } else if (event.key === "Enter") {
                    event.preventDefault();
                    handleSubmit(event);
                  }
                }}
                className="block w-full resize-none bg-transparent px-4 py-3 text-sm text-gray-900 dark:text-gray-100 placeholder:text-gray-400 dark:placeholder:text-gray-500 border-0  focus:border-0 focus:outline-none focus:ring-0 sm:text-sm/6 overflow-visible"
              />

              {/* Spacer element to match the height of the toolbar */}
              <div aria-hidden="true" className="py-2">
                {/* Matches height of button in toolbar (1px border + 36px content height) */}
                <div className="py-px">
                  <div className="h-9" />
                </div>
              </div>
            </div>

            <div className="absolute inset-x-0 bottom-0 flex justify-between py-2 pl-3 pr-2">
              <div className="flex items-center">
                {/* File attachment menu */}
                <AttachmentMenu
                  accept={getTextFileAcceptString()}
                  maxFileSize={MAX_TEXT_FILE_SIZE}
                  icon={DocumentTextIcon}
                  label="Attach file"
                  profile={profile}
                  onBrowserUpload={onFileBrowserUpload}
                  onRemoteSelect={onFileRemoteSelect}
                  onError={onFileError}
                />
              </div>
              <div className="shrink-0">
                <button
                  type="submit"
                  disabled={!selectedService || selectedService.status !== ServiceStatus.HEALTHY}
                  onClick={() => {
                    console.log("Submit button clicked:", prompt);
                  }}
                  className="inline-flex items-center rounded-full bg-white dark:bg-gray-600 p-2 text-sm font-semibold text-gray-900 dark:text-gray-100 border border-gray-300 dark:border-gray-500 shadow-sm hover:bg-gray-100 dark:hover:bg-gray-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-gray-600 disabled:text-gray-400 disabled:opacity-50 disabled:hover:bg-white dark:disabled:hover:bg-gray-600 disabled:border-gray-200 dark:disabled:border-gray-600 disabled:shadow-none"
                >
                  <PaperAirplaneIcon className="size-5" />
                </button>
              </div>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

TextGenerationPromptInput.propTypes = {
  prompt: PropTypes.string,
  setPrompt: PropTypes.func,
  handleSubmit: PropTypes.func,
  selectedService: PropTypes.object,
  toolbar: PropTypes.node,
  attachedFiles: PropTypes.array,
  onRemoveFile: PropTypes.func,
  onFileError: PropTypes.func,
  profile: PropTypes.object,
  onFileBrowserUpload: PropTypes.func,
  onFileRemoteSelect: PropTypes.func,
};

/**
 * Text generation response output component.
 * @param {object} options
 * @param {string} options.content
 * @param {Function} options.handleSubmit
 * @param {object} options.selectedService
 * @return {JSX.Element}
 */
function TextGenerationResponseOutput({
  content,
  handleSubmit,
  selectedService,
}) {
  if (content && content.length > 0) {
    try {
      sessionStorage.setItem("tgco", content);
    } catch(error) {
      console.error(error);
    };
    return (
      <div>
        {/* TODO: display loading in case first token is slow... */}
        <div className="mt-8">
          <div className="block w-full max-w-4xl overflow-y-auto bg-white dark:bg-transparent text-sm/6 text-gray-900 dark:text-gray-100 rounded-lg ml-1">
            {content}
          </div>
        </div>
        <div className="flex flex-row h-8 mt-1">
          <button
            onClick={() => {
              navigator.clipboard
                .writeText(content)
                .then(console.log("copied assistant message"))
                .catch((err) => {
                  console.error("Failed to copy content: ", err);
                });
            }}
          >
            <ClipboardDocumentIcon className="w-5 h-5 text-gray-600 dark:text-gray-400 hover:text-gray-400 dark:hover:text-gray-300 m-0.5" />
          </button>
          <button
            disabled={!selectedService || selectedService.status !== ServiceStatus.HEALTHY}
            onClick={handleSubmit}
          >
            <ArrowPathIcon className="w-5 h-5 text-gray-600 dark:text-gray-400 hover:text-gray-400 dark:hover:text-gray-300 m-0.5" />
          </button>
        </div>
      </div>
    );
  }
}

TextGenerationResponseOutput.propTypes = {
  content: PropTypes.string,
  handleSubmit: PropTypes.func,
  selectedService: PropTypes.object,
};

/**
 * Text generation completion container component.
 * @param {object} options
 * @param {object} options.parameters
 * @param {JSX.Element} options.toolbar
 * @return {JSX.Element}
 */
function TextGenerationCompletionContainer({ parameters, toolbar }) {
  const { selectedService } = useContext(ServiceContext);
  const { profile } = useContext(ProfileContext);
  const [prompt, setPrompt] = useState(
    sessionStorage.getItem("tgci") || ""
  );
  const [response, setResponse] = useState(
    sessionStorage.getItem("tgco") || ""
  );
  const [isLoading, setIsLoading] = useState(false);
  const [attachedFiles, setAttachedFiles] = useState([]);
  const [fileBrowserOpen, setFileBrowserOpen] = useState(false);
  const [fileError, setFileError] = useState(null);

  // File attachment handlers
  const handleFileBrowserUpload = useCallback(async (files) => {
    for (const file of files) {
      try {
        const content = await readFileAsText(file);
        setAttachedFiles((prev) => [
          ...prev,
          {
            source: "browser",
            file: file,
            name: file.name,
            content: content,
          },
        ]);
      } catch (error) {
        console.error("Failed to read file:", error);
        setFileError({ fileName: file.name, message: "Failed to read file" });
        setTimeout(() => setFileError(null), 5000);
      }
    }
  }, []);

  const handleFileRemoteSelect = useCallback(async (fileInfo) => {
    try {
      const content = await fetchRemoteText(fileInfo.path, fileInfo.profile);
      const fileName = fileInfo.path.split("/").pop();
      setAttachedFiles((prev) => [
        ...prev,
        {
          source: "remote",
          path: fileInfo.path,
          profile: fileInfo.profile,
          name: fileName,
          content: content,
        },
      ]);
    } catch (error) {
      console.error("Failed to fetch remote file:", error);
      const fileName = fileInfo.path.split("/").pop();
      setFileError({ fileName, message: error.message });
      setTimeout(() => setFileError(null), 5000);
    }
  }, []);

  const handleRemoveFile = (index) => {
    setAttachedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleFileError = useCallback((fileName, errorMessage) => {
    setFileError({ fileName, message: errorMessage });
    setTimeout(() => setFileError(null), 5000);
  }, []);

  const handleSubmit = async (event) => {
    event.preventDefault();

    // Prepend file context to the prompt
    const promptWithFileContext = prependFileContext(prompt, attachedFiles);
    const textInput = promptWithFileContext === "" ? "Write me a haiku about orcas." : promptWithFileContext;

    setIsLoading(true);
    setResponse("");
    sessionStorage.setItem("tgco", "");

    const stream = streamCompletionInference(
      selectedService,
      textInput,
      {
        ...parameters,
        stream: true,
      },
      true
    );

    const data = await stream.next();
    setIsLoading(false);
    const text = data.value
      .map((x) => x.choices[0].text)
      .join("")
      .trimStart();
    setResponse((prevResponse) => prevResponse + text);

    for await (const data of stream) {
      const text = data.map((x) => x.choices[0].text).join("");
      setResponse((prevOutput) => prevOutput + text);
    }
  };

  return (
    <div className="flex flex-col grow pt-2 bg-white dark:bg-gray-800">
      <TextGenerationPromptInput
        prompt={prompt || ""}
        setPrompt={setPrompt}
        handleSubmit={handleSubmit}
        selectedService={selectedService}
        isLoading={isLoading}
        toolbar={toolbar}
        attachedFiles={attachedFiles}
        onRemoveFile={handleRemoveFile}
        onFileError={handleFileError}
        profile={profile}
        onFileBrowserUpload={handleFileBrowserUpload}
        onFileRemoteSelect={() => setFileBrowserOpen(true)}
      />
      <TextGenerationResponseOutput
        content={response || ""}
        handleSubmit={handleSubmit}
        selectedService={selectedService}
        isLoading={isLoading}
      />

      {/* Text file browser modal */}
      <FileSelectModal
        open={fileBrowserOpen}
        setOpen={setFileBrowserOpen}
        profile={profile}
        onSelect={(file) => handleFileRemoteSelect({ path: file.path, profile: file.profile })}
        title="Select a file"
        acceptedExtensions={TEXT_FILE_EXTENSIONS}
        extensionErrorMessage="Please select a text file (txt, md, json, py, js, etc.)"
      />

      <Notification
        show={!!fileError}
        variant="error"
        message="Failed to attach file"
        detail={fileError ? `${fileError.fileName}: ${fileError.message}` : ""}
        onDismiss={() => setFileError(null)}
      />
    </div>
  );
}

TextGenerationCompletionContainer.propTypes = {
  parameters: PropTypes.object,
  toolbar: PropTypes.node,
};

export default TextGenerationCompletionContainer;
