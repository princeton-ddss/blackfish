/* eslint react/prop-types: 0 */

import { render, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import "@testing-library/jest-dom";
import { describe, expect, it, jest } from "@jest/globals";
import TextField from "@/app/components/inputs/TextField";

describe("TextField", () => {
  it("renders correctly with standard options", () => {
    const {baseElement} = render(
      <TextField
        label="Conubia a velit elit"
        tooltip="Aenean congue dictumst fringilla ipsum vulputate porta"
        value="123"
        onChange={() => jest.fn()}
        placeholder="Justo ullamcorper tortor suscipit"
        disabled={false}
      />
    );
    expect(baseElement).toMatchSnapshot();
  });

  it("renders correctly when disabled", () => {
    const {baseElement} = render(
      <TextField
        label="Conubia a velit elit"
        tooltip="Aenean congue dictumst fringilla ipsum vulputate porta"
        value="123"
        onChange={() => jest.fn()}
        placeholder="Justo ullamcorper tortor suscipit"
        disabled={true}
      />
    );
    expect(baseElement).toMatchSnapshot();
  });

  it("renders correctly with error", () => {
    const {baseElement, getByText} = render(
      <TextField
        label="Conubia a velit elit"
        tooltip="Aenean congue dictumst fringilla ipsum vulputate porta"
        value="123"
        onChange={() => jest.fn()}
        placeholder="Justo ullamcorper tortor suscipit"
        disabled={false}
        error="This is an error"
      />
    );
    expect(baseElement).toMatchSnapshot();
    expect(getByText("This is an error")).toBeInTheDocument();
  });

  it("renders correctly with disabled and error", () => {
    const {baseElement, getByText} = render(
      <TextField
        label="Conubia a velit elit"
        tooltip="Aenean congue dictumst fringilla ipsum vulputate porta"
        value="123"
        onChange={() => jest.fn()}
        placeholder="Justo ullamcorper tortor suscipit"
        disabled={true}
        error="This is an error"
      />
    );
    expect(baseElement).toMatchSnapshot();
    expect(getByText("This is an error")).toBeInTheDocument();
  });

  it("fires onChange event", async () => {
    const user = userEvent.setup();
    const mockOnChange = jest.fn();
    const {getByRole} = render(
      <TextField
        label="Conubia a velit elit"
        tooltip="Aenean congue dictumst fringilla ipsum vulputate porta"
        value="123"
        onChange={mockOnChange}
        placeholder="Justo ullamcorper tortor suscipit"
      />
    );
    await act(async () => {
      await user.click(getByRole("textbox"));
      await user.keyboard("3");
      expect(mockOnChange).toHaveBeenCalled();
    });
  });

  describe("onKeyDown input", () => {
    it("allows meta-a", async () => {
      const user = userEvent.setup();
      const mockOnKeyDown = jest.fn();
      const {getByRole} = render(
        <form onKeyDown={mockOnKeyDown}>
          <TextField
            label="Conubia a velit elit"
            tooltip="Aenean congue dictumst fringilla ipsum vulputate porta"
            value="123"
            onChange={() => jest.fn()}
            placeholder="Justo ullamcorper tortor suscipit"
          />
        </form>
      );
      await act(async () => {
        const input = getByRole("textbox");
        await user.keyboard("{Meta>}");
        await user.click(input);
        await user.keyboard("a");
        expect(mockOnKeyDown).toHaveBeenCalledWith(
          expect.objectContaining({type: "keydown", key: "a", metaKey: true})
        )
      });
    });

    it("allows number input", async () => {
      const user = userEvent.setup();
      const {getByRole} = render(
        <TextField
          label="Conubia a velit elit"
          tooltip="Aenean congue dictumst fringilla ipsum vulputate porta"
          placeholder="Justo ullamcorper tortor suscipit"
        />
      );
      await act(async () => {
        const input = getByRole("textbox");
        await user.click(input);
        await user.keyboard("12345");
        expect(input.value).toBe("12345");
      });
    });

    it("allows decimal input, converts to integer", async () => {
      const user = userEvent.setup();
      const {getByRole} = render(
        <TextField
          label="Conubia a velit elit"
          tooltip="Aenean congue dictumst fringilla ipsum vulputate porta"
          placeholder="Justo ullamcorper tortor suscipit"
        />
      );
      await act(async () => {
        const input = getByRole("textbox");
        await user.click(input);
        await user.keyboard("1.25");
        expect(input.value).toBe("125");
      });
    });

    it("allows Backspace, Enter, Escape, and Tab", async () => {
      const user = userEvent.setup();
      const mockFormSubmit = jest.fn();
      const mockOnKeyDown = jest.fn();
      const {getByRole} = render(
        <form onSubmit={mockFormSubmit} onKeyDown={mockOnKeyDown}>
          <TextField
            label="Conubia a velit elit"
            tooltip="Aenean congue dictumst fringilla ipsum vulputate porta"
            placeholder="Justo ullamcorper tortor suscipit"
          />
        </form>
      );
      await act(async () => {
        const input = getByRole("textbox");
        await user.click(input);
        await user.keyboard("123");
        expect(input.value).toBe("123");
        await user.keyboard("{Backspace}");
        expect(input.value).toBe("12");
        await user.keyboard("{Escape}");
        expect(mockOnKeyDown).toHaveBeenCalledWith(
          expect.objectContaining({key: "Escape"})
        );
        await user.keyboard("{Enter}");
        expect(mockFormSubmit).toHaveBeenCalledWith(
          expect.objectContaining({type: "submit"})
        );
        expect(document.activeElement).toBe(input);
        await user.keyboard("{Tab}");
        expect(document.activeElement).not.toBe(input);
      });
    });

    it("disallows non-number input", async () => {
      const user = userEvent.setup();
      const {getByRole} = render(
        <TextField
          label="Conubia a velit elit"
          tooltip="Aenean congue dictumst fringilla ipsum vulputate porta"
          placeholder="Justo ullamcorper tortor suscipit"
        />
      );
      await act(async () => {
        const input = getByRole("textbox");
        await user.click(input);
        await user.keyboard("abc");
        expect(input.value).toBe("");
      });
    });
  });
});
