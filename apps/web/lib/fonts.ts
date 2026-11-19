import { Inter, JetBrains_Mono } from 'next/font/google';

/**
 * Inter — human interface text (labels, prose, table headers, buttons).
 * JetBrains Mono — machine-generated data (confidence scores, field keys,
 * hashes, document IDs). The mono face is a provenance signal: if text is
 * set in JetBrains Mono, a model produced it; if it is set in Inter, a
 * human wrote it for a human to read.
 *
 * Both attach CSS variables, not font-family values: app/layout.tsx puts
 * `${fontSans.variable} ${fontMono.variable}` on <html>, and globals.css
 * binds --font-sans / --font-mono to them via @theme inline.
 *
 * Self-hosted via next/font: no font request ever leaves the origin at
 * runtime, no layout shift after first paint (size-adjusted fallbacks).
 */
export const fontSans = Inter({
  subsets: ['latin'],
  weight: ['400', '500', '600'],
  variable: '--font-inter',
  display: 'swap',
});

export const fontMono = JetBrains_Mono({
  subsets: ['latin'],
  weight: ['400', '500'],
  variable: '--font-jetbrains-mono',
  display: 'swap',
});
