import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import RevisionSelect from "@/components/RevisionSelect";

describe("RevisionSelect", () => {
  it("Standard", () => {
    const {baseElement} = render(
      <RevisionSelect
        models={[
          {
            repo_id: "169d4a4341b33bc18d8881c4b69c2e104e1cc0af",
            revision: "169d4a4341b33bc18d8881c4b69c2e104e1cc0af"
          },
          {
            repo_id: "7b5c7132e6f7b1126bf02b18d888c780180a0cf3",
            revision: "7b5c7132e6f7b1126bf02b18d888c780180a0cf3"
          },
        ]}
        repoId="169d4a4341b33bc18d8881c4b69c2e104e1cc0af"
        setModel={(e) => e}
        disabled={false}
      />
    );
    expect(baseElement).toMatchSnapshot();
  });

  it("stays enabled when the repo has multiple revisions", () => {
    // Guards the off-by-one direction of the `< 2` check: two options must
    // remain interactive, otherwise the launcher becomes unusable for any
    // repo that has more than one staged revision.
    const setModel = vi.fn();
    render(
      <RevisionSelect
        models={[
          { repo_id: "repo", revision: "rev-a" },
          { repo_id: "repo", revision: "rev-b" },
        ]}
        repoId="repo"
        setModel={setModel}
        disabled={false}
      />
    );
    expect(screen.getByRole("button")).not.toBeDisabled();
  });

  it("disables the control (but still lifts the model) with one revision", () => {
    const setModel = vi.fn();
    render(
      <RevisionSelect
        models={[{ repo_id: "repo", revision: "rev-only" }]}
        repoId="repo"
        setModel={setModel}
        disabled={false}
      />
    );
    expect(screen.getByRole("button")).toBeDisabled();
    expect(setModel).toHaveBeenCalledWith({ repo_id: "repo", revision: "rev-only" });
  });

  it("Disabled", () => {
    const {baseElement} = render(
      <RevisionSelect
        models={[
          {
            repo_id: "169d4a4341b33bc18d8881c4b69c2e104e1cc0af",
            revision: "169d4a4341b33bc18d8881c4b69c2e104e1cc0af"
          },
          {
            repo_id: "7b5c7132e6f7b1126bf02b18d888c780180a0cf3",
            revision: "7b5c7132e6f7b1126bf02b18d888c780180a0cf3"
          },
        ]}
        repoId="169d4a4341b33bc18d8881c4b69c2e104e1cc0af"
        setModel={(e) => e}
        disabled={true}
      />
    );
    expect(baseElement).toMatchSnapshot();
  });

  it("Loading", () => {
    const {container, getByText, queryByText} = render(
      <RevisionSelect
        models={[]}
        repoId="model-1"
        setModel={(e) => e}
        disabled={true}
        isLoading={true}
      />
    );
    expect(getByText("Revision")).toBeInTheDocument();
    expect(queryByText("Loading revisions...")).not.toBeInTheDocument();
    expect(container.querySelector('[aria-busy="true"].animate-pulse')).toBeInTheDocument();
  });

  it("Refreshing", () => {
    const {container, queryByText} = render(
      <RevisionSelect
        models={[
          {
            repo_id: "model-1",
            revision: "rev-1"
          },
        ]}
        repoId="model-1"
        setModel={(e) => e}
        disabled={true}
        isLoading={true}
      />
    );
    expect(container.querySelector('[aria-busy="true"].animate-pulse')).toBeInTheDocument();
    expect(queryByText("Loading revisions...")).not.toBeInTheDocument();
    expect(queryByText("rev-1")).not.toBeInTheDocument();
  });
});
