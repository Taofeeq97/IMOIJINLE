"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { getAccessToken } from "@/lib/api/client";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function OidcSettingsPage() {
  const [form, setForm] = useState({
    enabled: false,
    issuer: "",
    client_id: "",
    client_secret: "",
    scopes: "openid profile email",
  });

  useEffect(() => {
    void fetch(`${API_URL}/api/v1/settings/oidc`, {
      headers: { Authorization: `Bearer ${getAccessToken() || ""}` },
      credentials: "include",
    })
      .then((r) => r.json())
      .then((d) =>
        setForm((f) => ({
          ...f,
          enabled: !!d.enabled,
          issuer: d.issuer || "",
          client_id: d.client_id || "",
          scopes: d.scopes || f.scopes,
        })),
      )
      .catch((e: Error) => toast.error(e.message));
  }, []);

  return (
    <>
      <PageHeader
        title="SSO / OIDC"
        description="Phase 4 readiness — configure issuer and client to enable login redirect. Disabled by default."
      />
      <form
        className="max-w-lg space-y-3"
        onSubmit={(e) => {
          e.preventDefault();
          void fetch(`${API_URL}/api/v1/settings/oidc`, {
            method: "PUT",
            headers: {
              Authorization: `Bearer ${getAccessToken() || ""}`,
              "Content-Type": "application/json",
            },
            credentials: "include",
            body: JSON.stringify(form),
          })
            .then(async (r) => {
              if (!r.ok) throw new Error("Save failed");
              toast.success("OIDC settings saved");
            })
            .catch((err: Error) => toast.error(err.message));
        }}
      >
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={form.enabled}
            onChange={(e) => setForm({ ...form, enabled: e.target.checked })}
          />
          Enable OIDC
        </label>
        <Input placeholder="Issuer URL" value={form.issuer} onChange={(e) => setForm({ ...form, issuer: e.target.value })} />
        <Input
          placeholder="Client ID"
          value={form.client_id}
          onChange={(e) => setForm({ ...form, client_id: e.target.value })}
        />
        <Input
          placeholder="Client secret"
          type="password"
          value={form.client_secret}
          onChange={(e) => setForm({ ...form, client_secret: e.target.value })}
        />
        <Input placeholder="Scopes" value={form.scopes} onChange={(e) => setForm({ ...form, scopes: e.target.value })} />
        <Button type="submit">Save</Button>
      </form>
    </>
  );
}
