"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Toaster } from "sonner";

import { AuthProvider } from "@/lib/auth/auth-context";
import { api } from "@/lib/api/client";
import { applyBrandSettings } from "@/lib/brand";
import { ThemeProvider } from "@/lib/theme";

export function Providers({ children }: { children: React.ReactNode }) {
  const [client] = useState(() => new QueryClient());

  useEffect(() => {
    // Apply after theme class may already be on <html>
    void api
      .brand()
      .then(applyBrandSettings)
      .catch(() => {
        /* brand defaults from CSS tokens */
      });
  }, []);

  return (
    <QueryClientProvider client={client}>
      <ThemeProvider>
        <AuthProvider>
          {children}
          <Toaster richColors position="top-center" />
        </AuthProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
