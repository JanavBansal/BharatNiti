interface ConfidenceBadgeProps {
  confidence: "HIGH" | "MEDIUM" | "LOW";
}

const CONFIG = {
  HIGH: {
    label: "Clear statutory basis",
    bg: "bg-green-100 dark:bg-green-900/30",
    text: "text-green-800 dark:text-green-300",
    dot: "bg-green-500",
  },
  MEDIUM: {
    label: "Interpretation may vary",
    bg: "bg-yellow-100 dark:bg-yellow-900/30",
    text: "text-yellow-800 dark:text-yellow-300",
    dot: "bg-yellow-500",
  },
  LOW: {
    label: "Consult a CA",
    bg: "bg-red-100 dark:bg-red-900/30",
    text: "text-red-800 dark:text-red-300",
    dot: "bg-red-500",
  },
};

export function ConfidenceBadge({ confidence }: ConfidenceBadgeProps) {
  const config = CONFIG[confidence];
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${config.bg} ${config.text}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${config.dot}`} />
      {config.label}
    </span>
  );
}
