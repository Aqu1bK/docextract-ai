import type { Metadata } from 'next';

import { DocumentDetailView } from '@/components/documents/document-detail-view';

/**
 * Document detail page — the review surface's route.
 *
 * A server component shell (metadata + route) around the client view
 * that orchestrates the live data. The (app) layout above this page has
 * already authenticated the visitor; this page carries no auth logic
 * of its own. Next 16's dynamic `params` arrive as a Promise and are
 * awaited here — the page-level contract for dynamic routes.
 */
export const metadata: Metadata = {
  title: 'Document review — DocExtract AI',
};

export default async function DocumentDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <DocumentDetailView documentId={id} />;
}