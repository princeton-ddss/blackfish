import { useContext, useEffect, useState, useRef, useCallback } from "react";
import {
  ArrowPathIcon,
  CheckIcon,
  ClipboardDocumentIcon,
  PaperAirplaneIcon,
  PencilIcon,
  XMarkIcon,
} from "@heroicons/react/24/outline";
import { ServiceContext } from "@/providers/ServiceProvider";
import { ProfileContext } from "@/components/ProfileSelect";
import { streamChatCompletionInference } from "../lib/requests";
import {
  fileToBase64,
  buildMultimodalContent,
  extractTextFromContent,
  extractImagesFromContent,
} from "../lib/imageUtils";
import AttachmentMenu from "./AttachmentMenu";
import ImageAttachmentList from "./ImageAttachmentList";
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
 * User Message Input component.
 * @param {object} options
 * @param {string} options.message
 * @param {Function} options.onChange
 * @param {Function} options.onSubmit
 * @param {Array} options.attachedImages
 * @param {Function} options.onRemoveImage
 * @param {Function} options.onImageError
 * @param {object} options.profile
 * @param {Function} options.onBrowserUpload
 * @param {Function} options.onRemoteSelect
 * @return {JSX.Element}
 */
function UserMessageInput({
  message,
  onChange,
  onSubmit,
  attachedImages,
  onRemoveImage,
  onImageError,
  profile,
  onBrowserUpload,
  onRemoteSelect,
}) {
  return (
    <div className="flex items-start space-x-4 mt-auto pt-4">
      <div className="min-w-0 flex-1">
        <form action="#" onSubmit={onSubmit} className="relative">
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
  profile: PropTypes.object,
  onBrowserUpload: PropTypes.func,
  onRemoteSelect: PropTypes.func,
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

  // Extract text and images from content
  const textContent = extractTextFromContent(message.content);
  const images = extractImagesFromContent(message.content);
  const [content, setContent] = useState(textContent);

  // Update content when message changes
  useEffect(() => {
    setContent(extractTextFromContent(message.content));
  }, [message.content]);

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
        className="mt-5"
      >
        <div className="flex flex-row-reverse">
          <div className="max-w-xl content-end bg-gray-100 dark:bg-gray-700 text-sm text-gray-900 dark:text-gray-100 rounded-lg px-4 py-3 shadow-md">
            {/* Display images if any */}
            {images.length > 0 && (
              <div className="flex gap-2 flex-wrap mb-2">
                {images.map((src, idx) => (
                  <MessageImage key={idx} src={src} />
                ))}
              </div>
            )}
            {textContent}
          </div>
        </div>
        <div className="flex flex-row-reverse h-8">
          <button
            hidden={!hover}
            onClick={() => {
              console.log("deleting user message");
              onDeleteMessage();
            }}
          >
            <XMarkIcon className="w-5 h-5 text-gray-600 dark:text-gray-400 hover:text-gray-400 dark:hover:text-gray-300 m-0.5 mt-2" />
            <span className="sr-only">{`Delete message: "${textContent}"`}</span>
          </button>
          <button
            hidden={!hover}
            onClick={() => {
              console.log("edit button clicked");
              setIsEditing(true);
            }}
          >
            <PencilIcon className="w-5 h-5 text-gray-600 dark:text-gray-400 hover:text-gray-400 dark:hover:text-gray-300 m-0.5 mt-2" />
            <span className="sr-only">{`Edit message: "${textContent}"`}</span>
          </button>
          <button
            hidden={!hover}
            onClick={() => {
              navigator.clipboard
                .writeText(textContent)
                .then(console.log("copied user message"))
                .catch((err) => {
                  console.error("Failed to copy content: ", err);
                });
            }}
          >
            <ClipboardDocumentIcon className="w-5 h-5 text-gray-600 dark:text-gray-400 hover:text-gray-400 dark:hover:text-gray-300 m-0.5 mt-2" />
            <span className="sr-only">{`Copy message to clipboard: ${textContent}`}</span>
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
  return (
    <div className="mt-5 max-w-xl">
      <div className="flex flex-row">
        <div className="w-fit content-end bg-white dark:bg-transparent text-sm text-gray-900 dark:text-gray-100 rounded-lg ml-2">
          {message.content}
        </div>
      </div>
      <div className="flex flex-row h-8">
        <button
          onClick={() => {
            navigator.clipboard
              .writeText(message.content)
              .then(console.log("copied assistant message"))
              .catch((err) => {
                console.error("Failed to copy content: ", err);
              });
          }}
        >
          <ClipboardDocumentIcon className="ml-1.5 w-5 h-5 text-gray-600 dark:text-gray-400 hover:text-gray-400 dark:hover:text-gray-300 m-0.5" />
        </button>
        <button
          onClick={handleResubmit}
        >
          <ArrowPathIcon className="w-5 h-5 text-gray-600 dark:text-gray-400 hover:text-gray-400 dark:hover:text-gray-300 m-0.5" />
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
 * @return {JSX.Element}
 */
function MessageList({ messages, setMessages, handleResubmit, elementRef }) {
  try {
    sessionStorage.setItem("tgcc-ml", JSON.stringify(messages));
  } catch(error) {
    console.error(error);
  };
  return (
    <div className="flex-1 min-h-0 overflow-y-auto px-8">
      {messages.map((message, index) => (
        <Message
          key={index}
          message={message}
          onEditMessage={(content) => {
            console.log("editing message:", message);
            setMessages((messages) =>
              messages.map((m, i) => {
                if (i === index) {
                  return { ...m, content: content };
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
          handleResubmit={handleResubmit}
        />
      ))}
      <div ref={elementRef}></div>
    </div>
  );
}

MessageList.propTypes = {
  messages: PropTypes.array,
  setMessages: PropTypes.func,
  handleResubmit: PropTypes.func,
  elementRef: PropTypes.object,
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
  const [fileBrowserOpen, setFileBrowserOpen] = useState(false);
  const [imageError, setImageError] = useState(null);

  const elementRef = useRef(null);

  const scrollToElement = () => {
    elementRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    // TODO: only want to trigger this when the length of messages increases, i.e., a message is appended
    scrollToElement();
  }, [messages]);

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
    console.log("user message submitted");

    // Build the message content (multimodal if images attached)
    let messageContent = userMessage.content;
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
        messageContent = buildMultimodalContent(userMessage.content, imageUrls);
      } catch (error) {
        console.error("Failed to convert images:", error);
        return;
      }
    }

    const newUserMessage = {
      role: Role.USER,
      content: messageContent,
    };

    const stream = streamChatCompletionInference(
      selectedService,
      [systemMessage, ...messages, newUserMessage],
      {
        ...parameters,
        stream: true,
      },
      true
    );

    setMessages((messages) => [...messages, newUserMessage]);

    // Clear attached images after sending
    setAttachedImages([]);

    const data = await stream.next();
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
  };

  const handleResubmit = async (event) => {
    event.preventDefault();
    console.log("user message resubmitted");

    const stream = streamChatCompletionInference(
      selectedService,
      [systemMessage, ...messages.slice(0, messages.length - 1)],
      {
        ...parameters,
        stream: true,
      },
      true
    );

    setMessages((messages) => messages.slice(0, messages.length - 1));

    const data = await stream.next();
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

  return (
    <div className="flex flex-col grow pt-2 bg-white dark:bg-gray-800 lg:h-[calc(100vh-7rem)]">
      <div className="flex items-center justify-between mb-2">
        <label className="block text-sm font-medium leading-6 text-gray-900 dark:text-gray-100">
          Chat
        </label>
        {toolbar}
      </div>
      <MessageList
        messages={messages}
        setMessages={setMessages}
        handleResubmit={handleResubmit}
        elementRef={elementRef}
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
        profile={profile}
        onBrowserUpload={handleBrowserUpload}
        onRemoteSelect={() => setFileBrowserOpen(true)}
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

TextGenerationChatContainer.propTypes = {
  parameters: PropTypes.object,
  systemMessage: PropTypes.object,
  toolbar: PropTypes.node,
};
