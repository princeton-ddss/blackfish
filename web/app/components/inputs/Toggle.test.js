import {render} from "@testing-library/react";
import "@testing-library/jest-dom";
import Toggle from "@/app/components/inputs/Toggle";

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
