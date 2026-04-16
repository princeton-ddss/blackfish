import { render } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import AttachmentMenu from "./AttachmentMenu";

describe("AttachmentMenu", () => {
  const defaultProps = {
    accept: "image/*",
    onBrowserUpload: vi.fn(),
    onRemoteSelect: vi.fn(),
    onError: vi.fn(),
  };

  async function openMenu(profile) {
    const user = userEvent.setup();
    const result = render(<AttachmentMenu {...defaultProps} profile={profile} />);
    const button = result.getByRole("button", { name: /attach/i });
    await user.click(button);
    return result;
  }

  it("hides server button for a local profile", async () => {
    const profile = { name: "local", schema: "local", home_dir: "/home/u", cache_dir: "/cache" };
    const { queryByText } = await openMenu(profile);
    expect(queryByText("Upload from computer")).toBeTruthy();
    expect(queryByText("Select from server")).toBeNull();
  });

  it("shows server button for a Slurm-localhost profile", async () => {
    const profile = { name: "ondemand", schema: "slurm", host: "localhost", user: "u", home_dir: "/home/u", cache_dir: "/cache" };
    const { queryByText } = await openMenu(profile);
    expect(queryByText("Upload from computer")).toBeTruthy();
    expect(queryByText("Select from server")).toBeTruthy();
  });

  it("shows server button for a remote Slurm profile", async () => {
    const profile = { name: "della", schema: "slurm", host: "della.princeton.edu", user: "u", home_dir: "/home/u", cache_dir: "/cache" };
    const { queryByText } = await openMenu(profile);
    expect(queryByText("Upload from computer")).toBeTruthy();
    expect(queryByText("Select from server")).toBeTruthy();
  });
});
