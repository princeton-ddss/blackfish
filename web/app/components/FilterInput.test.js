import {render, act} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import "@testing-library/jest-dom";
import FilterInput from "@/app/components/FilterInput";

test("Enabled FilterInput", async () => {
  const user = userEvent.setup();
  const {baseElement, getByRole} = render(
    <FilterInput query="Hello, world!" setQuery={(e) => e} disabled={false} />
  );
  expect(baseElement).toMatchSnapshot();
  // TODO These event triggering tests are stubs.
  // They are not useful in function yet, as the setQuery function is noop.
  await act(async () => {
    const input = getByRole("textbox");
    input.focus();
    await user.keyboard("{Escape}");
  });
  expect(baseElement).toMatchSnapshot();
  await act(async () => {
    const input = getByRole("textbox");
    input.focus();
    await user.keyboard("Hi there");
  });
  expect(baseElement).toMatchSnapshot();
});

test("Disabled FilterInput", async () => {
  const user = userEvent.setup();
  const {baseElement, getByRole} = render(
    <FilterInput query="" setQuery={(e) => e} disabled={true} />
  );
  expect(baseElement).toMatchSnapshot();
  // TODO These event triggering tests are stubs.
  // They are not useful in function yet, as the setQuery function is noop.
  await act(async () => {
    const input = getByRole("textbox");
    input.focus();
    await user.keyboard("{Escape}");
  });
  expect(baseElement).toMatchSnapshot();
  await act(async () => {
    const input = getByRole("textbox");
    input.focus();
    user.keyboard("Hi there");
  });
  expect(baseElement).toMatchSnapshot();
});
