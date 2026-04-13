/* eslint react/prop-types: 0 */

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import ServiceModalForm from "@/components/ServiceModalForm";

// Mock child components that aren't relevant to partition tests
vi.mock("@/components/ModelSelect", () => ({
  default: () => <div data-testid="model-select" />,
}));
vi.mock("@/components/RevisionSelect", () => ({
  default: () => <div data-testid="revision-select" />,
}));
vi.mock("@/components/TierSelect", () => ({
  default: ({ tiers, selectedTier }) => (
    <div data-testid="tier-select">
      {tiers.map((t) => (
        <span key={t.name} data-testid={`tier-${t.name}`}>
          {t.name}
        </span>
      ))}
      {selectedTier && (
        <span data-testid="selected-tier">{selectedTier}</span>
      )}
    </div>
  ),
}));
vi.mock("@/components/ServiceModalValidatedInput", () => ({
  default: ({ label, value }) => (
    <div data-testid={`input-${label.toLowerCase()}`}>{value}</div>
  ),
}));
vi.mock("@/lib/requests", () => ({
  fetchModelSizeFromHub: vi.fn().mockResolvedValue(null),
}));
vi.mock("@/lib/util", () => ({
  classNames: (...args) => args.filter(Boolean).join(" "),
  selectTierByModelSize: vi.fn(),
}));

describe("ServiceModalForm – Partition Input", () => {
  const defaultProps = {
    models: [{ repo_id: "model-1", id: "m1" }],
    services: [],
    setModel: vi.fn(),
    jobOptions: {
      name: "blackfish-12345",
      time: "00:30:00",
      ntasks_per_node: null,
      mem: null,
      gres: null,
      partition: null,
      constraint: null,
      account: null,
    },
    setJobOptions: vi.fn(),
    setValidationErrors: vi.fn(),
    disabled: false,
    profile: { schema: "slurm", host: "test-host", user: "testuser" },
    task: "text-generation",
    resources: {
      partitions: [],
      time: { default: 30, max: 180 },
    },
    clusterPartitions: null,
    children: null,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderForm = (props = {}) =>
    render(<ServiceModalForm {...defaultProps} {...props} />);

  it("shows warning when blurred with a partition not on the cluster", async () => {
    const user = userEvent.setup();
    renderForm({ clusterPartitions: ["gpu", "cpu"] });

    const input = screen.getByRole("textbox", { name: /partition/i });
    await user.type(input, "nonexistent");
    await user.tab(); // blur

    expect(
      screen.getByText(
        'Partition "nonexistent" was not found on the cluster.'
      )
    ).toBeInTheDocument();
  });

  it("does not show warning when blurred with a valid partition", async () => {
    const user = userEvent.setup();
    renderForm({ clusterPartitions: ["gpu", "cpu"] });

    const input = screen.getByRole("textbox", { name: /partition/i });
    await user.type(input, "gpu");
    await user.tab();

    expect(
      screen.queryByText(/was not found on the cluster/)
    ).not.toBeInTheDocument();
  });

  it("does not show warning when cluster status is unavailable", async () => {
    const user = userEvent.setup();
    renderForm({ clusterPartitions: null });

    const input = screen.getByRole("textbox", { name: /partition/i });
    await user.type(input, "anything");
    await user.tab();

    expect(
      screen.queryByText(/was not found on the cluster/)
    ).not.toBeInTheDocument();
  });

  it("clears warning when the input value changes", async () => {
    const user = userEvent.setup();
    renderForm({ clusterPartitions: ["gpu"] });

    const input = screen.getByRole("textbox", { name: /partition/i });

    // Trigger warning
    await user.type(input, "bad");
    await user.tab();
    expect(
      screen.getByText('Partition "bad" was not found on the cluster.')
    ).toBeInTheDocument();

    // Type again — warning should clear immediately on change
    await user.type(input, "x");
    expect(
      screen.queryByText(/was not found on the cluster/)
    ).not.toBeInTheDocument();
  });

  it("updates tiers when partition matches a spec entry", async () => {
    const user = userEvent.setup();
    const gpuTiers = [
      { name: "A100-Small", gpu_count: 1, gpu_type: "A100", cpu_cores: 4, memory_gb: 16 },
      { name: "A100-Large", gpu_count: 4, gpu_type: "A100", cpu_cores: 16, memory_gb: 64 },
    ];
    const defaultTiers = [
      { name: "Default-Tier", gpu_count: 0, gpu_type: null, cpu_cores: 2, memory_gb: 4 },
    ];

    renderForm({
      resources: {
        partitions: [
          { name: "gpu", default: false, tiers: gpuTiers },
          { name: "cpu", default: true, tiers: defaultTiers },
        ],
        time: { default: 30, max: 180 },
      },
    });

    // Initially should show the default partition's tiers
    expect(screen.getByTestId("tier-Default-Tier")).toBeInTheDocument();
    expect(screen.queryByTestId("tier-A100-Small")).not.toBeInTheDocument();

    // Type a partition that matches a spec entry
    const input = screen.getByRole("textbox", { name: /partition/i });
    await user.type(input, "gpu");
    await user.tab();

    // Now should show the gpu partition's tiers
    expect(screen.getByTestId("tier-A100-Small")).toBeInTheDocument();
    expect(screen.getByTestId("tier-A100-Large")).toBeInTheDocument();
    expect(screen.queryByTestId("tier-Default-Tier")).not.toBeInTheDocument();
  });

  it("falls back to default tiers when partition does not match any spec", async () => {
    const user = userEvent.setup();
    const gpuTiers = [
      { name: "A100-Small", gpu_count: 1, gpu_type: "A100", cpu_cores: 4, memory_gb: 16 },
    ];
    const defaultTiers = [
      { name: "Default-Tier", gpu_count: 0, gpu_type: null, cpu_cores: 2, memory_gb: 4 },
    ];

    renderForm({
      resources: {
        partitions: [
          { name: "gpu", default: false, tiers: gpuTiers },
          { name: "cpu", default: true, tiers: defaultTiers },
        ],
        time: { default: 30, max: 180 },
      },
    });

    const input = screen.getByRole("textbox", { name: /partition/i });
    await user.type(input, "unknown");
    await user.tab();

    // Should still show default tiers, not gpu tiers
    expect(screen.getByTestId("tier-Default-Tier")).toBeInTheDocument();
    expect(screen.queryByTestId("tier-A100-Small")).not.toBeInTheDocument();
  });
});
