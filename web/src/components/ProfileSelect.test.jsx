import { render, act } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { useContext } from "react";
import ProfileSelect, {
  ProfileContext,
  ProfileProvider
} from "@/components/ProfileSelect";
import { useProfiles } from "@/lib/loaders";

const defaultProfiles = [
  {name: "test-profile", host: "example.com"},
  {name: "local-test-profile", host: "localhost"},
  {name: "new-profile", host: "newhost.com"}
];

// Mock the hooks
vi.mock("@/lib/loaders", () => ({
  useProfiles: vi.fn(() => ({
    profiles: defaultProfiles,
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
    vi.mocked(useProfiles).mockReturnValue({
      profiles: defaultProfiles,
      isLoading: false,
      error: false
    });
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

  it("resolves profile from storage by name", () => {
    localStorage.setItem("profileName", "test-profile");

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

    expect(contextValue.profile).toEqual(
      defaultProfiles.find((p) => p.name === "test-profile")
    );
    expect(baseElement).toMatchSnapshot();
  });

  it("resolves to null when the stored name is not in /api/profiles", () => {
    localStorage.setItem("profileName", "unknown-profile");

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

    expect(contextValue.profile).toBeNull();
  });

  it("removes legacy 'profile' key on mount", () => {
    localStorage.setItem("profile", JSON.stringify({name: "stale", type: "slurm"}));

    render(
      <ProfileProvider>
        <h1>Hello, world!</h1>
      </ProfileProvider>
    );

    expect(localStorage.getItem("profile")).toBeNull();
  });

  it("setProfile persists name and resolves fresh profile from the API list", () => {
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

    // Simulate an external writer passing a stale shape. Only the name
    // should be persisted; the resolved profile should be the fresh API copy.
    act(() => {
      contextValue.setProfile({name: "new-profile", type: "slurm", host: "stale"});
    });

    expect(localStorage.getItem("profileName")).toEqual("new-profile");
    expect(contextValue.profile).toEqual(
      defaultProfiles.find((p) => p.name === "new-profile")
    );
  });

  it("setProfile with null clears the stored name", () => {
    localStorage.setItem("profileName", "test-profile");

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
      contextValue.setProfile(null);
    });

    expect(localStorage.getItem("profileName")).toBeNull();
    expect(contextValue.profile).toBeNull();
  });
});

describe("ProfileSelect", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset mock to default
    vi.mocked(useProfiles).mockReturnValue({
      profiles: defaultProfiles,
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
    expect(getByText("Profile")).toBeInTheDocument();
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
    expect(getByText("Error")).toBeInTheDocument();
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
    expect(getByText("No profiles")).toBeInTheDocument();
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

  it("displays no profile selected state", () => {
    const {baseElement, getByRole, getByText} = render(
      <ProfileSelect />
    );
    // When no profile is selected, the menu button shows the "Profile"
    // fallback label alongside a warning triangle icon.
    expect(getByText("Profile")).toBeInTheDocument();
    expect(getByRole("button")).toBeInTheDocument();
    expect(baseElement.querySelector('svg[aria-hidden="true"].text-yellow-400')).toBeInTheDocument();
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
