import { render } from "@testing-library/react";
import ServiceModalValidatedInput from "@/app/components/ServiceModalValidatedInput";
import React from "react";

jest.mock("react", () => ({
  ...jest.requireActual("react"),
  useState: jest.fn(),
}));

jest.mock("@/app/lib/util", () => ({
  ...jest.requireActual("@/app/lib/util"),
  randomInt: jest.fn(() => 42),
}));

const mockSetIsValid = jest.fn();
const mockSetError = jest.fn();

beforeEach(() => {
  jest.clearAllMocks();
});

describe("ServiceModalValidatedInput", () => {
  it("renders correctly with standard parameters", () => {
    React.useState
      .mockReturnValueOnce([true, mockSetIsValid])
      .mockReturnValueOnce([null, mockSetError]);

    const {baseElement} = render(
      <ServiceModalValidatedInput
        label="Tempus proin donec"
        help="Lobortis amet quam ut consectetur rhoncus ornare"
        units="kg"
        placeholder="Et efficitur nunc lectus"
        value="Maximus duis neque mauris elementum id vestibulum"
        setValue={(e) => e}
        validate={(e) => e}
        type="text"
        disabled={false}
      />
    );

    expect(baseElement).toMatchSnapshot();
  });

  it("renders correctly when disabled", () => {
    React.useState
      .mockReturnValueOnce([true, mockSetIsValid])
      .mockReturnValueOnce([null, mockSetError]);

    const {baseElement} = render(
      <ServiceModalValidatedInput
        label="Tempus proin donec"
        help="Lobortis amet quam ut consectetur rhoncus ornare"
        units="kg"
        placeholder="Et efficitur nunc lectus"
        value="Maximus duis neque mauris elementum id vestibulum"
        setValue={(e) => e}
        validate={(e) => e}
        type="text"
        disabled={true}
      />
    );

    expect(baseElement).toMatchSnapshot();
  });

  it("renders correctly when invalid", () => {
    React.useState
      .mockReturnValueOnce([false, mockSetIsValid])
      .mockReturnValueOnce([null, mockSetError]);

    const {baseElement} = render(
      <ServiceModalValidatedInput
        label="Tempus proin donec"
        help="Lobortis amet quam ut consectetur rhoncus ornare"
        units="kg"
        placeholder="Et efficitur nunc lectus"
        value="Maximus duis neque mauris elementum id vestibulum"
        setValue={(e) => e}
        validate={(e) => e}
        type="text"
        disabled={false}
      />
    );

    expect(baseElement).toMatchSnapshot();
  });

  it("renders correcrlty with an error", () => {
    React.useState
      .mockReturnValueOnce([true, mockSetIsValid])
      .mockReturnValueOnce(["500 Internal Server Error", mockSetError]);

    const {baseElement} = render(
      <ServiceModalValidatedInput
        label="Tempus proin donec"
        help="Lobortis amet quam ut consectetur rhoncus ornare"
        units="kg"
        placeholder="Et efficitur nunc lectus"
        value="Maximus duis neque mauris elementum id vestibulum"
        setValue={(e) => e}
        validate={(e) => e}
        type="text"
        disabled={false}
      />
    );

    expect(baseElement).toMatchSnapshot();
  });

  it("renders correctly when it is invalid and has error", () => {
    React.useState
      .mockReturnValueOnce([false, mockSetIsValid])
      .mockReturnValueOnce(["500 Internal Server Error", mockSetError]);

    const {baseElement} = render(
      <ServiceModalValidatedInput
        label="Tempus proin donec"
        help="Lobortis amet quam ut consectetur rhoncus ornare"
        units="kg"
        placeholder="Et efficitur nunc lectus"
        value="Maximus duis neque mauris elementum id vestibulum"
        setValue={(e) => e}
        validate={(e) => e}
        type="text"
        disabled={false}
      />
    );

    expect(baseElement).toMatchSnapshot();
  });

  it("renders correctly without help text", () => {
    React.useState
      .mockReturnValueOnce([true, mockSetIsValid])
      .mockReturnValueOnce([null, mockSetError]);

    const {baseElement} = render(
      <ServiceModalValidatedInput
        label="Tempus proin donec"
        units="kg"
        placeholder="Et efficitur nunc lectus"
        value="Test value"
        setValue={(e) => e}
        validate={(e) => e}
        type="text"
        disabled={false}
      />
    );

    expect(baseElement).toMatchSnapshot();
  });

  it("renders correctly without units", () => {
    React.useState
      .mockReturnValueOnce([true, mockSetIsValid])
      .mockReturnValueOnce([null, mockSetError]);

    const {baseElement} = render(
      <ServiceModalValidatedInput
        label="Tempus proin donec"
        help="Lobortis amet quam ut consectetur rhoncus ornare"
        placeholder="Et efficitur nunc lectus"
        value="Test value"
        setValue={(e) => e}
        validate={(e) => e}
        type="text"
        disabled={false}
      />
    );

    expect(baseElement).toMatchSnapshot();
  });

  it("renders correctly with htmlFor prop", () => {
    React.useState
      .mockReturnValueOnce([true, mockSetIsValid])
      .mockReturnValueOnce([null, mockSetError]);

    const {baseElement} = render(
      <ServiceModalValidatedInput
        label="Tempus proin donec"
        help="Lobortis amet quam ut consectetur rhoncus ornare"
        units="kg"
        placeholder="Et efficitur nunc lectus"
        value="Test value"
        setValue={(e) => e}
        validate={(e) => e}
        type="text"
        disabled={false}
        htmlFor="custom-input"
      />
    );

    expect(baseElement).toMatchSnapshot();
  });
});
