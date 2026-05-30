"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { SignInPanel } from "@/components/SignInPanel";
import { type AuthConfig, getAuthConfig, getMe } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [authConfig, setAuthConfig] = useState<AuthConfig | null>(null);

  useEffect(() => {
    getMe().then((me) => {
      if (me.authenticated) router.replace("/");
    });
    getAuthConfig().then(setAuthConfig).catch(() => setAuthConfig(null));
  }, [router]);

  return (
    <SignInPanel
      authConfig={authConfig}
      authError={null}
      backendUp={null}
      onSignedIn={() => router.replace("/")}
    />
  );
}
