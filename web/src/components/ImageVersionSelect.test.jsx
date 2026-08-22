import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import ImageVersionSelect from "@/components/ImageVersionSelect";

const CONTAINER = {
  service: "text_generation",
  repo: "vllm/vllm-openai",
  tags: ["v0.8.4", "v0.8.5", "v0.10.2", "v0.20.0"],
  default: "v0.20.0",
  default_staged: true,
};

function renderSelect(props = {}) {
  const setImageRef = vi.fn();
  const result = render(
    <ImageVersionSelect
      container={CONTAINER}
      imageRef={null}
      setImageRef={setImageRef}
      disabled={false}
      {...props}
    />
  );
  return { ...result, setImageRef };
}

describe("ImageVersionSelect", () => {
  it("pre-selects the configured default, not the newest staged tag", () => {
    // v0.20.0 happens to be newest here, so pick a container where the
    // default is deliberately *not* the last tag to make the test meaningful.
    const container = { ...CONTAINER, default: "v0.8.5" };
    renderSelect({ container });
    expect(screen.getByText("v0.8.5")).toBeInTheDocument();
  });

  it("lifts the full repo:tag, since a pin may move repos not just tags", () => {
    const { setImageRef } = renderSelect();
    expect(setImageRef).toHaveBeenCalledWith("vllm/vllm-openai:v0.20.0");
  });

  it("falls back to the first staged tag when the default is not staged", () => {
    // An admin deleted the configured image, or an override names a tag
    // nobody staged. Offer something runnable rather than an absent default.
    const container = {
      ...CONTAINER,
      tags: ["v0.8.4", "v0.8.5"],
      default: "v0.20.0",
      default_staged: false,
    };
    const { setImageRef } = renderSelect({ container });
    expect(setImageRef).toHaveBeenCalledWith("vllm/vllm-openai:v0.8.4");
  });

  it("renders nothing and pins nothing when the profile is unreachable", () => {
    // container is undefined when discovery failed. The launch must still
    // proceed on the backend's configured default.
    const { container: dom, setImageRef } = renderSelect({ container: undefined });
    expect(dom).toBeEmptyDOMElement();
    expect(setImageRef).toHaveBeenCalledWith(null);
  });

  it("renders nothing when nothing is staged", () => {
    const container = { ...CONTAINER, tags: [], default_staged: false };
    const { container: dom } = renderSelect({ container });
    expect(dom).toBeEmptyDOMElement();
  });

  it("still renders with a single option, matching RevisionSelect", () => {
    // Disabling one-option selects is tracked separately (#489); until then
    // the version in use stays visible rather than vanishing.
    const container = {
      ...CONTAINER,
      tags: ["0.1.1"],
      default: "0.1.1",
    };
    renderSelect({ container });
    expect(screen.getByText("0.1.1")).toBeInTheDocument();
  });

  it("re-seeds when the container changes, e.g. on a profile switch", () => {
    const { rerender, setImageRef } = renderSelect();
    expect(setImageRef).toHaveBeenCalledWith("vllm/vllm-openai:v0.20.0");

    const other = {
      service: "tigerflow_ml",
      repo: "ghcr.io/princeton-ddss/tigerflow-ml",
      tags: ["0.1.1"],
      default: "0.1.1",
      default_staged: true,
    };
    rerender(
      <ImageVersionSelect
        container={other}
        imageRef={null}
        setImageRef={setImageRef}
        disabled={false}
      />
    );
    expect(setImageRef).toHaveBeenLastCalledWith(
      "ghcr.io/princeton-ddss/tigerflow-ml:0.1.1"
    );
  });

  it("never lifts a new repo paired with the previous tag", () => {
    // Regression: seeding `selected` in one effect and lifting it in another
    // let the lift fire first with the new container but the stale tag,
    // emitting a reference that does not exist. Deriving the selection from
    // the container removes the intermediate entirely. `toHaveBeenLastCalled`
    // would not catch this — every call has to be correct.
    const { rerender, setImageRef } = renderSelect();
    setImageRef.mockClear();

    const other = {
      service: "tigerflow_ml",
      repo: "ghcr.io/princeton-ddss/tigerflow-ml",
      tags: ["0.1.1"],
      default: "0.1.1",
      default_staged: true,
    };
    rerender(
      <ImageVersionSelect
        container={other}
        imageRef={null}
        setImageRef={setImageRef}
        disabled={false}
      />
    );

    for (const [ref] of setImageRef.mock.calls) {
      if (ref !== null) {
        expect(ref).toBe("ghcr.io/princeton-ddss/tigerflow-ml:0.1.1");
      }
    }
  });

  it("shows a skeleton rather than the select while loading", () => {
    renderSelect({ isLoading: true });
    // The real select renders its current value; the skeleton must not.
    expect(screen.queryByText("v0.20.0")).not.toBeInTheDocument();
  });

  it("does not crash when no setter is supplied", () => {
    expect(() =>
      render(<ImageVersionSelect container={CONTAINER} />)
    ).not.toThrow();
  });
});
