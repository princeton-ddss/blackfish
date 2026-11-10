import { render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";
import FileManager from "./FileManager";

vi.mock("@/lib/loaders", () => ({
  useFileSystem: () => ({
    files: [],
    error: null,
    isLoading: false,
    refresh: vi.fn(),
    isConnected: true,
    homeDir: "/home/test",
  }),
}));

vi.mock("@/providers/RemoteFileSystemProvider", () => ({
  useRemoteFileSystem: () => ({
    reconnect: vi.fn(),
    isConnecting: false,
    error: null,
  }),
}));

describe.each([
  ["no profile", null],
  ["a local profile", { name: "local", schema: "local" }],
  ["a localhost Slurm profile", { name: "ondemand", schema: "slurm", host: "localhost" }],
  ["a remote Slurm profile", { name: "cluster", schema: "slurm", host: "cluster.example", user: "testuser" }],
])("FileManager uploads with %s", (_label, profile) => {
  test.each([true, false])("upload visibility matches enableUpload=%s", (enableUpload) => {
    render(
      <FileManager
        root="/home/test"
        profile={profile}
        status={{ disabled: false }}
        enableUpload={enableUpload}
      />,
    );

    const button = screen.queryByRole("button", { name: "Upload file" });
    if (enableUpload) {
      expect(button).toBeInTheDocument();
      expect(button).toBeEnabled();
    } else {
      expect(button).not.toBeInTheDocument();
    }
  });
});
