/* eslint react/prop-types: 0 */

import { render, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import ServiceContainer from "@/components/ServiceContainer";
import { ServiceContext } from "@/providers/ServiceProvider";
import { useServices } from "@/lib/loaders";
import { deleteService, stopService } from "@/lib/requests";
import { ServiceStatus } from "@/lib/util";

vi.mock("@/lib/loaders", () => ({
  useServices: vi.fn(),
}));

vi.mock("@/lib/requests", () => ({
  deleteService: vi.fn(),
  stopService: vi.fn(),
}));

// Stub children that would otherwise pull in SWR/fetch calls.
vi.mock("@/components/ServiceSelect", () => ({
  default: function MockServiceSelect() {
    return <div data-testid="service-select" />;
  },
}));

vi.mock("@/components/ServiceLauncher", () => ({
  default: function MockServiceLauncher() {
    return <div data-testid="service-launcher" />;
  },
}));

vi.mock("@/components/ServiceSummary", () => ({
  default: function MockServiceSummary() {
    return <div data-testid="service-summary" />;
  },
}));

const mockService = {
  id: "service-123",
  model: "example/model-name",
  status: ServiceStatus.HEALTHY,
  created_at: "2023-06-01T12:00:00Z",
  updated_at: "2023-06-01T12:30:00Z",
  host: "localhost",
  port: 8080,
};

const mockProfile = { id: "profile-123", name: "Test Profile" };

const mockMutate = vi.fn();

function renderWithContext(service) {
  return render(
    <ServiceContext.Provider
      value={{ selectedService: service, setSelectedServiceId: vi.fn() }}
    >
      <ServiceContainer profile={mockProfile} task="test-task" />
    </ServiceContext.Provider>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  useServices.mockReturnValue({ mutate: mockMutate });
  deleteService.mockResolvedValue();
  stopService.mockResolvedValue();
});

describe("ServiceContainer", () => {
  describe("Action buttons", () => {
    const runningStatuses = [
      ["HEALTHY", ServiceStatus.HEALTHY],
      ["UNHEALTHY", ServiceStatus.UNHEALTHY],
      ["STARTING", ServiceStatus.STARTING],
      ["PENDING", ServiceStatus.PENDING],
      ["SUBMITTED", ServiceStatus.SUBMITTED],
    ];

    const terminalStatuses = [
      ["STOPPED", ServiceStatus.STOPPED],
      ["EXPIRED", ServiceStatus.EXPIRED],
      ["TIMEOUT", ServiceStatus.TIMEOUT],
      ["FAILED", ServiceStatus.FAILED],
    ];

    it.each(runningStatuses)(
      "renders Stop button for %s service",
      (_label, status) => {
        const { getByRole, queryByRole } = renderWithContext({
          ...mockService,
          status,
        });
        expect(
          getByRole("button", { name: "Stop service" })
        ).toBeInTheDocument();
        expect(
          queryByRole("button", { name: "Delete service" })
        ).not.toBeInTheDocument();
      }
    );

    it.each(terminalStatuses)(
      "renders Delete button for %s service",
      (_label, status) => {
        const { getByRole, queryByRole } = renderWithContext({
          ...mockService,
          status,
        });
        expect(
          getByRole("button", { name: "Delete service" })
        ).toBeInTheDocument();
        expect(
          queryByRole("button", { name: "Stop service" })
        ).not.toBeInTheDocument();
      }
    );

    it("renders no Stop or Delete button when no service is selected", () => {
      const { queryByRole } = renderWithContext(null);
      expect(
        queryByRole("button", { name: "Stop service" })
      ).not.toBeInTheDocument();
      expect(
        queryByRole("button", { name: "Delete service" })
      ).not.toBeInTheDocument();
    });
  });

  describe("Button interactions", () => {
    it("calls stopService when Stop button is clicked", async () => {
      const user = userEvent.setup();
      const { getByRole } = renderWithContext(mockService);
      await user.click(getByRole("button", { name: "Stop service" }));
      expect(stopService).toHaveBeenCalledWith("service-123");
      await waitFor(() => expect(mockMutate).toHaveBeenCalled());
    });

    it("calls deleteService when Delete button is clicked", async () => {
      const user = userEvent.setup();
      const { getByRole } = renderWithContext({
        ...mockService,
        status: ServiceStatus.STOPPED,
      });
      await user.click(getByRole("button", { name: "Delete service" }));
      expect(deleteService).toHaveBeenCalledWith("service-123");
      await waitFor(() => expect(mockMutate).toHaveBeenCalled());
    });

    it("handles stopService error gracefully", async () => {
      const user = userEvent.setup();
      const consoleErrorSpy = vi
        .spyOn(console, "error")
        .mockImplementation(() => {});
      stopService.mockRejectedValue(new Error("Network error"));
      const { getByRole } = renderWithContext(mockService);
      await user.click(getByRole("button", { name: "Stop service" }));
      await waitFor(() => {
        expect(consoleErrorSpy).toHaveBeenCalledWith(
          "An error occurred while stopping a service:",
          expect.any(Error)
        );
      });
      consoleErrorSpy.mockRestore();
    });

    it("handles deleteService error gracefully", async () => {
      const user = userEvent.setup();
      const consoleErrorSpy = vi
        .spyOn(console, "error")
        .mockImplementation(() => {});
      deleteService.mockRejectedValue(new Error("Network error"));
      const { getByRole } = renderWithContext({
        ...mockService,
        status: ServiceStatus.STOPPED,
      });
      await user.click(getByRole("button", { name: "Delete service" }));
      await waitFor(() => {
        expect(consoleErrorSpy).toHaveBeenCalledWith(
          "An error occurred while deleting a service:",
          expect.any(Error)
        );
      });
      consoleErrorSpy.mockRestore();
    });
  });
});
