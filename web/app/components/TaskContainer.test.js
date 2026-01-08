import {render} from "@testing-library/react";
import "@testing-library/jest-dom";
import { TaskContainer } from "@/app/components/TaskContainer";

test("TaskContainer", () => {
  const {baseElement} = render(
    <TaskContainer>
      <h1>Hello, world!</h1>
      <p>Platea mi vel etiam quam ante arcu</p>
    </TaskContainer>
  );
  expect(baseElement).toMatchSnapshot();
});
