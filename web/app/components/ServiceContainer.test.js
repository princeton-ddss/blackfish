import {render} from "@testing-library/react";
import "@testing-library/jest-dom";
import ServiceContainer from "@/app/components/ServiceContainer";

jest.mock("@/app/components/ServiceContainer", () => {
  // eslint-disable-next-line react/prop-types
  return function MockServiceContainer({ children }) {
    return <div data-testid="service-container">{children}</div>;
  };
});

jest.mock("@/app/components/ServiceSummary", () => {
  return function MockServiceSummary() {
    return <div data-testid="service-launcher">Service Summary</div>;
  };
});

test("ServiceContainer", () => {
  const {baseElement} = render(
    <ServiceContainer
      profile="default"
      task="text-generation"
    >
      <div>
        <h1>Hello, world!</h1>
        <p>Conubia nam a elit ullamcorper phasellus habitasse ligula nullam auctor sociosqu dis lacus, varius parturient ad vitae sollicitudin ridiculus mauris tempor dictum molestie turpis.</p>
      </div>
    </ServiceContainer>
  );
  expect(baseElement).toMatchSnapshot();
});
