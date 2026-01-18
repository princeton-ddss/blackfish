/* eslint react/prop-types: 0 */

import { render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import ServiceModalCheckBox from "@/components/ServiceModalCheckbox";

describe("ServiceModalCheckbox", () => {
  it("renders properly with standard options", () => {
    const {baseElement} = render(
      <ServiceModalCheckBox
        id="gpu-service-checkbox"
        checked={false}
        disabled={false}
        onChange={() => vi.fn()}
        label="Hello, world!"
        help="Ultrices porttitor pellentesque ut quis amet volutpat"
      />
    );
    expect(baseElement).toMatchSnapshot();
  });

  it("renders properly when checked", () => {
    const {baseElement} = render(
      <ServiceModalCheckBox
        id="gpu-service-checkbox"
        checked={true}
        disabled={false}
        onChange={() => vi.fn()}
        label="Hello, world!"
        help="Ultrices porttitor pellentesque ut quis amet volutpat"
      />
    );
    expect(baseElement).toMatchSnapshot();
  });

  it("renders in disabled state", () => {
    const {baseElement} = render(
      <ServiceModalCheckBox
        id="gpu-service-checkbox"
        checked={false}
        disabled={true}
        onChange={() => vi.fn()}
        label="Hello, world!"
        help="Ultrices porttitor pellentesque ut quis amet volutpat"
      />
    );
    expect(baseElement).toMatchSnapshot();
  });

  it("renders in checked and disabled state", () => {
    const {baseElement} = render(
      <ServiceModalCheckBox
        id="gpu-service-checkbox"
        checked={true}
        disabled={true}
        onChange={() => vi.fn()}
        label="Hello, world!"
        help="Ultrices porttitor pellentesque ut quis amet volutpat"
      />
    );
    expect(baseElement).toMatchSnapshot();
  });
});
