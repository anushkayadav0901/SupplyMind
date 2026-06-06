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
    const files = event.target.files;

    if (!files || files.length === 0) {
      return;
    }

    setIsUploading(true);
    setStatus(null);

    const total = files.length;
    let succeeded = 0;
    let failed = 0;

    for (let i = 0; i < total; i++) {
      const file = files[i];
      setStatus(`Uploading ${i + 1} of ${total}: ${file.name}`);
      try {
        await api.uploadDocument(file);
        succeeded++;
      } catch {
        failed++;
      }
    }

    event.target.value = "";
    setIsUploading(false);

    if (failed === 0) {
      setStatus(`✓ ${succeeded} file${succeeded > 1 ? "s" : ""} uploaded successfully.`);
    } else {
      setStatus(`${succeeded} uploaded, ${failed} failed out of ${total}.`);
    }

    router.refresh();
  }

  return (
    <div className="flex flex-col items-start gap-2 sm:items-end">
      <input
        ref={inputRef}
        type="file"
        className="hidden"
        accept=".pdf,.png,.jpg,.jpeg,.txt,.doc,.docx"
        multiple
        onChange={handleFileChange}
      />
      <Button type="button" onClick={() => inputRef.current?.click()} disabled={isUploading}>
        <Upload className="size-4" />
        {isUploading ? "Uploading…" : "Upload"}
      </Button>
      {status ? <p className="max-w-72 text-xs text-muted-foreground">{status}</p> : null}
    </div>
  );
}
