import { render, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import PropTypes from "prop-types";
import {
  ScrollContainerContext,
  useScrollOnExpand,
} from "@/lib/useScrollOnExpand";

function Section({ expanded }) {
  useScrollOnExpand(expanded);
  return null;
}

Section.propTypes = {
  expanded: PropTypes.bool,
};

function renderWithContainer(expanded, containerRef) {
  return render(
    <ScrollContainerContext.Provider value={containerRef}>
      <Section expanded={expanded} />
    </ScrollContainerContext.Provider>
  );
}

describe("useScrollOnExpand", () => {
  let containerRef;

  beforeEach(() => {
    vi.useFakeTimers();
    containerRef = { current: { scrollTo: vi.fn(), scrollHeight: 1200 } };
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("scrolls the container to the bottom when a section expands", () => {
    renderWithContainer(true, containerRef);
    act(() => vi.advanceTimersByTime(100));
    expect(containerRef.current.scrollTo).toHaveBeenCalledWith({
      top: 1200,
      behavior: "smooth",
    });
  });

  it("does not scroll while the section is collapsed", () => {
    renderWithContainer(false, containerRef);
    act(() => vi.advanceTimersByTime(100));
    expect(containerRef.current.scrollTo).not.toHaveBeenCalled();
  });

  it("scrolls after a delay, so the revealed content is measured", () => {
    // scrollHeight must include the newly expanded section; scrolling in the
    // same tick would use the pre-expansion height and stop short.
    renderWithContainer(true, containerRef);
    expect(containerRef.current.scrollTo).not.toHaveBeenCalled();
    act(() => vi.advanceTimersByTime(100));
    expect(containerRef.current.scrollTo).toHaveBeenCalledTimes(1);
  });

  it("does not scroll if the section collapses before the timer fires", () => {
    const { rerender } = renderWithContainer(true, containerRef);
    rerender(
      <ScrollContainerContext.Provider value={containerRef}>
        <Section expanded={false} />
      </ScrollContainerContext.Provider>
    );
    act(() => vi.advanceTimersByTime(100));
    expect(containerRef.current.scrollTo).not.toHaveBeenCalled();
  });

  it("is a no-op outside a modal, where there is no scroll container", () => {
    // Rendered without a provider — the components using this hook are also
    // rendered directly in tests.
    expect(() => {
      render(<Section expanded={true} />);
      act(() => vi.advanceTimersByTime(100));
    }).not.toThrow();
  });
});
