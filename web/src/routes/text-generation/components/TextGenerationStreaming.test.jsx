import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ServiceContext } from "@/providers/ServiceProvider";
import { ProfileContext } from "@/components/ProfileSelect";
import { ServiceStatus } from "@/lib/util";
import { STORAGE_KEYS } from "@/lib/storage";
import TextGenerationChatContainer from "./TextGenerationChatContainer";
import TextGenerationCompletionContainer from "./TextGenerationCompletionContainer";

// Keep the real request helpers and error notifications; attachments are unrelated.
vi.mock("./AttachmentMenu", () => ({ default: () => null }));
vi.mock("./ImageAttachmentList", () => ({ default: () => null }));
vi.mock("./FileAttachmentList", () => ({ default: () => null }));
vi.mock("@/components/FileSelectModal", () => ({ default: () => null }));

const variants = [
  { name: "chat", Component: TextGenerationChatContainer, label: "Ask anything", event: (text) => ({ choices: [{ delta: { content: text } }] }) },
  { name: "completion", Component: TextGenerationCompletionContainer, label: "Prompt anything", event: (text) => ({ choices: [{ text }] }) },
];
const errors = [
  { tail: "data: invalid\n\n", message: "Invalid JSON in inference stream." },
  { tail: "data: {", message: "Inference stream ended with an incomplete event." },
];

function response(text) {
  const bytes = new TextEncoder().encode(text);
  return { ok: true, body: new ReadableStream({
    start(controller) {
      // Exercise framing through the component, including a split field prefix.
      controller.enqueue(bytes.slice(0, 3));
      controller.enqueue(bytes.slice(3));
      controller.close();
    },
  }) };
}

function mount(Component) {
  render(
    <ProfileContext.Provider value={{ profile: { name: "local", schema: "local" } }}>
      <ServiceContext.Provider value={{ selectedService: { id: "svc", name: "svc", port: 8123, status: ServiceStatus.HEALTHY } }}>
        <Component parameters={{}} systemMessage={{ role: "system", content: "" }} />
      </ServiceContext.Provider>
    </ProfileContext.Provider>
  );
}

async function submit(label) {
  const input = screen.getByRole("textbox", { name: label });
  await userEvent.setup().type(input, "My request");
  fireEvent.submit(input.closest("form"));
}

beforeEach(() => {
  vi.spyOn(console, "debug").mockImplementation(() => {});
  vi.spyOn(console, "error").mockImplementation(() => {});
  Object.defineProperty(Element.prototype, "scrollIntoView", { value: vi.fn(), configurable: true });
});
afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe.each(variants)("$name UI with real streaming helpers", ({ Component, label, event }) => {
  it.each(errors)("keeps partial output and displays $message", async ({ tail, message }) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(`data: ${JSON.stringify(event("Partial answer"))}\n\n${tail}`)));
    mount(Component);
    await submit(label);
    expect(await screen.findByText(message)).toBeVisible();
    expect(screen.getByText("Partial answer")).toBeVisible();
  });

  it("reports a first-event failure and allows a successful retry", async () => {
    vi.stubGlobal("fetch", vi.fn()
      .mockResolvedValueOnce(response(errors[0].tail))
      .mockResolvedValueOnce(response(`data: ${JSON.stringify(event("Retry answer"))}\n\ndata: [DONE]\n\n`)));
    mount(Component);
    await submit(label);
    expect(await screen.findByText(errors[0].message)).toBeVisible();
    const input = screen.getByRole("textbox", { name: label });
    expect(input).toHaveValue("My request");
    fireEvent.submit(input.closest("form"));
    expect(await screen.findByText("Retry answer")).toBeVisible();
    await waitFor(() => expect(screen.queryByText(errors[0].message)).not.toBeInTheDocument());
  });

  it("accepts an empty DONE stream without an error", async () => {
    const fetchMock = vi.fn().mockResolvedValue(response("data: [DONE]\n\n"));
    vi.stubGlobal("fetch", fetchMock);
    mount(Component);
    await submit(label);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledOnce());
    expect(screen.queryByText("Request failed")).not.toBeInTheDocument();
    expect(screen.queryByText("Completion failed")).not.toBeInTheDocument();
  });
});

it.each(errors.flatMap((error) => [
  { ...error, replacement: "Partial replacement", expected: "Partial replacement" },
  { ...error, replacement: "", expected: "Original answer" },
]))("preserves $expected after regeneration reports $message", async ({ tail, message, replacement, expected }) => {
  sessionStorage.setItem(STORAGE_KEYS.TG_CHAT_MESSAGES, JSON.stringify([
    { role: "user", content: "My request" },
    { role: "assistant", content: "Original answer" },
  ]));
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(
    `data: ${JSON.stringify(variants[0].event(replacement))}\n\n${tail}`
  )));
  mount(TextGenerationChatContainer);
  await userEvent.setup().click(screen.getByRole("button", { name: "Regenerate" }));
  expect(await screen.findByText(message)).toBeVisible();
  expect(screen.getByText(expected)).toBeVisible();
});

it("keeps the original chat answer when regeneration completes without text", async () => {
  sessionStorage.setItem(STORAGE_KEYS.TG_CHAT_MESSAGES, JSON.stringify([
    { role: "user", content: "My request" },
    { role: "assistant", content: "Original answer" },
  ]));
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response("data: [DONE]\n\n")));
  mount(TextGenerationChatContainer);
  await userEvent.setup().click(screen.getByRole("button", { name: "Regenerate" }));
  expect(await screen.findByText("Original answer")).toBeVisible();
  expect(screen.queryByText("Request failed")).not.toBeInTheDocument();
});
