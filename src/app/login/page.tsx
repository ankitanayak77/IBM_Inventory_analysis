import { Suspense } from "react";
import { LoginForm } from "@/components/LoginForm";

/**
 * useSearchParams() (used inside LoginForm, to read ?callbackUrl) requires
 * a Suspense boundary in a static/prerendered page — confirmed empirically
 * via `next build`, which fails outright without one
 * ("useSearchParams() should be wrapped in a suspense boundary").
 */
export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginForm />
    </Suspense>
  );
}
