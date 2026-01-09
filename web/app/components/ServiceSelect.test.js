import { render } from "@testing-library/react";
import "@testing-library/jest-dom";
import ServiceSelect from "./ServiceSelect";
import { ServiceContext } from "@/app/providers/ServiceProvider";
import { useServices } from "@/app/lib/loaders";
import { ServiceStatus } from "@/app/lib/util";

// Mock the useServices hook.
jest.mock("@/app/lib/loaders", () => ({
  useServices: jest.fn(),
}));

// Mock the Headless UI components.
jest.mock("@headlessui/react", () => ({
  // eslint-disable-next-line react/prop-types
  Field: function Field({ children }) {
    return <div data-testid="field">{children}</div>;
  },
  // eslint-disable-next-line react/prop-types
  Label: function Label({ children, className }) {
    return <label className={className}>{children}</label>;
  },
  // eslint-disable-next-line react/prop-types
  Listbox: function Listbox({ children, value, onChange }) {
    return (
      // eslint-disable-next-line react/prop-types
      <div data-testid="listbox" data-value={value?.id} onClick={() => onChange && onChange("test-service-id")}>
        {typeof children === "function" ? children({ open: false }) : children}
      </div>
    );
  },
  // eslint-disable-next-line react/prop-types
  ListboxButton: function ListboxButton({ children, className, disabled }) {
    return (
      <button className={className} disabled={disabled} data-testid="listbox-button">
        {children}
      </button>
    );
  },
  // eslint-disable-next-line react/prop-types
  ListboxOptions: function ({ children, className }) {
    return (
      <div className={className} data-testid="listbox-options">{children}</div>
    );
  },
  // eslint-disable-next-line react/prop-types
  ListboxOption: function ListboxOption({ children, value, className }) {
    return (
      <div
        data-testid="listbox-option"
        // eslint-disable-next-line react/prop-types
        data-value={value?.id}
        className={typeof className === "function" ? className({ focus: false }) : className}
      >
        {typeof children === "function" ? children({ selected: false, focus: false }) : children}
      </div>
    );
  },
  // eslint-disable-next-line react/prop-types
  Transition: function Transition({ children, show }) {
    return show ? <div data-testid="transition">{children}</div> : null;
  },
}));

// Mock the Heroicons.
jest.mock("@heroicons/react/20/solid", () => ({
  CheckIcon: function CheckIcon(props) {
    return <svg data-testid="check-icon" {...props} />;
  },
  ChevronUpDownIcon: function ChevronUpDownIcon(props) {
    return <svg data-testid="chevron-up-down-icon" {...props} />;
  },
  ExclamationTriangleIcon: function ExclamationTriangleIcon(props) {
    return <svg data-testid="exclamation-triangle-icon" {...props} />;
  },
}));
jest.mock("@heroicons/react/24/solid", () => ({
  ExclamationCircleIcon: function ExclamationCircleIcon(props) {
    return <svg data-testid="exclamation-circle-icon" {...props} />;
  },
}));

// Helper function to create mock context.
const createMockContext = (selectedService = null, setSelectedServiceId = jest.fn()) => ({
  selectedService,
  setSelectedServiceId,
});

// Helper function to render component with context.
const renderWithContext = (component, contextValue) => {
  return render(
    <ServiceContext.Provider value={contextValue}>
      {component}
    </ServiceContext.Provider>
  );
};

// Mock data.
const mockProfile = { id: 1, name: "test-profile" };
const mockServices = [
  {
    id: "service-healthy",
    name: "Healthy Service",
    status: ServiceStatus.HEALTHY,
  },
  {
    id: "service-starting",
    name: "Starting Service",
    status: ServiceStatus.STARTING,
  },
  {
    id: "service-failed",
    name: "Failed Service",
    status: ServiceStatus.FAILED,
  },
  {
    id: "service-timeout",
    name: "Timed out Service",
    status: ServiceStatus.TIMEOUT,
  },
  {
    id: "service-submitted",
    name: "Submitted Service",
    status: ServiceStatus.SUBMITTED,
  },
  {
    id: "service-pending",
    name: "Pending Service",
    status: ServiceStatus.PENDING,
  },
];

describe("ServiceSelect", () => {
  const mockSetSelectedServiceId = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test("Error State", () => {
    useServices.mockReturnValue({
      services: [],
      error: new Error("Failed to fetch"),
      isLoading: false,
    });
    const contextValue = createMockContext();
    const {baseElement} = renderWithContext(
      <ServiceSelect profile={mockProfile} task="test-task" />,
      contextValue
    );
    expect(baseElement).toMatchSnapshot();
  });

  test("Loading State", () => {
    useServices.mockReturnValue({
      services: [],
      error: null,
      isLoading: true,
    });
    const contextValue = createMockContext();
    const {baseElement} = renderWithContext(
      <ServiceSelect profile={mockProfile} task="test-task" />,
      contextValue
    );
    expect(baseElement).toMatchSnapshot();
  });

  test("No Services Available State", () => {
    useServices.mockReturnValue({
      services: [],
      error: null,
      isLoading: false,
    });
    const contextValue = createMockContext();
    const {baseElement} = renderWithContext(
      <ServiceSelect profile={mockProfile} task="test-task" />,
      contextValue
    );
    expect(baseElement).toMatchSnapshot();
  });

  test("Healthy service selected", () => {
    useServices.mockReturnValue({
      services: mockServices,
      error: null,
      isLoading: false,
    });
    const contextValue = createMockContext(mockServices[0], mockSetSelectedServiceId);
    const {baseElement} = renderWithContext(
      <ServiceSelect profile={mockProfile} task="test-task" />,
      contextValue
    );
    expect(baseElement).toMatchSnapshot();
  });

  test("Starting service selected", () => {
    useServices.mockReturnValue({
      services: mockServices,
      error: null,
      isLoading: false,
    });
    const contextValue = createMockContext(mockServices[1], mockSetSelectedServiceId);
    const {baseElement} = renderWithContext(
      <ServiceSelect profile={mockProfile} task="test-task" />,
      contextValue
    );
    expect(baseElement).toMatchSnapshot();
  });

  test("Failed service selected", () => {
    useServices.mockReturnValue({
      services: mockServices,
      error: null,
      isLoading: false,
    });
    const contextValue = createMockContext(mockServices[2], mockSetSelectedServiceId);
    const {baseElement} = renderWithContext(
      <ServiceSelect profile={mockProfile} task="test-task" />,
      contextValue
    );
    expect(baseElement).toMatchSnapshot();
  });

  test("Timed-out service selected", () => {
    useServices.mockReturnValue({
      services: mockServices,
      error: null,
      isLoading: false,
    });
    const contextValue = createMockContext(mockServices[3], mockSetSelectedServiceId);
    const {baseElement} = renderWithContext(
      <ServiceSelect profile={mockProfile} task="test-task" />,
      contextValue
    );
    expect(baseElement).toMatchSnapshot();
  });

  test("Submitted service selected", () => {
    useServices.mockReturnValue({
      services: mockServices,
      error: null,
      isLoading: false,
    });
    const contextValue = createMockContext(mockServices[4], mockSetSelectedServiceId);
    const {baseElement} = renderWithContext(
      <ServiceSelect profile={mockProfile} task="test-task" />,
      contextValue
    );
    expect(baseElement).toMatchSnapshot();
  });

  test("Pending service selected", () => {
    useServices.mockReturnValue({
      services: mockServices,
      error: null,
      isLoading: false,
    });
    const contextValue = createMockContext(mockServices[5], mockSetSelectedServiceId);
    const {baseElement} = renderWithContext(
      <ServiceSelect profile={mockProfile} task="test-task" />,
      contextValue
    );
    expect(baseElement).toMatchSnapshot();
  });

  test("Service Selection without Selected Service but with Profile", () => {
    useServices.mockReturnValue({
      services: mockServices,
      error: null,
      isLoading: false,
    });
    const contextValue = createMockContext(null, mockSetSelectedServiceId);
    const {baseElement} = renderWithContext(
      <ServiceSelect profile={mockProfile} task="test-task" />,
      contextValue
    );
    expect(baseElement).toMatchSnapshot();
  });

  test("Disabled State when No Profile Selected", () => {
    useServices.mockReturnValue({
      services: [],
      error: null,
      isLoading: false,
    });
    const contextValue = createMockContext(null, mockSetSelectedServiceId);
    const {baseElement} = renderWithContext(
      <ServiceSelect profile={null} task="test-task" />,
      contextValue
    );
    expect(baseElement).toMatchSnapshot();
  });

  describe("Empty data", () => {
    it("gracefully handles an undefined profile", () => {
      useServices.mockReturnValue({
        services: [],
        error: null,
        isLoading: false,
      });
      const contextValue = createMockContext(null, mockSetSelectedServiceId);
      expect(() => {
        renderWithContext(
          <ServiceSelect profile={undefined} task="test-task" />,
          contextValue
        );
      }).not.toThrow();
    });

    it("gracefully handles an undefined task", () => {
      useServices.mockReturnValue({
        services: [],
        error: null,
        isLoading: false,
      });

      const contextValue = createMockContext(null, mockSetSelectedServiceId);

      expect(() => {
        renderWithContext(
          <ServiceSelect profile={mockProfile} task={undefined} />,
          contextValue
        );
      }).not.toThrow();
    });
  });
});
