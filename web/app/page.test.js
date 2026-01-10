import {render} from '@testing-library/react';
import Home from "./page";

test('Page', () => {
  const component = render(<Home />);
  expect(component.baseElement).toMatchSnapshot();
});
