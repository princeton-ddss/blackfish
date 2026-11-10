import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import RevisionSelect from "@/components/RevisionSelect";

describe("RevisionSelect", () => {
  it("selects the matching repository revision", () => {
    const setModel = vi.fn();
    render(
      <RevisionSelect
        models={[
          { repo_id: "repo", revision: "rev-a" },
          { repo_id: "other-repo", revision: "rev-b" },
        ]}
        repoId="repo"
        setModel={setModel}
        disabled={false}
      />
    );
    expect(screen.getByRole("button")).toHaveTextContent("rev-a");
    expect(setModel).toHaveBeenCalledWith({ repo_id: "repo", revision: "rev-a" });
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

  it("disables selection when disabled even with multiple revisions", () => {
    render(
      <RevisionSelect
        models={[
          { repo_id: "repo", revision: "rev-a" },
          { repo_id: "repo", revision: "rev-b" },
        ]}
        repoId="repo"
        setModel={vi.fn()}
        disabled={true}
      />
    );
    expect(screen.getByRole("button")).toBeDisabled();
    expect(screen.getByRole("button")).toHaveTextContent("rev-a");
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
