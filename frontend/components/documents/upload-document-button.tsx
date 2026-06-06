"use client";

import type React from "react";
import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";

export function UploadDocumentButton() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  async function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];

    if (!file) {
      return;
    }

    setIsUploading(true);
    setStatus(null);

    try {
      const response = await api.uploadDocument(file);
      setStatus(response.message);
      event.target.value = "";
      router.refresh();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Upload failed.");
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <div className="flex flex-col items-start gap-2 sm:items-end">
      <input
        ref={inputRef}
        type="file"
        className="hidden"
        accept=".pdf,.png,.jpg,.jpeg,.txt,.doc,.docx"
        onChange={handleFileChange}
      />
      <Button type="button" onClick={() => inputRef.current?.click()} disabled={isUploading}>
        <Upload className="size-4" />
        {isUploading ? "Uploading" : "Upload"}
      </Button>
      {status ? <p className="max-w-72 text-xs text-muted-foreground">{status}</p> : null}
    </div>
  );
}
