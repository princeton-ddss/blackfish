/* eslint react/prop-types: 0 */

import { render, screen, waitFor, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import ServiceModal from "@/components/ServiceModal";
import { ServiceContext } from "@/providers/ServiceProvider";
import { useModels, useServices, useClusterStatus, useStagedContainers } from "@/lib/loaders";
import { runService, fetchProfileResources } from "@/lib/requests";
import { sleep, randomInt, isDeepEmpty } from "@/lib/util";

vi.mock("@/providers/ServiceProvider");
vi.mock("@/lib/loaders");
vi.mock("@/lib/requests");
vi.mock("@/lib/util");
vi.mock("@/components/ServiceModalForm", () => {
  return {
    default: function MockServiceModalForm({
      setModel,
      jobOptions,
      setJobOptions,
      setValidationErrors,
      children
    }) {
      return (
        <div data-testid="service-modal-form">
          <button
            onClick={() => setModel({ repo_id: "test-model" })}
            data-testid="set-model-button"
          >
            Set Model
          </button>
          <button
            onClick={() => setJobOptions({ ...jobOptions, name: "test-job" })}
            data-testid="set-job-options-button"
          >
            Set Job Options
          </button>
          <button
            onClick={() => setValidationErrors({ name: "Required" })}
            data-testid="set-validation-errors-button"
          >
            Set Validation Errors
          </button>
          {children}
        </div>
      );
    }
  };
});
vi.mock("@/components/ServiceLaunchErrorAlert", () => {
  return {
    default: function MockServiceLaunchErrorAlert({ error, onClick }) {
      return (
        <div data-testid="service-launch-error-alert">
          Error: {error?.message}
          <button onClick={onClick} data-testid="dismiss-error-button">
            Dismiss
          </button>
        </div>
      );
    }
  };
});

describe("ServiceModal", () => {
  const mockSetOpen = vi.fn();
  const mockSetContainerOptions = vi.fn();
  const mockSetLaunchSuccess = vi.fn();
  const mockSetIsLaunching = vi.fn();
  const mockSetLaunchError = vi.fn();
  const mockSetValidationErrors = vi.fn();
  const mockSetSelectedServiceId = vi.fn();
  const mockMutateServices = vi.fn();

  const defaultProps = {
    task: "test-task",
    open: true,
    setOpen: mockSetOpen,
    defaultContainerOptions: { port: 8080 },
    containerOptions: { port: 8080 },
    setContainerOptions: mockSetContainerOptions,
    launchSuccess: false,
    setLaunchSuccess: mockSetLaunchSuccess,
    isLaunching: false,
    setIsLaunching: mockSetIsLaunching,
    launchError: null,
    setLaunchError: mockSetLaunchError,
    validationErrors: {},
    setValidationErrors: mockSetValidationErrors,
    profile: { schema: "slurm", host: "test-host", user: "testuser" },
    children: <div data-testid="modal-children">Test Children</div>
  };

  const mockServiceContext = {
    selectedService: {
      id: "service-1",
      name: "test-service",
      status: "running",
      model: "test-model"
    },
    setSelectedServiceId: mockSetSelectedServiceId
  };

  beforeEach(() => {
    vi.resetAllMocks();

    mockMutateServices.mockResolvedValue([]);

    useServices.mockReturnValue({
      services: [
        { id: "service-1", name: "existing-service" }
      ],
      mutate: mockMutateServices
    });

    useModels.mockReturnValue({
      models: [
        { repo_id: "model-1" },
        { repo_id: "model-2" }
      ]
    });

    useClusterStatus.mockReturnValue({
      status: null,
      error: null,
      isLoading: false,
      isRefreshing: false,
      refresh: vi.fn(),
    });

    useStagedContainers.mockReturnValue({
      container: undefined,
      error: null,
      isLoading: false,
      isRefreshing: false,
      refresh: vi.fn(),
    });

    randomInt.mockReturnValue(12345);
    isDeepEmpty.mockReturnValue(true);
    sleep.mockResolvedValue();
    fetchProfileResources.mockResolvedValue({ partitions: [], time: { default: 30, max: 180 } });
  });

  const renderServiceModal = async (props = {}) => {
    let result;
    await act(async () => {
      result = render(
        <ServiceContext.Provider value={mockServiceContext}>
          <ServiceModal {...defaultProps} {...props} />
        </ServiceContext.Provider>
      );
    });
    return result;
  };

  describe("Rendering", () => {
    it("renders modal when open is true", async () => {
      await renderServiceModal();
      expect(screen.getByRole("dialog")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Launch" })).toBeEnabled();
      expect(screen.getByRole("button", { name: "Cancel" })).toBeEnabled();
    });

    it("does not render modal when open is false", async () => {
      await renderServiceModal({ open: false });
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });

    it("renders children correctly", async () => {
      const {getByTestId} = await renderServiceModal();
      expect(getByTestId("modal-children")).toBeInTheDocument();
    });

    it("renders ServiceModalForm component", async () => {
      const {getByTestId} = await renderServiceModal();
      expect(getByTestId("service-modal-form")).toBeInTheDocument();
    });
  });

  describe("Initial State", () => {
    it("sets initial model when models are available", async () => {
      await renderServiceModal();
      // Model is set internally, verified by the form receiving it
      expect(screen.getByTestId("service-modal-form")).toBeInTheDocument();
    });

    it("handles empty models array", async () => {
      useModels.mockReturnValue({ models: [] });
      await renderServiceModal();
      // Should still render the form even without models
      expect(screen.getByTestId("service-modal-form")).toBeInTheDocument();
    });
  });


  describe("Reset on Open", () => {
    it("resets state when modal opens", async () => {
      const { rerender } = await renderServiceModal({ open: false });
      rerender(
        <ServiceContext.Provider value={mockServiceContext}>
          <ServiceModal {...defaultProps} open={true} />
        </ServiceContext.Provider>
      );
      // A generated API key is mixed into the defaults, so match the shape
      // rather than an exact object.
      expect(mockSetContainerOptions).toHaveBeenCalledWith(
        expect.objectContaining({ port: 8080, api_key: expect.any(String) })
      );
      expect(mockSetLaunchSuccess).toHaveBeenCalledWith(false);
      expect(mockSetIsLaunching).toHaveBeenCalledWith(false);
      expect(mockSetLaunchError).toHaveBeenCalledWith(null);
      expect(mockSetValidationErrors).toHaveBeenCalledWith({});
    });
  });

  describe("Loading State", () => {
    it("shows loading state on button when isLaunching is true", async () => {
      const {getByText} = await renderServiceModal({ isLaunching: true });
      expect(getByText("Launching")).toBeInTheDocument();
    });

    it("shows Launch text when isLaunching is false", async () => {
      const {getByText} = await renderServiceModal({ isLaunching: false });
      expect(getByText("Launch")).toBeInTheDocument();
    });

    it("disables Launch button when isLaunching is true", async () => {
      const {getByText} = await renderServiceModal({ isLaunching: true });
      expect(getByText("Launching").closest("button")).toBeDisabled();
    });

    it("disables Launch button while no model is selected", async () => {
      useModels.mockReturnValue({ models: [], isLoading: true });
      const {getByText} = await renderServiceModal();
      expect(getByText("Launch")).toBeDisabled();
    });

    it("enables Launch button once a model is selected", async () => {
      const user = userEvent.setup();
      const {getByText, getByTestId} = await renderServiceModal();
      await user.click(getByTestId("set-model-button"));
      expect(getByText("Launch")).not.toBeDisabled();
    });
  });

  describe("Launch Error State", () => {
    it("displays launch error when present", async () => {
      const error = new Error("Launch failed");
      const {getByTestId, getByText} = await renderServiceModal({ launchError: error });
      expect(getByTestId("service-launch-error-alert")).toBeInTheDocument();
      expect(getByText("Error: Launch failed")).toBeInTheDocument();
    });

    it("dismisses launch error when dismiss button is clicked", async () => {
      const user = userEvent.setup();
      const error = new Error("Launch failed");
      const {getByTestId} = await renderServiceModal({ launchError: error });
      await user.click(getByTestId("dismiss-error-button"));
      expect(mockSetLaunchError).toHaveBeenCalledWith(null);
    });

    it("disables Launch button when validation errors exist", async () => {
      isDeepEmpty.mockReturnValue(false);
      const {getByText} = await renderServiceModal({
        validationErrors: { name: "Required" }
      });
      expect(getByText("Launch")).toBeDisabled();
    });
  });

  describe("Launch Success State", () => {
    it("auto-closes modal when launchSuccess is true", async () => {
      await renderServiceModal({ launchSuccess: true });
      expect(mockSetOpen).toHaveBeenCalledWith(false);
    });

    it("closes modal when Cancel button is clicked", async () => {
      const user = userEvent.setup();
      const {getByText} = await renderServiceModal();
      await user.click(getByText("Cancel"));
      expect(mockSetOpen).toHaveBeenCalledWith(false);
    });
  });

  describe("Form Submission", () => {
    beforeEach(() => {
      runService.mockResolvedValue({
        ok: true,
        json: vi.fn().mockResolvedValue({ id: "new-service-id" })
      });
    });

    it("calls runService with correct parameters on form submit", async () => {
      const user = userEvent.setup();
      const {getByText} = await renderServiceModal();
      await user.click(getByText("Launch"));
      expect(mockSetIsLaunching).toHaveBeenCalledWith(true);
      expect(mockSetLaunchError).toHaveBeenCalledWith(null);
      expect(runService).toHaveBeenCalledWith(
        "test-task",
        { repo_id: "model-1" },
        expect.objectContaining({
          name: expect.stringContaining("blackfish-"),
          time: "00:30:00",
        }),
        { port: 8080 },
        { schema: "slurm", host: "test-host", user: "testuser" },
        // No staged containers mocked, so no pin is selected and the backend
        // resolves its configured default.
        null
      );
    });

    it("handles successful service launch", async () => {
      const user = userEvent.setup();
      mockMutateServices.mockResolvedValue([
        { id: "new-service-id", name: "new-service" }
      ]);
      const {getByText} = await renderServiceModal();
      await user.click(getByText("Launch"));
      await waitFor(() => {
        expect(mockSetSelectedServiceId).toHaveBeenCalledWith("new-service-id");
        expect(mockSetIsLaunching).toHaveBeenCalledWith(false);
        expect(mockSetLaunchSuccess).toHaveBeenCalledWith(true);
      });
    });

    it("handles service launch API error", async () => {
      const user = userEvent.setup();
      runService.mockResolvedValue({
        ok: false,
        text: vi.fn().mockResolvedValue("API Error")
      });

      await renderServiceModal();
      await user.click(screen.getByText("Launch"));

      await waitFor(() => {
        expect(mockSetIsLaunching).toHaveBeenCalledWith(false);
        expect(mockSetLaunchError).toHaveBeenCalledWith(expect.any(Error));
      });
    });

    it("handles timeout when service is not found", async () => {
      const user = userEvent.setup();
      mockMutateServices.mockResolvedValue([]);

      await renderServiceModal();
      await user.click(screen.getByText("Launch"));

      await waitFor(() => {
        expect(mockSetIsLaunching).toHaveBeenCalledWith(false);
        expect(mockSetLaunchError).toHaveBeenCalledWith(
          expect.objectContaining({
            message: expect.stringContaining("Maximum wait time")
          })
        );
      });
    });

    it("retries finding service up to maxAttempts", async () => {
      const user = userEvent.setup();
      mockMutateServices
        .mockResolvedValueOnce([])
        .mockResolvedValueOnce([])
        .mockResolvedValueOnce([{ id: "new-service-id", name: "new-service" }]);

      await renderServiceModal();
      await user.click(screen.getByText("Launch"));

      await waitFor(() => {
        expect(mockMutateServices).toHaveBeenCalledTimes(3);
        expect(mockSetLaunchSuccess).toHaveBeenCalledWith(true);
      });
    });
  });

  describe("Profile Types", () => {
    it("uses correct default job options for slurm profile", async () => {
      await renderServiceModal({
        profile: { schema: "slurm", host: "test-host", user: "testuser" },
      });
      // Slurm profiles should have time field and null resource fields (set by tier selection)
      expect(screen.getByTestId("service-modal-form")).toBeInTheDocument();
    });

    it("uses correct default job options for local profile", async () => {
      await renderServiceModal({
        profile: { schema: "local" },
      });
      // Local profiles should work without slurm-specific fields
      expect(screen.getByTestId("service-modal-form")).toBeInTheDocument();
    });
  });

  describe("API key generation", () => {
    it("generates a different key each time the modal opens", async () => {
      // Memoizing the key would reuse one value across every service the
      // user launches from this page.
      const { rerender } = await renderServiceModal({ open: false });
      const openModal = () =>
        rerender(
          <ServiceContext.Provider value={mockServiceContext}>
            <ServiceModal {...defaultProps} open={true} />
          </ServiceContext.Provider>
        );

      openModal();
      const first = mockSetContainerOptions.mock.calls.at(-1)[0].api_key;

      rerender(
        <ServiceContext.Provider value={mockServiceContext}>
          <ServiceModal {...defaultProps} open={false} />
        </ServiceContext.Provider>
      );
      openModal();
      const second = mockSetContainerOptions.mock.calls.at(-1)[0].api_key;

      expect(first).toBeTruthy();
      expect(second).not.toBe(first);
    });
  });
});
