import { render, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import ServiceModalValidatedInput from "@/components/ServiceModalValidatedInput";

vi.mock("@/lib/util", async () => {
  const actual = await vi.importActual("@/lib/util");
  return {
    ...actual,
    randomInt: vi.fn(() => 42),
  };
});

beforeEach(() => {
  vi.clearAllMocks();
});

describe("ServiceModalValidatedInput", () => {
  const defaultProps = {
    label: "Tempus proin donec",
    help: "Lobortis amet quam ut consectetur rhoncus ornare",
    units: "kg",
    placeholder: "Et efficitur nunc lectus",
    value: "Maximus duis neque mauris elementum id vestibulum",
    setValue: vi.fn(),
    validate: vi.fn(() => ({ ok: true })),
    type: "text",
    disabled: false,
  };

  it("renders correctly with standard parameters", () => {
    const {baseElement} = render(
      <ServiceModalValidatedInput {...defaultProps} />
    );
    expect(baseElement).toMatchSnapshot();
  });

  it("renders correctly when disabled", () => {
    const {baseElement} = render(
      <ServiceModalValidatedInput {...defaultProps} disabled={true} />
    );
    expect(baseElement).toMatchSnapshot();
  });

  it("renders correctly when invalid after user input", async () => {
    const user = userEvent.setup();
    const validate = vi.fn(() => ({ ok: false, message: "Invalid value" }));
    const setValue = vi.fn();

    const {baseElement, getByRole} = render(
      <ServiceModalValidatedInput
        {...defaultProps}
        value=""
        setValue={setValue}
        validate={validate}
      />
    );

    const input = getByRole("textbox");
    await act(async () => {
      await user.type(input, "x");
    });

    expect(baseElement).toMatchSnapshot();
  });

  it("renders correctly with an error", async () => {
    const user = userEvent.setup();
    const validate = vi.fn(() => ({ ok: false, message: "500 Internal Server Error" }));
    const setValue = vi.fn();

    const {baseElement, getByRole} = render(
      <ServiceModalValidatedInput
        {...defaultProps}
        value=""
        setValue={setValue}
        validate={validate}
      />
    );

    const input = getByRole("textbox");
    await act(async () => {
      await user.type(input, "x");
    });

    expect(baseElement).toMatchSnapshot();
  });

  it("renders correctly without help text", () => {
    const {baseElement} = render(
      <ServiceModalValidatedInput
        {...defaultProps}
        help={undefined}
      />
    );
    expect(baseElement).toMatchSnapshot();
  });

  it("renders correctly without units", () => {
    const {baseElement} = render(
      <ServiceModalValidatedInput
        {...defaultProps}
        units={undefined}
      />
    );
    expect(baseElement).toMatchSnapshot();
  });

  it("renders correctly with htmlFor prop", () => {
    const {baseElement} = render(
      <ServiceModalValidatedInput
        {...defaultProps}
        htmlFor="custom-input"
      />
    );
    expect(baseElement).toMatchSnapshot();
  });

  it("calls setValue and validate on input change", async () => {
    const user = userEvent.setup();
    const setValue = vi.fn();
    const validate = vi.fn(() => ({ ok: true }));

    const {getByRole} = render(
      <ServiceModalValidatedInput
        {...defaultProps}
        value=""
        setValue={setValue}
        validate={validate}
      />
    );

    const input = getByRole("textbox");
    await act(async () => {
      await user.type(input, "test");
    });

    expect(setValue).toHaveBeenCalled();
    expect(validate).toHaveBeenCalled();
  });
});
