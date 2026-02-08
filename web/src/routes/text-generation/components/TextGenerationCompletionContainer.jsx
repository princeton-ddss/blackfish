import { useContext, useState, useCallback } from "react";
import { ServiceContext } from "@/providers/ServiceProvider";
import { ProfileContext } from "@/components/ProfileSelect";
import { streamCompletionInference } from "../lib/requests";
import { fileToBase64, buildMultimodalContent } from "../lib/imageUtils";
import {
  ArrowPathIcon,
  ClipboardDocumentIcon,
  PaperAirplaneIcon,
} from "@heroicons/react/24/outline";
import AttachmentMenu from "./AttachmentMenu";
import ImageAttachmentList from "./ImageAttachmentList";
import FileSelectModal from "@/components/FileSelectModal";
import Notification from "@/components/Notification";
import { IMAGE_EXTENSIONS } from "../lib/imageUtils";

import { ServiceStatus } from "@/lib/util";
import PropTypes from "prop-types";


/**
 * Text generation prompt input component.
 * @param {object} options
 * @param {string} options.prompt
 * @param {Function} options.setPrompt
 * @param {Function} options.handleSubmit
 * @param {object} options.selectedService
 * @param {boolean} options.isLoading
 * @param {Array} options.attachedImages
 * @param {Function} options.onRemoveImage
 * @param {Function} options.onImageError
 * @param {object} options.profile
 * @param {Function} options.onBrowserUpload
 * @param {Function} options.onRemoteSelect
 * @return {JSX.Element}
 */
function TextGenerationPromptInput({
  prompt,
  setPrompt,
  handleSubmit,
  selectedService,
  toolbar,
  attachedImages,
  onRemoveImage,
  onImageError,
  profile,
  onBrowserUpload,
  onRemoteSelect,
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

      {/* TODO: disable while isLoading... */}

      <div className="flex items-start space-x-4">
        <div className="min-w-0 flex-1">
          <form action="#" onSubmit={handleSubmit} className="relative">
            <div className="rounded-lg bg-white dark:bg-gray-700 outline outline-1 -outline-offset-1 outline-gray-300 dark:outline-gray-600 shadow-md">
              {/* Image attachments preview */}
              {attachedImages.length > 0 && (
                <div className="px-3 pt-2 border-b border-gray-200 dark:border-gray-600">
                  <ImageAttachmentList
                    images={attachedImages}
                    onRemove={onRemoveImage}
                    onImageError={onImageError}
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
              <div className="flex items-center space-x-5">
                <div className="flex items-center">
                  <AttachmentMenu
                    profile={profile}
                    onBrowserUpload={onBrowserUpload}
                    onRemoteSelect={onRemoteSelect}
                    onError={onImageError}
                  />
                </div>
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
  isLoading: PropTypes.bool,
  toolbar: PropTypes.node,
  attachedImages: PropTypes.array,
  onRemoveImage: PropTypes.func,
  onImageError: PropTypes.func,
  profile: PropTypes.object,
  onBrowserUpload: PropTypes.func,
  onRemoteSelect: PropTypes.func,
};

/**
 * Text generation response output component.
 * @param {object} options
 * @param {string} options.content
 * @param {Function} options.handleSubmit
 * @param {object} options.selectedService
 * @param {boolean} options.isLoading
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
  isLoading: PropTypes.bool
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
  const [attachedImages, setAttachedImages] = useState([]);
  const [fileBrowserOpen, setFileBrowserOpen] = useState(false);
  const [imageError, setImageError] = useState(null);

  const handleBrowserUpload = (files) => {
    const newImages = files.map((file) => ({
      source: "browser",
      file: file,
    }));
    setAttachedImages((prev) => [...prev, ...newImages]);
  };

  const handleRemoteSelect = (image) => {
    setAttachedImages((prev) => [...prev, image]);
  };

  const handleRemoveImage = (index) => {
    setAttachedImages((prev) => prev.filter((_, i) => i !== index));
  };

  const handleImageError = useCallback((fileName, errorMessage) => {
    setImageError({ fileName, message: errorMessage });
    // Auto-dismiss after 5 seconds
    setTimeout(() => setImageError(null), 5000);
  }, []);

  const handleSubmit = async (event) => {
    event.preventDefault();

    const textInput = prompt === "" ? "Write me a haiku about orcas." : prompt;

    setIsLoading(true);
    setResponse("");
    sessionStorage.setItem("tgco", "");

    // Build multimodal content if images are attached
    let requestPrompt = textInput;
    if (attachedImages.length > 0) {
      try {
        const imageUrls = await Promise.all(
          attachedImages.map(async (img) => {
            if (img.source === "browser") {
              // Browser files must be converted to base64
              return await fileToBase64(img.file);
            } else {
              // Remote files: pass file path directly (vLLM can read from filesystem)
              return `file://${img.path}`;
            }
          })
        );
        requestPrompt = buildMultimodalContent(textInput, imageUrls);
      } catch (error) {
        console.error("Failed to convert images:", error);
        setIsLoading(false);
        return;
      }
    }

    const stream = streamCompletionInference(
      selectedService,
      requestPrompt,
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
        attachedImages={attachedImages}
        onRemoveImage={handleRemoveImage}
        onImageError={handleImageError}
        profile={profile}
        onBrowserUpload={handleBrowserUpload}
        onRemoteSelect={() => setFileBrowserOpen(true)}
      />
      <TextGenerationResponseOutput
        content={response || ""}
        handleSubmit={handleSubmit}
        selectedService={selectedService}
        isLoading={isLoading}
      />

      <FileSelectModal
        open={fileBrowserOpen}
        setOpen={setFileBrowserOpen}
        profile={profile}
        onSelect={(file) => handleRemoteSelect({ source: "remote", path: file.path, profile: file.profile })}
        title="Select an image"
        acceptedExtensions={IMAGE_EXTENSIONS}
        extensionErrorMessage="Please select an image file (PNG, JPG, JPEG, GIF, BMP, TIFF, WEBP)"
      />

      <Notification
        show={!!imageError}
        variant="error"
        message="Failed to attach image"
        detail={imageError ? `${imageError.fileName}: ${imageError.message}` : ""}
        onDismiss={() => setImageError(null)}
      />
    </div>
  );
}

TextGenerationCompletionContainer.propTypes = {
  parameters: PropTypes.object,
  toolbar: PropTypes.node,
};

export default TextGenerationCompletionContainer;
