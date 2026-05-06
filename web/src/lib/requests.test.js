import { describe, it, expect } from "vitest";
import { buildContainerConfig } from "@/lib/requests";

describe("buildContainerConfig", () => {
  it("strips disable_thinking when false and adds no launch_kwargs", () => {
    const out = buildContainerConfig({
      disable_thinking: false,
      disable_custom_kernels: false,
      input_dir: "/data",
    });
    expect(out).toEqual({
      disable_custom_kernels: false,
      input_dir: "/data",
    });
    expect(out).not.toHaveProperty("disable_thinking");
    expect(out).not.toHaveProperty("launch_kwargs");
  });

  it("translates disable_thinking=true into launch_kwargs and strips the flag", () => {
    const out = buildContainerConfig({
      disable_thinking: true,
      disable_custom_kernels: false,
    });
    expect(out).not.toHaveProperty("disable_thinking");
    expect(out.launch_kwargs).toBe(
      `--default-chat-template-kwargs '{"enable_thinking": false, "thinking": false}'`
    );
    expect(out.disable_custom_kernels).toBe(false);
  });
});
