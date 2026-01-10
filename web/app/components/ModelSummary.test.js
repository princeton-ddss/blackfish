import {render} from "@testing-library/react";
import "@testing-library/jest-dom";
import ModelSummary from "@/app/components/ModelSummary";

describe("ModelSummary", () => {
  test("Link and description", () => {
    const component = render(
      <ModelSummary model={{
        description: "Mauris a quisque praesent aptent risus condimentum feugiat placerat, aenean nec elementum taciti tortor himenaeos. Scelerisque leo ipsum consequat posuere sagittis lacus volutpat taciti, sodales tristique sed laoreet placerat rhoncus nisi, platea hendrerit aliquet fermentum curae blandit mattis. Lorem donec amet luctus rhoncus praesent natoque hac torquent elit phasellus felis, consequat laoreet senectus platea condimentum feugiat tempor fames scelerisque justo.",
        link: "https://example.com"
      }} setModalOpen={(e) => e} />
    );
    expect(component.baseElement).toMatchSnapshot();
  });

  test("Link only", () => {
    const component = render(
      <ModelSummary model={{
        link: "https://example.com"
      }} setModalOpen={(e) => e} />
    );
    expect(component.baseElement).toMatchSnapshot();
  });

  test("Description only", () => {
    const component = render(
      <ModelSummary model={{
        description: "Nostra ullamcorper phasellus fames velit taciti laoreet"
      }} setModalOpen={(e) => e} />
    );
    expect(component.baseElement).toMatchSnapshot();
  });
});
