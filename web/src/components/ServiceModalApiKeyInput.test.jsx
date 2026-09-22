import { render } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import ServiceModalApiKeyInput, {
  generateApiKey,
} from "@/components/ServiceModalApiKeyInput";

function renderInput({ value = "abc123", setValue = vi.fn(), disabled = false } = {}) {
  return {
    setValue,
    ...render(
      <ServiceModalApiKeyInput value={value} setValue={setValue} disabled={disabled} />
    ),
  };
}

describe("generateApiKey", () => {
  it("returns 32 hex characters", () => {
    expect(generateApiKey()).toMatch(/^[0-9a-f]{32}$/);
  });

  it("returns a different key each call", () => {
    const keys = new Set(Array.from({ length: 20 }, () => generateApiKey()));
    expect(keys.size).toBe(20);
  });
});

describe("ServiceModalApiKeyInput", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows the key so the user can read it before launching", () => {
    // It is not recoverable from Blackfish afterwards, only from the job
    // script, so launch is the moment it has to be legible.
    const { getByLabelText } = renderInput({ value: "abc123" });

    expect(getByLabelText("API Key")).toHaveValue("abc123");
    expect(getByLabelText("API Key")).toHaveAttribute("type", "text");
  });

  it("copies the key to the clipboard", async () => {
    // userEvent.setup() installs its own clipboard stub, so spy on the one it
    // provides rather than replacing navigator.
    const user = userEvent.setup();
    const writeText = vi.spyOn(navigator.clipboard, "writeText");
    const { getByLabelText } = renderInput({ value: "abc123" });

    await user.click(getByLabelText("Copy API key"));

    expect(writeText).toHaveBeenCalledWith("abc123");
  });

  it("confirms the copy so the user knows it worked", async () => {
    const user = userEvent.setup();
    const { getByLabelText, findByLabelText } = renderInput({ value: "abc123" });

    await user.click(getByLabelText("Copy API key"));

    expect(await findByLabelText("API key copied")).toBeInTheDocument();
  });

  it("lets the user supply their own key", async () => {
    const user = userEvent.setup();
    const setValue = vi.fn();
    const { getByLabelText } = renderInput({ value: "", setValue });

    await user.type(getByLabelText("API Key"), "m");

    expect(setValue).toHaveBeenCalledWith("m");
  });

  it("hides the copy button when the key is cleared", () => {
    // An empty field is a deliberate choice to run the service open; there is
    // nothing to copy.
    const { queryByLabelText } = renderInput({ value: "" });

    expect(queryByLabelText("Copy API key")).not.toBeInTheDocument();
  });
});
