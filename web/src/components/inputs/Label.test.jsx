import { render } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import Label from "@/components/inputs/Label";

describe("Label", () => {
  it("renders correctly when enabled", () => {
    const {baseElement} = render(
      <Label
        label="Hello, world!"
        htmlFor="hello-world"
        description="Non arcu tortor hac lorem mauris ultricies."
      />
    );
    expect(baseElement).toMatchSnapshot();
  });

  it("uses label for htmlFor if missing", () => {
    const {baseElement} = render(
      <Label
        label="Hello, world!"
        description="Non arcu tortor hac lorem mauris ultricies."
      />
    );
    expect(baseElement).toMatchSnapshot();
  });

  it("renders correctly when disabled", () => {
    const {baseElement} = render(
      <Label
        label="Hello, world!"
        htmlFor="hello-world"
        description="Non arcu tortor hac lorem mauris ultricies."
        disabled={true}
      />
    );
    expect(baseElement).toMatchSnapshot();
  });
});
