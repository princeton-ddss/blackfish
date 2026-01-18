/* eslint react/prop-types: 0 */

import { render, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import TextGenerationCompletionContainer from "./TextGenerationCompletionContainer";
import { ServiceContext } from "@/providers/ServiceProvider";
import { streamCompletionInference } from "../lib/requests";
import { ServiceStatus } from "@/lib/util";

vi.mock("../lib/requests", () => ({
  streamCompletionInference: vi.fn(),
}));

vi.mock("@heroicons/react/24/outline", () => ({
  ArrowPathIcon: ({ className, ...props }) => {
    return <div data-testid="arrow-path-icon" className={className} {...props} />;
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
}));

const mockClipboard = {
  writeText: vi.fn(),
};

Object.defineProperty(navigator, 'clipboard', {
  value: mockClipboard,
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

describe("TextGenerationCompletionContainer", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockClipboard.writeText.mockClear();
    console.log = vi.fn();
    console.error = vi.fn();
  });

  describe("Component rendering", () => {
    it("renders the main container with prompt input and response output", () => {
      const {baseElement, getByText, getByPlaceholderText} = render(
        <MockServiceProvider>
          <TextGenerationCompletionContainer parameters={{}} />
        </MockServiceProvider>
      );
      expect(getByText("Prompt")).toBeInTheDocument();
      expect(getByPlaceholderText("Orcas are awesome because..."))
        .toBeInTheDocument();
      expect(baseElement).toMatchSnapshot();
    });
  });

  describe("TextGenerationPromptInput", () => {
    it("submits form on Enter key press", async () => {
      const user = userEvent.setup();
      const mockStream = {
        next: vi.fn().mockResolvedValue({
          value: [{ choices: [{ text: "Test response" }] }]
        }),
        [Symbol.asyncIterator]: vi.fn().mockReturnValue({
          next: vi.fn().mockResolvedValue({ done: true })
        })
      };
      streamCompletionInference.mockReturnValue(mockStream);
      const {getByPlaceholderText} = render(
        <MockServiceProvider>
          <TextGenerationCompletionContainer parameters={{}} />
        </MockServiceProvider>
      );
      const textarea = getByPlaceholderText("Orcas are awesome because...");
      await user.type(textarea, "Test prompt");
      await user.keyboard("{Enter}");
      expect(streamCompletionInference).toHaveBeenCalled();
    });

    it("allows new line on Shift+Enter", async () => {
      const user = userEvent.setup();
      const {getByPlaceholderText} = render(
        <MockServiceProvider>
          <TextGenerationCompletionContainer parameters={{}} />
        </MockServiceProvider>
      );
      const textarea = getByPlaceholderText("Orcas are awesome because...");
      await user.type(textarea, "First line");
      await user.keyboard("{Shift>}{Enter}{/Shift}");
      await user.type(textarea, "Second line");
      expect(textarea.value).toContain("\n");
    });
  });

  describe("Form submission and streaming", () => {
    it("handles streaming response correctly", async () => {
      const user = userEvent.setup();
      const mockStreamData = [
        { choices: [{ text: "First" }] },
        { choices: [{ text: " chunk" }] },
        { choices: [{ text: " of text" }] }
      ];
      let streamIterator;
      const mockStream = {
        next: vi.fn().mockResolvedValue({
          value: [mockStreamData[0]]
        }),
        [Symbol.asyncIterator]: vi.fn().mockImplementation(() => {
          let index = 1;
          streamIterator = {
            next: vi.fn().mockImplementation(() => {
              if (index < mockStreamData.length) {
                return Promise.resolve({
                  value: [mockStreamData[index++]],
                  done: false
                });
              }
              return Promise.resolve({ done: true });
            })
          };
          return streamIterator;
        })
      };
      streamCompletionInference.mockReturnValue(mockStream);
      const {getByTestId, getByText} = render(
        <MockServiceProvider>
          <TextGenerationCompletionContainer parameters={{}} />
        </MockServiceProvider>
      );
      const submitButton = getByTestId("paper-airplane-icon").parentElement;
      await user.click(submitButton);
      await waitFor(() => {
        expect(getByText("First chunk of text")).toBeInTheDocument();
      });
    });

    it("handles refresh button click", async () => {
      const user = userEvent.setup();
      const mockStream = {
        next: vi.fn().mockResolvedValue({
          value: [{ choices: [{ text: "Initial response" }] }]
        }),
        [Symbol.asyncIterator]: vi.fn().mockReturnValue({
          next: vi.fn().mockResolvedValue({ done: true })
        })
      };
      streamCompletionInference.mockReturnValue(mockStream);
      const {getByPlaceholderText, getByText, getByTestId} = render(
        <MockServiceProvider>
          <TextGenerationCompletionContainer parameters={{}} />
        </MockServiceProvider>
      );
      const textarea = getByPlaceholderText("Orcas are awesome because...");
      await user.type(textarea, "Test prompt");
      const submitButton = getByTestId("paper-airplane-icon").parentElement;
      await user.click(submitButton);
      await waitFor(() => {
        expect(getByText("Initial response")).toBeInTheDocument();
      });
      mockStream.next.mockResolvedValue({
        value: [{ choices: [{ text: "Refreshed response" }] }]
      });
      const refreshButton = getByTestId("arrow-path-icon").parentElement;
      await user.click(refreshButton);
      await waitFor(() => {
        expect(getByText("Refreshed response")).toBeInTheDocument();
      });
      expect(streamCompletionInference).toHaveBeenCalledTimes(2);
    });
  });
});
