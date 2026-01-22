import { render } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import ServiceLaunchErrorAlert from "@/components/ServiceLaunchErrorAlert";

const mockHandleClick = vi.fn();

describe("ServiceLaunchErrorAlert", () => {
  it("renders error text", () => {
    const {baseElement, getByText} = render(
      <ServiceLaunchErrorAlert
        error={{message: "Hello, world!"}}
        onClick={(e) => e}
      />
    );
    expect(getByText("Hello, world!")).toBeInTheDocument();
    expect(baseElement).toMatchSnapshot();
  });

  it("calls onClick when button is clicked", async () => {
    const user = userEvent.setup();
    const {getByRole} = render(
      <ServiceLaunchErrorAlert
        error={{message: "Hi, all!"}}
        onClick={mockHandleClick}
      />
    );
    await user.click(getByRole("button"));
    expect(mockHandleClick).toHaveBeenCalled();
  });
});
