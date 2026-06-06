"use client";

import type React from "react";
import { useState } from "react";
import { SendHorizontal, Sparkles, FileText } from "lucide-react";
import { cn } from "@/lib/utils";
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
        <label
          htmlFor={documentId ? "document-question" : "rag-question"}
          className="text-sm font-medium"
        >
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
            className="h-11 flex-1 rounded-md border border-input bg-background px-3.5 text-sm outline-none transition-all placeholder:text-muted-foreground/60 focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/20"
          />
          <Button type="submit" disabled={isAsking || !question.trim()} className="h-11">
            <SendHorizontal className="size-4" />
            {isAsking ? "Asking…" : "Ask"}
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
          {/* Answer block */}
          <div className="overflow-hidden rounded-md border border-border">
            {/* Status bar */}
            <div className="flex flex-wrap items-center gap-2 border-b border-border bg-card px-4 py-2.5">
              <div className="flex items-center gap-1.5 text-indigo-600">
                <Sparkles className="size-3.5" />
                <span className="text-xs font-semibold uppercase tracking-wide">Answer</span>
              </div>
              <span className="text-muted-foreground/40">·</span>
              <StatusBadge value={answer.grounded ? "indexed" : "offline"} />
              <span className="text-xs text-muted-foreground">
                {answer.chunks_retrieved} chunks retrieved
              </span>
              {answer.elapsed_seconds ? (
                <>
                  <span className="text-muted-foreground/40">·</span>
                  <span className="text-xs text-muted-foreground">
                    {answer.elapsed_seconds.toFixed(2)}s
                  </span>
                </>
              ) : null}
            </div>
            {/* Answer text */}
            <div className="bg-slate-50/60 px-4 py-4">
              <p className="whitespace-pre-wrap text-sm leading-7 text-foreground">
                {answer.answer}
              </p>
            </div>
          </div>

          {/* Sources */}
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Retrieved Sources
            </h3>
            {answer.sources.length > 0 ? (
              <div className="mt-3 space-y-2">
                {answer.sources.map((source, index) => {
                  const relevancePercent = Math.round(source.relevance_score * 100);
                  return (
                    <div
                      key={`${source.document_id}-${index}`}
                      className="rounded-md border border-border bg-card p-3.5 transition-colors hover:bg-muted/30"
                    >
                      <div className="flex flex-wrap items-start justify-between gap-2">
                        <div className="flex items-center gap-2.5">
                          <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-indigo-50 text-[11px] font-bold text-indigo-600">
                            {index + 1}
                          </span>
                          <div className="flex items-center gap-1.5">
                            <FileText className="size-3.5 text-muted-foreground" />
                            <p className="text-sm font-semibold text-foreground">
                              {source.filename}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="h-1.5 w-16 overflow-hidden rounded-full bg-slate-100">
                            <div
                              className={cn(
                                "h-full rounded-full",
                                relevancePercent >= 80
                                  ? "bg-emerald-500"
                                  : relevancePercent >= 50
                                    ? "bg-amber-500"
                                    : "bg-slate-400"
                              )}
                              style={{ width: `${relevancePercent}%` }}
                            />
                          </div>
                          <span
                            className={cn(
                              "text-xs font-medium",
                              relevancePercent >= 80
                                ? "text-emerald-700"
                                : relevancePercent >= 50
                                  ? "text-amber-700"
                                  : "text-slate-500"
                            )}
                          >
                            {relevancePercent}%
                          </span>
                        </div>
                      </div>
                      <p className="mt-2 line-clamp-3 pl-8.5 text-xs leading-5 text-muted-foreground">
                        {source.snippet}
                      </p>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="mt-2 text-sm text-muted-foreground">No citations were returned.</p>
            )}
          </div>

          {/* Powered by RAG label */}
          <p className="pt-1 text-center text-[10px] font-medium uppercase tracking-[0.15em] text-muted-foreground/50">
            Powered by RAG
          </p>
        </div>
      ) : null}
    </div>
  );
}
