"use client";

import { useState } from "react";
import { lookupTDSRate, lookupGSTRate, calculateIncomeTax } from "@/lib/api/client";
import type { SlabResult } from "@/lib/types";

type Tab = "tds" | "gst" | "income-tax";

export default function RatesPage() {
  const [activeTab, setActiveTab] = useState<Tab>("tds");
  const [tdsResults, setTdsResults] = useState<Record<string, unknown>[]>([]);
  const [gstResults, setGstResults] = useState<Record<string, unknown>[]>([]);
  const [taxCalc, setTaxCalc] = useState<SlabResult | null>(null);
  const [income, setIncome] = useState("");
  const [regime, setRegime] = useState("new");
  const [loading, setLoading] = useState(false);

  const fetchTDS = async () => {
    setLoading(true);
    const data = await lookupTDSRate();
    setTdsResults(data.results);
    setLoading(false);
  };

  const fetchGST = async () => {
    setLoading(true);
    const data = await lookupGSTRate();
    setGstResults(data.results);
    setLoading(false);
  };

  const calcTax = async () => {
    if (!income) return;
    setLoading(true);
    const data = await calculateIncomeTax(Number(income), regime);
    setTaxCalc(data);
    setLoading(false);
  };

  return (
    <main className="max-w-4xl mx-auto px-6 py-8">
      <h1 className="text-2xl font-bold mb-6">Tax Rate Lookup</h1>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-[var(--border)] mb-6">
        {(["tds", "gst", "income-tax"] as Tab[]).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab
                ? "border-[var(--primary)] text-[var(--primary)]"
                : "border-transparent text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
            }`}
          >
            {tab.toUpperCase()}
          </button>
        ))}
      </div>

      {/* TDS Tab */}
      {activeTab === "tds" && (
        <div>
          <button
            onClick={fetchTDS}
            disabled={loading}
            className="mb-4 px-4 py-2 text-sm rounded-lg bg-[var(--primary)] text-white disabled:opacity-50"
          >
            {loading ? "Loading..." : "Load TDS Rates"}
          </button>
          {tdsResults.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm border border-[var(--border)]">
                <thead className="bg-[var(--muted)]">
                  <tr>
                    <th className="px-3 py-2 text-left">Section</th>
                    <th className="px-3 py-2 text-left">Category</th>
                    <th className="px-3 py-2 text-right">Rate (%)</th>
                    <th className="px-3 py-2 text-right">Threshold</th>
                    <th className="px-3 py-2 text-left">Notes</th>
                  </tr>
                </thead>
                <tbody>
                  {tdsResults.map((r, i) => (
                    <tr key={i} className="border-t border-[var(--border)]">
                      <td className="px-3 py-2 font-mono">{String(r.section || "-")}</td>
                      <td className="px-3 py-2">{String(r.category || "")}</td>
                      <td className="px-3 py-2 text-right">{String(r.rate || "")}</td>
                      <td className="px-3 py-2 text-right">
                        {r.threshold ? `₹${Number(r.threshold).toLocaleString("en-IN")}` : "-"}
                      </td>
                      <td className="px-3 py-2 text-[var(--muted-foreground)]">{String(r.notes || "")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* GST Tab */}
      {activeTab === "gst" && (
        <div>
          <button
            onClick={fetchGST}
            disabled={loading}
            className="mb-4 px-4 py-2 text-sm rounded-lg bg-[var(--primary)] text-white disabled:opacity-50"
          >
            {loading ? "Loading..." : "Load GST Rates"}
          </button>
          {gstResults.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm border border-[var(--border)]">
                <thead className="bg-[var(--muted)]">
                  <tr>
                    <th className="px-3 py-2 text-left">Category</th>
                    <th className="px-3 py-2 text-right">Rate (%)</th>
                    <th className="px-3 py-2 text-left">Notes</th>
                  </tr>
                </thead>
                <tbody>
                  {gstResults.map((r, i) => (
                    <tr key={i} className="border-t border-[var(--border)]">
                      <td className="px-3 py-2">{String(r.category || "")}</td>
                      <td className="px-3 py-2 text-right">{String(r.rate || "")}</td>
                      <td className="px-3 py-2 text-[var(--muted-foreground)]">{String(r.notes || "")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Income Tax Tab */}
      {activeTab === "income-tax" && (
        <div>
          <div className="flex gap-4 items-end mb-4">
            <div>
              <label className="block text-xs text-[var(--muted-foreground)] mb-1">
                Annual Income (₹)
              </label>
              <input
                type="number"
                value={income}
                onChange={(e) => setIncome(e.target.value)}
                placeholder="e.g. 1500000"
                className="px-3 py-2 border border-[var(--border)] rounded-lg text-sm bg-[var(--card)]"
              />
            </div>
            <div>
              <label className="block text-xs text-[var(--muted-foreground)] mb-1">
                Regime
              </label>
              <select
                value={regime}
                onChange={(e) => setRegime(e.target.value)}
                className="px-3 py-2 border border-[var(--border)] rounded-lg text-sm bg-[var(--card)]"
              >
                <option value="new">New Regime</option>
                <option value="old">Old Regime</option>
              </select>
            </div>
            <button
              onClick={calcTax}
              disabled={loading || !income}
              className="px-4 py-2 text-sm rounded-lg bg-[var(--primary)] text-white disabled:opacity-50"
            >
              {loading ? "Calculating..." : "Calculate"}
            </button>
          </div>

          {taxCalc && (
            <div className="border border-[var(--border)] rounded-xl p-6">
              <h3 className="font-semibold mb-4">
                Tax Calculation — {taxCalc.regime.toUpperCase()} Regime (AY{" "}
                {taxCalc.assessment_year})
              </h3>
              <table className="w-full text-sm mb-4">
                <thead className="bg-[var(--muted)]">
                  <tr>
                    <th className="px-3 py-2 text-left">Slab</th>
                    <th className="px-3 py-2 text-right">Rate</th>
                    <th className="px-3 py-2 text-right">Taxable Amount</th>
                    <th className="px-3 py-2 text-right">Tax</th>
                  </tr>
                </thead>
                <tbody>
                  {taxCalc.slabs.map((slab, i) => (
                    <tr key={i} className="border-t border-[var(--border)]">
                      <td className="px-3 py-2">{slab.range}</td>
                      <td className="px-3 py-2 text-right">{slab.rate}%</td>
                      <td className="px-3 py-2 text-right">
                        ₹{slab.taxable_amount.toLocaleString("en-IN")}
                      </td>
                      <td className="px-3 py-2 text-right">
                        ₹{slab.tax.toLocaleString("en-IN")}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="space-y-1 text-sm border-t border-[var(--border)] pt-3">
                <div className="flex justify-between">
                  <span>Total Tax</span>
                  <span>₹{taxCalc.total_tax.toLocaleString("en-IN")}</span>
                </div>
                {taxCalc.rebate_87a > 0 && (
                  <div className="flex justify-between text-green-600">
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
