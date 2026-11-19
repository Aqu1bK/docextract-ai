import type { ReactNode } from 'react';
import { DemoModeBanner } from './demo-mode-banner';
import { Sidebar } from './sidebar';
import { Topbar } from './topbar';

/**
 * The frame for every authenticated screen: banner (conditional) →
 * sidebar + content column → topbar + scrolling content.
 *
 * The DemoModeBanner sits in the flow above everything, so when it renders,
 * the entire app below it shifts down 32px structurally — no fixed
 * positioning, no compensating padding, nothing to keep in sync.
 */
export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-dvh flex-col bg-paper text-ink">
      <DemoModeBanner />

      <div className="flex min-h-0 flex-1">
        <Sidebar />

        <div className="flex min-w-0 flex-1 flex-col">
          <Topbar />

          <main className="flex-1 overflow-y-auto p-6">
            {/* 24px breathing room; a single 1400px reading/measurement
                column, centered — wide tables cap instead of stretching
                to fill a 4K monitor. */}
            <div className="mx-auto w-full max-w-[1400px]">{children}</div>
          </main>
        </div>
      </div>
    </div>
  );
}
