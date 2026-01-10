import {render} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import "@testing-library/jest-dom";
import NavbarLight from "@/app/components/NavbarLight";

jest.mock("next/navigation", () => ({
  useRouter() {
    return {
      push: jest.fn(),
      replace: jest.fn(),
    };
  },
  usePathname() {
    return '';
  },
}));

describe("NavbarLight", () => {
  const user = userEvent.setup();

  test("Standard", async () => {
    const {baseElement, getByRole, getAllByRole} = render(
      <NavbarLight task="test" />
    );
    await user.click(getByRole("button"));
    expect(baseElement).toMatchSnapshot();
    await user.click(getAllByRole("button")[1]);
    expect(baseElement).toMatchSnapshot();
  });

  test("Login", () => {
    jest.mock("next/navigation", () => ({
      usePathname: () => "localhost:3000/login",
    }));
    const {baseElement} = render(
      <NavbarLight task="test" />
    );
    expect(baseElement).toMatchSnapshot();
  });
});
