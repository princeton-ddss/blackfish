import { render } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import SpeechRecognitionContainerOptionsForm from "./SpeechRecognitionContainerOptionsForm";

const defaultOptions = {
  input_dir: "",
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
