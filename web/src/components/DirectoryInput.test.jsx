import { render, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { test, expect, vi } from "vitest";
import DirectoryInput from "@/components/DirectoryInput";

test("Enabled DirectoryInput renders its controlled value", () => {
  const { baseElement, getByRole } = render(
    <DirectoryInput
      root="/"
      value="test-path"
      onChange={() => {}}
      onSubmit={() => {}}
      disabled={false}
    />
  );
  expect(getByRole("textbox")).toHaveValue("test-path");
  expect(baseElement).toMatchSnapshot();
});

test("onChange fires on edit; onSubmit fires on Enter and Search click", async () => {
  const user = userEvent.setup();
  const onChange = vi.fn();
  const onSubmit = vi.fn();
  const { getByRole } = render(
    <DirectoryInput
      root="/"
      value="/data"
      onChange={onChange}
      onSubmit={onSubmit}
      disabled={false}
    />
  );

  const input = getByRole("textbox");
  await act(async () => {
    input.focus();
    await user.keyboard("x");
  });
  expect(onChange).toHaveBeenCalled();

  await act(async () => {
    await user.keyboard("{Enter}");
  });
  expect(onSubmit).toHaveBeenCalledTimes(1);

  await act(async () => {
    await user.click(getByRole("button"));
  });
  expect(onSubmit).toHaveBeenCalledTimes(2);
});

test("Disabled DirectoryInput ignores edits and submits", async () => {
  const user = userEvent.setup();
  const onChange = vi.fn();
  const onSubmit = vi.fn();
  const { baseElement, getByRole } = render(
    <DirectoryInput
      root="/"
      value="test-path"
      onChange={onChange}
      onSubmit={onSubmit}
      disabled={true}
    />
  );
  expect(baseElement).toMatchSnapshot();

  await act(async () => {
    await user.click(getByRole("button"));
  });
  await act(async () => {
    const input = getByRole("textbox");
    input.focus();
    await user.keyboard("{Enter}");
  });
  expect(onSubmit).not.toHaveBeenCalled();
  expect(onChange).not.toHaveBeenCalled();
});

test("Shows the error message and applies error styling", () => {
  const { getByText, getByRole } = render(
    <DirectoryInput
      root="/"
      value="/missing"
      onChange={() => {}}
      onSubmit={() => {}}
      disabled={false}
      error={{ message: "Path not found" }}
    />
  );
  expect(getByText("Path not found")).toBeInTheDocument();
  // Error border is applied on the wrapping container.
  expect(getByRole("textbox").closest("div.border")).toHaveClass("border-red-500");
});
