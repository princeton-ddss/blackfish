import { useContext } from "react";
import { render, act } from "@testing-library/react";
import { describe, test, expect, vi } from "vitest";
import ServiceProvider, { ServiceContext } from "./ServiceProvider";

// Grab the registry callbacks out of the context so we can exercise them
// directly, without wiring up a full request flow.
function captureRegistry(onReady) {
  function Consumer() {
    const ctx = useContext(ServiceContext);
    onReady(ctx);
    return null;
  }
  render(
    <ServiceProvider>
      <Consumer />
    </ServiceProvider>
  );
}

describe("ServiceProvider cancellation registry", () => {
  test("cancelInFlight only aborts requests for the matching service", () => {
    let ctx;
    captureRegistry((c) => (ctx = c));

    const cancelA = vi.fn();
    const cancelB = vi.fn();
    act(() => {
      ctx.registerInFlight("svc-a", cancelA);
      ctx.registerInFlight("svc-b", cancelB);
    });

    act(() => ctx.cancelInFlight("svc-a"));

    expect(cancelA).toHaveBeenCalledOnce();
    expect(cancelB).not.toHaveBeenCalled();
  });

  test("cancels every concurrent request registered against one service", () => {
    let ctx;
    captureRegistry((c) => (ctx = c));

    const first = vi.fn();
    const second = vi.fn();
    act(() => {
      ctx.registerInFlight("svc", first);
      ctx.registerInFlight("svc", second);
    });

    act(() => ctx.cancelInFlight("svc"));

    expect(first).toHaveBeenCalledOnce();
    expect(second).toHaveBeenCalledOnce();
  });

  test("unregistering a request drops it so it is not cancelled later", () => {
    let ctx;
    captureRegistry((c) => (ctx = c));

    const cancel = vi.fn();
    let unregister;
    act(() => {
      unregister = ctx.registerInFlight("svc", cancel);
    });

    act(() => unregister());
    act(() => ctx.cancelInFlight("svc"));

    expect(cancel).not.toHaveBeenCalled();
  });

  test("cancelInFlight for an unknown service is a no-op", () => {
    let ctx;
    captureRegistry((c) => (ctx = c));

    expect(() => act(() => ctx.cancelInFlight("nobody"))).not.toThrow();
  });
});
