import { dirname } from 'path';
import { fileURLToPath } from 'url';
import { FlatCompat } from '@eslint/eslintrc';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Use the flat config exports from eslint-config-next directly.
// The "next/core-web-vitals" preset covers performance rules for next/image,
// fonts, and links. The "next/typescript" preset covers typed-lint rules.
// eslint-config-next@16.x ships both as native flat config arrays.
import nextCoreWebVitals from 'eslint-config-next/core-web-vitals';
import nextTypescript from 'eslint-config-next/typescript';

const eslintConfig = [
  {
    ignores: [
      'node_modules/**',
      '.next/**',
      'out/**',
      'coverage/**',
      'next-env.d.ts',
    ],
  },
  // Spread the native flat config arrays. If your installed version uses
  // a different export shape (array vs single object), wrap in an array:
  // ...[nextCoreWebVitals].flat(), ...[nextTypescript].flat()
  ...(Array.isArray(nextCoreWebVitals)
    ? nextCoreWebVitals
    : [nextCoreWebVitals]),
  ...(Array.isArray(nextTypescript) ? nextTypescript : [nextTypescript]),
];

export default eslintConfig;
