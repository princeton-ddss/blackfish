import { render } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, test, expect, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import NavbarLight from "@/components/NavbarLight";
import { ProfileContext } from "@/components/ProfileSelect";

// Mock useProfiles so the embedded ProfileSelect doesn't try to fetch.
vi.mock("@/lib/loaders", () => ({
  useProfiles: vi.fn(() => ({
    profiles: [],
    isLoading: false,
    error: false,
  })),
}));

// Wrap component with MemoryRouter and ProfileContext for React Router /
// ProfileContext dependencies.
const renderWithRouter = (ui, { route = "/" } = {}) => {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <ProfileContext.Provider value={{ profile: null, setProfile: vi.fn() }}>
        {ui}
      </ProfileContext.Provider>
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
