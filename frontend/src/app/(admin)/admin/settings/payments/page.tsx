"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  api,
  type ApplicationFeeSettings,
  type GatewaySettings,
} from "@/lib/api/client";
import type { ApiError } from "@/lib/api/schema";
import { cn } from "@/lib/utils";

type Tab = "gateway" | "application-fees";

export default function PaymentSettingsPage() {
  const [tab, setTab] = useState<Tab>("gateway");
  const [gateway, setGateway] = useState<GatewaySettings | null>(null);
  const [fees, setFees] = useState<ApplicationFeeSettings | null>(null);
  const [publicKey, setPublicKey] = useState("");
  const [secretKey, setSecretKey] = useState("");
  const [naira, setNaira] = useState("5000");

  async function load() {
    const [g, f] = await Promise.all([
      api.getGatewaySettings(),
      api.getApplicationFeeSettings(),
    ]);
    setGateway(g);
    setFees(f);
    setNaira(String(f.default_amount_naira));
  }

  useEffect(() => {
    void load().catch((err: ApiError) => toast.error(err.message));
  }, []);

  async function saveGateway() {
    try {
      const body: Record<string, unknown> = {
        mode: gateway?.mode ?? "test",
        channels: gateway?.channels,
        default_currency: gateway?.default_currency ?? "NGN",
      };
      if (publicKey.trim()) body.public_key = publicKey.trim();
      if (secretKey.trim()) body.secret_key = secretKey.trim();
      const updated = await api.updateGatewaySettings(body);
      setGateway(updated);
      setSecretKey("");
      toast.success("Gateway settings saved");
    } catch (err) {
      toast.error((err as ApiError).message);
    }
  }

  async function saveFees() {
    try {
      const updated = await api.updateApplicationFeeSettings({
        default_amount_naira: Number(naira),
        fee_required_before_admit: fees?.fee_required_before_admit ?? true,
        is_free: Number(naira) === 0,
        waiver_codes: fees?.waiver_codes ?? [],
        refundable_policy: fees?.refundable_policy ?? {},
      });
      setFees(updated);
      toast.success("Application fees saved");
    } catch (err) {
      toast.error((err as ApiError).message);
    }
  }

  async function testWebhook() {
    try {
      const res = await api.testPaymentWebhook();
      toast.message(res.message);
      await load();
    } catch (err) {
      toast.error((err as ApiError).message);
    }
  }

  const tabs: { id: Tab; label: string }[] = [
    { id: "gateway", label: "Gateway" },
    { id: "application-fees", label: "Application fees" },
  ];

  return (
    <>
      <PageHeader
        title="Payment configuration"
        description="Paystack gateway and application fee defaults. Class fees land in M5."
      />
      {gateway?.mode === "test" ? (
        <div className="mb-4 rounded-lg border border-[var(--warning)]/40 bg-[var(--warning)]/10 px-4 py-3 text-sm">
          Test mode is on — no live charges.
        </div>
      ) : null}

      <div className="mb-6 flex flex-col gap-2 md:flex-row">
        {tabs.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={cn(
              "min-h-11 rounded-lg px-4 text-left text-sm md:text-center",
              tab === t.id
                ? "bg-[var(--primary)] text-[var(--primary-foreground)]"
                : "bg-[var(--muted)] text-[var(--foreground)]",
            )}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "gateway" && gateway ? (
        <Card>
          <CardHeader>
            <CardTitle className="font-display text-xl">Gateway</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap gap-2">
              <Badge>{gateway.mode}</Badge>
              <Badge className="bg-[var(--muted)]">
                Public key {gateway.public_key_set ? gateway.public_key_masked : "not set"}
              </Badge>
              <Badge className="bg-[var(--muted)]">
                Secret {gateway.secret_key_set ? "set" : "not set"}
              </Badge>
            </div>
            <div className="space-y-2">
              <Label>Mode</Label>
              <select
                className="h-11 w-full rounded-[10px] border bg-[var(--card)] px-3"
                value={gateway.mode}
                onChange={(e) =>
                  setGateway({ ...gateway, mode: e.target.value as "test" | "live" })
                }
              >
                <option value="test">Test</option>
                <option value="live">Live</option>
              </select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="pk">Public key</Label>
              <Input
                id="pk"
                value={publicKey}
                onChange={(e) => setPublicKey(e.target.value)}
                placeholder="pk_test_…"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="sk">Secret key (write-only)</Label>
              <Input
                id="sk"
                type="password"
                value={secretKey}
                onChange={(e) => setSecretKey(e.target.value)}
                placeholder="sk_test_… (never returned)"
              />
            </div>
            <div className="space-y-2">
              <Label>Webhook URL</Label>
              <Input readOnly value={gateway.webhook_url} />
            </div>
            <div className="grid gap-2 sm:grid-cols-2">
              {(
                [
                  ["card", "Card"],
                  ["bank", "Bank"],
                  ["ussd", "USSD"],
                  ["transfer", "Transfer"],
                  ["mobile_money", "Mobile money"],
                ] as const
              ).map(([key, label]) => (
                <label key={key} className="flex min-h-11 items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={gateway.channels[key]}
                    onChange={(e) =>
                      setGateway({
                        ...gateway,
                        channels: { ...gateway.channels, [key]: e.target.checked },
                      })
                    }
                  />
                  {label}
                </label>
              ))}
            </div>
            <div className="flex flex-wrap gap-2">
              <Button onClick={() => void saveGateway()}>Save gateway</Button>
              <Button variant="outline" onClick={() => void testWebhook()}>
                Send test event
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : null}

      {tab === "application-fees" && fees ? (
        <Card>
          <CardHeader>
            <CardTitle className="font-display text-xl">Application fees</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="naira">Default fee (₦)</Label>
              <Input
                id="naira"
                type="number"
                min={0}
                value={naira}
                onChange={(e) => setNaira(e.target.value)}
              />
              <p className="text-xs text-[var(--muted-foreground)]">
                Stored as {Math.round(Number(naira || 0) * 100)} kobo
              </p>
            </div>
            <label className="flex min-h-11 items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={fees.fee_required_before_admit}
                onChange={(e) =>
                  setFees({ ...fees, fee_required_before_admit: e.target.checked })
                }
              />
              Require paid fee before admit
            </label>
            <Button onClick={() => void saveFees()}>Save application fees</Button>
          </CardContent>
        </Card>
      ) : null}
    </>
  );
}
