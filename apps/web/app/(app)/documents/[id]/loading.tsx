/**
 * Document detail loading skeleton — what renders while the route segment loads.
 *
 * The two-column shape the real view renders (PDF pane left, review
 * panel right) as muted blocks: the skeleton reserves the layout so
 * the real content lands without a jump. Row-shaped bars mirror the
 * field rows that will fill the right column.
 */
export default function DocumentDetailLoading() {
  return (
    <div className="space-y-6">
      <div>
        <div className="h-7 w-64 bg-paper-muted" />
        <div className="mt-2 h-4 w-44 bg-paper-muted" />
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <div className="h-96 border border-rule bg-paper-muted" aria-busy="true" />
        <div className="border border-rule bg-paper">
          {Array.from({ length: 4 }, (_, index) => (
            <div
              key={index}
              className="flex items-center gap-4 border-b border-rule px-3 py-4 last:border-b-0"
            >
              <div className="h-3 w-32 bg-paper-muted" />
              <div className="ml-auto h-3 w-20 bg-paper-muted" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}