import {render} from "@testing-library/react";
import "@testing-library/jest-dom";
import Info from "@/app/components/Info";

test("Info", () => {
  const {baseElement} = render(
    <Info header="Torquent luctus dui" message="Netus sollicitudin commodo nisi convallis fermentum quam." />
  );
  expect(baseElement).toMatchSnapshot();
});
