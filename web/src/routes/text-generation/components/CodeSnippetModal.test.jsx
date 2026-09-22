import { render, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { ServiceContext } from "@/providers/ServiceProvider";
import CodeSnippetModal from "./CodeSnippetModal";

// The modal asks the backend whether the service has a key; only that fact
// comes back, never the key itself.
vi.mock("@/lib/loaders", () => ({
  useServiceApiKeyStatus: vi.fn(() => ({ configured: false })),
}));
import { useServiceApiKeyStatus } from "@/lib/loaders";

const service = { id: "svc-1", port: 8080 };

function renderModal() {
  return render(
    <ServiceContext.Provider value={{ selectedService: service }}>
      <CodeSnippetModal open onClose={vi.fn()} mode="chat" parameters={{}} />
    </ServiceContext.Provider>
  );
}

describe("CodeSnippetModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("omits an auth header when the service has no key", async () => {
    useServiceApiKeyStatus.mockReturnValue({ configured: false });

    renderModal();

    await waitFor(() => expect(useServiceApiKeyStatus).toHaveBeenCalled());
    expect(document.body.textContent).not.toContain("Authorization");
  });

  it("includes an auth header when the service has a key", async () => {
    // Without this the generated snippets 401 against a keyed service, which
    // is the main way users learn to call it from outside the UI.
    useServiceApiKeyStatus.mockReturnValue({ configured: true });

    renderModal();

    await waitFor(() =>
      expect(document.body.textContent).toContain("Authorization")
    );
  });

  it("tells the user the service is protected", async () => {
    useServiceApiKeyStatus.mockReturnValue({ configured: true });

    renderModal();

    await waitFor(() =>
      expect(document.body.textContent).toContain("This service is protected")
    );
  });

  it("renders no part of the key", async () => {
    // The endpoint is hint-only by construction; the modal shows neither the
    // key nor the hint, just that one is required.
    useServiceApiKeyStatus.mockReturnValue({ configured: true });

    renderModal();

    await waitFor(() => expect(document.body.textContent).toContain("Authorization"));
    expect(document.body.textContent).not.toContain("sk-");
    expect(document.body.textContent).not.toContain("cdef");
  });
});
