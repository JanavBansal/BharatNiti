export default function RatesLoading() {
  return (
    <main className="max-w-4xl mx-auto px-6 py-8">
      <div className="h-8 w-48 rounded animate-shimmer mb-6" />
      <div className="flex gap-4 mb-6">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="h-8 w-24 rounded animate-shimmer" />
        ))}
      </div>
      <div className="space-y-2">
        {[...Array(8)].map((_, i) => (
          <div key={i} className="flex gap-3">
            {[...Array(4)].map((_, j) => (
              <div key={j} className="h-10 flex-1 rounded animate-shimmer" />
            ))}
          </div>
        ))}
      </div>
    </main>
  );
}
