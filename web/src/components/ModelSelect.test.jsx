import { render, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import ModelSelect from "./ModelSelect";

global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}));

const mockModels = [
  { repo_id: "model-1", revision: "rev-1" },
  { repo_id: "model-2", revision: "rev-2" },
  { repo_id: "model-1", revision: "rev-3" },
  { repo_id: "model-3", revision: "rev-4" }
];

const mockSetRepoId = vi.fn();

describe("ModelSelect", () => {
  beforeEach(() => {
    mockSetRepoId.mockClear();
  });

  it("renders nothing when models array is empty", () => {
    const {container} = render(
      <ModelSelect models={[]} setRepoId={mockSetRepoId} disabled={false} />
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders nothing when models is null", () => {
    const {container} = render(
      <ModelSelect models={null} setRepoId={mockSetRepoId} disabled={false} />
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders model select with first model selected by default", () => {
    const {baseElement, getByText} = render(
      <ModelSelect
        models={mockModels}
        setRepoId={mockSetRepoId}
        disabled={false}
      />
    );
    expect(getByText("Model")).toBeInTheDocument();
    expect(getByText("model-1")).toBeInTheDocument();
    expect(baseElement).toMatchSnapshot();
  });

  it("calls setRepoId with first model repo_id on mount", async () => {
    render(
      <ModelSelect
        models={mockModels}
        setRepoId={mockSetRepoId}
        disabled={false}
      />
    );
    await waitFor(() => {
      expect(mockSetRepoId).toHaveBeenCalledWith("model-1");
    });
  });

  it("displays unique repo_ids in dropdown when opened", async () => {
    const user = userEvent.setup();
    const {getByRole, getByText, getAllByText} = render(
      <ModelSelect
        models={mockModels}
        setRepoId={mockSetRepoId}
        disabled={false}
      />
    );
    const button = getByRole("button");
    await user.click(button);
    await waitFor(() => {
      expect(getAllByText("model-1")).toHaveLength(2);
      expect(getByText("model-2")).toBeInTheDocument();
      expect(getByText("model-3")).toBeInTheDocument();
    });
  });

  it("changes selection when different model is clicked", async () => {
    const user = userEvent.setup();
    const {getByRole, getAllByText} = render(
      <ModelSelect
        models={mockModels}
        setRepoId={mockSetRepoId}
        disabled={false}
      />
    );
    const button = getByRole("button");
    await user.click(button);
    await user.click(getAllByText("model-2")[0]);
    await waitFor(() => {
      expect(mockSetRepoId).toHaveBeenCalledWith("model-2");
    });
  });

  it("applies disabled styling when disabled prop is true", () => {
    const {baseElement} = render(
      <ModelSelect
        models={mockModels}
        setRepoId={mockSetRepoId}
        disabled={true}
      />
    );
    expect(baseElement).toMatchSnapshot();
  });

  it("updates selection when models prop changes", async () => {
    const {rerender, getByText} = render(
      <ModelSelect
        models={mockModels}
        setRepoId={mockSetRepoId}
        disabled={false}
      />
    );
    const newModels = [
      { repo_id: "new-model", revision: "new-rev-1" }
    ];
    rerender(
      <ModelSelect
        models={newModels}
        setRepoId={mockSetRepoId}
        disabled={false}
      />
    );
    await waitFor(() => {
      expect(getByText("new-model")).toBeInTheDocument();
      expect(mockSetRepoId).toHaveBeenCalledWith("new-model");
    });
  });

  it("resets selection to null when models becomes empty", () => {
    const {container, rerender} = render(
      <ModelSelect
        models={mockModels}
        setRepoId={mockSetRepoId}
        disabled={false}
      />
    );
    rerender(
      <ModelSelect models={[]} setRepoId={mockSetRepoId} disabled={false} />
    );
    expect(container.firstChild).toBeNull();
  });

  it("handles undefined models prop", () => {
    const {container} = render(
      <ModelSelect
        models={undefined}
        setRepoId={mockSetRepoId}
        disabled={false}
      />
    );
    expect(container.firstChild).toBeNull();
  });

  it("displays check icon for selected option in dropdown", async () => {
    const user = userEvent.setup();
    const {container, getByRole} = render(
      <ModelSelect
        models={mockModels}
        setRepoId={mockSetRepoId}
        disabled={false}
      />
    );
    await user.click(getByRole("button"));
    await waitFor(() => {
      expect(container.querySelector('.check-icon')).toBeInTheDocument();
    });
  });

  it("handles selection change event correctly", async () => {
    const user = userEvent.setup();
    const {getByRole, getByText} = render(
      <ModelSelect
        models={mockModels}
        setRepoId={mockSetRepoId}
        disabled={false}
      />
    );
    await user.click(getByRole("button"));
    await user.click(getByText("model-3"));
    await waitFor(() => {
      expect(mockSetRepoId).toHaveBeenCalledWith("model-3");
    });
  });
});
