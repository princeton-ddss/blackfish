import { render } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import TextGenerationContainerOptionsForm from "./TextGenerationContainerOptionsForm";

const defaultOptions = {
  disable_custom_kernels: false,
  disable_thinking: true,
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
    expect(checkboxFor(container, "Disable Custom Kernels")).toBeInTheDocument();
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
});
