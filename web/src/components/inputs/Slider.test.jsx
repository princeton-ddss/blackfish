import { render } from "@testing-library/react";
import { describe, test, expect } from "vitest";
import Slider from "@/components/inputs/Slider";

describe("Slider", () => {
  test("Standard", () => {
    const {baseElement} = render(
      <Slider
        name="Test slider"
        value={0}
        onSliderChange={(e) => e}
        onTextChange={(e) => e}
        onReset={(e) => e}
        min={0}
        max={10}
        step={0.01}
        tooltip="Ad leo bibendum nisi tempus purus vivamus senectus pellentesque est finibus fermentum a taciti, potenti tortor pharetra condimentum interdum ex dis nisl lectus lacus quam phasellus."
        disabled={false}
        optional={false}
        enabled={true}
        onOptionalToggle={(e) => e}
      />
    );
    expect(baseElement).toMatchSnapshot();
    // TODO The component's spinbutton inputs should be tested with
    // increment and decrements. However, this is blocked upstream by
    // this issue.
    // https://github.com/testing-library/user-event/issues/1066
  });

  test("Optional", () => {
    const {baseElement} = render(
      <Slider
        name="Test slider"
        value={0}
        onSliderChange={(e) => e}
        onTextChange={(e) => e}
        onReset={(e) => e}
        min={0}
        max={10}
        step={0.01}
        tooltip="Ad leo bibendum nisi tempus purus vivamus senectus pellentesque est finibus fermentum a taciti, potenti tortor pharetra condimentum interdum ex dis nisl lectus lacus quam phasellus."
        disabled={false}
        optional={true}
        enabled={true}
        onOptionalToggle={(e) => e}
      />
    );
    expect(baseElement).toMatchSnapshot();
  });

  test("Disabled", () => {
    const {baseElement} = render(
      <Slider
        name="Test slider"
        value={0}
        onSliderChange={(e) => e}
        onTextChange={(e) => e}
        onReset={(e) => e}
        min={0}
        max={10}
        step={0.01}
        tooltip="Ad leo bibendum nisi tempus purus vivamus senectus pellentesque est finibus fermentum a taciti, potenti tortor pharetra condimentum interdum ex dis nisl lectus lacus quam phasellus."
        disabled={true}
        optional={false}
        enabled={true}
        onOptionalToggle={(e) => e}
      />
    );
    expect(baseElement).toMatchSnapshot();
  });

  test("Optional", () => {
    const {baseElement} = render(
      <Slider
        name="Test slider"
        value={0}
        onSliderChange={(e) => e}
        onTextChange={(e) => e}
        onReset={(e) => e}
        min={0}
        max={10}
        step={0.01}
        tooltip="Ad leo bibendum nisi tempus purus vivamus senectus pellentesque est finibus fermentum a taciti, potenti tortor pharetra condimentum interdum ex dis nisl lectus lacus quam phasellus."
        disabled={false}
        optional={true}
        enabled={true}
        onOptionalToggle={(e) => e}
      />
    );
    expect(baseElement).toMatchSnapshot();
  });

  test("Not enabled", () => {
    const {baseElement} = render(
      <Slider
        name="Test slider"
        value={0}
        onSliderChange={(e) => e}
        onTextChange={(e) => e}
        onReset={(e) => e}
        min={0}
        max={10}
        step={0.01}
        tooltip="Ad leo bibendum nisi tempus purus vivamus senectus pellentesque est finibus fermentum a taciti, potenti tortor pharetra condimentum interdum ex dis nisl lectus lacus quam phasellus."
        disabled={false}
        optional={false}
        enabled={false}
        onOptionalToggle={(e) => e}
      />
    );
    expect(baseElement).toMatchSnapshot();
  });

  test("Disabled, optional, and not enabled", () => {
    const {baseElement} = render(
      <Slider
        name="Test slider"
        value={0}
        onSliderChange={(e) => e}
        onTextChange={(e) => e}
        onReset={(e) => e}
        min={0}
        max={10}
        step={0.01}
        tooltip="Ad leo bibendum nisi tempus purus vivamus senectus pellentesque est finibus fermentum a taciti, potenti tortor pharetra condimentum interdum ex dis nisl lectus lacus quam phasellus."
        disabled={true}
        optional={true}
        enabled={false}
        onOptionalToggle={(e) => e}
      />
    );
    expect(baseElement).toMatchSnapshot();
  });
});
