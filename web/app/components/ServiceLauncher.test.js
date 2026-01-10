/* eslint react/prop-types: 0 */

import { render, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import "@testing-library/jest-dom";
import { describe, expect, it, jest } from "@jest/globals";
import ServiceLauncher from "@/app/components/ServiceLauncher";
import { ServiceContext } from "@/app/providers/ServiceProvider";

// Mock the hooks
jest.mock("@/app/lib/loaders", () => ({
  useModels: jest.fn(() => ({
    models: [{ id: "test-model", name: "Test Model" }],
    isLoading: false
  })),
  useServices: jest.fn(() => ({
    services: [],
    mutate: jest.fn()
  }))
}));

// Mock ServiceModal component
jest.mock("@/app/components/ServiceModal", () => {
  return function MockServiceModal({ children }) {
    return <div data-testid="service-modal">{children}</div>;
  };
});

const mockServiceContext = {
  selectedService: null,
  setSelectedServiceId: jest.fn()
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
    const {useModels} = require("@/app/lib/loaders");
    useModels.mockReturnValueOnce({
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
    const {useModels} = require("@/app/lib/loaders");
    useModels.mockReturnValueOnce({
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
