import eslint from "@eslint/js";
import tseslint from "typescript-eslint";
import eslintPluginPrettierRecommended from "eslint-plugin-prettier/recommended";
import globals from "globals";

export default tseslint.config(
  {
    ignores: ["node_modules/**", "dist/**"],
  },
  {
    files: ["**/*.ts"],
    extends: [
      eslint.configs.recommended,
      ...tseslint.configs.recommended,
      eslintPluginPrettierRecommended,
    ],
    languageOptions: {
      ecmaVersion: 2020,
      sourceType: "module",
      globals: {
        ...globals.node,
        ...globals.jest,
        ...globals.es2020,
      },
    },
    rules: {
      "@typescript-eslint/no-unused-vars": [
        "off",
        {
          argsIgnorePattern: "^_",
        },
      ],
      "getter-return": [
        "error",
        {
          allowImplicit: true,
        },
      ],
      "prettier/prettier": [
        "error",
        {
          singleQuote: true,
          trailingComma: "all",
          bracketSpacing: false,
          printWidth: 120,
          tabWidth: 2,
          semi: false,
        },
      ],
      camelcase: "off",
    },
  },
);
