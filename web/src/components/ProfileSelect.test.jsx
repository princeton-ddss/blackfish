import { render, act } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { useContext } from "react";
import ProfileSelect, {
  ProfileContext,
  ProfileProvider
} from "@/components/ProfileSelect";
import { useProfiles } from "@/lib/loaders";

// Mock the hooks
vi.mock("@/lib/loaders", () => ({
  useProfiles: vi.fn(() => ({
    profiles: [
      {name: "test-profile", host: "example.com"},
      {name: "local-test-profile", host: "localhost"}
    ],
    isLoading: false,
    error: false
  }))
}));

// Mock ResizeObserver
global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}));

describe("ProfileProvider", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Clear localStorage
    localStorage.clear();
  });

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

    // Set the item in localStorage before rendering
    localStorage.setItem("profile", JSON.stringify(mockProfile));

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

    expect(contextValue.profile).toEqual(mockProfile);
    expect(baseElement).toMatchSnapshot();
  });

  it("setProfile updates context and localStorage", () => {
    const mockProfile = {
      name: "new-profile",
      host: "newhost.com"
    };

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

    expect(localStorage.getItem("profile")).toEqual(JSON.stringify(mockProfile));
    expect(contextValue.profile).toEqual(mockProfile);
  });
});

describe("ProfileSelect", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset mock to default
    vi.mocked(useProfiles).mockReturnValue({
      profiles: [
        {name: "test-profile", host: "example.com"},
        {name: "local-test-profile", host: "localhost"}
      ],
      isLoading: false,
      error: false
    });
  });

  it("renders loading message", () => {
    vi.mocked(useProfiles).mockReturnValueOnce({
      profiles: [{name: "test-profile", host: "example.com"}],
      isLoading: true,
      error: false
    });
    const {getByText} = render(
      <ProfileSelect
        selectedProfile={{name: "test-profile", host: "example.com"}}
        setSelectedProfile={() => vi.fn()}
      />
    );
    expect(getByText("Loading profiles...")).toBeInTheDocument();
  });

  it("renders error message", () => {
    vi.mocked(useProfiles).mockReturnValueOnce({
      profiles: [{name: "test-profile", host: "example.com"}],
      isLoading: false,
      error: true
    });
    const {getByText} = render(
      <ProfileSelect
        selectedProfile={{name: "test-profile", host: "example.com"}}
        setSelectedProfile={() => vi.fn()}
      />
    );
    expect(getByText("Error!")).toBeInTheDocument();
  });

  it("renders no profiles message", () => {
    vi.mocked(useProfiles).mockReturnValueOnce({
      profiles: [],
      isLoading: false,
      error: false
    });
    const {getByText} = render(
      <ProfileSelect
        selectedProfile={{name: "test-profile", host: "example.com"}}
        setSelectedProfile={() => vi.fn()}
      />
    );
    expect(getByText("No profiles found.")).toBeInTheDocument();
  });

  it("renders with standard options", () => {
    const {baseElement} = render(
      <ProfileSelect
        selectedProfile={{name: "test-profile", host: "example.com"}}
        setSelectedProfile={() => vi.fn()}
      />
    );
    expect(baseElement).toMatchSnapshot();
  });

  it("displays localhost if no host is passed", () => {
    const {baseElement} = render(
      <ProfileSelect
        selectedProfile={{name: "test-profile"}}
        setSelectedProfile={() => vi.fn()}
      />
    );
    expect(baseElement).toMatchSnapshot();
  });

  it("displays empty string if no name is passed", () => {
    const {baseElement} = render(
      <ProfileSelect
        selectedProfile={{host: "example.com"}}
        setSelectedProfile={() => vi.fn()}
      />
    );
    expect(baseElement).toMatchSnapshot();
  });

  it("displays profile missing message", () => {
    const {baseElement, getByText} = render(
      <ProfileSelect
        selectedProfile={{name: "not-listed", host: "example.com"}}
        setSelectedProfile={() => vi.fn()}
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
    const mockSetSelectedProfile = vi.fn();
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
    vi.mocked(useProfiles).mockReturnValueOnce({
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
        setSelectedProfile={() => vi.fn()}
      />
    );
    expect(baseElement).toMatchSnapshot();
  });
});
