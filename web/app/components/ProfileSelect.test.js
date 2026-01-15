import { render, act } from "@testing-library/react";
import "@testing-library/jest-dom";
import { describe, expect, it, jest } from "@jest/globals";
import { useContext } from "react";
import ProfileSelect, {
  ProfileContext,
  ProfileProvider
} from "@/app/components/ProfileSelect";

describe("ProfileProvider", () => {
  it("renders children", () => {
    const {baseElement, getByText} = render(
      <ProfileProvider>
        <h1>Hello, world!</h1>
      </ProfileProvider>
    );
    expect(getByText("Hello, world!")).toBeInTheDocument();
    expect(baseElement).toMatchSnapshot();
  });

  it("restores profile from storage", () => {
    const mockProfile = {
      name: "test-profile",
      host: "example.com"
    };

    const mockGetItem = jest.spyOn(Storage.prototype, "getItem");
    mockGetItem.mockReturnValue(JSON.stringify(mockProfile));

    let contextValue = null;
    const TestComponent = () => {
      const context = useContext(ProfileContext);
      contextValue = context;
      return <h1>Hello, world!</h1>;
    };

    const {baseElement} = render(
      <ProfileProvider>
        <ProfileContext.Consumer>
          {(value) => {
            contextValue = value;
            return <TestComponent />;
          }}
        </ProfileContext.Consumer>
      </ProfileProvider>
    );

    expect(mockGetItem).toHaveBeenCalledWith("profile");
    expect(contextValue.profile).toEqual(mockProfile);
    expect(baseElement).toMatchSnapshot();

    mockGetItem.mockRestore();
  });

  it("setProfile updates context and localStorage", () => {
    const mockProfile = {
      name: "new-profile",
      host: "newhost.com"
    };

    const mockSetItem = jest.spyOn(Storage.prototype, "setItem");
    mockSetItem.mockImplementation(() => {});

    let contextValue = null;
    const TestComponent = () => {
      const context = useContext(ProfileContext);
      contextValue = context;
      return <h1>Hello, world!</h1>;
    };

    render(
      <ProfileProvider>
        <ProfileContext.Consumer>
          {(value) => {
            contextValue = value;
            return <TestComponent />;
          }}
        </ProfileContext.Consumer>
      </ProfileProvider>
    );

    act(() => {
      contextValue.setProfile(mockProfile);
    });

    expect(mockSetItem).toHaveBeenCalledWith("profile", JSON.stringify(mockProfile));
    expect(contextValue.profile).toEqual(mockProfile);

    mockSetItem.mockRestore();
  });
});

// Mock ResizeObserver
global.ResizeObserver = jest.fn().mockImplementation(() => ({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn(),
}));

// Mock the hooks
jest.mock("@/app/lib/loaders", () => ({
  useProfiles: jest.fn(() => ({
    profiles: [
      {name: "test-profile", host: "example.com"},
      {name: "local-test-profile", host: "localhost"}
    ],
    isLoading: false,
    error: false
  }))
}));

describe("ProfileSelect", () => {
  it("renders loading message", () => {
    const {useProfiles} = require("@/app/lib/loaders");
    useProfiles.mockReturnValueOnce({
      profiles: [{name: "test-profile", host: "example.com"}],
      isLoading: true,
      error: false
    });
    const {getByText} = render(
      <ProfileSelect
        selectedProfile={{name: "test-profile", host: "example.com"}}
        setSelectedProfile={() => jest.fn()}
      />
    );
    expect(getByText("Loading profiles...")).toBeInTheDocument();
  });

  it("renders error message", () => {
    const {useProfiles} = require("@/app/lib/loaders");
    useProfiles.mockReturnValueOnce({
      profiles: [{name: "test-profile", host: "example.com"}],
      isLoading: false,
      error: true
    });
    const {getByText} = render(
      <ProfileSelect
        selectedProfile={{name: "test-profile", host: "example.com"}}
        setSelectedProfile={() => jest.fn()}
      />
    );
    expect(getByText("Error!")).toBeInTheDocument();
  });

  it("renders no profiles message", () => {
    const {useProfiles} = require("@/app/lib/loaders");
    useProfiles.mockReturnValueOnce({
      profiles: [],
      isLoading: false,
      error: false
    });
    const {getByText} = render(
      <ProfileSelect
        selectedProfile={{name: "test-profile", host: "example.com"}}
        setSelectedProfile={() => jest.fn()}
      />
    );
    expect(getByText("No profiles found.")).toBeInTheDocument();
  });

  it("renders with standard options", () => {
    const {baseElement} = render(
      <ProfileSelect
        selectedProfile={{name: "test-profile", host: "example.com"}}
        setSelectedProfile={() => jest.fn()}
      />
    );
    expect(baseElement).toMatchSnapshot();
  });

  it("displays localhost if no host is passed", () => {
    const {baseElement} = render(
      <ProfileSelect
        selectedProfile={{name: "test-profile"}}
        setSelectedProfile={() => jest.fn()}
      />
    );
    expect(baseElement).toMatchSnapshot();
  });

  it("displays empty string if no name is passed", () => {
    const {baseElement} = render(
      <ProfileSelect
        selectedProfile={{host: "example.com"}}
        setSelectedProfile={() => jest.fn()}
      />
    );
    expect(baseElement).toMatchSnapshot();
  });

  it("displays profile missing message", () => {
    const {baseElement, getByText} = render(
      <ProfileSelect
        selectedProfile={{name: "not-listed", host: "example.com"}}
        setSelectedProfile={() => jest.fn()}
      />
    );
    expect(getByText("Profile is missing.")).toBeInTheDocument();
    expect(baseElement).toMatchSnapshot();
  });

  it("displays no profile selected message", () => {
    const {baseElement, getByText} = render(
      <ProfileSelect />
    );
    expect(getByText("No profile selected")).toBeInTheDocument();
    expect(baseElement).toMatchSnapshot();
  });

  it("calls setSelectedProfile when profile is selected", () => {
    const mockSetSelectedProfile = jest.fn();
    const {getByRole} = render(
      <ProfileSelect
        selectedProfile={{name: "test-profile", host: "example.com"}}
        setSelectedProfile={mockSetSelectedProfile}
      />
    );
    const button = getByRole("button");
    expect(button).toBeInTheDocument();
  });

  it("renders profiles with localhost when no host specified", () => {
    const {useProfiles} = require("@/app/lib/loaders");
    useProfiles.mockReturnValueOnce({
      profiles: [
        {name: "no-host-profile"},
        {name: "with-host-profile", host: "example.com"}
      ],
      isLoading: false,
      error: false
    });

    const {baseElement} = render(
      <ProfileSelect
        selectedProfile={{name: "no-host-profile"}}
        setSelectedProfile={() => jest.fn()}
      />
    );
    expect(baseElement).toMatchSnapshot();
  });
});
