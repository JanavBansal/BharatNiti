import { Calculator, Scale, FileText, IndianRupee, ArrowRightLeft, HelpCircle } from "lucide-react";

interface QuestionCategory {
  icon: React.ReactNode;
  label: string;
  color: string;
  questions: string[];
}

const CATEGORIES: QuestionCategory[] = [
  {
    icon: <Calculator className="w-4 h-4" />,
    label: "Tax Calculation",
    color: "text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-950/50 border-blue-200 dark:border-blue-800",
    questions: [
      "How much tax do I pay on 15 lakh income?",
      "Calculate tax on 50 lakh salary",
      "Tax on 1 crore income under new regime",
    ],
  },
  {
    icon: <ArrowRightLeft className="w-4 h-4" />,
    label: "Compare Regimes",
    color: "text-purple-600 dark:text-purple-400 bg-purple-50 dark:bg-purple-950/50 border-purple-200 dark:border-purple-800",
    questions: [
      "Old vs new regime for 20 lakh income",
      "Which tax regime is better for salaried employees?",
      "Compare old and new regime for 8 lakh",
    ],
  },
  {
    icon: <FileText className="w-4 h-4" />,
    label: "Deductions & Exemptions",
    color: "text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-950/50 border-green-200 dark:border-green-800",
    questions: [
      "What deductions can I claim under Section 80C?",
      "Can I claim HRA exemption under the new regime?",
      "What is the limit for 80D medical insurance deduction?",
    ],
  },
  {
    icon: <IndianRupee className="w-4 h-4" />,
    label: "TDS & GST Rates",
    color: "text-orange-600 dark:text-orange-400 bg-orange-50 dark:bg-orange-950/50 border-orange-200 dark:border-orange-800",
    questions: [
      "TDS rate on rent payment above 50,000",
      "What is the GST rate for restaurant services?",
      "TDS rate under Section 194J for professional fees",
    ],
  },
  {
    icon: <Scale className="w-4 h-4" />,
    label: "Capital Gains",
    color: "text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950/50 border-red-200 dark:border-red-800",
    questions: [
      "How is LTCG on equity shares taxed?",
      "What is the indexation benefit for property sale?",
      "Short-term capital gains tax rate on mutual funds",
    ],
  },
  {
    icon: <HelpCircle className="w-4 h-4" />,
    label: "Filing & Compliance",
    color: "text-teal-600 dark:text-teal-400 bg-teal-50 dark:bg-teal-950/50 border-teal-200 dark:border-teal-800",
    questions: [
      "What is the due date for filing ITR?",
      "Penalty for late filing of income tax return",
      "What are the changes in Budget 2025?",
    ],
  },
];

interface SuggestedQuestionsProps {
  onSelect: (question: string) => void;
}

export function SuggestedQuestions({ onSelect }: SuggestedQuestionsProps) {
  return (
    <div className="py-8 max-w-3xl mx-auto">
      <div className="text-center mb-8 animate-fade-in-up">
        <h2 className="text-2xl font-bold mb-2">
          Ask anything about Indian Tax Law
        </h2>
        <p className="text-sm text-[var(--muted-foreground)]">
          Get instant answers with citations from the Income Tax Act, GST Act, Finance Act & more.
          Click any question below or type your own.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {CATEGORIES.map((cat, ci) => (
          <div
            key={cat.label}
            className="space-y-2 animate-fade-in-up"
            style={{ animationDelay: `${ci * 80}ms` }}
          >
            <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${cat.color}`}>
              {cat.icon}
              {cat.label}
            </div>

            <div className="space-y-1.5">
              {cat.questions.map((q) => (
                <button
                  key={q}
                  onClick={() => onSelect(q)}
                  className="w-full text-left text-sm px-3 py-2.5 rounded-lg border border-[var(--border)] hover:bg-[var(--accent)] hover:border-[var(--primary)] hover:translate-x-0.5 transition-all duration-150 cursor-pointer leading-snug"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>

      <p className="text-center text-xs text-[var(--muted-foreground)] mt-6">
        You can ask in any format — plain English, Hinglish, or just a number like &quot;tax on 50 lakh&quot;
      </p>
    </div>
  );
}
