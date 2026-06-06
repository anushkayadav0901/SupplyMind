import type React from "react";
import { Shell } from "@/components/layout/shell";

export default function AppLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return <Shell>{children}</Shell>;
}
