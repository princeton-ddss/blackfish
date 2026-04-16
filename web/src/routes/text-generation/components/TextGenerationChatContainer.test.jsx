/* eslint react/prop-types: 0 */

import { render, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import TextGenerationChatContainer from "./TextGenerationChatContainer";
import { ServiceContext } from "@/providers/ServiceProvider";
import { ProfileContext } from "@/components/ProfileSelect";
import { streamChatCompletionInference } from "../lib/requests";
import { ServiceStatus } from "@/lib/util";

vi.mock("../lib/requests", () => ({
  streamChatCompletionInference: vi.fn(),
}));

vi.mock("@heroicons/react/20/solid", () => ({
  XMarkIcon: ({ className, ...props }) => {
    return <div data-testid="x-mark-icon-solid" className={className} {...props} />;
  },
}));

vi.mock("@heroicons/react/24/outline", () => ({
  ArrowPathIcon: ({ className, ...props }) => {
    return <div data-testid="arrow-path-icon" className={className} {...props} />;
  },
  CheckIcon: ({ className, ...props }) => {
    return <div data-testid="check-icon" className={className} {...props} />;
  },
  CheckCircleIcon: ({ className, ...props }) => {
    return <div data-testid="check-circle-icon" className={className} {...props} />;
  },
  ClipboardDocumentIcon: ({ className, ...props }) => {
    return <div data-testid="clipboard-icon" className={className} {...props} />;
  },
  DocumentTextIcon: ({ className, ...props }) => {
    return <div data-testid="document-text-icon" className={className} {...props} />;
  },
  PaperAirplaneIcon: ({ className, ...props }) => {
    return <div data-testid="paper-airplane-icon" className={className} {...props} />;
  },
  PaperClipIcon: ({ className, ...props }) => {
    return <div data-testid="paper-clip-icon" className={className} {...props} />;
  },
  PencilIcon: ({ className, ...props }) => {
    return <div data-testid="pencil-icon" className={className} {...props} />;
  },
  XCircleIcon: ({ className, ...props }) => {
    return <div data-testid="x-circle-icon" className={className} {...props} />;
  },
  XMarkIcon: ({ className, ...props }) => {
    return <div data-testid="x-mark-icon" className={className} {...props} />;
  },
  ComputerDesktopIcon: ({ className, ...props }) => {
    return <div data-testid="computer-desktop-icon" className={className} {...props} />;
  },
  ServerIcon: ({ className, ...props }) => {
    return <div data-testid="server-icon" className={className} {...props} />;
  },
  PhotoIcon: ({ className, ...props }) => {
    return <div data-testid="photo-icon" className={className} {...props} />;
  },
  TrashIcon: ({ className, ...props }) => {
    return <div data-testid="trash-icon" className={className} {...props} />;
  },
}));

// Mock the attachment components to simplify testing
vi.mock("./AttachmentMenu", () => ({
  default: ({ onBrowserUpload, onRemoteSelect }) => (
    <div data-testid="attachment-menu">
      <button data-testid="upload-button" onClick={() => onBrowserUpload([])}>Upload</button>
      <button data-testid="remote-button" onClick={onRemoteSelect}>Remote</button>
    </div>
  ),
}));

vi.mock("./ImageAttachmentList", () => ({
  default: () => <div data-testid="image-attachment-list" />,
}));

vi.mock("./FileAttachmentList", () => ({
  default: () => <div data-testid="file-attachment-list" />,
}));

vi.mock("@/components/FileSelectModal", () => ({
  default: () => <div data-testid="file-select-modal" />,
}));

vi.mock("@/components/Notification", () => ({
  default: () => <div data-testid="notification" />,
}));

const mockClipboard = {
  writeText: vi.fn().mockResolvedValue(),
};

Object.defineProperty(navigator, "clipboard", {
  value: mockClipboard,
  configurable: true,
});

Object.defineProperty(Element.prototype, "scrollIntoView", {
  value: vi.fn(),
  writable: true,
  configurable: true,
});

const mockSelectedService = {
  name: "Test Service",
  status: ServiceStatus.HEALTHY,
  id: "test-service-1",
};

const mockProfile = {
  name: "local",
  schema: "local",
};

const MockProviders = ({ children, selectedService = mockSelectedService, profile = mockProfile }) => (
  <ProfileContext.Provider value={{ profile }}>
    <ServiceContext.Provider value={{ selectedService }}>
      {children}
    </ServiceContext.Provider>
  </ProfileContext.Provider>
);

describe("TextGenerationChatContainer", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockClipboard.writeText.mockClear();
    console.log = vi.fn();
    console.error = vi.fn();
    console.debug = vi.fn();
  });

  describe("Component rendering", () => {
    it("renders the main container with chat label and user message input", () => {
      const {baseElement, getByText, getByPlaceholderText} = render(
        <MockProviders>
          <TextGenerationChatContainer parameters={{}} systemMessage={{ role: "system", content: "" }} />
        </MockProviders>
      );
      expect(getByText("Chat")).toBeInTheDocument();
      expect(getByPlaceholderText("Why are orcas so awesome?"))
        .toBeInTheDocument();
      expect(baseElement).toMatchSnapshot();
    });

    it("renders empty message list initially", () => {
      const {queryByText} = render(
        <MockProviders>
          <TextGenerationChatContainer parameters={{}} systemMessage={{ role: "system", content: "" }} />
        </MockProviders>
      );
      expect(queryByText("No messages")).not.toBeInTheDocument();
    });
  });

  describe("UserMessageInput", () => {
    it("allows typing in user message textarea", async () => {
      const user = userEvent.setup();
      const {getByPlaceholderText} = render(
        <MockProviders>
          <TextGenerationChatContainer parameters={{}} systemMessage={{ role: "system", content: "" }} />
        </MockProviders>
      );
      const textarea = getByPlaceholderText("Why are orcas so awesome?");
      await user.type(textarea, "Test user message");
      expect(textarea.value).toBe("Test user message");
    });

    it("submits form on Enter key press", async () => {
      const user = userEvent.setup();
      const mockStream = {
        next: vi.fn().mockResolvedValue({
          value: [{ choices: [{ delta: { content: "Test response" } }] }]
        }),
        [Symbol.asyncIterator]: vi.fn().mockReturnValue({
          next: vi.fn().mockResolvedValue({ done: true })
        })
      };
      streamChatCompletionInference.mockReturnValue(mockStream);
      const {getByPlaceholderText} = render(
        <MockProviders>
          <TextGenerationChatContainer parameters={{}} systemMessage={{ role: "system", content: "" }} />
        </MockProviders>
      );
      const textarea = getByPlaceholderText("Why are orcas so awesome?");
      await user.type(textarea, "Test prompt");
      await user.keyboard("{Enter}");
      expect(streamChatCompletionInference).toHaveBeenCalled();
    });

    it("allows new line on Shift+Enter", async () => {
      const user = userEvent.setup();
      const {getByPlaceholderText} = render(
        <MockProviders>
          <TextGenerationChatContainer parameters={{}} systemMessage={{ role: "system", content: "" }} />
        </MockProviders>
      );
      const textarea = getByPlaceholderText("Why are orcas so awesome?");
      await user.type(textarea, "First line");
      await user.keyboard("{Shift>}{Enter}{/Shift}");
      await user.type(textarea, "Second line");
      expect(textarea.value).toContain("\n");
      await user.clear(textarea);
    });

    it("enables submit button when message has content", async () => {
      const user = userEvent.setup();
      const {getByPlaceholderText, getByRole} = render(
        <MockProviders>
          <TextGenerationChatContainer parameters={{}} systemMessage={{ role: "system", content: "" }} />
        </MockProviders>
      );
      const textarea = getByPlaceholderText("Why are orcas so awesome?");
      await user.type(textarea, "Test message");
      const submitButton = getByRole("button", { name: "Submit" });
      expect(submitButton).not.toBeDisabled();
      await user.clear(textarea);
    });
  });

  describe("Message editing", () => {
    it("allows editing user messages", async () => {
      const user = userEvent.setup();
      const mockStream = {
        next: vi.fn().mockResolvedValue({
          value: [{ choices: [{ delta: { content: "Response" } }] }]
        }),
        [Symbol.asyncIterator]: vi.fn().mockReturnValue({
          next: vi.fn().mockResolvedValue({ done: true })
        })
      };
      streamChatCompletionInference.mockReturnValue(mockStream);
      const {getByRole, getByPlaceholderText, getByText} = render(
        <MockProviders>
          <TextGenerationChatContainer parameters={{}} systemMessage={{ role: "system", content: "" }} />
        </MockProviders>
      );
      const textarea = getByPlaceholderText("Why are orcas so awesome?");
      await user.type(textarea, "Original message");
      const submitButton = getByRole("button", { name: "Submit" });
      await user.click(submitButton);
      await user.clear(textarea);
      await waitFor(() => {
        expect(getByText("Original message")).toBeInTheDocument();
      });
      const userMessage = getByText("Original message").closest(".mt-3");
      await user.hover(userMessage);
      const editButton = getByRole("button", { name: "Edit" });
      await user.click(editButton);
      await waitFor(() => {
        const editTextarea = userMessage.querySelector("textarea[name='edit-message']");
        expect(editTextarea).toBeInTheDocument();
      });
      const editTextarea = userMessage.querySelector("textarea[name='edit-message']");
      await user.clear(editTextarea);
      await user.type(editTextarea, "Edited message");
      const saveButton = getByRole("button", { name: "Save" });
      await user.click(saveButton);
      await waitFor(() => {
        expect(getByText("Edited message")).toBeInTheDocument();
        expect(userMessage.querySelector("textarea[name='edit-message']")).not.toBeInTheDocument();
      });
    });

    it("cancels editing when cancel button is clicked", async () => {
      const user = userEvent.setup();
      const mockStream = {
        next: vi.fn().mockResolvedValue({
          value: [{ choices: [{ delta: { content: "Response" } }] }]
        }),
        [Symbol.asyncIterator]: vi.fn().mockReturnValue({
          next: vi.fn().mockResolvedValue({ done: true })
        })
      };
      streamChatCompletionInference.mockReturnValue(mockStream);
      const {getByRole, getByPlaceholderText, getByText} = render(
        <MockProviders>
          <TextGenerationChatContainer parameters={{}} systemMessage={{ role: "system", content: "" }} />
        </MockProviders>
      );
      const textarea = getByPlaceholderText("Why are orcas so awesome?");
      await user.type(textarea, "Original message");
      const submitButton = getByRole("button", { name: "Submit" });
      await user.click(submitButton);
      await user.clear(textarea);
      await waitFor(() => {
        expect(getByText("Original message")).toBeInTheDocument();
      });
      const userMessage = getByText("Original message").closest(".mt-3");
      await user.hover(userMessage);
      const editButton = getByRole("button", { name: "Edit" });
      await user.click(editButton);
      await waitFor(() => {
        const editTextarea = userMessage.querySelector("textarea[name='edit-message']");
        expect(editTextarea).toBeInTheDocument();
      });
      const editTextarea = userMessage.querySelector("textarea[name='edit-message']");
      await user.clear(editTextarea);
      await user.type(editTextarea, "Changed text");
      const cancelButton = getByRole("button", { name: "Cancel" });
      await user.click(cancelButton);
      await waitFor(() => {
        expect(getByText("Original message")).toBeInTheDocument();
        expect(userMessage.querySelector("textarea[name='edit-message']")).not.toBeInTheDocument();
      });
    });

    it("disables save button when edit content is empty", async () => {
      const user = userEvent.setup();
      const mockStream = {
        next: vi.fn().mockResolvedValue({
          value: [{ choices: [{ delta: { content: "Response" } }] }]
        }),
        [Symbol.asyncIterator]: vi.fn().mockReturnValue({
          next: vi.fn().mockResolvedValue({ done: true })
        })
      };
      streamChatCompletionInference.mockReturnValue(mockStream);
      const {getByRole, getByPlaceholderText, getByText} = render(
        <MockProviders>
          <TextGenerationChatContainer parameters={{}} systemMessage={{ role: "system", content: "" }} />
        </MockProviders>
      );
      const textarea = getByPlaceholderText("Why are orcas so awesome?");
      await user.type(textarea, "Original message");
      const submitButton = getByRole("button", { name: "Submit" });
      await user.click(submitButton);
      await user.clear(textarea);
      await waitFor(() => {
        expect(getByText("Original message")).toBeInTheDocument();
      });
      const userMessage = getByText("Original message").closest(".mt-3");
      await user.hover(userMessage);
      const editButton = getByRole("button", { name: "Edit" });
      await user.click(editButton);
      await waitFor(() => {
        const editTextarea = userMessage.querySelector("textarea[name='edit-message']");
        expect(editTextarea).toBeInTheDocument();
      });
      const editTextarea = userMessage.querySelector("textarea[name='edit-message']");
      await user.clear(editTextarea);
      await waitFor(() => {
        const saveButton = getByRole("button", { name: "Save" });
        expect(saveButton).toBeDisabled();
      });
    });
  });

  describe("Message deletion", () => {
    it("deletes user message and subsequent assistant message", async () => {
      const user = userEvent.setup();
      const mockStream = {
        next: vi.fn().mockResolvedValue({
          value: [{ choices: [{ delta: { content: "Assistant response" } }] }]
        }),
        [Symbol.asyncIterator]: vi.fn().mockReturnValue({
          next: vi.fn().mockResolvedValue({ done: true })
        })
      };
      streamChatCompletionInference.mockReturnValue(mockStream);
      const {getByPlaceholderText, getByRole, getByText, queryByText} = render(
        <MockProviders>
          <TextGenerationChatContainer parameters={{}} systemMessage={{ role: "system", content: "" }} />
        </MockProviders>
      );
      const textarea = getByPlaceholderText("Why are orcas so awesome?");
      await user.type(textarea, "Test message");
      await user.click(getByRole("button", { name: "Submit" }));
      await user.clear(textarea);
      await waitFor(() => {
        expect(getByText("Test message")).toBeInTheDocument();
        expect(getByText("Assistant response")).toBeInTheDocument();
      });
      const userMessage = getByText("Test message").closest(".mt-3");
      await user.hover(userMessage);
      const deleteButton = getByRole("button", { name: "Delete" });
      await user.click(deleteButton);
      expect(queryByText("Test message")).not.toBeInTheDocument();
      expect(queryByText("Assistant response")).not.toBeInTheDocument();
    });
  });

  describe("Error recovery", () => {
    it("restores typed input when submission fails", async () => {
      const user = userEvent.setup();
      const failingStream = {
        next: vi.fn().mockRejectedValue(new Error("API error")),
        [Symbol.asyncIterator]: vi.fn().mockReturnValue({
          next: vi.fn().mockResolvedValue({ done: true })
        })
      };
      streamChatCompletionInference.mockReturnValue(failingStream);
      const { getByPlaceholderText, getByRole } = render(
        <MockProviders>
          <TextGenerationChatContainer parameters={{}} systemMessage={{ role: "system", content: "" }} />
        </MockProviders>
      );
      const textarea = getByPlaceholderText("Why are orcas so awesome?");
      await user.type(textarea, "My important message");
      await user.click(getByRole("button", { name: "Submit" }));
      await waitFor(() => {
        expect(textarea.value).toBe("My important message");
      });
    });

    it("preserves assistant message when regeneration fails", async () => {
      const user = userEvent.setup();
      // First call succeeds
      const successStream = {
        next: vi.fn().mockResolvedValue({
          value: [{ choices: [{ delta: { content: "Original response" } }] }]
        }),
        [Symbol.asyncIterator]: vi.fn().mockReturnValue({
          next: vi.fn().mockResolvedValue({ done: true })
        })
      };
      streamChatCompletionInference.mockReturnValue(successStream);
      const { getByPlaceholderText, getByRole, getByText } = render(
        <MockProviders>
          <TextGenerationChatContainer parameters={{}} systemMessage={{ role: "system", content: "" }} />
        </MockProviders>
      );
      const textarea = getByPlaceholderText("Why are orcas so awesome?");
      await user.type(textarea, "Test message");
      await user.click(getByRole("button", { name: "Submit" }));
      await waitFor(() => {
        expect(getByText("Original response")).toBeInTheDocument();
      });
      // Second call (regeneration) fails
      const failingStream = {
        next: vi.fn().mockRejectedValue(new Error("API error")),
        [Symbol.asyncIterator]: vi.fn().mockReturnValue({
          next: vi.fn().mockResolvedValue({ done: true })
        })
      };
      streamChatCompletionInference.mockReturnValue(failingStream);
      const assistantMessage = getByText("Original response").closest(".mt-3");
      await user.hover(assistantMessage);
      const regenButton = getByRole("button", { name: "Regenerate" });
      await user.click(regenButton);
      await waitFor(() => {
        expect(getByText("Original response")).toBeInTheDocument();
      });
    });

    it("does not append ghost message when conversation is cleared mid-stream", async () => {
      const user = userEvent.setup();
      const abortError = new DOMException("The operation was aborted.", "AbortError");
      const mockStream = {
        next: vi.fn().mockResolvedValue({
          value: [{ choices: [{ delta: { content: "Partial response" } }] }]
        }),
        [Symbol.asyncIterator]: vi.fn().mockReturnValue({
          next: vi.fn().mockRejectedValue(abortError)
        })
      };
      streamChatCompletionInference.mockReturnValue(mockStream);
      const { getByPlaceholderText, getByRole, queryByText } = render(
        <MockProviders>
          <TextGenerationChatContainer parameters={{}} systemMessage={{ role: "system", content: "" }} />
        </MockProviders>
      );
      const textarea = getByPlaceholderText("Why are orcas so awesome?");
      await user.type(textarea, "Test message");
      await user.click(getByRole("button", { name: "Submit" }));
      await waitFor(() => {
        expect(queryByText("Partial response")).toBeInTheDocument();
      });
      const clearButton = getByRole("button", { name: "Clear conversation" });
      await user.click(clearButton);
      await waitFor(() => {
        expect(queryByText("Partial response")).not.toBeInTheDocument();
        expect(queryByText("Test message")).not.toBeInTheDocument();
      });
    });
  });

  describe("Resubmit functionality", () => {
    it("handles resubmit of assistant message", async () => {
      const user = userEvent.setup();
      const mockStream = {
        next: vi.fn().mockResolvedValue({
          value: [{ choices: [{ delta: { content: "Initial response" } }] }]
        }),
        [Symbol.asyncIterator]: vi.fn().mockReturnValue({
          next: vi.fn().mockResolvedValue({ done: true })
        })
      };
      streamChatCompletionInference.mockReturnValue(mockStream);
      const {getByRole, getByPlaceholderText, getByText} = render(
        <MockProviders>
          <TextGenerationChatContainer parameters={{}} systemMessage={{ role: "system", content: "" }} />
        </MockProviders>
      );
      const textarea = getByPlaceholderText("Why are orcas so awesome?");
      await user.type(textarea, "Test message");
      const submitButton = getByRole("button", { name: "Submit" });
      await user.click(submitButton);
      await waitFor(() => {
        expect(getByText("Initial response")).toBeInTheDocument();
      });
      mockStream.next.mockResolvedValue({
        value: [{ choices: [{ delta: { content: "Resubmitted response" } }] }]
      });
      await user.click(submitButton);
      await waitFor(() => {
        expect(getByText("Resubmitted response")).toBeInTheDocument();
      });
      expect(streamChatCompletionInference).toHaveBeenCalledTimes(2);
      await user.clear(textarea);
    });
  });
});
