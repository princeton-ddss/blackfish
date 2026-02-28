import { useContext, useEffect, useState, useRef, useCallback } from "react";
import {
  ArrowPathIcon,
  CheckIcon,
  ClipboardDocumentIcon,
  DocumentTextIcon,
  PaperAirplaneIcon,
  PencilIcon,
  TrashIcon,
  XMarkIcon,
  PhotoIcon,
} from "@heroicons/react/24/outline";
import { ServiceContext } from "@/providers/ServiceProvider";
import { ProfileContext } from "@/components/ProfileSelect";
import { streamChatCompletionInference } from "../lib/requests";
import {
  fileToBase64,
  buildMultimodalContent,
  extractTextFromContent,
  extractImagesFromContent,
  MAX_IMAGE_FILE_SIZE,
} from "../lib/imageUtils";
import {
  prependFileContext,
  getTextFileAcceptString,
  MAX_TEXT_FILE_SIZE,
  TEXT_FILE_EXTENSIONS,
} from "../lib/fileUtils";
import { useFileAttachments } from "../lib/useFileAttachments";
import AttachmentMenu from "./AttachmentMenu";
import ImageAttachmentList from "./ImageAttachmentList";
import FileAttachmentList from "./FileAttachmentList";
import FileSelectModal from "@/components/FileSelectModal";
import Notification from "@/components/Notification";
import { IMAGE_EXTENSIONS } from "../lib/imageUtils";
import PropTypes from "prop-types";

const Role = {
  USER: "user",
  ASSISTANT: "assistant",
  SYSTEM: "system",
};

/**
 * Classify a streaming API error and return a user-friendly error object.
 * @param {Error} error
 * @returns {{ message: string, detail: string | null, isContextLength: boolean }}
 */
function classifyApiError(error) {
  const msg = error.message || "An unexpected error occurred.";
  const isContextLength =
    /context length|token/.test(msg) && /maximum|exceeded/.test(msg);

  if (isContextLength) {
    return {
      message: "Context length exceeded",
      detail:
        "Your conversation is too long for this model. Try clearing the conversation or reducing message length.",
      isContextLength: true,
    };
  }

  return {
    message: "Request failed",
    detail: msg,
    isContextLength: false,
  };
}

/**
 * User Message Input component.
 * @param {object} options
 * @param {string} options.message
 * @param {Function} options.onChange
 * @param {Function} options.onSubmit
 * @param {Array} options.attachedImages
 * @param {Function} options.onRemoveImage
 * @param {Function} options.onImageError
 * @param {Function} options.onImageLoad
 * @param {Array} options.attachedFiles
 * @param {Function} options.onRemoveFile
 * @param {Function} options.onFileError
 * @param {object} options.profile
 * @param {Function} options.onImageBrowserUpload
 * @param {Function} options.onImageRemoteSelect
 * @param {Function} options.onFileBrowserUpload
 * @param {Function} options.onFileRemoteSelect
 * @return {JSX.Element}
 */
function UserMessageInput({
  message,
  onChange,
  onSubmit,
  attachedImages,
  onRemoveImage,
  onImageError,
  onImageLoad,
  attachedFiles,
  onRemoveFile,
  onFileError,
  profile,
  onImageBrowserUpload,
  onImageRemoteSelect,
  onFileBrowserUpload,
  onFileRemoteSelect,
}) {
  return (
    <div className="flex items-start space-x-4 mt-auto pt-4">
      <div className="min-w-0 flex-1">
        <form action="#" onSubmit={onSubmit} className="relative">
          <div className="rounded-lg bg-white dark:bg-gray-700 outline outline-1 -outline-offset-1 outline-gray-300 dark:outline-gray-600 shadow-md overflow-visible">
            {/* Image attachments preview */}
            {attachedImages.length > 0 && (
              <div className="px-4 pt-2 border-b border-gray-200 dark:border-gray-600">
                <ImageAttachmentList
                  images={attachedImages}
                  onRemove={onRemoveImage}
                  onImageError={onImageError}
                  onImageLoad={onImageLoad}
                />
              </div>
            )}

            {/* File attachments preview */}
            {attachedFiles.length > 0 && (
              <div className="px-4 pt-2 border-b border-gray-200 dark:border-gray-600">
                <FileAttachmentList
                  files={attachedFiles}
                  onRemove={onRemoveFile}
                />
              </div>
            )}

            <label htmlFor="comment" className="sr-only">
              Ask anything
            </label>
            <textarea
              id="comment"
              name="comment"
              rows={3}
              placeholder="Why are orcas so awesome?"
              value={message && message.content || ""}
              onChange={onChange}
              onKeyDown={(event) => {
                if (event.key === "Enter" && event.shiftKey) {
                  // Allow new line
                  return;
                } else if (event.key === "Enter") {
                  event.preventDefault();
                  onSubmit(event);
                }
              }}
              className="block w-full resize-none bg-transparent px-4 py-3 text-sm text-gray-900 dark:text-gray-100 placeholder:text-gray-400 dark:placeholder:text-gray-500 border-0  focus:border-0 focus:outline-none focus:ring-0 sm:text-sm/6"
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
              <div className="flex items-center gap-2">
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
                {/* Image attachment menu */}
                <AttachmentMenu
                  accept="image/*"
                  maxFileSize={MAX_IMAGE_FILE_SIZE}
                  icon={PhotoIcon}
                  label="Attach image"
                  profile={profile}
                  onBrowserUpload={onImageBrowserUpload}
                  onRemoteSelect={onImageRemoteSelect}
                  onError={onImageError}
                />
              </div>
            </div>
            <div className="shrink-0">
              <button
                type="submit"
                disabled={message && message.content && message.content.length === 0}
                className="inline-flex items-center rounded-full bg-white dark:bg-gray-600 p-2 text-sm font-semibold text-gray-900 dark:text-gray-100 border border-gray-300 dark:border-gray-500 shadow-sm hover:bg-gray-100 dark:hover:bg-gray-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-gray-600 disabled:text-gray-400 disabled:opacity-50 disabled:hover:bg-white dark:disabled:hover:bg-gray-600 disabled:border-gray-200 dark:disabled:border-gray-600 disabled:shadow-none"
              >
                <PaperAirplaneIcon className="size-5" />
                <span className="sr-only">Submit</span>
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}

UserMessageInput.propTypes = {
  message: PropTypes.object,
  onChange: PropTypes.func,
  onSubmit: PropTypes.func,
  attachedImages: PropTypes.array,
  onRemoveImage: PropTypes.func,
  onImageError: PropTypes.func,
  onImageLoad: PropTypes.func,
  attachedFiles: PropTypes.array,
  onRemoveFile: PropTypes.func,
  onFileError: PropTypes.func,
  profile: PropTypes.object,
  onImageBrowserUpload: PropTypes.func,
  onImageRemoteSelect: PropTypes.func,
  onFileBrowserUpload: PropTypes.func,
  onFileRemoteSelect: PropTypes.func,
};

/**
 * Message Image component for displaying images in messages.
 * @param {object} options
 * @param {string} options.src - The base64 image source.
 * @return {JSX.Element}
 */
function MessageImage({ src }) {
  return (
    <div className="relative w-20 h-20 rounded-lg overflow-hidden bg-gray-100 dark:bg-gray-600 flex-shrink-0">
      <img
        src={src}
        alt="Attached image"
        className="w-full h-full object-cover"
      />
    </div>
  );
}

MessageImage.propTypes = {
  src: PropTypes.string.isRequired,
};

/**
 * User Message component.
 * @param {object} options
 * @param {object} options.message
 * @param {Function} options.onDeleteMessage
 * @param {Function} options.onEditMessage
 * @return {JSX.Element}
 */
function UserMessage({ message, onDeleteMessage, onEditMessage }) {
  const [hover, setHover] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [copied, setCopied] = useState(false);

  // Extract text and images from content
  // Use _displayText if available (when files were attached), otherwise extract from content
  const textContent = message._displayText !== undefined
    ? message._displayText
    : extractTextFromContent(message.content);
  const images = extractImagesFromContent(message.content);
  const attachedFiles = message._attachedFiles || [];
  const [content, setContent] = useState(textContent);

  // Update content when message changes
  useEffect(() => {
    setContent(message._displayText !== undefined
      ? message._displayText
      : extractTextFromContent(message.content));
  }, [message.content, message._displayText]);

  if (isEditing) {
    return (
      <div className="flex flex-row-reverse space-x-4 mt-5">
        <div className="min-w-0 max-w-xl flex-1">
          <form
            action="#"
            onSubmit={(event) => {
              event.preventDefault();
              // When editing, preserve images if any
              if (images.length > 0) {
                onEditMessage(buildMultimodalContent(content, images));
              } else {
                onEditMessage(content);
              }
              setIsEditing(false);
            }}
            className="relative"
          >
            <div className="rounded-lg bg-gray-100 dark:bg-gray-700 shadow-md">
              {/* Display attached images (read-only) */}
              {images.length > 0 && (
                <div className="px-4 pt-2 border-b border-gray-200 dark:border-gray-600">
                  <div className="flex gap-2 flex-wrap py-2">
                    {images.map((src, idx) => (
                      <MessageImage key={idx} src={src} />
                    ))}
                  </div>
                </div>
              )}
              {/* Display attached files as chips (read-only) */}
              {attachedFiles.length > 0 && (
                <div className="px-4 pt-2 border-b border-gray-200 dark:border-gray-600">
                  <FileAttachmentList
                    files={attachedFiles.map(f => ({ source: "browser", name: f.name, content: f.content }))}
                    readOnly
                  />
                </div>
              )}
              <label htmlFor="comment" className="sr-only">
                Edit message
              </label>
              <textarea
                id="edit-message"
                name="edit-message"
                rows={3}
                defaultValue={content}
                onChange={(event) => {
                  setContent(event.target.value);
                }}
                className="block w-full resize-none bg-transparent px-4 py-3 text-sm text-gray-900 dark:text-gray-100 placeholder:text-gray-400 dark:placeholder:text-gray-500 border-0  focus:border-0 focus:outline-none focus:ring-0 sm:text-sm"
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
              <div className="flex items-center space-x-5"></div>
              <div className="shrink-0">
                <button
                  type="button"
                  onClick={() => {
                    console.log("cancel button clicked");
                    setIsEditing(false);
                    setContent(textContent);
                  }}
                  className="inline-flex items-center rounded-full bg-transparent mr-2 p-2 text-sm font-semibold text-gray-900 dark:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-600 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-gray-600 disabled:text-gray-400 disabled:opacity-50 disabled:hover:bg-white dark:disabled:hover:bg-gray-700 disabled:border-gray-200 disabled:shadow-none"
                >
                  <XMarkIcon className="size-5 text-gray-900 dark:text-gray-100 hover:text-gray-400" />
                  <span className="sr-only">Cancel</span>
                </button>
                <button
                  type="submit"
                  disabled={content.length === 0}
                  className="inline-flex items-center rounded-full bg-white dark:bg-gray-600 p-2 text-sm font-semibold text-gray-900 dark:text-gray-100 border border-gray-300 dark:border-gray-500 shadow-sm hover:bg-gray-100 dark:hover:bg-gray-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-gray-600 disabled:text-gray-400 disabled:opacity-50 disabled:hover:bg-white dark:disabled:hover:bg-gray-600 disabled:border-gray-200 dark:disabled:border-gray-600 disabled:shadow-none"
                >
                  <CheckIcon className="size-5" />
                  <span className="sr-only">Save</span>
                </button>
              </div>
            </div>
          </form>
        </div>
      </div>
    );
  } else {
    return (
      <div
        onMouseOver={() => {
          setHover(true);
        }}
        onMouseLeave={() => {
          setHover(false);
        }}
        className="mt-3"
      >
        <div className="flex flex-row-reverse">
          <div className="max-w-xl content-end bg-gray-100 dark:bg-gray-700 text-sm text-gray-900 dark:text-gray-100 rounded-lg px-4 py-3 shadow-sm">
            {/* Display images if any */}
            {images.length > 0 && (
              <div className="flex gap-2 flex-wrap mb-2">
                {images.map((src, idx) => (
                  <MessageImage key={idx} src={src} />
                ))}
              </div>
            )}
            {/* Display attached files as chips */}
            {attachedFiles.length > 0 && (
              <div className="mb-2">
                <FileAttachmentList
                  files={attachedFiles.map(f => ({ source: "browser", name: f.name, content: f.content }))}
                  readOnly
                />
              </div>
            )}
            {textContent}
          </div>
        </div>
        <div className={`flex flex-row-reverse items-center mt-2 transition-opacity duration-150 ${hover ? "opacity-100" : "opacity-0"}`}>
          <button
            onClick={() => {
              console.log("deleting user message");
              onDeleteMessage();
            }}
            className="group relative p-1 rounded-md text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700"
          >
            <XMarkIcon className="w-5 h-5" />
            <span className="absolute top-full left-1/2 -translate-x-1/2 mt-0.5 text-xs whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none">Delete</span>
          </button>
          <button
            onClick={() => {
              console.log("edit button clicked");
              setIsEditing(true);
            }}
            className="group relative p-1 rounded-md text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700"
          >
            <PencilIcon className="w-5 h-5" />
            <span className="absolute top-full left-1/2 -translate-x-1/2 mt-0.5 text-xs whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none">Edit</span>
          </button>
          <button
            onClick={() => {
              navigator.clipboard
                .writeText(textContent)
                .then(() => {
                  setCopied(true);
                  setTimeout(() => setCopied(false), 2000);
                })
                .catch((err) => {
                  console.error("Failed to copy content: ", err);
                });
            }}
            className="group relative p-1 rounded-md text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700"
          >
            {copied ? <CheckIcon className="w-5 h-5" /> : <ClipboardDocumentIcon className="w-5 h-5" />}
            <span className="absolute top-full left-1/2 -translate-x-1/2 mt-0.5 text-xs whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none">{copied ? "Copied" : "Copy"}</span>
          </button>
        </div>
      </div>
    );
  }
}

UserMessage.propTypes = {
  message: PropTypes.object,
  onDeleteMessage: PropTypes.func,
  onEditMessage: PropTypes.func,
};

/**
 * Assistant Message component.
 * @param {object} options
 * @param {object} options.message
 * @param {Function} options.handleResubmit
 * @param {JSX.Element}
 */
function AssisantMessage({ message, handleResubmit }) {
  const [copied, setCopied] = useState(false);
  return (
    <div className="mt-3 max-w-xl">
      <div className="flex flex-row">
        <div className="w-fit content-end bg-white dark:bg-transparent text-sm text-gray-900 dark:text-gray-100 rounded-lg ml-2">
          {message.content}
        </div>
      </div>
      <div className="flex flex-row items-center mt-2 ml-1">
        <button
          onClick={() => {
            navigator.clipboard
              .writeText(message.content)
              .then(() => {
                setCopied(true);
                setTimeout(() => setCopied(false), 2000);
              })
              .catch((err) => {
                console.error("Failed to copy content: ", err);
              });
          }}
          className="group relative px-1 py-0.5 text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300"
        >
          {copied ? <CheckIcon className="w-5 h-5" /> : <ClipboardDocumentIcon className="w-5 h-5" />}
          <span className="absolute top-full left-1/2 -translate-x-1/2 mt-0.5 text-xs whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none">{copied ? "Copied" : "Copy"}</span>
        </button>
        <button
          onClick={handleResubmit}
          className="group relative px-1 py-0.5 text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300"
        >
          <ArrowPathIcon className="w-5 h-5" />
          <span className="absolute top-full left-1/2 -translate-x-1/2 mt-0.5 text-xs whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none">Regenerate</span>
        </button>
      </div>
    </div>
  );
}

AssisantMessage.propTypes = {
  message: PropTypes.object,
  handleResubmit: PropTypes.func,
};

/**
 * Message component.
 * @param {object} options
 * @param {object} options.message
 * @param {Function} options.onEditMessage
 * @param {Function} options.onDeleteMessage
 * @param {Function} options.handleResubmit
 * @return {JSX.Element}
 */
function Message({
  message,
  onEditMessage,
  onDeleteMessage,
  handleResubmit,
}) {
  if (message.role === Role.USER) {
    return (
      <UserMessage
        message={message}
        onEditMessage={onEditMessage}
        onDeleteMessage={onDeleteMessage}
      />
    );
  } else if (message.role === Role.ASSISTANT) {
    return (
      <AssisantMessage
        message={message}
        handleResubmit={handleResubmit}
      />
    );
  }
}

Message.propTypes = {
  message: PropTypes.object,
  onEditMessage: PropTypes.func,
  onDeleteMessage: PropTypes.func,
  handleResubmit: PropTypes.func,
};

/**
 * Message List component.
 * @param {object} options
 * @param {Array} options.messages
 * @param {Function} options.setMessages
 * @param {Function} options.handleResubmit
 * @param {JSX.Element} options.elementRef
 * @param {boolean} options.isWaitingForResponse
 * @return {JSX.Element}
 */
function MessageList({ messages, setMessages, handleResubmit, elementRef, isWaitingForResponse }) {
  try {
    sessionStorage.setItem("tgcc-ml", JSON.stringify(messages));
  } catch (error) {
    console.error(error);
  };
  return (
    <div className="flex-1 min-h-0 overflow-y-auto px-8">
      {messages.map((message, index) => (
        <Message
          key={index}
          message={message}
          onEditMessage={(newContent) => {
            console.log("editing message:", message);
            setMessages((messages) =>
              messages.map((m, i) => {
                if (i === index) {
                  // Extract text for display if content is multimodal (has images)
                  const displayText = typeof newContent === 'string'
                    ? newContent
                    : extractTextFromContent(newContent);

                  // Re-add file context if files were attached
                  let finalContent = newContent;
                  if (m._attachedFiles && m._attachedFiles.length > 0) {
                    const textWithFileContext = prependFileContext(displayText, m._attachedFiles);
                    // If there are images, rebuild multimodal content with file context
                    if (typeof newContent !== 'string') {
                      const images = extractImagesFromContent(newContent);
                      finalContent = buildMultimodalContent(textWithFileContext, images);
                    } else {
                      finalContent = textWithFileContext;
                    }
                  }

                  return {
                    ...m,
                    content: finalContent,
                    _displayText: displayText,
                    // Preserve _attachedFiles
                  };
                }
                return m;
              })
            );
            // TODO: recursively submit this and all subsequent user messages
          }}
          onDeleteMessage={() => {
            console.log("delete message:", message);
            setMessages((messages) =>
              messages.filter((_, i) => i !== index && i !== index + 1)
            );
          }}
          handleResubmit={(event) => handleResubmit(event, index)}
        />
      ))}
      {isWaitingForResponse && (
        <div className="py-6">
          <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
            <div className="flex gap-1">
              <span className="w-2 h-2 bg-gray-400 dark:bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: "0ms" }}></span>
              <span className="w-2 h-2 bg-gray-400 dark:bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: "150ms" }}></span>
              <span className="w-2 h-2 bg-gray-400 dark:bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: "300ms" }}></span>
            </div>
          </div>
        </div>
      )}
      <div ref={elementRef}></div>
    </div>
  );
}

MessageList.propTypes = {
  messages: PropTypes.array,
  setMessages: PropTypes.func,
  handleResubmit: PropTypes.func,
  elementRef: PropTypes.object,
  isWaitingForResponse: PropTypes.bool,
};

/**
 * Text Generation Chat Container component.
 * @param {object} options
 * @param {object} options.parameters
 * @param {object} options.systemMessage
 * @param {JSX.Element} options.toolbar
 * @return {JSX.Element}
 */
export default function TextGenerationChatContainer({ parameters, systemMessage, toolbar }) {
  const { selectedService } = useContext(ServiceContext);
  const { profile } = useContext(ProfileContext);
  const storedMessages = sessionStorage.getItem("tgcc-ml");
  const [messages, setMessages] = useState(
    storedMessages ? JSON.parse(storedMessages) : []
  );
  const [userMessage, setUserMessage] = useState({
    role: Role.USER,
    content: sessionStorage.getItem("tgcc-um") || "",
  });
  const [attachedImages, setAttachedImages] = useState([]);
  const [imageBrowserOpen, setImageBrowserOpen] = useState(false);
  const [imageError, setImageError] = useState(null);
  const [apiError, setApiError] = useState(null);
  const [isWaitingForResponse, setIsWaitingForResponse] = useState(false);

  // File attachment state and handlers
  const {
    attachedFiles,
    fileBrowserOpen,
    setFileBrowserOpen,
    fileError,
    setFileError,
    handleFileBrowserUpload,
    handleFileRemoteSelect,
    handleRemoveFile,
    handleFileError,
    clearFiles,
  } = useFileAttachments();

  const elementRef = useRef(null);

  const scrollToElement = () => {
    elementRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    // TODO: only want to trigger this when the length of messages increases, i.e., a message is appended
    scrollToElement();
  }, [messages]);

  // Image attachment handlers
  const handleImageBrowserUpload = (files) => {
    const newImages = files.map((file) => ({
      source: "browser",
      file: file,
    }));
    setAttachedImages((prev) => [...prev, ...newImages]);
  };

  const handleImageRemoteSelect = (image) => {
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

  const handleImageLoad = useCallback((index, base64) => {
    // Cache the base64 data on the image object for use when submitting
    setAttachedImages((prev) =>
      prev.map((img, i) => (i === index ? { ...img, base64 } : img))
    );
  }, []);

  
  const handleSubmit = async (event) => {
    event.preventDefault();
    console.log("user message submitted");

    // Prepend file context to the message text (for LLM)
    const textWithFileContext = prependFileContext(userMessage.content, attachedFiles);

    // Build the message content (multimodal if images attached)
    let messageContent = textWithFileContext;
    if (attachedImages.length > 0) {
      try {
        const imageUrls = await Promise.all(
          attachedImages.map(async (img) => {
            if (img.source === "browser") {
              // Browser files must be converted to base64
              return await fileToBase64(img.file);
            } else {
              // Remote files: use cached base64 from preview fetch
              if (!img.base64) {
                throw new Error(`Image ${img.path} not yet loaded`);
              }
              return img.base64;
            }
          })
        );
        messageContent = buildMultimodalContent(textWithFileContext, imageUrls);
      } catch (error) {
        console.error("Failed to convert images:", error);
        return;
      }
    }

    // Store file metadata for UI display (chips), content goes to LLM
    const fileMetadata = attachedFiles.length > 0
      ? attachedFiles.map(f => ({ name: f.name, content: f.content }))
      : undefined;

    const newUserMessage = {
      role: Role.USER,
      content: messageContent,
      // UI-only fields (ignored by LLM API):
      _displayText: userMessage.content,
      _attachedFiles: fileMetadata,
    };

    // Clear any previous error
    setApiError(null);

    setMessages((messages) => [...messages, newUserMessage]);

    // Clear input and attached items after sending
    setUserMessage({ role: Role.USER, content: "" });
    sessionStorage.removeItem("tgcc-um");
    setAttachedImages([]);
    clearFiles();

    // Show loading state while waiting for first response chunk
    setIsWaitingForResponse(true);

    try {
      const stream = streamChatCompletionInference(
        selectedService,
        [systemMessage, ...messages, newUserMessage],
        {
          ...parameters,
          stream: true,
        },
        true
      );

      const data = await stream.next();
      setIsWaitingForResponse(false);
      console.debug("data:", data);
      let response = data.value
        .map((x) => x.choices[0].delta.content)
        .join("")
        .trimStart();
      setMessages((messages) => [
        ...messages.slice(0, messages.length),
        {
          role: "assistant",
          content: response,
        },
      ]);

      for await (const data of stream) {
        console.debug("data:", data);
        const text = data.map((x) => x.choices[0].delta.content).join("");
        response += text;
        console.debug("response: ", response);
        setMessages((messages) => [
          ...messages.slice(0, messages.length - 1),
          {
            role: "assistant",
            content: response,
          },
        ]);
      }
    } catch (error) {
      console.error("Chat submission error:", error);
      setIsWaitingForResponse(false);
      // Roll back the optimistically-added user message if no assistant response was started
      setMessages((prev) => {
        if (prev.length > 0 && prev[prev.length - 1].role === Role.USER) {
          return prev.slice(0, -1);
        }
        return prev;
      });
      setApiError(classifyApiError(error));
    }
  };

  const handleResubmit = async (event, index) => {
    event.preventDefault();
    console.log(`regenerating message at index ${index}`);

    setApiError(null);

    // Get messages up to (but not including) the message being regenerated
    const conversationUpToIndex = messages.slice(0, index);

    // Clear messages from the regenerated index onwards
    setMessages(conversationUpToIndex);

    // Show loading state while waiting for first response chunk
    setIsWaitingForResponse(true);

    try {
      const stream = streamChatCompletionInference(
        selectedService,
        [systemMessage, ...conversationUpToIndex],
        {
          ...parameters,
          stream: true,
        },
        true
      );

      const data = await stream.next();
      setIsWaitingForResponse(false);
      console.debug("data:", data);
      let response = data.value
        .map((x) => x.choices[0].delta.content)
        .join("")
        .trimStart();
      setMessages((messages) => [
        ...messages.slice(0, messages.length),
        {
          role: "assistant",
          content: response,
        },
      ]);

      for await (const data of stream) {
        console.debug("data:", data);
        const text = data.map((x) => x.choices[0].delta.content).join("");
        response += text;
        console.debug("response: ", response);
        setMessages((messages) => [
          ...messages.slice(0, messages.length - 1),
          {
            role: "assistant",
            content: response,
          },
        ]);
      }
    } catch (error) {
      console.error("Chat resubmit error:", error);
      setIsWaitingForResponse(false);
      setApiError(classifyApiError(error));
    }
  };

  /**
   * Set input value in React state and session storage.
   * @param {string} value
   */
  function handleUserMessageChange(value) {
    setUserMessage({
      ...userMessage,
      content: value
    });
    sessionStorage.setItem("tgcc-um", value);
  }

  function handleClearConversation() {
    if (messages.length === 0) return;
    setMessages([]);
    setUserMessage({ role: Role.USER, content: "" });
    setAttachedImages([]);
    setIsWaitingForResponse(false);
    setApiError(null);
    sessionStorage.removeItem("tgcc-ml");
    sessionStorage.removeItem("tgcc-um");
  }

  return (
    <div className="flex flex-col grow pt-2 bg-white dark:bg-gray-800 lg:h-[calc(100vh-7rem)]">
      <div className="flex items-center justify-between mb-2">
        <label className="block text-sm font-medium leading-6 text-gray-900 dark:text-gray-100">
          Chat
        </label>
        <div className="flex items-center">
          <button
            type="button"
            onClick={handleClearConversation}
            disabled={messages.length === 0}
            className="group relative p-2 text-gray-500 hover:text-red-600 hover:bg-red-50 dark:text-gray-400 dark:hover:text-red-400 dark:hover:bg-red-900/20 rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
            aria-label="Clear conversation"
          >
            <TrashIcon className="h-5 w-5" />
            <span className="absolute top-full left-1/2 -translate-x-1/2 mt-0.5 text-xs whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none">Clear chat</span>
          </button>
          {toolbar}
        </div>
      </div>
      <MessageList
        messages={messages}
        setMessages={setMessages}
        handleResubmit={handleResubmit}
        elementRef={elementRef}
        isWaitingForResponse={isWaitingForResponse}
      />

      <UserMessageInput
        message={userMessage.content ? userMessage : {
          ...userMessage,
          content: sessionStorage.getItem("tgcc-um")
        }}
        onChange={(event) => handleUserMessageChange(event.target.value)}
        onSubmit={handleSubmit}
        attachedImages={attachedImages}
        onRemoveImage={handleRemoveImage}
        onImageError={handleImageError}
        onImageLoad={handleImageLoad}
        attachedFiles={attachedFiles}
        onRemoveFile={handleRemoveFile}
        onFileError={handleFileError}
        profile={profile}
        onImageBrowserUpload={handleImageBrowserUpload}
        onImageRemoteSelect={() => setImageBrowserOpen(true)}
        onFileBrowserUpload={handleFileBrowserUpload}
        onFileRemoteSelect={() => setFileBrowserOpen(true)}
      />

      {/* Image file browser modal */}
      <FileSelectModal
        open={imageBrowserOpen}
        setOpen={setImageBrowserOpen}
        profile={profile}
        onSelect={(file) => handleImageRemoteSelect({ source: "remote", path: file.path, profile: file.profile })}
        title="Select an image"
        acceptedExtensions={IMAGE_EXTENSIONS}
        extensionErrorMessage="Please select an image file (PNG, JPG, JPEG, GIF, BMP, TIFF, WEBP)"
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
        show={!!imageError}
        variant="error"
        message="Failed to attach image"
        detail={imageError ? `${imageError.fileName}: ${imageError.message}` : ""}
        onDismiss={() => setImageError(null)}
      />

      <Notification
        show={!!fileError}
        variant="error"
        message="Failed to attach file"
        detail={fileError ? `${fileError.fileName}: ${fileError.message}` : ""}
        onDismiss={() => setFileError(null)}
      />

      <Notification
        show={!!apiError}
        variant="error"
        message={apiError ? apiError.message : ""}
        detail={apiError ? apiError.detail : ""}
        onDismiss={() => setApiError(null)}
      />
    </div>
  );
}

TextGenerationChatContainer.propTypes = {
  parameters: PropTypes.object,
  systemMessage: PropTypes.object,
  toolbar: PropTypes.node,
};
