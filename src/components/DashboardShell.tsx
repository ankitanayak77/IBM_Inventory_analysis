"use client";

import { useState } from "react";
import type { AnalysisResult } from "@/lib/analytics/analyze";
import type { StaffTaskListView } from "@/lib/auth/staffView";
import type { ClassifiedSku } from "@/lib/analytics/types";
import type { UserRole } from "@/db/userRepository";
import { UploadForm } from "@/components/UploadForm";
import { Dashboard } from "@/components/Dashboard";
import { ExportControls } from "@/components/ExportControls";
import { HistoryPanel } from "@/components/HistoryPanel";
import { SignOutButton } from "@/components/SignOutButton";
import { StaffTaskList } from "@/components/StaffTaskList";
import { NewlyAtRiskBanner } from "@/components/NewlyAtRiskBanner";

interface DashboardShellProps {
  initialData: AnalysisResult | StaffTaskListView;
  userRole: UserRole;
  userName: string;
}

/**
 * Report FR-9: branches by role at the top level, not with scattered
 * conditionals — a staff session renders StaffTaskList (read-only reorder
 * list, no upload/export/history — those are manager actions the API
 * layer 403s anyway; the UI doesn't offer buttons that would just fail).
 * An owner_manager session renders the full manager dashboard exactly as
 * before Phase 4 added auth.
 *
 * `initialData` is already role-restricted by the Server Component that
 * renders this (src/app/page.tsx) — never the full AnalysisResult for a
 * staff session, so there's no full data sitting in the client bundle to
 * begin with.
 */
export function DashboardShell({ initialData, userRole, userName }: DashboardShellProps) {
  if (userRole === "staff") {
    return <StaffTaskList data={initialData as StaffTaskListView} userName={userName} />;
  }

  return <ManagerDashboardShell sampleResult={initialData as AnalysisResult} userName={userName} />;
}

function ManagerDashboardShell({ sampleResult, userName }: { sampleResult: AnalysisResult; userName: string }) {
  const [current, setCurrent] = useState<AnalysisResult>(sampleResult);
  const [sourceLabel, setSourceLabel] = useState<string>("sample dataset");
  const [newlyAtRisk, setNewlyAtRisk] = useState<ClassifiedSku[]>([]);
  const [emailAlert, setEmailAlert] = useState<{ sent: boolean; skipReason?: string; error?: string } | null>(null);

  const isShowingUpload = sourceLabel !== "sample dataset";

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-[var(--color-navy)] text-white px-8 py-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Inventory Analysis</h1>
          <p className="text-sm text-slate-300 mt-1">
            {userName} · {current.rows.length} SKUs, {current.kpis.distinctProducts} product lines · source:{" "}
            {sourceLabel}
            {current.rejected.length > 0 && (
              <span className="ml-2 text-amber-300">· {current.rejected.length} row(s) rejected on load</span>
            )}
          </p>
        </div>
        <SignOutButton />
      </header>

      <main className="p-8 max-w-6xl mx-auto space-y-8">
        <UploadForm
          isShowingUpload={isShowingUpload}
          onResult={(result, fileName, alertSkus, emailStatus) => {
            setCurrent(result);
            setSourceLabel(fileName);
            setNewlyAtRisk(alertSkus ?? []);
            setEmailAlert(emailStatus);
          }}
          onReset={() => {
            setCurrent(sampleResult);
            setSourceLabel("sample dataset");
            setNewlyAtRisk([]);
            setEmailAlert(null);
          }}
        />

        <NewlyAtRiskBanner skus={newlyAtRisk} emailAlert={emailAlert} onDismiss={() => setNewlyAtRisk([])} />

        <ExportControls result={current} sourceLabel={sourceLabel} />

        <HistoryPanel
          onLoad={(result, label) => {
            setCurrent(result);
            setSourceLabel(label);
            setNewlyAtRisk([]);
          }}
        />

        <Dashboard result={current} sourceLabel={sourceLabel} />

        <footer className="text-xs text-slate-400 pb-8">
          Classification logic ported and numerically verified against the project report
          (Chapters 3–4) — see <code>src/lib/analytics/__tests__/classify.test.ts</code> and{" "}
          <code>src/app/api/upload/__tests__/route.test.ts</code>.
        </footer>
      </main>
    </div>
  );
}
