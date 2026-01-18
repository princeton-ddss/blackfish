import { render } from "@testing-library/react";
import { test, expect } from "vitest";
import Warning from "@/components/Warning";

test("Warning", () => {
  const component = render(
    <Warning
      header="Hello, world!"
      message="Phasellus eget risus pretium nec primis varius"
    />
  );
  expect(component.baseElement).toMatchSnapshot();
});
