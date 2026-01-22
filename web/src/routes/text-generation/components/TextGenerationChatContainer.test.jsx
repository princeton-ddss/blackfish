/* eslint react/prop-types: 0 */

import { render, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import TextGenerationChatContainer from "./TextGenerationChatContainer";
import { ServiceContext } from "@/providers/ServiceProvider";
import { streamChatCompletionInference } from "../lib/requests";
import { ServiceStatus } from "@/lib/util";

vi.mock("../lib/requests", () => ({
  streamChatCompletionInference: vi.fn(),
}));

vi.mock("@heroicons/react/24/outline", () => ({
  ArrowPathIcon: ({ className, ...props }) => {
    return <div data-testid="arrow-path-icon" className={className} {...props} />;
  },
  CheckIcon: ({ className, ...props }) => {
    return <div data-testid="check-icon" className={className} {...props} />;
  },
  ClipboardDocumentIcon: ({ className, ...props }) => {
    return <div data-testid="clipboard-icon" className={className} {...props} />;
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
  XMarkIcon: ({ className, ...props }) => {
    return <div data-testid="x-mark-icon" className={className} {...props} />;
  },
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

const MockServiceProvider = ({ children, selectedService = mockSelectedService }) => (
  <ServiceContext.Provider value={{ selectedService }}>
    {children}
  </ServiceContext.Provider>
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
    it("renders the main container with system message input and user message input", () => {
      const {baseElement, getByText, getByPlaceholderText} = render(
        <MockServiceProvider>
          <TextGenerationChatContainer parameters={{}} />
        </MockServiceProvider>
      );
      expect(getByText("System Message")).toBeInTheDocument();
      expect(getByPlaceholderText("You are a helpful assistant."))
        .toBeInTheDocument();
      expect(getByPlaceholderText("Why are orcas so awesome?"))
        .toBeInTheDocument();
      expect(baseElement).toMatchSnapshot();
    });

    it("renders empty message list initially", () => {
      const {queryByText} = render(
        <MockServiceProvider>
          <TextGenerationChatContainer parameters={{}} />
        </MockServiceProvider>
      );
      expect(queryByText("No messages")).not.toBeInTheDocument();
    });
  });

  describe("SystemMessageInput", () => {
    it("allows typing in system message textarea", async () => {
      const user = userEvent.setup();
      const {getByPlaceholderText} = render(
        <MockServiceProvider>
          <TextGenerationChatContainer parameters={{}} />
        </MockServiceProvider>
      );
      const textarea = getByPlaceholderText("You are a helpful assistant.");
      await user.type(textarea, "Custom system message");
      expect(textarea.value).toBe("Custom system message");
      await user.clear(textarea);
    });

    it("updates system message state on change", async () => {
      const user = userEvent.setup();
      const {getByPlaceholderText} = render(
        <MockServiceProvider>
          <TextGenerationChatContainer parameters={{}} />
        </MockServiceProvider>
      );
      const textarea = getByPlaceholderText("You are a helpful assistant.");
      await user.type(textarea, "Test system message");
      expect(textarea.value).toBe("Test system message");
      await user.clear(textarea);
    });
  });

  describe("UserMessageInput", () => {
    it("allows typing in user message textarea", async () => {
      const user = userEvent.setup();
      const {getByPlaceholderText} = render(
        <MockServiceProvider>
          <TextGenerationChatContainer parameters={{}} />
        </MockServiceProvider>
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
        <MockServiceProvider>
          <TextGenerationChatContainer parameters={{}} />
        </MockServiceProvider>
      );
      const textarea = getByPlaceholderText("Why are orcas so awesome?");
      await user.type(textarea, "Test prompt");
      await user.keyboard("{Enter}");
      expect(streamChatCompletionInference).toHaveBeenCalled();
    });

    it("allows new line on Shift+Enter", async () => {
      const user = userEvent.setup();
      const {getByPlaceholderText} = render(
        <MockServiceProvider>
          <TextGenerationChatContainer parameters={{}} />
        </MockServiceProvider>
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
        <MockServiceProvider>
          <TextGenerationChatContainer parameters={{}} />
        </MockServiceProvider>
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
        <MockServiceProvider>
          <TextGenerationChatContainer parameters={{}} />
        </MockServiceProvider>
      );
      const textarea = getByPlaceholderText("Why are orcas so awesome?");
      await user.type(textarea, "Original message");
      const submitButton = getByRole("button", { name: "Submit" });
      await user.click(submitButton);
      await user.clear(textarea);
      await waitFor(() => {
        expect(getByText("Original message")).toBeInTheDocument();
      });
      const userMessage = getByText("Original message").closest(".mt-5");
      await user.hover(userMessage);
      const editButton = getByRole("button", { name: 'Edit message: "Original message"' });
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
        <MockServiceProvider>
          <TextGenerationChatContainer parameters={{}} />
        </MockServiceProvider>
      );
      const textarea = getByPlaceholderText("Why are orcas so awesome?");
      await user.type(textarea, "Original message");
      const submitButton = getByRole("button", { name: "Submit" });
      await user.click(submitButton);
      await user.clear(textarea);
      await waitFor(() => {
        expect(getByText("Original message")).toBeInTheDocument();
      });
      const userMessage = getByText("Original message").closest(".mt-5");
      await user.hover(userMessage);
      const editButton = getByRole("button", { name: 'Edit message: "Original message"' });
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
        <MockServiceProvider>
          <TextGenerationChatContainer parameters={{}} />
        </MockServiceProvider>
      );
      const textarea = getByPlaceholderText("Why are orcas so awesome?");
      await user.type(textarea, "Original message");
      const submitButton = getByRole("button", { name: "Submit" });
      await user.click(submitButton);
      await user.clear(textarea);
      await waitFor(() => {
        expect(getByText("Original message")).toBeInTheDocument();
      });
      const userMessage = getByText("Original message").closest(".mt-5");
      await user.hover(userMessage);
      const editButton = getByRole("button", { name: 'Edit message: "Original message"' });
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
        <MockServiceProvider>
          <TextGenerationChatContainer parameters={{}} />
        </MockServiceProvider>
      );
      const textarea = getByPlaceholderText("Why are orcas so awesome?");
      await user.type(textarea, "Test message");
      await user.click(getByRole("button", { name: "Submit" }));
      await user.clear(textarea);
      await waitFor(() => {
        expect(getByText("Test message")).toBeInTheDocument();
        expect(getByText("Assistant response")).toBeInTheDocument();
      });
      const userMessage = getByText("Test message").closest(".mt-5");
      await user.hover(userMessage);
      const deleteButton = getByRole("button", { name: 'Delete message: "Test message"' });
      await user.click(deleteButton);
      expect(queryByText("Test message")).not.toBeInTheDocument();
      expect(queryByText("Assistant response")).not.toBeInTheDocument();
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
        <MockServiceProvider>
          <TextGenerationChatContainer parameters={{}} />
        </MockServiceProvider>
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
