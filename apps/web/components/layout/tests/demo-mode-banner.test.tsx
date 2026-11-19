import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { DemoModeBanner } from '../demo-mode-banner';

/**
 * The banner reads exactly one thing: env.NEXT_PUBLIC_DEMO_MODE from the
 * '@/lib/env' module. Mocking the module — rather than poking process.env —
 * pins two contracts at once:
 *   1. the component consumes the validated env object, never raw
 *      process.env;
 *   2. tests can flip the flag per case without re-importing the module
 *      graph (env parses once, at module load).
 *
 * vi.hoisted runs before vitest's hoisted vi.mock, so the factory can
 * safely reference mockEnv.
 */
const mockEnv = vi.hoisted(() => ({
  NEXT_PUBLIC_DEMO_MODE: 'false' as 'true' | 'false',
}));

vi.mock('@/lib/env', () => ({ env: mockEnv }));

describe('DemoModeBanner', () => {
  it('renders nothing when demo mode is off', () => {
    mockEnv.NEXT_PUBLIC_DEMO_MODE = 'false';
    const { container } = render(<DemoModeBanner />);
    expect(container).toBeEmptyDOMElement();
  });

  it('renders the demo notice with the exact copy when demo mode is on', () => {
    mockEnv.NEXT_PUBLIC_DEMO_MODE = 'true';
    render(<DemoModeBanner />);

    expect(
      screen.getByText(
        'Demo Mode — Extraction runs with simulated AI. No real data is processed.',
      ),
    ).toBeInTheDocument();

    // The explanation affordance is present and labelled.
    expect(
      screen.getByLabelText('What does demo mode mean?'),
    ).toBeInTheDocument();
  });
});
