import js from '@eslint/js'
import globals from 'globals'
import tseslint from '@typescript-eslint/eslint-plugin'
import tsParser from '@typescript-eslint/parser'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'

export default [
  // Base JS recommended rules (applies to all JS files)
  js.configs.recommended,

  // TypeScript source files
  {
    files: ['src/**/*.{ts,tsx}'],
    languageOptions: {
      parser: tsParser,
      parserOptions: {
        ecmaVersion: 'latest',
        sourceType: 'module',
        ecmaFeatures: { jsx: true },
      },
      globals: {
        ...globals.browser,
        ...globals.es2020,
      },
    },
    plugins: {
      '@typescript-eslint': tseslint,
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },
    rules: {
      // TypeScript recommended (flat config version)
      ...tseslint.configs['flat/recommended'].rules,

      // React Hooks
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'warn',

      // React Refresh (Vite HMR)
      'react-refresh/only-export-components': ['warn', { allowConstantExport: true }],

      // TypeScript's own compiler covers undefined variables; `no-undef` produces
      // false positives on DOM/browser types (RequestInit, etc.) in .ts/.tsx files.
      'no-undef': 'off',

      // Allow explicit `any` in a few pragmatic cases (e.g. error handler catch blocks).
      '@typescript-eslint/no-explicit-any': 'warn',

      // `@typescript-eslint/no-unused-vars` replaces the base ESLint rule.
      // Underscore-prefixed variables are a well-established ignore convention.
      'no-unused-vars': 'off',
      '@typescript-eslint/no-unused-vars': [
        'error',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_', caughtErrorsIgnorePattern: '^_' },
      ],
    },
  },

  // Config/tooling files (vite.config.ts, vitest.config.ts, postcss.config.js, tailwind.config.js)
  {
    files: ['*.config.{js,ts,mjs,cjs}', '*.config.*.{js,ts}'],
    languageOptions: {
      globals: {
        ...globals.node,
        ...globals.es2020,
      },
    },
  },

  // Ignore generated/third-party directories
  {
    ignores: ['dist/', 'node_modules/', 'coverage/'],
  },
]
