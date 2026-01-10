import {render} from "@testing-library/react";
import "@testing-library/jest-dom";
import { SidebarContainer } from "@/app/components/SidebarContainer";
import { ProfileContext } from "@/app/components/ProfileSelect";
import TextGenerationContainerOptionsForm from "@/app/text-generation/components/TextGenerationContainerOptionsForm";

jest.mock("@/app/components/ServiceContainer", () => {
  // eslint-disable-next-line react/prop-types
  function MockServiceContainer({ children }) {
    return <div data-testid="service-container">{children}</div>;
  };
  return MockServiceContainer;
});

jest.mock("@/app/components/ServiceLauncher", () => {
  return function MockServiceLauncher() {
    return <div data-testid="service-launcher">Service Launcher</div>;
  };
});

jest.mock("@/app/components/ProfileSelect", () => {
  const ProfileContext = require("react").createContext();
  return {
    __esModule: true,
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
      setProfile: jest.fn()
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
