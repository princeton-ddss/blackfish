import { describe, test, expect } from "vitest";
import {
  dirname,
  isFileSystemRoot,
  isAtSecurityBoundary,
  isWithinRoot,
  clampToRoot,
} from "@/lib/pathUtils";

describe("pathUtils", () => {
  describe("dirname", () => {
    test("returns root for the filesystem root", () => {
      expect(dirname("/")).toBe("/");
    });

    test("returns root (not empty) at depth 1", () => {
      expect(dirname("/home")).toBe("/");
    });

    test("preserves leading slash for deep absolute paths", () => {
      expect(dirname("/home/colinswaney/audio/clips")).toBe(
        "/home/colinswaney/audio"
      );
      expect(dirname("/a/b")).toBe("/a");
    });

    test("ignores trailing slashes", () => {
      expect(dirname("/home/user/")).toBe("/home");
      expect(dirname("/home/")).toBe("/");
      expect(dirname("/home/user/data/")).toBe("/home/user");
    });

    test("collapses repeated slashes", () => {
      expect(dirname("/home//user")).toBe("/home");
    });

    test("returns root for empty or nullish input", () => {
      expect(dirname("")).toBe("/");
      expect(dirname(null)).toBe("/");
      expect(dirname(undefined)).toBe("/");
    });

    test("handles relative paths without inventing a leading slash", () => {
      expect(dirname("a/b/c")).toBe("a/b");
      expect(dirname("a")).toBe(".");
    });
  });

  describe("isFileSystemRoot", () => {
    test("true for root representations", () => {
      expect(isFileSystemRoot("/")).toBe(true);
      expect(isFileSystemRoot("")).toBe(true);
      expect(isFileSystemRoot(null)).toBe(true);
    });

    test("false for non-root paths", () => {
      expect(isFileSystemRoot("/home")).toBe(false);
      expect(isFileSystemRoot("/home/user")).toBe(false);
    });
  });

  describe("isAtSecurityBoundary", () => {
    test("true when path equals root (with or without trailing slash)", () => {
      expect(isAtSecurityBoundary("/home/user", "/home/user")).toBe(true);
      expect(isAtSecurityBoundary("/home/user/", "/home/user")).toBe(true);
    });

    test("false below the root", () => {
      expect(isAtSecurityBoundary("/home/user/data", "/home/user")).toBe(false);
    });

    test("no boundary when root is null", () => {
      expect(isAtSecurityBoundary("/home/user", null)).toBe(false);
    });
  });

  describe("isWithinRoot", () => {
    test("true for the root itself and its descendants", () => {
      expect(isWithinRoot("/home/user", "/home/user")).toBe(true);
      expect(isWithinRoot("/home/user/data", "/home/user")).toBe(true);
      expect(isWithinRoot("/home/user/", "/home/user")).toBe(true);
    });

    test("is segment-aware: a prefix sibling is NOT within root", () => {
      // The bug this replaces: "/home/user".startsWith("/home/us") is true.
      expect(isWithinRoot("/home/user", "/home/us")).toBe(false);
      expect(isWithinRoot("/home/username", "/home/user")).toBe(false);
    });

    test("tolerates a trailing slash on root", () => {
      expect(isWithinRoot("/home/user/data", "/home/user/")).toBe(true);
    });

    test("everything is within the filesystem root", () => {
      expect(isWithinRoot("/anything/here", "/")).toBe(true);
    });
  });

  describe("clampToRoot", () => {
    test("returns the path when it is within root", () => {
      expect(clampToRoot("/home/user/data", "/home/user")).toBe("/home/user/data");
    });

    test("clamps to root when the path escapes it", () => {
      // dirname("/home/user") -> "/home"; must clamp back to the root.
      expect(clampToRoot("/home", "/home/user")).toBe("/home/user");
    });

    test("clamps a prefix-sibling back to root (not treated as inside)", () => {
      expect(clampToRoot("/home/us", "/home/user")).toBe("/home/user");
    });

    test("passes the path through when there is no root", () => {
      expect(clampToRoot("/home", null)).toBe("/home");
    });
  });
});
