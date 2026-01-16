import { render, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { test, expect, vi } from "vitest";
import Chips from "@/components/inputs/Chips";

test("Chips renders correctly with initial values", async () => {
  const user = userEvent.setup();
  const {baseElement, getByRole, getAllByRole} = render(
    <Chips
      values={[
        'one',
        'two',
        'three',
        'four',
        'five',
        'six',
        'seven',
        'eight',
        'nine',
        'ten'
      ]}
      onChange={(e) => e}
      label="Hello, world!"
      tooltip="Feugiat lacinia montes sem himenaeos varius placerat curae nunc scelerisque cubilia a vitae, pellentesque enim odio nascetur lobortis libero penatibus facilisis aenean justo."
    />
  );
  expect(baseElement).toMatchSnapshot();
  const input = getByRole("textbox");
  await act(async () => {
    await user.click(input);
    await user.keyboard("More text");
  });
  expect(baseElement).toMatchSnapshot();
  await act(async () => {
    await user.keyboard("{Enter}");
  });
  expect(baseElement).toMatchSnapshot();
  await act(async () => {
    await user.click(getAllByRole("button")[3]);
  });
  expect(baseElement).toMatchSnapshot();
});

test("Chips renders with empty values array", () => {
  const onChange = vi.fn();
  const {baseElement, getByRole} = render(
    <Chips
      values={[]}
      onChange={onChange}
      label="Empty chips"
      tooltip="No chips yet"
    />
  );
  expect(getByRole("textbox")).toBeInTheDocument();
  expect(baseElement).toMatchSnapshot();
});

test("Chips calls onChange with ADD action when Enter is pressed", async () => {
  const user = userEvent.setup();
  const onChange = vi.fn().mockReturnValue(true);
  const {baseElement, getByRole} = render(
    <Chips
      values={['existing']}
      onChange={onChange}
      label="Test chips"
    />
  );
  const input = getByRole("textbox");
  await user.type(input, "new chip");
  await user.keyboard("{Enter}");
  expect(onChange).toHaveBeenCalledWith("new chip", "add");
  expect(baseElement).toMatchSnapshot();
});

test("Chips does not clear input when onChange returns false", async () => {
  const user = userEvent.setup();
  const onChange = vi.fn().mockReturnValue(false);
  const {baseElement, getByRole} = render(
    <Chips
      values={['existing']}
      onChange={onChange}
      label="Test chips"
    />
  );
  const input = getByRole("textbox");
  await user.type(input, "invalid chip");
  await user.keyboard("{Enter}");
  expect(onChange).toHaveBeenCalledWith("invalid chip", "add");
  expect(input.value).toBe("invalid chip");
  expect(baseElement).toMatchSnapshot();
});

test("Chips clears input when onChange returns true", async () => {
  const user = userEvent.setup();
  const onChange = vi.fn().mockReturnValue(true);
  const {baseElement, getByRole} = render(
    <Chips
      values={['existing']}
      onChange={onChange}
      label="Test chips"
    />
  );
  const input = getByRole("textbox");
  await user.type(input, "valid chip");
  await user.keyboard("{Enter}");
  expect(onChange).toHaveBeenCalledWith("valid chip", "add");
  expect(input.value).toBe("");
  expect(baseElement).toMatchSnapshot();
});

test("Chips calls onChange with REMOVE action when remove button is clicked", async () => {
  const user = userEvent.setup();
  const onChange = vi.fn();
  const values = ['chip1', 'chip2', 'chip3'];
  const {baseElement, getAllByRole} = render(
    <Chips
      values={values}
      onChange={onChange}
      label="Test chips"
    />
  );
  await user.click(getAllByRole("button")[1]);
  expect(onChange).toHaveBeenCalledWith(1, "remove");
  expect(baseElement).toMatchSnapshot();
});

test("Chips input updates correctly on typing", async () => {
  const user = userEvent.setup();
  const onChange = vi.fn();
  const {baseElement, getByRole} = render(
    <Chips
      values={[]}
      onChange={onChange}
      label="Test chips"
    />
  );
  const input = getByRole("textbox");
  await user.type(input, "typing test");
  expect(input.value).toBe("typing test");
  expect(baseElement).toMatchSnapshot();
});

test("Chips renders correct number of chips", () => {
  const values = ['one', 'two', 'three'];
  const {getAllByRole} = render(
    <Chips
      values={values}
      onChange={vi.fn()}
      label="Test chips"
    />
  );
  expect(getAllByRole("button")).toHaveLength(3);
});

test("Chips renders without label and tooltip", () => {
  const {baseElement} = render(
    <Chips
      values={['test']}
      onChange={vi.fn()}
    />
  );
  expect(baseElement).toMatchSnapshot();
});

test("Chips only adds chip on Enter key, not other keys", async () => {
  const user = userEvent.setup();
  const onChange = vi.fn();
  const {getByRole} = render(
    <Chips
      values={[]}
      onChange={onChange}
      label="Test chips"
    />
  );
  await user.type(getByRole("textbox"), "test");
  await user.keyboard("{Space}");
  await user.keyboard("{Tab}");
  await user.keyboard("{Escape}");
  expect(onChange).not.toHaveBeenCalled();
});
