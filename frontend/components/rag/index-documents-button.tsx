"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { DatabaseZap } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";

export function IndexDocumentsButton() {
  const router = useRouter();
  const [status, setStatus] = useState<string | null>(null);
  const [isIndexing, setIsIndexing] = useState(false);

  async function handleClick() {
    setIsIndexing(true);
    setStatus(null);

    try {
      const response = await api.indexDocuments();
      setStatus(response.message);
      router.refresh();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Indexing failed.");
    } finally {
      setIsIndexing(false);
    }
  }

  return (
    <div className="flex flex-col items-start gap-2 sm:items-end">
      <Button type="button" onClick={handleClick} disabled={isIndexing}>
        <DatabaseZap className="size-4" />
        {isIndexing ? "Indexing" : "Index documents"}
      </Button>
      {status ? <p className="max-w-80 text-xs text-muted-foreground">{status}</p> : null}
    </div>
  );
}
