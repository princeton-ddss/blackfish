import { render } from "@testing-library/react";
import { test, expect } from "vitest";
import DirectoryInputAlert from "./DirectoryInputAlert";

test("DirectoryInputAlert visible", () => {
  const {baseElement, getByText} = render(
    <DirectoryInputAlert root="/mount/audio" isVisible={true} />
  );
  // Surfaces the mount root in the message; transient (no dismiss control).
  expect(getByText(/Only files in the mounted directory/)).toHaveTextContent(
    "/mount/audio"
  );
  expect(baseElement).toMatchSnapshot();
});

test("DirectoryInputAlert not visible", () => {
  const {container} = render(
    <DirectoryInputAlert root="/" isVisible={false} />
  );
  expect(container.firstChild).toBeNull();
});

test("DirectoryInputAlert with default isVisible", () => {
  const {container} = render(
    <DirectoryInputAlert root="/" />
  );
  expect(container.firstChild).toBeNull();
});
