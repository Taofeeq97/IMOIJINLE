"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { toast } from "sonner";

import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api/client";
import type { ApiError } from "@/lib/api/schema";
import { useAuth } from "@/lib/auth/auth-context";

function CallbackInner() {
  const search = useSearchParams();
  const router = useRouter();
  const { user, loading } = useAuth();
  const reference = search.get("reference") ?? "";
  const [message, setMessage] = useState("Confirming payment…");

  useEffect(() => {
    if (loading) return;
    if (!user) {
      router.replace("/login");
      return;
    }
    if (!reference) {
      setMessage("Missing payment reference.");
      return;
    }
    void (async () => {
      try {
        const status = await api.paymentStatus(reference);
        if (status.status === "success") {
          setMessage("Payment confirmed. Redirecting to your application…");
          toast.success("Payment successful");
          setTimeout(() => router.push("/portal"), 1200);
        } else {
          setMessage(`Payment status: ${status.status}. Waiting for Paystack webhook/verify…`);
        }
      } catch (err) {
        setMessage((err as ApiError).message ?? "Could not confirm payment");
        toast.error((err as ApiError).message ?? "Payment confirmation failed");
      }
    })();
  }, [reference, user, loading, router]);

  return (
    <div className="mx-auto max-w-lg px-4 py-16 text-center">
      <PageHeader title="Payment" description={message} />
      <Button asChild variant="outline">
        <Link href="/portal">Back to portal</Link>
      </Button>
    </div>
  );
}

export default function PaymentCallbackPage() {
  return (
    <Suspense fallback={<p className="p-8 text-sm">Confirming…</p>}>
      <CallbackInner />
    </Suspense>
  );
}
