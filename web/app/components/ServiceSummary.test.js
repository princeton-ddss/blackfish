import { render, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import "@testing-library/jest-dom";
import ServiceSummary from "@/app/components/ServiceSummary";
import { useServices } from "@/app/lib/loaders";
import { deleteService, stopService } from "@/app/lib/requests";
import { ServiceStatus } from "@/app/lib/util";

jest.mock("@/app/lib/loaders", () => ({
  useServices: jest.fn(),
}));

jest.mock("@/app/lib/requests", () => ({
  deleteService: jest.fn(),
  stopService: jest.fn(),
}));

jest.mock("@/app/lib/util", () => ({
  ...jest.requireActual("@/app/lib/util"),
  formattedTimeInterval: jest.fn(() => "2 hours ago"),
}));

const mockMutate = jest.fn();

beforeEach(() => {
  jest.clearAllMocks();
  useServices.mockReturnValue({
    mutate: mockMutate,
  });
  deleteService.mockResolvedValue();
  stopService.mockResolvedValue();
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

  describe("Action buttons", () => {
    it("renders Stop button for HEALTHY service", () => {
      const {baseElement, getByRole} = render(
        <ServiceSummary
          service={mockService}
          profile={mockProfile}
          task="test-task"
        />
      );
      expect(getByRole("button", { name: "Stop" })).toBeInTheDocument();
      expect(baseElement).toMatchSnapshot();
    });

    it("renders Stop button for UNHEALTHY service", () => {
      const unhealthyService = {
        ...mockService,
        status: ServiceStatus.UNHEALTHY,
      };
      const {baseElement, getByRole} = render(
        <ServiceSummary
          service={unhealthyService}
          profile={mockProfile}
          task="test-task"
        />
      );
      expect(getByRole("button", { name: "Stop" })).toBeInTheDocument();
      expect(baseElement).toMatchSnapshot();
    });

    it("renders Cancel button for STARTING service", () => {
      const startingService = {
        ...mockService,
        status: ServiceStatus.STARTING,
      };
      const {baseElement, getByRole} = render(
        <ServiceSummary
          service={startingService}
          profile={mockProfile}
          task="test-task"
        />
      );
      expect(getByRole("button", { name: "Cancel" })).toBeInTheDocument();
      expect(baseElement).toMatchSnapshot();
    });

    it("renders Cancel button for PENDING service", () => {
      const pendingService = {
        ...mockService,
        status: ServiceStatus.PENDING,
      };
      const {baseElement, getByRole} = render(
        <ServiceSummary
          service={pendingService}
          profile={mockProfile}
          task="test-task"
        />
      );
      expect(getByRole("button", { name: "Cancel" })).toBeInTheDocument();
      expect(baseElement).toMatchSnapshot();
    });

    it("renders Cancel button for SUBMITTED service", () => {
      const submittedService = {
        ...mockService,
        status: ServiceStatus.SUBMITTED,
      };
      const {baseElement, getByRole} = render(
        <ServiceSummary
          service={submittedService}
          profile={mockProfile}
          task="test-task"
        />
      );
      expect(getByRole("button", { name: "Cancel" })).toBeInTheDocument();
      expect(baseElement).toMatchSnapshot();
    });

    it("renders Delete button for STOPPED service", () => {
      const stoppedService = {
        ...mockService,
        status: ServiceStatus.STOPPED,
      };
      const {baseElement, getByRole} = render(
        <ServiceSummary
          service={stoppedService}
          profile={mockProfile}
          task="test-task"
        />
      );
      expect(getByRole("button", { name: "Delete" })).toBeInTheDocument();
      expect(baseElement).toMatchSnapshot();
    });

    it("renders Delete button for EXPIRED service", () => {
      const expiredService = {
        ...mockService,
        status: ServiceStatus.EXPIRED,
      };
      const {baseElement, getByRole} = render(
        <ServiceSummary
          service={expiredService}
          profile={mockProfile}
          task="test-task"
        />
      );
      expect(getByRole("button", { name: "Delete" })).toBeInTheDocument();
      expect(baseElement).toMatchSnapshot();
    });

    it("renders Delete button for TIMEOUT service", () => {
      const timeoutService = {
        ...mockService,
        status: ServiceStatus.TIMEOUT,
      };
      const {baseElement, getByRole} = render(
        <ServiceSummary
          service={timeoutService}
          profile={mockProfile}
          task="test-task"
        />
      );
      expect(getByRole("button", { name: "Delete" })).toBeInTheDocument();
      expect(baseElement).toMatchSnapshot();
    });

    it("renders Delete button for FAILED service", () => {
      const failedService = {
        ...mockService,
        status: ServiceStatus.FAILED,
      };
      const {baseElement, getByRole} = render(
        <ServiceSummary
          service={failedService}
          profile={mockProfile}
          task="test-task"
        />
      );
      expect(getByRole("button", { name: "Delete" })).toBeInTheDocument();
      expect(baseElement).toMatchSnapshot();
    });

    it("renders no button for unknown service status", () => {
      const unknownStatusService = {
        ...mockService,
        status: "UNKNOWN_STATUS",
      };
      const {baseElement, queryByRole} = render(
        <ServiceSummary
          service={unknownStatusService}
          profile={mockProfile}
          task="test-task"
        />
      );
      expect(queryByRole("button")).not.toBeInTheDocument();
      expect(baseElement).toMatchSnapshot();
    });

    it("renders no button when service has no status", () => {
      const noStatusService = {
        ...mockService,
        status: null,
      };
      const {baseElement, queryByRole} = render(
        <ServiceSummary
          service={noStatusService}
          profile={mockProfile}
          task="test-task"
        />
      );
      expect(queryByRole("button")).not.toBeInTheDocument();
      expect(baseElement).toMatchSnapshot();
    });
  });

  describe("Button interactions", () => {
    it("calls stopService when Stop button is clicked", async () => {
      const user = userEvent.setup();
      const {baseElement, getByRole} = render(
        <ServiceSummary
          service={mockService}
          profile={mockProfile}
          task="test-task"
        />
      );
      await user.click(getByRole("button", { name: "Stop" }));
      expect(stopService).toHaveBeenCalledWith("service-123");
      expect(mockMutate).toHaveBeenCalled();
      expect(baseElement).toMatchSnapshot();
    });

    it("calls stopService when Cancel button is clicked", async () => {
      const user = userEvent.setup();
      const startingService = {
        ...mockService,
        status: ServiceStatus.STARTING,
      };
      const {baseElement, getByRole} = render(
        <ServiceSummary
          service={startingService}
          profile={mockProfile}
          task="test-task"
        />
      );
      await user.click(getByRole("button", { name: "Cancel" }));
      expect(stopService).toHaveBeenCalledWith("service-123");
      expect(mockMutate).toHaveBeenCalled();
      expect(baseElement).toMatchSnapshot();
    });

    it("calls deleteService when Delete button is clicked", async () => {
      const user = userEvent.setup();
      const stoppedService = {
        ...mockService,
        status: ServiceStatus.STOPPED,
      };
      const {baseElement, getByRole} = render(
        <ServiceSummary
          service={stoppedService}
          profile={mockProfile}
          task="test-task"
        />
      );
      await user.click(getByRole("button", { name: "Delete" }));
      expect(deleteService).toHaveBeenCalledWith("service-123");
      expect(mockMutate).toHaveBeenCalled();
      expect(baseElement).toMatchSnapshot();
    });

    it("shows loading state while updating", async () => {
      const user = userEvent.setup();
      let resolveStopService;
      stopService.mockReturnValue(
        new Promise((resolve) => {
          resolveStopService = resolve;
        })
      );
      const {baseElement, getByRole, container} = render(
        <ServiceSummary
          service={mockService}
          profile={mockProfile}
          task="test-task"
        />
      );
      await user.click(getByRole("button", { name: "Stop" }));
      const status = container.querySelector(".service-summary__status");
      expect(status).toHaveClass("service-summary__status--updating");
      resolveStopService();
      await waitFor(() => {
        expect(status).not.toHaveClass("service-summary__status--updating");
      });
      expect(baseElement).toMatchSnapshot();
    });

    it("handles stopService error gracefully", async () => {
      const user = userEvent.setup();
      const consoleErrorSpy = jest.spyOn(console, "error").mockImplementation();
      stopService.mockRejectedValue(new Error("Network error"));
      const {baseElement, getByRole} = render(
        <ServiceSummary
          service={mockService}
          profile={mockProfile}
          task="test-task"
        />
      );
      await user.click(getByRole("button", { name: "Stop" }));
      await waitFor(() => {
        expect(consoleErrorSpy).toHaveBeenCalledWith(
          "An error occurred while stopping a service:",
          expect.any(Error)
        );
      });
      expect(baseElement).toMatchSnapshot();
      consoleErrorSpy.mockRestore();
    });

    it("handles deleteService error gracefully", async () => {
      const user = userEvent.setup();
      const consoleErrorSpy = jest.spyOn(console, "error").mockImplementation();
      deleteService.mockRejectedValue(new Error("Network error"));
      const stoppedService = {
        ...mockService,
        status: ServiceStatus.STOPPED,
      };
      const {baseElement, getByRole} = render(
        <ServiceSummary
          service={stoppedService}
          profile={mockProfile}
          task="test-task"
        />
      );
      await user.click(getByRole("button", { name: "Delete" }));
      await waitFor(() => {
        expect(consoleErrorSpy).toHaveBeenCalledWith(
          "An error occurred while deleting a service:",
          expect.any(Error)
        );
      });
      expect(baseElement).toMatchSnapshot();
      consoleErrorSpy.mockRestore();
    });

    it("does not call service actions when service is null", async () => {
      const consoleWarnSpy = jest.spyOn(console, "warn").mockImplementation();
      const {baseElement} = render(
        <ServiceSummary service={null} profile={mockProfile} task="test-task" />
      );
      expect(consoleWarnSpy).not.toHaveBeenCalled();
      expect(stopService).not.toHaveBeenCalled();
      expect(deleteService).not.toHaveBeenCalled();
      expect(baseElement).toMatchSnapshot();
      consoleWarnSpy.mockRestore();
    });
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

  describe("Status display", () => {
    it("shows animate-pulse for STARTING status", () => {
      const startingService = {
        ...mockService,
        status: ServiceStatus.STARTING,
      };
      const {baseElement, getByText} = render(
        <ServiceSummary
          service={startingService}
          profile={mockProfile}
          task="test-task"
        />
      );
      expect(getByText("starting")).toHaveClass("animate-pulse");
      expect(baseElement).toMatchSnapshot();
    });

    it("does not show animate-pulse for non-STARTING status", () => {
      const {baseElement, getByText} = render(
        <ServiceSummary
          service={mockService}
          profile={mockProfile}
          task="test-task"
        />
      );
      expect(getByText("healthy")).not.toHaveClass("animate-pulse");
      expect(baseElement).toMatchSnapshot();
    });
  });
});
