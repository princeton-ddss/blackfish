import { render } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import ServiceSummary from "@/components/ServiceSummary";
import { ServiceStatus } from "@/lib/util";

vi.mock("@/lib/util", async () => {
  const actual = await vi.importActual("@/lib/util");
  return {
    ...actual,
    formattedTimeInterval: vi.fn(() => "2 hours ago"),
  };
});

beforeEach(() => {
  vi.clearAllMocks();
});

const mockService = {
  id: "service-123",
  model: "example/model-name",
  status: ServiceStatus.HEALTHY,
  created_at: "2023-06-01T12:00:00Z",
  updated_at: "2023-06-01T12:30:00Z",
  host: "localhost",
  port: 8080,
  ntasks_per_node: 4,
  mem: "8GB",
  gres: 2,
};

const mockProfile = {
  id: "profile-123",
  name: "Test Profile",
};

describe("ServiceSummary", () => {
  it("renders empty without a service", () => {
    const {baseElement} = render(
      <ServiceSummary service={null} profile={mockProfile} task="test-task" />
    );
    expect(baseElement).toMatchSnapshot();
  });

  it("renders without a profile", () => {
    const {baseElement} = render(
      <ServiceSummary service={mockService} profile={null} task="test-task" />
    );
    expect(baseElement).toMatchSnapshot();
  });

  it("renders without a profile and a service", () => {
    const {baseElement} = render(
      <ServiceSummary service={null} profile={null} task="test-task" />
    );
    expect(baseElement).toMatchSnapshot();
  });

  it("renders service information when service and profile are provided", () => {
    const {baseElement} = render(
      <ServiceSummary
        service={mockService}
        profile={mockProfile}
        task="test-task"
      />
    );
    expect(baseElement).toMatchSnapshot();
  });

  it("renders service with model without slash", () => {
    const serviceWithoutSlash = {
      ...mockService,
      model: "simple-model",
    };
    const {baseElement, getByText} = render(
      <ServiceSummary
        service={serviceWithoutSlash}
        profile={mockProfile}
        task="test-task"
      />
    );
    expect(getByText("simple-model")).toBeInTheDocument();
    expect(baseElement).toMatchSnapshot();
  });

  it("renders host without port when port is not provided", () => {
    const serviceWithoutPort = {
      ...mockService,
      port: null,
    };
    const {baseElement, getByText} = render(
      <ServiceSummary
        service={serviceWithoutPort}
        profile={mockProfile}
        task="test-task"
      />
    );
    expect(getByText("localhost")).toBeInTheDocument();
    expect(baseElement).toMatchSnapshot();
  });

  it("renders GPU as ice cube when gres is 0", () => {
    const serviceWithNoGPU = {
      ...mockService,
      gres: 0,
    };
    const {baseElement} = render(
      <ServiceSummary
        service={serviceWithNoGPU}
        profile={mockProfile}
        task="test-task"
      />
    );
    expect(baseElement).toMatchSnapshot();
  });

  it("renders dashes for missing service properties", () => {
    const incompleteService = {
      id: "service-123",
      status: ServiceStatus.HEALTHY,
    };
    const {baseElement, container} = render(
      <ServiceSummary
        service={incompleteService}
        profile={mockProfile}
        task="test-task"
      />
    );
    const gpus = Array.from(
      container.querySelectorAll('.gpus-indicator')
    ).filter((el) => el.textContent.trim() === "-");
    expect(gpus).toHaveLength(1);
    expect(baseElement).toMatchSnapshot();
  });

  describe("Timer component", () => {
    it("renders Timer for running service created_at", () => {
      const {baseElement, getAllByText} = render(
        <ServiceSummary
          service={mockService}
          profile={mockProfile}
          task="test-task"
        />
      );
      const timeAgo = getAllByText("2 hours ago");
      expect(timeAgo).toHaveLength(2);
      expect(timeAgo[0]).toBeInTheDocument();
      expect(timeAgo[1]).toBeInTheDocument();
      expect(baseElement).toMatchSnapshot();
    });

    it("renders dash for non-running service time", () => {
      const stoppedService = {
        ...mockService,
        status: ServiceStatus.STOPPED,
      };
      const {baseElement, getAllByText} = render(
        <ServiceSummary
          service={stoppedService}
          profile={mockProfile}
          task="test-task"
        />
      );
      expect(getAllByText("-").length).toBeGreaterThan(0);
      expect(baseElement).toMatchSnapshot();
    });

    it("renders Timer for updated_at when it exists", () => {
      const {baseElement, getByText} = render(
        <ServiceSummary
          service={mockService}
          profile={mockProfile}
          task="test-task"
        />
      );
      expect(getByText("Last updated")).toBeInTheDocument();
      expect(baseElement).toMatchSnapshot();
    });

    it("renders empty div when service doesn't have updated_at", () => {
      const serviceWithoutUpdated = {
        ...mockService,
        updated_at: null,
      };
      const {baseElement, container} = render(
        <ServiceSummary
          service={serviceWithoutUpdated}
          profile={mockProfile}
          task="test-task"
        />
      );
      const empty = container.querySelector(".service-summary__updated-at--empty");
      expect(empty).toBeInTheDocument();
      expect(baseElement).toMatchSnapshot();
    });
  });

});
