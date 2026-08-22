import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import PartitionSelect from "@/components/PartitionSelect";

const MULTI = [
  { name: "gpu", default: true },
  { name: "cpu" },
];

describe("PartitionSelect", () => {
  it("renders nothing when there are no partitions", () => {
    const { container } = render(
      <PartitionSelect partitions={[]} setSelectedPartition={vi.fn()} />
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("stays enabled when there are multiple partitions", () => {
    render(
      <PartitionSelect
        partitions={MULTI}
        selectedPartition="gpu"
        setSelectedPartition={vi.fn()}
      />
    );
    expect(screen.getByRole("button")).not.toBeDisabled();
  });

  it("disables the control with a single partition", () => {
    // The parent already syncs the default into state, so disabling here is
    // safe: the partition name still reaches the launch payload without any
    // click from the user.
    render(
      <PartitionSelect
        partitions={[{ name: "only", default: true }]}
        selectedPartition="only"
        setSelectedPartition={vi.fn()}
      />
    );
    expect(screen.getByRole("button")).toBeDisabled();
    expect(screen.getByText("only (Default)")).toBeInTheDocument();
  });

  it("honors an explicit disabled prop even with multiple partitions", () => {
    render(
      <PartitionSelect
        partitions={MULTI}
        selectedPartition="gpu"
        setSelectedPartition={vi.fn()}
        disabled
      />
    );
    expect(screen.getByRole("button")).toBeDisabled();
  });
});
