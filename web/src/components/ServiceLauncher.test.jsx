/* eslint react/prop-types: 0 */

import { render, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import ServiceLauncher from "@/components/ServiceLauncher";
import { ServiceContext } from "@/providers/ServiceProvider";
import { useModels, useServices } from "@/lib/loaders";

// Mock the hooks
vi.mock("@/lib/loaders", () => ({
  useModels: vi.fn(() => ({
    models: [{ id: "test-model", name: "Test Model" }],
    isLoading: false
  })),
  useServices: vi.fn(() => ({
    services: [],
    mutate: vi.fn()
  }))
}));

// Mock ServiceModal component
vi.mock("@/components/ServiceModal", () => {
  return {
    default: function MockServiceModal({ children }) {
      return <div data-testid="service-modal">{children}</div>;
    }
  };
});

const mockServiceContext = {
  selectedService: null,
  setSelectedServiceId: vi.fn()
};

function testComponent() {
  return (
    <fieldset>
      <legend>Legend</legend>
      <p>Service deployment.</p>
      <input type="text" />
    </fieldset>
  );
}

describe("ServiceLauncher", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset useModels to default
    vi.mocked(useModels).mockReturnValue({
      models: [{ id: "test-model", name: "Test Model" }],
      isLoading: false
    });
    vi.mocked(useServices).mockReturnValue({
      services: [],
      mutate: vi.fn()
    });
  });

  it("renders properly with standard options", () => {
    const {baseElement} = render(
      <ServiceContext.Provider value={mockServiceContext}>
        <ServiceLauncher
          profile={{
            host: "localhost",
            type: "local"
          }}
          task="speech-recognition"
          defaultContainerOptions={{testProp: "yes"}}
          ContainerOptionsFormComponent={testComponent}
        />
      </ServiceContext.Provider>
    );
    expect(baseElement).toMatchSnapshot();
  });

  it("renders in disabled state when missing profile", () => {
    const {baseElement} = render(
      <ServiceContext.Provider value={mockServiceContext}>
        <ServiceLauncher
          task="speech-recognition"
          defaultContainerOptions={{testProp: "yes"}}
          ContainerOptionsFormComponent={testComponent}
        />
      </ServiceContext.Provider>
    );
    expect(baseElement).toMatchSnapshot();
  });

  it("renders in enabled state when missing models and not loading", () => {
    vi.mocked(useModels).mockReturnValueOnce({
      models: undefined,
      isLoading: false
    });
    const {baseElement} = render(
      <ServiceContext.Provider value={mockServiceContext}>
        <ServiceLauncher
          profile={{
            host: "localhost",
            type: "local"
          }}
          task="speech-recognition"
          defaultContainerOptions={{testProp: "yes"}}
          ContainerOptionsFormComponent={testComponent}
        />
      </ServiceContext.Provider>
    );
    expect(baseElement).toMatchSnapshot();
  });

  it("renders in disabled state when missing models and loading", () => {
    vi.mocked(useModels).mockReturnValueOnce({
      models: undefined,
      isLoading: true
    });
    const {baseElement} = render(
      <ServiceContext.Provider value={mockServiceContext}>
        <ServiceLauncher
          profile={{
            host: "localhost",
            type: "local"
          }}
          task="speech-recognition"
          defaultContainerOptions={{testProp: "yes"}}
          ContainerOptionsFormComponent={testComponent}
        />
      </ServiceContext.Provider>
    );
    expect(baseElement).toMatchSnapshot();
  });

  it("renders container component", () => {
    const {getByText} = render(
      <ServiceContext.Provider value={mockServiceContext}>
        <ServiceLauncher
          profile={{
            host: "localhost",
            type: "local"
          }}
          task="speech-recognition"
          defaultContainerOptions={{testProp: "yes"}}
          ContainerOptionsFormComponent={testComponent}
        />
      </ServiceContext.Provider>
    );
    expect(getByText("Legend")).toBeInTheDocument();
  });

  it("opens the modal", async () => {
    const user = userEvent.setup();
    const {baseElement, getByRole} = render(
      <ServiceContext.Provider value={mockServiceContext}>
        <ServiceLauncher
          profile={{
            host: "localhost",
            type: "local"
          }}
          task="speech-recognition"
          defaultContainerOptions={{testProp: "yes"}}
          ContainerOptionsFormComponent={testComponent}
        />
      </ServiceContext.Provider>
    );
    await act(async () => {
      await user.click(getByRole("button"));
      expect(baseElement).toMatchSnapshot();
    });
  });
});
