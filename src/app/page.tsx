import { redirect } from "next/navigation";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth/authOptions";
import { loadAndClassifySampleData } from "@/lib/analytics/loadSampleData";
import { toStaffView } from "@/lib/auth/staffView";
import { DashboardShell } from "@/components/DashboardShell";

/**
 * Report FR-9 — page-level protection. getServerSession(authOptions) here
 * runs inside a real Server Component request, so next/headers's ambient
 * request-scope requirement is satisfied normally (unlike calling it from
 * a bare Vitest test — see lib/auth/session.ts's comment). Not relying on
 * middleware/proxy for this either, per the same CVE-2025-29927 reasoning
 * applied to every protected route in this app.
 *
 * Critically, the *initial* data passed to the client here must already
 * be role-restricted for a staff session — not just the API routes.
 * Passing the full AnalysisResult as this Server Component's props would
 * ship it to a staff browser regardless of what /api/analysis/summary
 * itself would return, defeating that restriction entirely.
 */
export default async function Home() {
  const session = await getServerSession(authOptions);
  if (!session?.user) {
    redirect("/login");
  }

  const sampleResult = loadAndClassifySampleData();
  const initialData = session.user.role === "staff" ? toStaffView(sampleResult, "sample dataset") : sampleResult;

  return (
    <DashboardShell
      initialData={initialData}
      userRole={session.user.role}
      userName={session.user.name ?? session.user.email ?? ""}
    />
  );
}
