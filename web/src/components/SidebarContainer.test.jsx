import { render } from "@testing-library/react";
import { test, expect, vi } from "vitest";
import { SidebarContainer } from "@/components/SidebarContainer";
import { ProfileContext } from "@/components/ProfileSelect";
import TextGenerationContainerOptionsForm from "@/routes/text-generation/components/TextGenerationContainerOptionsForm";

vi.mock("@/components/ServiceContainer", () => {
  // eslint-disable-next-line react/prop-types
  return {
    default: function MockServiceContainer({ children }) {
      return <div data-testid="service-container">{children}</div>;
    }
  };
});

vi.mock("@/components/ServiceLauncher", () => {
  return {
    default: function MockServiceLauncher() {
      return <div data-testid="service-launcher">Service Launcher</div>;
    }
  };
});

vi.mock("@/components/ProfileSelect", async () => {
  const { createContext } = await import("react");
  const ProfileContext = createContext();
  return {
    default: function MockProfileSelect() {
      return <div data-testid="profile-select">Profile Select</div>;
    },
    ProfileContext,
  };
});

test("SidebarContainer", () => {
  const mockProfile = {
    name: "default",
    home_dir: "/Users/me/.blackfish",
    cache_dir: "/Users/me/.blackfish",
    type: "local",
  };

  const {baseElement} = render(
    <ProfileContext.Provider value={{
      profile: mockProfile,
      setProfile: vi.fn()
    }}>
      <SidebarContainer
        task="speech-recognition"
        defaultContainerOptions={{
          input_dir: "",
          disable_custom_kernels: false
        }}
        ContainerOptionsFormComponent={
          TextGenerationContainerOptionsForm
        }
      >
        <h1>Hello, world!</h1>
      </SidebarContainer>
    </ProfileContext.Provider>
  );
  expect(baseElement).toMatchSnapshot();
});
