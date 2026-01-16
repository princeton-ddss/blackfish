import { render, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { test, expect } from "vitest";
import DirectoryInput from "@/components/DirectoryInput";

test("Enabled DirectoryInput", async () => {
  const user = userEvent.setup();
  const {baseElement, getByRole} = render(
    <DirectoryInput
      root="/"
      path="test-path"
      setPath={(e) => e}
      pathError={false}
      setPathError={(e) => e}
      disabled={false}
    />
  );
  expect(baseElement).toMatchSnapshot();
  // TODO These event triggering tests are stubs.
  // They are not useful in function yet, as the setPath and setPathError functions are noop.
  await act(async () => {
    await user.click(getByRole("button"));
  });
  expect(baseElement).toMatchSnapshot();
  await act(async () => {
    const input = getByRole("textbox");
    input.focus();
    await user.keyboard("{Enter}");
  });
  expect(baseElement).toMatchSnapshot();
  await act(async () => {
    const input = getByRole("textbox");
    input.focus();
    await user.keyboard("Hello, world!");
  });
  expect(baseElement).toMatchSnapshot();
});

test("Disabled DirectoryInput", async () => {
  const user = userEvent.setup();
  const {baseElement, getByRole} = render(
    <DirectoryInput
      root="/"
      path="test-path"
      setPath={(e) => e}
      pathError={false}
      setPathError={(e) => e}
      disabled={true}
    />
  );
  expect(baseElement).toMatchSnapshot();
  // TODO These event triggering tests are stubs.
  // They are not useful in function yet, as the setPath and setPathError functions are noop.
  await act(async () => {
    await user.click(getByRole("button"));
  });
  expect(baseElement).toMatchSnapshot();
  await act(async () => {
    const input = getByRole("textbox");
    input.focus();
    await user.keyboard("{Enter}");
  });
  expect(baseElement).toMatchSnapshot();
  await act(async () => {
    const input = getByRole("textbox");
    input.focus();
    await user.keyboard("Hello, world!");
  });
  expect(baseElement).toMatchSnapshot();
});
