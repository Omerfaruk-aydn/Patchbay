"use client";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function LoginPage() {
  return (
    <div
      className="flex min-h-screen items-center justify-center"
      style={{ backgroundColor: "var(--bg-base)" }}
    >
      <div
        className="w-full max-w-md space-y-6 rounded-lg border p-8"
        style={{
          backgroundColor: "var(--bg-elevated-1)",
          borderColor: "var(--border-subtle)",
          boxShadow: "var(--shadow-md)",
        }}
      >
        <div className="text-center">
          <div
            className="mx-auto flex h-12 w-12 items-center justify-center rounded-lg text-lg font-bold"
            style={{ backgroundColor: "var(--accent-blue)", color: "var(--bg-base)" }}
          >
            P
          </div>
          <h1
            className="mt-4 text-2xl font-bold"
            style={{ color: "var(--text-primary)" }}
          >
            Patchbay
          </h1>
          <p
            className="mt-1 text-sm"
            style={{ color: "var(--text-secondary)" }}
          >
            Sign in to your gateway
          </p>
        </div>

        <form className="space-y-4">
          <div className="space-y-2">
            <label
              className="text-sm font-medium"
              style={{ color: "var(--text-secondary)" }}
            >
              Email
            </label>
            <Input type="email" placeholder="you@example.com" />
          </div>
          <div className="space-y-2">
            <label
              className="text-sm font-medium"
              style={{ color: "var(--text-secondary)" }}
            >
              Password
            </label>
            <Input type="password" placeholder="••••••••" />
          </div>
          <Button className="w-full" type="submit">
            Sign In
          </Button>
        </form>
      </div>
    </div>
  );
}
