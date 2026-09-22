import { render, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { ServiceContext } from "@/providers/ServiceProvider";
import CodeSnippetModal from "./CodeSnippetModal";

// The modal asks the backend whether the service has a key; only a hint comes
// back, never the key itself.
vi.mock("@/lib/requests", () => ({
  fetchServiceApiKeyStatus: vi.fn(),
}));
import { fetchServiceApiKeyStatus } from "@/lib/requests";

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
    fetchServiceApiKeyStatus.mockResolvedValue({ configured: false, hint: null });

    renderModal();

    await waitFor(() => expect(fetchServiceApiKeyStatus).toHaveBeenCalled());
    expect(document.body.textContent).not.toContain("Authorization");
  });

  it("includes an auth header when the service has a key", async () => {
    // Without this the generated snippets 401 against a keyed service, which
    // is the main way users learn to call it from outside the UI.
    fetchServiceApiKeyStatus.mockResolvedValue({ configured: true, hint: "...cdef" });

    renderModal();

    await waitFor(() =>
      expect(document.body.textContent).toContain("Authorization")
    );
  });

  it("tells the user the service is protected", async () => {
    fetchServiceApiKeyStatus.mockResolvedValue({ configured: true, hint: "...cdef" });

    renderModal();

    await waitFor(() =>
      expect(document.body.textContent).toContain("This service is protected")
    );
  });

  it("renders no part of the key", async () => {
    // The endpoint is hint-only by construction; the modal shows neither the
    // key nor the hint, just that one is required.
    fetchServiceApiKeyStatus.mockResolvedValue({ configured: true, hint: "...cdef" });

    renderModal();

    await waitFor(() => expect(document.body.textContent).toContain("Authorization"));
    expect(document.body.textContent).not.toContain("sk-");
    expect(document.body.textContent).not.toContain("cdef");
  });
});
