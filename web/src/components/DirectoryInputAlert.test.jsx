import { render, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { test, expect } from "vitest";
import DirectoryInputAlert from "./DirectoryInputAlert";

test("DirectoryInputAlert visible and dismissible", async () => {
  const user = userEvent.setup();
  const {baseElement, getByRole, asFragment} = render(
    <DirectoryInputAlert root="/" isVisible={true} />
  );
  expect(baseElement).toMatchSnapshot();
  await act(async () => {
    await user.click(getByRole("button"));
  });
  expect(asFragment().baseElement).toBeUndefined();
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
