import { render } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import SpeechRecognitionContainerOptionsForm from "./SpeechRecognitionContainerOptionsForm";

const defaultOptions = {
  input_dir: "",
  api_key: "",
};

function renderForm({
  containerOptions = defaultOptions,
  setContainerOptions = vi.fn(),
  setValidationErrors = vi.fn(),
  disabled = false,
} = {}) {
  return {
    setContainerOptions,
    setValidationErrors,
    ...render(
      <SpeechRecognitionContainerOptionsForm
        containerOptions={containerOptions}
        setContainerOptions={setContainerOptions}
        setValidationErrors={setValidationErrors}
        disabled={disabled}
      />
    ),
  };
}

describe("SpeechRecognitionContainerOptionsForm", () => {
  it("records an API key as the user types", async () => {
    const user = userEvent.setup();
    const setContainerOptions = vi.fn();
    const { getByLabelText } = renderForm({ setContainerOptions });

    await user.type(getByLabelText("API Key"), "s");

    const updater = setContainerOptions.mock.calls[0][0];
    expect(updater(defaultOptions)).toEqual({ ...defaultOptions, api_key: "s" });
  });

  it("masks the API key input", () => {
    const { getByLabelText } = renderForm();

    expect(getByLabelText("API Key")).toHaveAttribute("type", "password");
  });

  it("does not register a validation error for an empty API key", async () => {
    // Speech recognition could not take a key from any interface before, so
    // an over-eager validator here would newly block launches that work today.
    const user = userEvent.setup();
    const setValidationErrors = vi.fn();
    const { getByLabelText } = renderForm({ setValidationErrors });

    await user.type(getByLabelText("API Key"), "x");
    await user.clear(getByLabelText("API Key"));

    // input_dir is the only field that registers errors; api_key never does.
    for (const call of setValidationErrors.mock.calls) {
      const next = call[0]({});
      expect(next.api_key ?? null).toBeNull();
    }
  });

  it("still validates the input directory", async () => {
    // Guards against the new field disturbing the existing one: a non-empty
    // directory clears its error. (`user.clear()` does not fire this
    // component's onChange, so the empty case isn't reachable this way.)
    const user = userEvent.setup();
    const setValidationErrors = vi.fn();
    const { getByLabelText } = renderForm({ setValidationErrors });

    await user.type(getByLabelText("Input Directory"), "x");

    const states = setValidationErrors.mock.calls
      .map((call) => call[0]({}))
      .filter((state) => "input_dir" in state);
    expect(states.at(-1).input_dir).toBeNull();
  });
});
