import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { MessageCircle, Send, History, Plus } from "lucide-react";
import { useChatStream } from "../../lib/useChatStream";
import { useChatHistory, useChatSessions } from "../../lib/queries";
import { useQueryClient } from "@tanstack/react-query";
import { Markdown } from "./Markdown";
import { CitationChips } from "./CitationChips";
import { ToolActivityList } from "./ToolActivity";
import { AppointmentCard } from "./AppointmentCard";

export function ChatPanel() {
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [showSessions, setShowSessions] = useState(false);
  const [input, setInput] = useState("");
  const qc = useQueryClient();
  const scrollRef = useRef<HTMLDivElement>(null);

  const { data: sessions } = useChatSessions();
  const { data: history } = useChatHistory(sessionId);

  const { messages, send, isStreaming, loadHistory } = useChatStream(sessionId, (id) => {
    setSessionId(id);
    qc.invalidateQueries({ queryKey: ["chat-sessions"] });
  });

  useEffect(() => {
    if (sessionId !== null && history) loadHistory(history);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId, history]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || isStreaming) return;
    setInput("");
    send(text);
  }

  return (
    <aside className="flex h-screen w-96 shrink-0 flex-col border-l border-ink-100 bg-white">
      <header className="flex items-center justify-between border-b border-ink-100 px-4 py-4">
        <div className="flex items-center gap-2">
          <div className="flex size-8 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
            <MessageCircle className="size-4" />
          </div>
          <span className="text-sm font-semibold text-ink-900">Assistant</span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => {
              setSessionId(null);
            }}
            title="New conversation"
            className="flex size-8 items-center justify-center rounded-lg text-ink-500 transition-colors duration-150 hover:bg-ink-50 hover:text-ink-900"
          >
            <Plus className="size-4" />
          </button>
          <button
            onClick={() => setShowSessions((v) => !v)}
            title="Past conversations"
            className={`flex size-8 items-center justify-center rounded-lg transition-colors duration-150 ${
              showSessions ? "bg-brand-50 text-brand-600" : "text-ink-500 hover:bg-ink-50 hover:text-ink-900"
            }`}
          >
            <History className="size-4" />
          </button>
        </div>
      </header>

      <AnimatePresence>
        {showSessions && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.18 }}
            className="overflow-hidden border-b border-ink-100"
          >
            <div className="max-h-56 overflow-y-auto p-2">
              {sessions && sessions.length > 0 ? (
                sessions.map((s) => (
                  <button
                    key={s.id}
                    onClick={() => {
                      setSessionId(s.id);
                      setShowSessions(false);
                    }}
                    className={`block w-full truncate rounded-lg px-3 py-2 text-left text-sm transition-colors duration-150 ${
                      sessionId === s.id ? "bg-brand-50 text-brand-700" : "text-ink-700 hover:bg-ink-50"
                    }`}
                  >
                    {s.title}
                  </button>
                ))
              ) : (
                <p className="px-3 py-2 text-sm text-ink-500">No past conversations yet.</p>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto px-4 py-4">
        {messages.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center gap-2 text-center">
            <MessageCircle className="size-8 text-ink-300" />
            <p className="text-sm text-ink-500">
              Ask about policies, deadlines, your schedule, or degree progress.
            </p>
          </div>
        )}

        {messages.map((m) => (
          <div key={m.id} className={m.role === "user" ? "flex justify-end" : "flex justify-start"}>
            {m.role === "user" ? (
              <div className="max-w-[85%] rounded-2xl rounded-br-sm bg-brand-600 px-3.5 py-2.5 text-sm text-white">
                {m.content}
              </div>
            ) : (
              <div className="w-full max-w-[92%]">
                <ToolActivityList calls={m.toolCalls} />
                {m.content ? (
                  <div className="rounded-2xl rounded-bl-sm border border-ink-100 bg-ink-50 px-3.5 py-2.5 text-sm text-ink-900">
                    <Markdown>{m.content}</Markdown>
                    <CitationChips text={m.content} />
                  </div>
                ) : m.streaming && m.toolCalls.length === 0 ? (
                  <div className="flex items-center gap-1.5 px-1 py-2">
                    <span className="size-1.5 animate-pulse-dot rounded-full bg-ink-300" />
                    <span className="size-1.5 animate-pulse-dot rounded-full bg-ink-300 [animation-delay:150ms]" />
                    <span className="size-1.5 animate-pulse-dot rounded-full bg-ink-300 [animation-delay:300ms]" />
                  </div>
                ) : null}

                {m.error && (
                  <p className="mt-1 text-xs text-amber-500">{m.error}</p>
                )}

                {m.toolCalls
                  .filter((t) => t.tool === "request_advisor_appointment" && t.status === "done" && t.content)
                  .map((t, i) => (
                    <AppointmentCard key={i} proposal={t.content as never} />
                  ))}
              </div>
            )}
          </div>
        ))}
      </div>

      <form onSubmit={handleSubmit} className="border-t border-ink-100 p-3">
        <div className="flex items-end gap-2 rounded-2xl border border-ink-200 bg-white px-3 py-2 transition-colors duration-150 focus-within:border-brand-400">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSubmit(e);
              }
            }}
            rows={1}
            placeholder="Ask a question…"
            className="max-h-24 flex-1 resize-none bg-transparent text-sm text-ink-900 placeholder:text-ink-300 focus:outline-none"
          />
          <button
            type="submit"
            disabled={!input.trim() || isStreaming}
            className="flex size-8 shrink-0 items-center justify-center rounded-xl bg-brand-600 text-white transition-colors duration-150 hover:bg-brand-700 disabled:opacity-40"
          >
            <Send className="size-4" />
          </button>
        </div>
      </form>
    </aside>
  );
}
