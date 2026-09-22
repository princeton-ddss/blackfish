import { render, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { ServiceContext } from "@/providers/ServiceProvider";
import CodeSnippetModal from "./CodeSnippetModal";

// Whether a key is required comes with the service row itself, so the modal
// reads it directly — no second request, and no window where the snippet is
// generated without the header it needs.
function renderModal({ isProtected = false } = {}) {
  return render(
    <ServiceContext.Provider
      value={{ selectedService: { id: "svc-1", port: 8080, protected: isProtected } }}
    >
      <CodeSnippetModal open onClose={vi.fn()} mode="chat" parameters={{}} />
    </ServiceContext.Provider>
  );
}

describe("CodeSnippetModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("omits an auth header when the service has no key", async () => {
    renderModal({ isProtected: false });

    // The modal opens on the Python tab.
    await waitFor(() =>
      expect(document.body.textContent).toContain("import requests")
    );
    expect(document.body.textContent).not.toContain("Authorization");
  });

  it("includes an auth header when the service has a key", async () => {
    // Without this the generated snippets 401 against a keyed service, which
    // is the main way users learn to call it from outside the UI.
    renderModal({ isProtected: true });

    await waitFor(() =>
      expect(document.body.textContent).toContain("Authorization")
    );
  });

  it("tells the user the service is protected", async () => {
    renderModal({ isProtected: true });

    await waitFor(() =>
      expect(document.body.textContent).toContain("This service is protected")
    );
  });

  it("renders no part of the key", async () => {
    // The endpoint is hint-only by construction; the modal shows neither the
    // key nor the hint, just that one is required.
    renderModal({ isProtected: true });

    await waitFor(() => expect(document.body.textContent).toContain("Authorization"));
    expect(document.body.textContent).not.toContain("sk-");
    expect(document.body.textContent).not.toContain("cdef");
  });
});
