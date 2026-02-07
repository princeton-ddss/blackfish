import React, { useContext, useEffect, useState } from "react";
import {
  ArrowPathIcon,
  CheckIcon,
  ClipboardDocumentIcon,
  PaperAirplaneIcon,
  PaperClipIcon,
  PencilIcon,
  XMarkIcon,
} from "@heroicons/react/24/outline";
import { ServiceContext } from "@/providers/ServiceProvider";
import { streamChatCompletionInference } from "../lib/requests";
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
 * @return {JSX.Element}
 */
function UserMessageInput({ message, onChange, onSubmit }) {
  return (
    <div className="flex items-start space-x-4 mt-auto pt-4">
      <div className="min-w-0 flex-1">
        <form action="#" onSubmit={onSubmit} className="relative">
          <div className="rounded-lg bg-white dark:bg-gray-700 outline outline-1 -outline-offset-1 outline-gray-300 dark:outline-gray-600 shadow-md">
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
                <button
                  type="button"
                  className="-m-2.5 flex size-10 items-center justify-center rounded-full text-gray-400 hover:text-gray-500"
                >
                  <PaperClipIcon aria-hidden="true" className="size-5" />
                  <span className="sr-only">Attach a file</span>
                </button>
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
  message: PropTypes.string,
  onChange: PropTypes.func,
  onSubmit: PropTypes.func
};

/**
 * User Message component.
 * @param {object} options
 * @param {string} options.message
 * @param {Function} options.onDeleteMessage
 * @param {Function} options.onEditMessage
 * @return {JSX.Element}
 */
function UserMessage({ message, onDeleteMessage, onEditMessage }) {
  const [hover, setHover] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [content, setContent] = useState(message.content);

  if (isEditing) {
    return (
      <div className="flex flex-row-reverse space-x-4 mt-5">
        <div className="min-w-0 max-w-xl flex-1">
          <form
            action="#"
            onSubmit={(event) => {
              event.preventDefault();
              onEditMessage(content);
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
                  onClick={() => {
                    console.log("cancel button clicked");
                    setIsEditing(false);
                    setContent(message.content);
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
            {content}
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
            <span className="sr-only">{`Delete message: "${message.content}"`}</span>
          </button>
          <button
            hidden={!hover}
            onClick={() => {
              console.log("edit button clicked");
              setIsEditing(true);
            }}
          >
            <PencilIcon className="w-5 h-5 text-gray-600 dark:text-gray-400 hover:text-gray-400 dark:hover:text-gray-300 m-0.5 mt-2" />
            <span className="sr-only">{`Edit message: "${message.content}"`}</span>
          </button>
          <button
            hidden={!hover}
            onClick={() => {
              navigator.clipboard
                .writeText(content)
                .then(console.log("copied user message"))
                .catch((err) => {
                  console.error("Failed to copy content: ", err);
                });
            }}
          >
            <ClipboardDocumentIcon className="w-5 h-5 text-gray-600 dark:text-gray-400 hover:text-gray-400 dark:hover:text-gray-300 m-0.5 mt-2" />
            <span className="sr-only">{`Copy message to clipboard: ${message.content}`}</span>
          </button>
        </div>
      </div>
    );
  }
}

UserMessage.propTypes = {
  message: PropTypes.string,
  onDeleteMessage: PropTypes.func,
  onEditMessage: PropTypes.func,
};

/**
 * Assistant Message component.
 * @param {object} options
 * @param {string} options.message
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
  message: PropTypes.string,
  handleResubmit: PropTypes.func,
};

/**
 * Message component.
 * @param {object} options
 * @param {string} options.message
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
  message: PropTypes.string,
  onEditMessage: PropTypes.func,
  onDeleteMessage: PropTypes.func,
  handleResubmit: PropTypes.func,
};

/**
 * Message List component.
 * @param {object} options
 * @param {string} options.messages
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
  messages: PropTypes.string,
  setMessages: PropTypes.func,
  handleResubmit: PropTypes.func,
  elementRef: PropTypes.node,
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
  const storedMessages = sessionStorage.getItem("tgcc-ml");
  const [messages, setMessages] = useState(
    storedMessages ? JSON.parse(storedMessages) : []
  );
  const [userMessage, setUserMessage] = useState({
    role: Role.USER,
    content: sessionStorage.getItem("tgcc-um") || "",
  });

  const elementRef = React.useRef(null);

  const scrollToElement = () => {
    elementRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    // TODO: only want to trigger this when the length of messages increases, i.e., a message is appended
    scrollToElement();
  }, [messages]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    console.log("user message submitted");

    const stream = streamChatCompletionInference(
      selectedService,
      [systemMessage, ...messages, userMessage],
      {
        ...parameters,
        stream: true,
      },
      true
    );

    setMessages((messages) => [...messages, userMessage]);

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
      />
    </div>
  );
}

TextGenerationChatContainer.propTypes = {
  parameters: PropTypes.object,
  systemMessage: PropTypes.object,
  toolbar: PropTypes.node,
};
