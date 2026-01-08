/* eslint react/prop-types: 0 */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import "@testing-library/jest-dom";
import { describe, expect, it, jest } from "@jest/globals";
import ServiceModal from "@/app/components/ServiceModal";
import { ServiceContext } from "@/app/providers/ServiceProvider";
import { useModels, useServices } from "@/app/lib/loaders";
import { runService } from "@/app/lib/requests";
import { sleep, randomInt, isDeepEmpty } from "@/app/lib/util";

jest.mock("@/app/providers/ServiceProvider");
jest.mock("@/app/lib/loaders");
jest.mock("@/app/lib/requests");
jest.mock("@/app/lib/util");
jest.mock("@/app/components/ServiceSummary", () => {
  return function MockServiceSummary({ service }) {
    return (
      <div data-testid="service-summary">
        Service: {service?.name || "Unknown"}
        Status: {service?.status || "None"}
        Model: {service?.model || "None"}
      </div>
    );
  };
});
jest.mock("@/app/components/ServiceModalForm", () => {
  return function MockServiceModalForm({
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
  };
});
jest.mock("@/app/components/ServiceLaunchErrorAlert", () => {
  return function MockServiceLaunchErrorAlert({ error, onClick }) {
    return (
      <div data-testid="service-launch-error-alert">
        Error: {error?.message}
        <button onClick={onClick} data-testid="dismiss-error-button">
          Dismiss
        </button>
      </div>
    );
  };
});

describe("ServiceModal", () => {
  const mockSetOpen = jest.fn();
  const mockSetContainerOptions = jest.fn();
  const mockSetLaunchSuccess = jest.fn();
  const mockSetIsLaunching = jest.fn();
  const mockSetLaunchError = jest.fn();
  const mockSetValidationErrors = jest.fn();
  const mockSetSelectedServiceId = jest.fn();
  const mockMutateServices = jest.fn();

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
    profile: { type: "remote", host: "test-host" },
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
    jest.clearAllMocks();

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

    randomInt.mockReturnValue(12345);
    isDeepEmpty.mockReturnValue(true);
    sleep.mockResolvedValue();
  });

  const renderServiceModal = (props = {}) => {
    return render(
      <ServiceContext.Provider value={mockServiceContext}>
        <ServiceModal {...defaultProps} {...props} />
      </ServiceContext.Provider>
    );
  };

  describe("Rendering", () => {
    it("renders modal when open is true", () => {
      const { baseElement } = renderServiceModal();
      expect(baseElement).toMatchSnapshot();
    });

    it("does not render modal when open is false", () => {
      const { baseElement } = renderServiceModal({ open: false });
      expect(baseElement).toMatchSnapshot();
    });

    it("renders children correctly", () => {
      const {getByTestId} = renderServiceModal();
      expect(getByTestId("modal-children")).toBeInTheDocument();
    });

    it("renders ServiceSummary component", () => {
      const {getByTestId} = renderServiceModal();
      expect(getByTestId("service-summary")).toBeInTheDocument();
    });

    it("renders ServiceModalForm component", () => {
      const {getByTestId} = renderServiceModal();
      expect(getByTestId("service-modal-form")).toBeInTheDocument();
    });
  });

  describe("Initial State", () => {
    it("sets initial model when models are available", () => {
      const {getByTestId} = renderServiceModal();
      expect(getByTestId("service-summary")).toHaveTextContent("Model: model-1");
    });

    it("handles empty models array", () => {
      useModels.mockReturnValue({ models: [] });
      const {getByTestId} = renderServiceModal();
      expect(getByTestId("service-summary")).toHaveTextContent("Model: None");
    });
  });

  describe("Reset on Open", () => {
    it("resets state when modal opens", () => {
      const { rerender } = renderServiceModal({ open: false });
      rerender(
        <ServiceContext.Provider value={mockServiceContext}>
          <ServiceModal {...defaultProps} open={true} />
        </ServiceContext.Provider>
      );
      expect(mockSetContainerOptions).toHaveBeenCalledWith({ port: 8080 });
      expect(mockSetLaunchSuccess).toHaveBeenCalledWith(false);
      expect(mockSetIsLaunching).toHaveBeenCalledWith(false);
      expect(mockSetLaunchError).toHaveBeenCalledWith(null);
      expect(mockSetValidationErrors).toHaveBeenCalledWith({});
    });
  });

  describe("Loading State", () => {
    it("shows loading spinner when isLaunching is true", async () => {
      const {getByLabelText} = renderServiceModal({ isLaunching: true });
      await waitFor(async () => {
        expect(getByLabelText("Services are loading")).toBeInTheDocument();
      });
    });

    it("hides loading spinner when isLaunching is false", () => {
      const {container} = renderServiceModal({ isLaunching: false });
      expect(container.querySelector('.loading')).not.toBeInTheDocument();
    });

    it("disables Launch button when isLaunching is true", () => {
      const {getByText} = renderServiceModal({ isLaunching: true });
      expect(getByText("Launch")).toBeDisabled();
    });

    it("hides ServiceSummary when isLaunching is true", () => {
      const {queryByTestId} = renderServiceModal({ isLaunching: true });
      expect(queryByTestId("service-summary")).not.toBeInTheDocument();
    });
  });

  describe("Launch Error State", () => {
    it("displays launch error when present", () => {
      const error = new Error("Launch failed");
      const {getByTestId, getByText} = renderServiceModal({ launchError: error });
      expect(getByTestId("service-launch-error-alert")).toBeInTheDocument();
      expect(getByText("Error: Launch failed")).toBeInTheDocument();
    });

    it("dismisses launch error when dismiss button is clicked", async () => {
      const user = userEvent.setup();
      const error = new Error("Launch failed");
      const {getByTestId} = renderServiceModal({ launchError: error });
      await user.click(getByTestId("dismiss-error-button"));
      expect(mockSetLaunchError).toHaveBeenCalledWith(null);
    });

    it("disables Launch button when validation errors exist", () => {
      isDeepEmpty.mockReturnValue(false);
      const {getByText} = renderServiceModal({
        validationErrors: { name: "Required" }
      });
      expect(getByText("Launch")).toBeDisabled();
    });
  });

  describe("Launch Success State", () => {
    it("shows Close button when launchSuccess is true", () => {
      const {getByText, queryByText} = renderServiceModal({ launchSuccess: true });
      expect(getByText("Close")).toBeInTheDocument();
      expect(queryByText("Launch")).not.toBeInTheDocument();
      expect(queryByText("Cancel")).not.toBeInTheDocument();
    });

    it("shows selected service in summary when launch is successful", () => {
      const {getByTestId} = renderServiceModal({ launchSuccess: true });
      expect(getByTestId("service-summary")).toHaveTextContent("Service: test-service");
      expect(getByTestId("service-summary")).toHaveTextContent("Status: running");
    });

    it("closes modal when Close button is clicked", async () => {
      const user = userEvent.setup();
      const {getByText} = renderServiceModal({ launchSuccess: true });
      await user.click(getByText("Close"));
      expect(mockSetOpen).toHaveBeenCalledWith(false);
    });

    it("closes modal when Cancel button is clicked", async () => {
      const user = userEvent.setup();
      const {getByText} = renderServiceModal();
      await user.click(getByText("Cancel"));
      expect(mockSetOpen).toHaveBeenCalledWith(false);
    });
  });

  describe("Form Submission", () => {
    beforeEach(() => {
      runService.mockResolvedValue({
        ok: true,
        json: jest.fn().mockResolvedValue({ id: "new-service-id" })
      });
    });

    it("calls runService with correct parameters on form submit", async () => {
      const user = userEvent.setup();
      const {getByText} = renderServiceModal();
      await user.click(getByText("Launch"));
      expect(mockSetIsLaunching).toHaveBeenCalledWith(true);
      expect(mockSetLaunchError).toHaveBeenCalledWith(null);
      expect(runService).toHaveBeenCalledWith(
        "test-task",
        { repo_id: "model-1" },
        expect.objectContaining({
          name: expect.stringContaining("blackfish-"),
          time: "00:30:00",
          ntasks_per_node: 8,
          mem: 16,
          gres: 1,
          partition: null,
          constraint: null
        }),
        { port: 8080 },
        { type: "remote", host: "test-host" }
      );
    });

    it("handles successful service launch", async () => {
      const user = userEvent.setup();
      mockMutateServices.mockResolvedValue([
        { id: "new-service-id", name: "new-service" }
      ]);
      const {getByText} = renderServiceModal();
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
        text: jest.fn().mockResolvedValue("API Error")
      });

      renderServiceModal();
      await user.click(screen.getByText("Launch"));

      await waitFor(() => {
        expect(mockSetIsLaunching).toHaveBeenCalledWith(false);
        expect(mockSetLaunchError).toHaveBeenCalledWith(expect.any(Error));
      });
    });

    it("handles timeout when service is not found", async () => {
      const user = userEvent.setup();
      mockMutateServices.mockResolvedValue([]);

      renderServiceModal();
      await user.click(screen.getByText("Launch"));

      await waitFor(() => {
        expect(mockSetIsLaunching).toHaveBeenCalledWith(false);
        expect(mockSetLaunchError).toHaveBeenCalledWith(
          expect.objectContaining({
            message: expect.stringContaining("Maximum wait time")
          })
        );
      }, { timeout: 20000 });
    });

    it("retries finding service up to maxAttempts", async () => {
      const user = userEvent.setup();
      mockMutateServices
        .mockResolvedValueOnce([])
        .mockResolvedValueOnce([])
        .mockResolvedValueOnce([{ id: "new-service-id", name: "new-service" }]);

      renderServiceModal();
      await user.click(screen.getByText("Launch"));

      await waitFor(() => {
        expect(mockMutateServices).toHaveBeenCalledTimes(3);
        expect(mockSetLaunchSuccess).toHaveBeenCalledWith(true);
      });
    });
  });

  describe("Profile Types", () => {
    it("handles local profile type in service summary", () => {
      const {getByTestId} = renderServiceModal({
        profile: { type: "local" },
        launchSuccess: false
      });
      expect(getByTestId("service-summary")).toHaveTextContent("Service: blackfish-12345");
    });

    it("handles remote profile type in service summary", () => {
      const {getByTestId} = renderServiceModal({
        profile: { type: "remote", host: "remote-host" },
        launchSuccess: false
      });
      expect(getByTestId("service-summary")).toHaveTextContent("Service: blackfish-12345");
    });
  });
});
