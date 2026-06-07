import js from "@eslint/js";
import jsxA11y from "eslint-plugin-jsx-a11y";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import globals from "globals";
import tseslint from "typescript-eslint";

export default tseslint.config(
  { ignores: ["dist", "coverage"] },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ["**/*.{ts,tsx}"],
    languageOptions: {
      ecmaVersion: 2022,
      globals: globals.browser,
    },
    plugins: {
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh,
      "jsx-a11y": jsxA11y,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      ...jsxA11y.flatConfigs.recommended.rules,
      "react-refresh/only-export-components": ["warn", { allowConstantExport: true }],
    },
  },
  {
    // Context providers co-export their hook, shadcn/ui primitives co-export
    // variant helpers, and test utilities export render helpers — all
    // intentional; fast-refresh's one-export rule doesn't apply to them.
    files: [
      "src/components/ui/**/*.tsx",
      "src/components/theme-provider.tsx",
      "src/session/session-context.tsx",
      "src/test/**/*.tsx",
    ],
    rules: {
      "react-refresh/only-export-components": "off",
    },
  },
  {
    files: ["**/*.{test,spec}.{ts,tsx}", "src/test/**"],
    languageOptions: {
      globals: { ...globals.browser, ...globals.node },
    },
  },
);
