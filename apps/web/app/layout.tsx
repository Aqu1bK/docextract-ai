import type { Metadata } from 'next';
import { fontMono, fontSans } from '@/lib/fonts';
import './globals.css';

export const metadata: Metadata = {
  title: {
    default: 'DocExtract AI',
    template: '%s — DocExtract AI',
  },
  description:
    'Document extraction with a human decision on every field. Upload, review, correct, and export candidate data with a full audit trail.',
};

/**
 * Root layout for the whole app.
 *
 * Both font variables must attach here: --font-inter for the sans stack
 * and --font-jetbrains-mono for the mono stack (globals.css binds both
 * via @theme inline — either variable missing and that whole type family
 * silently falls back to the generic stack).
 *
 * `theme-light` is a static marker class, not a toggle. There is no theme
 * provider, no `dark` class, and therefore no suppressHydrationWarning:
 * nothing ever mutates this element after hydration.
 */
export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${fontSans.variable} ${fontMono.variable} theme-light`}
    >
      <body>{children}</body>
    </html>
  );
}
