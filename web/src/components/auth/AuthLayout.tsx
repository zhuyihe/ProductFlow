import type { ReactNode } from "react";

import { AuthBackground } from "./AuthBackground";
import { AuthBrand } from "./AuthBrand";
import { AuthFooter } from "./AuthFooter";

interface AuthLayoutProps {
  children: ReactNode;
  footer?: ReactNode;
  /**
   * Render the brand block by default. Pass false to suppress it when an
   * inner page already owns the brand placement (e.g. error pages with a
   * tighter hero).
   */
  showBrand?: boolean;
}

export function AuthLayout({ children, footer, showBrand = true }: AuthLayoutProps) {
  return (
    <div className="relative flex min-h-screen items-center justify-center bg-zinc-50 dark:bg-[#060a12] dark:text-slate-100">
      <AuthBackground />
      <div className="relative w-full max-w-md px-6">
        {showBrand ? <AuthBrand /> : null}
        {children}
        {footer ?? <AuthFooter />}
      </div>
    </div>
  );
}
