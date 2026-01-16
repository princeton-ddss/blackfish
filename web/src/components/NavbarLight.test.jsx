import { render } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, test, expect, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import NavbarLight from "@/components/NavbarLight";

// Wrap component with MemoryRouter for React Router context
const renderWithRouter = (ui, { route = "/" } = {}) => {
  return render(
    <MemoryRouter initialEntries={[route]}>
      {ui}
    </MemoryRouter>
  );
};

describe("NavbarLight", () => {
  const user = userEvent.setup();

  test("Standard", async () => {
    const { baseElement, getByRole, getAllByRole } = renderWithRouter(
      <NavbarLight task="test" />
    );
    await user.click(getByRole("button"));
    expect(baseElement).toMatchSnapshot();
    await user.click(getAllByRole("button")[1]);
    expect(baseElement).toMatchSnapshot();
  });

  test("Login", () => {
    const { baseElement } = renderWithRouter(
      <NavbarLight task="test" />,
      { route: "/login" }
    );
    expect(baseElement).toMatchSnapshot();
  });
});
