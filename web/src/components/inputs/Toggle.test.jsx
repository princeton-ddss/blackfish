import { render } from "@testing-library/react";
import { describe, test, expect } from "vitest";
import Toggle from "@/components/inputs/Toggle";

describe("Toggle", () => {
  test("Checked", () => {
    const {baseElement} = render(
      <Toggle
        checked={true}
        onChange={(e) => e}
        label="Massa fringilla maximus neque pulvinar scelerisque interdum"
        tooltip="Netus consectetur imperdiet etiam eleifend leo nostra"
      />
    );
    expect(baseElement).toMatchSnapshot();
  });

  test("Unchecked", () => {
    const {baseElement} = render(
      <Toggle
        checked={false}
        onChange={(e) => e}
        label="Massa fringilla maximus neque pulvinar scelerisque interdum"
        tooltip="Netus consectetur imperdiet etiam eleifend leo nostra"
      />
    );
    expect(baseElement).toMatchSnapshot();
  });
});
