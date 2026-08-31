// ESLint flat config (eslint.config.mjs)
// Uses @eslint/eslintrc FlatCompat to wrap the legacy eslint-config-next
// package (v14.x ships only the legacy config format).
// No new dependencies are required — @eslint/eslintrc ships with ESLint 8.

import { FlatCompat } from '@eslint/eslintrc'
import { fileURLToPath } from 'url'
import path from 'path'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

const compat = new FlatCompat({
  baseDirectory: __dirname,
})

/** @type {import('eslint').Linter.FlatConfig[]} */
const config = [
  // Global ignores for generated/build output directories
  {
    ignores: [
      '.next/**',
      'out/**',
      'build/**',
      'next-env.d.ts',
      'node_modules/**',
    ],
  },

  // Wrap the legacy eslint-config-next/core-web-vitals using FlatCompat
  ...compat.extends('next/core-web-vitals'),
]

export default config
