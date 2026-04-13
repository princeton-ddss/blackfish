import { describe, expect, it } from "vitest";
import {
  buildMultimodalContent,
  isMultimodalContent,
  extractTextFromContent,
  extractImagesFromContent,
  IMAGE_EXTENSIONS,
  isImageFile,
} from "./imageUtils";

describe("imageUtils", () => {
  describe("buildMultimodalContent", () => {
    it("builds content array with images first, then text", () => {
      const result = buildMultimodalContent("Hello", ["data:image/png;base64,abc"]);
      expect(result).toEqual([
        { type: "image_url", image_url: { url: "data:image/png;base64,abc" } },
        { type: "text", text: "Hello" },
      ]);
    });

    it("handles multiple images", () => {
      const result = buildMultimodalContent("Test", [
        "data:image/png;base64,img1",
        "data:image/jpeg;base64,img2",
      ]);
      expect(result).toHaveLength(3);
      expect(result[0].type).toBe("image_url");
      expect(result[1].type).toBe("image_url");
      expect(result[2].type).toBe("text");
    });

    it("handles empty text", () => {
      const result = buildMultimodalContent("", ["data:image/png;base64,abc"]);
      expect(result).toEqual([
        { type: "image_url", image_url: { url: "data:image/png;base64,abc" } },
      ]);
    });

    it("handles empty images array", () => {
      const result = buildMultimodalContent("Just text", []);
      expect(result).toEqual([{ type: "text", text: "Just text" }]);
    });
  });

  describe("isMultimodalContent", () => {
    it("returns true for array content", () => {
      expect(isMultimodalContent([{ type: "text", text: "Hello" }])).toBe(true);
    });

    it("returns false for string content", () => {
      expect(isMultimodalContent("Hello")).toBe(false);
    });

    it("returns false for null", () => {
      expect(isMultimodalContent(null)).toBe(false);
    });

    it("returns false for undefined", () => {
      expect(isMultimodalContent(undefined)).toBe(false);
    });
  });

  describe("extractTextFromContent", () => {
    it("returns string content as-is", () => {
      expect(extractTextFromContent("Hello world")).toBe("Hello world");
    });

    it("extracts text from multimodal array", () => {
      const content = [
        { type: "image_url", image_url: { url: "data:image/png;base64,abc" } },
        { type: "text", text: "Describe this image" },
      ];
      expect(extractTextFromContent(content)).toBe("Describe this image");
    });

    it("returns empty string if no text part in array", () => {
      const content = [
        { type: "image_url", image_url: { url: "data:image/png;base64,abc" } },
      ];
      expect(extractTextFromContent(content)).toBe("");
    });

    it("returns empty string for empty array", () => {
      expect(extractTextFromContent([])).toBe("");
    });

    it("returns empty string for non-string, non-array", () => {
      expect(extractTextFromContent(null)).toBe("");
      expect(extractTextFromContent(undefined)).toBe("");
      expect(extractTextFromContent(123)).toBe("");
    });
  });

  describe("extractImagesFromContent", () => {
    it("returns empty array for string content", () => {
      expect(extractImagesFromContent("Hello")).toEqual([]);
    });

    it("extracts image URLs from multimodal array", () => {
      const content = [
        { type: "image_url", image_url: { url: "data:image/png;base64,img1" } },
        { type: "text", text: "Hello" },
        { type: "image_url", image_url: { url: "data:image/jpeg;base64,img2" } },
      ];
      expect(extractImagesFromContent(content)).toEqual([
        "data:image/png;base64,img1",
        "data:image/jpeg;base64,img2",
      ]);
    });

    it("returns empty array if no images in array", () => {
      const content = [{ type: "text", text: "Hello" }];
      expect(extractImagesFromContent(content)).toEqual([]);
    });

    it("returns empty array for null", () => {
      expect(extractImagesFromContent(null)).toEqual([]);
    });
  });

  describe("IMAGE_EXTENSIONS", () => {
    it("contains common image extensions", () => {
      expect(IMAGE_EXTENSIONS).toContain(".png");
      expect(IMAGE_EXTENSIONS).toContain(".jpg");
      expect(IMAGE_EXTENSIONS).toContain(".jpeg");
      expect(IMAGE_EXTENSIONS).toContain(".gif");
      expect(IMAGE_EXTENSIONS).toContain(".webp");
    });
  });

  describe("isImageFile", () => {
    it("returns true for supported extensions", () => {
      expect(isImageFile("photo.png")).toBe(true);
      expect(isImageFile("photo.jpg")).toBe(true);
      expect(isImageFile("photo.jpeg")).toBe(true);
      expect(isImageFile("photo.gif")).toBe(true);
      expect(isImageFile("photo.webp")).toBe(true);
    });

    it("is case-insensitive", () => {
      expect(isImageFile("photo.PNG")).toBe(true);
      expect(isImageFile("photo.JPG")).toBe(true);
      expect(isImageFile("PHOTO.JPEG")).toBe(true);
    });

    it("returns false for unsupported extensions", () => {
      expect(isImageFile("document.pdf")).toBe(false);
      expect(isImageFile("script.js")).toBe(false);
      expect(isImageFile("data.json")).toBe(false);
    });

    it("returns false for files without extension", () => {
      expect(isImageFile("noextension")).toBe(false);
    });
  });
});
