"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, UserCircle } from "lucide-react";
import type { UserProfile as UserProfileType } from "@/lib/types";

interface UserProfileProps {
  profile: UserProfileType;
  onChange: (profile: UserProfileType) => void;
}

const INCOME_RANGES = ["", "<5L", "5-10L", "10-20L", "20-50L", "50L+", "1Cr+"];
const TAXPAYER_TYPES = ["", "Salaried", "Self-employed", "Freelancer", "Business Owner", "NRI"];
const AGE_GROUPS = ["", "Below 60", "60-80", "Above 80"];
const REGIMES = ["", "New", "Old", "Not sure"];

export function UserProfilePanel({ profile, onChange }: UserProfileProps) {
  const [expanded, setExpanded] = useState(false);

  const hasProfile = profile.income_range || profile.taxpayer_type || profile.age_group || profile.regime;

  return (
    <div className="mb-2">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 text-xs text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition-colors px-1 py-1"
      >
        <UserCircle className="w-3.5 h-3.5" />
        <span>{hasProfile ? "Your profile (active)" : "Set your profile for better advice"}</span>
        {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
      </button>

      {expanded && (
        <div className="mt-2 p-3 border border-[var(--border)] rounded-lg bg-[var(--card)] animate-fade-in-up grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div>
            <label className="block text-[10px] font-medium text-[var(--muted-foreground)] mb-1 uppercase tracking-wider">
              Income
            </label>
            <select
              value={profile.income_range || ""}
              onChange={(e) => onChange({ ...profile, income_range: e.target.value || undefined })}
              className="w-full text-xs px-2 py-1.5 border border-[var(--border)] rounded-md bg-[var(--background)] focus:ring-1 focus:ring-[var(--ring)] focus:border-[var(--primary)] outline-none transition-all"
            >
              {INCOME_RANGES.map((r) => (
                <option key={r} value={r}>{r || "Select..."}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-[10px] font-medium text-[var(--muted-foreground)] mb-1 uppercase tracking-wider">
              Type
            </label>
            <select
              value={profile.taxpayer_type || ""}
              onChange={(e) => onChange({ ...profile, taxpayer_type: e.target.value || undefined })}
              className="w-full text-xs px-2 py-1.5 border border-[var(--border)] rounded-md bg-[var(--background)] focus:ring-1 focus:ring-[var(--ring)] focus:border-[var(--primary)] outline-none transition-all"
            >
              {TAXPAYER_TYPES.map((t) => (
                <option key={t} value={t}>{t || "Select..."}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-[10px] font-medium text-[var(--muted-foreground)] mb-1 uppercase tracking-wider">
              Age
            </label>
            <select
              value={profile.age_group || ""}
              onChange={(e) => onChange({ ...profile, age_group: e.target.value || undefined })}
              className="w-full text-xs px-2 py-1.5 border border-[var(--border)] rounded-md bg-[var(--background)] focus:ring-1 focus:ring-[var(--ring)] focus:border-[var(--primary)] outline-none transition-all"
            >
              {AGE_GROUPS.map((a) => (
                <option key={a} value={a}>{a || "Select..."}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-[10px] font-medium text-[var(--muted-foreground)] mb-1 uppercase tracking-wider">
              Regime
            </label>
            <select
              value={profile.regime || ""}
              onChange={(e) => onChange({ ...profile, regime: e.target.value || undefined })}
              className="w-full text-xs px-2 py-1.5 border border-[var(--border)] rounded-md bg-[var(--background)] focus:ring-1 focus:ring-[var(--ring)] focus:border-[var(--primary)] outline-none transition-all"
            >
              {REGIMES.map((r) => (
                <option key={r} value={r}>{r || "Select..."}</option>
              ))}
            </select>
          </div>
        </div>
      )}
    </div>
  );
}
