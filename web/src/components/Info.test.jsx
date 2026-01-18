import { render } from "@testing-library/react";
import { test, expect } from "vitest";
import Info from "@/components/Info";

test("Info", () => {
  const {baseElement} = render(
    <Info header="Torquent luctus dui" message="Netus sollicitudin commodo nisi convallis fermentum quam." />
  );
  expect(baseElement).toMatchSnapshot();
});
