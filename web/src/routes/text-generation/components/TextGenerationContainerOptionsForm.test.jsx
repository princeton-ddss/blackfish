import { render } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import TextGenerationContainerOptionsForm from "./TextGenerationContainerOptionsForm";

const defaultOptions = {
  disable_thinking: true,
  api_key: "",
};

function renderForm({ containerOptions = defaultOptions, setContainerOptions = vi.fn(), disabled = false } = {}) {
  return {
    setContainerOptions,
    ...render(
      <TextGenerationContainerOptionsForm
        containerOptions={containerOptions}
        setContainerOptions={setContainerOptions}
        disabled={disabled}
      />
    ),
  };
}

// Find the checkbox <input> nearest to a label's text. ServiceModalCheckbox
// doesn't wire htmlFor/id, so getByLabelText doesn't work.
function checkboxFor(container, labelText) {
  const label = Array.from(container.querySelectorAll("label")).find(
    (el) => el.textContent === labelText
  );
  return label.closest("div.relative").querySelector("input[type='checkbox']");
}

describe("TextGenerationContainerOptionsForm", () => {
  it("hides the toggles until Deployment Options is expanded", async () => {
    const user = userEvent.setup();
    const { getByText, container, queryByText } = renderForm();
    expect(queryByText("Disable Thinking")).not.toBeInTheDocument();
    await user.click(getByText("Deployment Options"));
    expect(checkboxFor(container, "Disable Thinking")).toBeInTheDocument();
  });

  it("renders Disable Thinking checked when disable_thinking is true", async () => {
    const user = userEvent.setup();
    const { getByText, container } = renderForm();
    await user.click(getByText("Deployment Options"));
    expect(checkboxFor(container, "Disable Thinking")).toBeChecked();
  });

  it("flips disable_thinking when the checkbox is clicked", async () => {
    const user = userEvent.setup();
    const setContainerOptions = vi.fn();
    const { getByText, container } = renderForm({ setContainerOptions });
    await user.click(getByText("Deployment Options"));
    await user.click(checkboxFor(container, "Disable Thinking"));
    expect(setContainerOptions).toHaveBeenCalledTimes(1);
    const updater = setContainerOptions.mock.calls[0][0];
    expect(updater(defaultOptions)).toEqual({
      ...defaultOptions,
      disable_thinking: false,
    });
  });

  it("shows the API key without expanding Deployment Options", () => {
    // The field is pre-filled with a generated key. If it were inside the
    // collapsed section, a user who never expanded it would launch a protected
    // service whose key they never saw and cannot retrieve.
    const { getByLabelText, queryByText } = renderForm();

    expect(getByLabelText("API Key")).toBeInTheDocument();
    // Still collapsed: the section's own options remain hidden.
    expect(queryByText("Disable Thinking")).not.toBeInTheDocument();
  });

  it("records an API key as the user types", async () => {
    const user = userEvent.setup();
    const setContainerOptions = vi.fn();
    const { getByLabelText } = renderForm({ setContainerOptions });

    await user.type(getByLabelText("API Key"), "s");

    const updater = setContainerOptions.mock.calls[0][0];
    expect(updater(defaultOptions)).toEqual({ ...defaultOptions, api_key: "s" });
  });

  it("shows the API key rather than masking it", () => {
    // The key is only readable at launch; masking it would hide the one value
    // the user needs to copy before it becomes unrecoverable.
    const { getByLabelText } = renderForm();

    expect(getByLabelText("API Key")).toHaveAttribute("type", "text");
  });

  it("treats an empty API key as valid", async () => {
    // The field is optional: an over-eager validator would block Launch via
    // the isDeepEmpty(validationErrors) gate in ServiceModal.
    const user = userEvent.setup();
    const { getByLabelText, queryByText } = renderForm();

    await user.type(getByLabelText("API Key"), "x");
    await user.clear(getByLabelText("API Key"));

    expect(queryByText(/required/i)).not.toBeInTheDocument();
  });
});
