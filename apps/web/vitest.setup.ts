import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';

/**
 * Two jobs:
 *  1. jest-dom matchers (toBeInTheDocument, toBeEmptyDOMElement, ...)
 *     registered on vitest's `expect`.
 *  2. Explicit DOM cleanup after every test. RTL's auto-cleanup only
 *     engages when test-framework globals are enabled; this project uses
 *     explicit imports, so cleanup is wired here instead. Without it,
 *     queries in test 2 can match nodes left behind by test 1.
 */
afterEach(cleanup);
