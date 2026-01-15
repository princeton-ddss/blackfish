import {render} from "@testing-library/react";
import "@testing-library/jest-dom";
import Warning from "@/app/components/Warning";

test("Warning", () => {
  const component = render(
    <Warning
      header="Hello, world!"
      message="Phasellus eget risus pretium nec primis varius"
    />
  );
  expect(component.baseElement).toMatchSnapshot();
});
