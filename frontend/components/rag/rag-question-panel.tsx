"use client";

import type React from "react";
import { useState } from "react";
import { SendHorizontal } from "lucide-react";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/status-badge";
import { api } from "@/lib/api";
import type { RagAnswer } from "@/lib/types";

interface RagQuestionPanelProps {
  documentId?: number;
  initialQuestion?: string;
}

export function RagQuestionPanel({ documentId, initialQuestion = "" }: RagQuestionPanelProps) {
  const [question, setQuestion] = useState(initialQuestion);
  const [answer, setAnswer] = useState<RagAnswer | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isAsking, setIsAsking] = useState(false);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const trimmed = question.trim();

    if (!trimmed) {
      return;
    }

    setIsAsking(true);
    setError(null);

    try {
      const response = documentId
        ? await api.askDocumentQuestion(documentId, trimmed)
        : await api.askRagQuestion(trimmed);
      setAnswer(response);
    } catch (caught) {
      setAnswer(null);
      setError(caught instanceof Error ? caught.message : "The assistant could not answer.");
    } finally {
      setIsAsking(false);
    }
  }

  return (
    <div className="rounded-lg border border-border bg-card p-5">
      <form onSubmit={handleSubmit} className="space-y-3">
        <label htmlFor={documentId ? "document-question" : "rag-question"} className="text-sm font-medium">
          Ask a procurement question
        </label>
        <div className="flex flex-col gap-2 sm:flex-row">
          <input
            id={documentId ? "document-question" : "rag-question"}
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder={
              documentId
                ? "What are the payment terms in this document?"
                : "Which vendors have elevated delivery risk?"
            }
            className="h-9 flex-1 rounded-md border border-input bg-background px-3 text-sm outline-none transition-colors focus:border-ring focus:ring-2 focus:ring-ring/20"
          />
          <Button type="submit" disabled={isAsking || !question.trim()}>
            <SendHorizontal className="size-4" />
            {isAsking ? "Asking" : "Ask"}
          </Button>
        </div>
      </form>

      {error ? (
        <div className="mt-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}

      {answer ? (
        <div className="mt-5 space-y-4">
          <div className="rounded-md border border-border bg-background p-4">
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <StatusBadge value={answer.grounded ? "indexed" : "offline"} />
              <span className="text-xs text-muted-foreground">
                {answer.chunks_retrieved} chunks retrieved
              </span>
              {answer.elapsed_seconds ? (
                <span className="text-xs text-muted-foreground">
                  {answer.elapsed_seconds.toFixed(2)}s
                </span>
              ) : null}
            </div>
            <p className="whitespace-pre-wrap text-sm leading-6 text-foreground">{answer.answer}</p>
          </div>

          <div>
            <h3 className="text-sm font-medium">Sources</h3>
            {answer.sources.length > 0 ? (
              <div className="mt-2 space-y-2">
                {answer.sources.map((source, index) => (
                  <div key={`${source.document_id}-${index}`} className="rounded-md border border-border p-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <p className="text-sm font-medium">{source.filename}</p>
                      <span className="text-xs text-muted-foreground">
                        {(source.relevance_score * 100).toFixed(0)}% match
                      </span>
                    </div>
                    <p className="mt-2 line-clamp-3 text-xs leading-5 text-muted-foreground">
                      {source.snippet}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="mt-2 text-sm text-muted-foreground">No citations were returned.</p>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
