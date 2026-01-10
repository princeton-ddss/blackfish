import js from "@eslint/js";
import globals from "globals";
import pluginReact from "eslint-plugin-react";
import pluginJest from "eslint-plugin-jest";
import { defineConfig, globalIgnores } from "eslint/config";
import { FlatCompat } from "@eslint/eslintrc";

const compat = new FlatCompat({
  baseDirectory: import.meta.dirname + "/app",
});

export default defineConfig([
  ...compat.config({
    extends: ["next/core-web-vitals"]
  }),
  {
    files: ["app/**/*.{js,mjs,cjs,jsx}"],
    plugins: { js },
    extends: [
      "js/recommended",
    ]
  },
  {
    files: ["app/**/*.{js,mjs,cjs,jsx}"],
    languageOptions: {
      globals: globals.browser
    }
  },
  {
    files: ["app/**/*.{spec.js,test.js}"],
    plugins: { jest: pluginJest },
    languageOptions: {
      globals: pluginJest.environments.globals.globals
    }
  },
  pluginReact.configs.flat.recommended,
  pluginReact.configs.flat["jsx-runtime"],
  globalIgnores(["build/*", ".next/*"]),
]);
