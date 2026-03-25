"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { lookupTDSRate, lookupGSTRate, calculateIncomeTax } from "@/lib/api/client";
import type { SlabResult } from "@/lib/types";
import { Loader2 } from "lucide-react";

type Tab = "tds" | "gst" | "income-tax";

const TAB_LABELS: Record<Tab, string> = {
  tds: "TDS Rates",
  gst: "GST Rates",
  "income-tax": "Income Tax",
};

const TABS: Tab[] = ["tds", "gst", "income-tax"];

function TableSkeleton({ cols }: { cols: number }) {
  return (
    <div className="space-y-2">
      {[...Array(5)].map((_, i) => (
        <div key={i} className="flex gap-3">
          {[...Array(cols)].map((_, j) => (
            <div key={j} className="h-8 flex-1 rounded animate-shimmer" />
          ))}
        </div>
      ))}
    </div>
  );
}

export default function RatesPage() {
  const [activeTab, setActiveTab] = useState<Tab>("tds");
  const [tdsResults, setTdsResults] = useState<Record<string, unknown>[]>([]);
  const [gstResults, setGstResults] = useState<Record<string, unknown>[]>([]);
  const [taxCalc, setTaxCalc] = useState<SlabResult | null>(null);
  const [income, setIncome] = useState("");
  const [regime, setRegime] = useState("new");
  const [loading, setLoading] = useState(false);
  const loadedTabs = useRef<Set<Tab>>(new Set());

  const fetchTDS = useCallback(async () => {
    if (loadedTabs.current.has("tds")) return;
    setLoading(true);
    try {
      const data = await lookupTDSRate();
      setTdsResults(data.results);
      loadedTabs.current.add("tds");
    } catch {}
    setLoading(false);
  }, []);

  const fetchGST = useCallback(async () => {
    if (loadedTabs.current.has("gst")) return;
    setLoading(true);
    try {
      const data = await lookupGSTRate();
      setGstResults(data.results);
      loadedTabs.current.add("gst");
    } catch {}
    setLoading(false);
  }, []);

  // Auto-load on tab switch
  useEffect(() => {
    if (activeTab === "tds") fetchTDS();
    else if (activeTab === "gst") fetchGST();
  }, [activeTab, fetchTDS, fetchGST]);

  const calcTax = async () => {
    if (!income) return;
    setLoading(true);
    try {
      const data = await calculateIncomeTax(Number(income), regime);
      setTaxCalc(data);
    } catch {}
    setLoading(false);
  };

  // Keyboard navigation for tabs
  const handleTabKeyDown = (e: React.KeyboardEvent, idx: number) => {
    let next = idx;
    if (e.key === "ArrowRight") next = (idx + 1) % TABS.length;
    else if (e.key === "ArrowLeft") next = (idx - 1 + TABS.length) % TABS.length;
    else return;
    e.preventDefault();
    setActiveTab(TABS[next]);
    (e.currentTarget.parentElement?.children[next] as HTMLElement)?.focus();
  };

  return (
    <main className="max-w-4xl mx-auto px-4 sm:px-6 py-8">
      <h1 className="text-2xl font-bold mb-6 animate-fade-in-up">Tax Rate Lookup</h1>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-[var(--border)] mb-6" role="tablist">
        {TABS.map((tab, idx) => (
          <button
            key={tab}
            role="tab"
            aria-selected={activeTab === tab}
            tabIndex={activeTab === tab ? 0 : -1}
            onClick={() => setActiveTab(tab)}
            onKeyDown={(e) => handleTabKeyDown(e, idx)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-all duration-200 ${
              activeTab === tab
                ? "border-[var(--primary)] text-[var(--primary)]"
                : "border-transparent text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
            }`}
          >
            {TAB_LABELS[tab]}
          </button>
        ))}
      </div>

      {/* TDS Tab */}
      {activeTab === "tds" && (
        <div className="animate-fade-in-up" style={{ animationDuration: "0.2s" }} role="tabpanel">
          {loading && tdsResults.length === 0 ? (
            <TableSkeleton cols={5} />
          ) : tdsResults.length > 0 ? (
            <div className="overflow-x-auto rounded-lg border border-[var(--border)]">
              <table className="w-full text-sm">
                <thead className="bg-[var(--muted)] sticky top-0 z-10">
                  <tr>
                    <th className="px-3 py-2.5 text-left font-semibold">Section</th>
                    <th className="px-3 py-2.5 text-left font-semibold">Category</th>
                    <th className="px-3 py-2.5 text-right font-semibold">Rate (%)</th>
                    <th className="px-3 py-2.5 text-right font-semibold">Threshold</th>
                    <th className="px-3 py-2.5 text-left font-semibold">Notes</th>
                  </tr>
                </thead>
                <tbody>
                  {tdsResults.map((r, i) => (
                    <tr key={i} className="border-t border-[var(--border)] hover:bg-[var(--accent)] transition-colors">
                      <td className="px-3 py-2 font-mono text-[var(--primary)]">{String(r.section || "-")}</td>
                      <td className="px-3 py-2">{String(r.category || "")}</td>
                      <td className="px-3 py-2 text-right font-medium">{String(r.rate || "")}</td>
                      <td className="px-3 py-2 text-right">
                        {r.threshold ? `₹${Number(r.threshold).toLocaleString("en-IN")}` : "-"}
                      </td>
                      <td className="px-3 py-2 text-[var(--muted-foreground)] text-xs">{String(r.notes || "")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </div>
      )}

      {/* GST Tab */}
      {activeTab === "gst" && (
        <div className="animate-fade-in-up" style={{ animationDuration: "0.2s" }} role="tabpanel">
          {loading && gstResults.length === 0 ? (
            <TableSkeleton cols={3} />
          ) : gstResults.length > 0 ? (
            <div className="overflow-x-auto rounded-lg border border-[var(--border)]">
              <table className="w-full text-sm">
                <thead className="bg-[var(--muted)] sticky top-0 z-10">
                  <tr>
                    <th className="px-3 py-2.5 text-left font-semibold">Category</th>
                    <th className="px-3 py-2.5 text-right font-semibold">Rate (%)</th>
                    <th className="px-3 py-2.5 text-left font-semibold">Notes</th>
                  </tr>
                </thead>
                <tbody>
                  {gstResults.map((r, i) => (
                    <tr key={i} className="border-t border-[var(--border)] hover:bg-[var(--accent)] transition-colors">
                      <td className="px-3 py-2">{String(r.category || "")}</td>
                      <td className="px-3 py-2 text-right font-medium">{String(r.rate || "")}</td>
                      <td className="px-3 py-2 text-[var(--muted-foreground)] text-xs">{String(r.notes || "")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </div>
      )}

      {/* Income Tax Tab */}
      {activeTab === "income-tax" && (
        <div className="animate-fade-in-up" style={{ animationDuration: "0.2s" }} role="tabpanel">
          <div className="border border-[var(--border)] rounded-xl p-4 sm:p-6 bg-[var(--card)] mb-6">
            <div className="flex flex-col sm:flex-row gap-3 sm:gap-4 sm:items-end">
              <div className="flex-1">
                <label htmlFor="income-input" className="block text-xs font-medium text-[var(--muted-foreground)] mb-1">
                  Annual Income (₹)
                </label>
                <input
                  id="income-input"
                  type="number"
                  value={income}
                  onChange={(e) => setIncome(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && calcTax()}
                  placeholder="e.g. 1500000"
                  min="0"
                  className="w-full px-3 py-2 border border-[var(--border)] rounded-lg text-sm bg-[var(--background)] focus:ring-2 focus:ring-[var(--ring)] focus:border-[var(--primary)] transition-all outline-none"
                />
              </div>
              <div>
                <label htmlFor="regime-select" className="block text-xs font-medium text-[var(--muted-foreground)] mb-1">
                  Regime
                </label>
                <select
                  id="regime-select"
                  value={regime}
                  onChange={(e) => setRegime(e.target.value)}
                  className="w-full px-3 py-2 border border-[var(--border)] rounded-lg text-sm bg-[var(--background)] focus:ring-2 focus:ring-[var(--ring)] focus:border-[var(--primary)] transition-all outline-none"
                >
                  <option value="new">New Regime</option>
                  <option value="old">Old Regime</option>
                </select>
              </div>
              <button
                onClick={calcTax}
                disabled={loading || !income}
                className="px-5 py-2 text-sm font-medium rounded-lg bg-gradient-to-r from-[var(--gradient-start)] to-[var(--gradient-end)] text-white disabled:opacity-40 hover:shadow-md hover:scale-[1.02] active:scale-[0.98] transition-all duration-150"
              >
                {loading ? <Loader2 className="w-4 h-4 animate-spin mx-auto" /> : "Calculate"}
              </button>
            </div>
          </div>

          {taxCalc && (
            <div className="border border-[var(--border)] rounded-xl p-4 sm:p-6 animate-fade-in-up">
              <h3 className="font-semibold mb-4">
                Tax Calculation — {taxCalc.regime === "new" ? "New" : "Old"} Regime (AY{" "}
                {taxCalc.assessment_year})
              </h3>
              <div className="overflow-x-auto rounded-lg border border-[var(--border)] mb-4">
                <table className="w-full text-sm">
                  <thead className="bg-[var(--muted)]">
                    <tr>
                      <th className="px-3 py-2.5 text-left font-semibold">Slab</th>
                      <th className="px-3 py-2.5 text-right font-semibold">Rate</th>
                      <th className="px-3 py-2.5 text-right font-semibold">Taxable Amount</th>
                      <th className="px-3 py-2.5 text-right font-semibold">Tax</th>
                    </tr>
                  </thead>
                  <tbody>
                    {taxCalc.slabs.map((slab, i) => (
                      <tr key={i} className="border-t border-[var(--border)] hover:bg-[var(--accent)] transition-colors">
                        <td className="px-3 py-2">{slab.range}</td>
                        <td className="px-3 py-2 text-right">{slab.rate}%</td>
                        <td className="px-3 py-2 text-right">
                          ₹{slab.taxable_amount.toLocaleString("en-IN")}
                        </td>
                        <td className="px-3 py-2 text-right font-medium">
                          ₹{slab.tax.toLocaleString("en-IN")}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="space-y-1.5 text-sm border-t border-[var(--border)] pt-3">
                <div className="flex justify-between">
                  <span>Total Tax</span>
                  <span>₹{taxCalc.total_tax.toLocaleString("en-IN")}</span>
                </div>
                {taxCalc.rebate_87a > 0 && (
                  <div className="flex justify-between text-[var(--success)]">
                    <span>Rebate u/s 87A</span>
                    <span>- ₹{taxCalc.rebate_87a.toLocaleString("en-IN")}</span>
                  </div>
                )}
                <div className="flex justify-between">
                  <span>Health & Education Cess (4%)</span>
                  <span>₹{taxCalc.cess.toLocaleString("en-IN")}</span>
                </div>
                <div className="flex justify-between font-bold text-base border-t border-[var(--border)] pt-2">
                  <span>Total Liability</span>
                  <span>₹{taxCalc.total_liability.toLocaleString("en-IN")}</span>
                </div>
                <div className="flex justify-between text-[var(--muted-foreground)]">
                  <span>Effective Rate</span>
                  <span>{taxCalc.effective_rate}%</span>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </main>
  );
}
