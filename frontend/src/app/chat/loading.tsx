export default function ChatLoading() {
  return (
    <div className="flex flex-col h-[calc(100vh-3.5rem)]">
      <div className="flex-1 px-6 py-4">
        <div className="max-w-3xl mx-auto space-y-6">
          {/* Skeleton message bubbles */}
          {[...Array(3)].map((_, i) => (
            <div
              key={i}
              className={`flex gap-3 ${i % 2 === 0 ? "" : "justify-end"}`}
            >
              {i % 2 === 0 && (
                <div className="w-8 h-8 rounded-full animate-shimmer flex-shrink-0" />
              )}
              <div
                className={`rounded-2xl animate-shimmer ${
                  i % 2 === 0 ? "w-3/4 h-24" : "w-1/2 h-12"
                }`}
              />
              {i % 2 !== 0 && (
                <div className="w-8 h-8 rounded-full animate-shimmer flex-shrink-0" />
              )}
            </div>
          ))}
        </div>
      </div>
      <div className="border-t border-[var(--border)] p-4">
        <div className="max-w-3xl mx-auto">
          <div className="h-12 rounded-xl animate-shimmer" />
        </div>
      </div>
    </div>
  );
}
