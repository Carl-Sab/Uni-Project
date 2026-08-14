import { useCallback, useRef, useState } from "react";
import { getToken } from "./tokenStore";

export interface ToolActivity {
  tool: string;
  status: "running" | "done";
  content?: unknown;
}

export interface UIMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  toolCalls: ToolActivity[];
  streaming?: boolean;
  error?: string;
}

let counter = 0;
const uid = () => `m${Date.now()}_${counter++}`;

export function useChatStream(sessionId: number | null, onSessionId: (id: number) => void) {
  const [messages, setMessages] = useState<UIMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const loadHistory = useCallback((history: { role: "user" | "assistant"; content: string }[]) => {
    setMessages(history.map((m) => ({ id: uid(), role: m.role, content: m.content, toolCalls: [] })));
  }, []);

  const send = useCallback(
    async (text: string) => {
      const userMsg: UIMessage = { id: uid(), role: "user", content: text, toolCalls: [] };
      const assistantId = uid();
      const assistantMsg: UIMessage = {
        id: assistantId,
        role: "assistant",
        content: "",
        toolCalls: [],
        streaming: true,
      };
      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setIsStreaming(true);

      const controller = new AbortController();
      abortRef.current = controller;

      function patch(fn: (m: UIMessage) => UIMessage) {
        setMessages((prev) => prev.map((m) => (m.id === assistantId ? fn(m) : m)));
      }

      try {
        const res = await fetch("/api/chat", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${getToken()}`,
          },
          body: JSON.stringify({ message: text, session_id: sessionId }),
          signal: controller.signal,
        });

        if (!res.body) throw new Error("No response body");
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });

          // sse-starlette emits CRLF ("\r\n\r\n") block separators, not
          // bare "\n\n" - splitting on "\n\n" alone never matches a
          // CRLF-delimited stream at all, so every event silently piled up
          // in `buffer` forever and nothing ever rendered (no error,
          // since nothing throws - the loop just never found a block).
          const blocks = buffer.split(/\r?\n\r?\n/);
          buffer = blocks.pop() ?? "";

          for (const block of blocks) {
            const lines = block.split(/\r?\n/);
            const eventLine = lines.find((l) => l.startsWith("event:"));
            const dataLine = lines.find((l) => l.startsWith("data:"));
            if (!eventLine || !dataLine) continue;
            const eventType = eventLine.slice(6).trim();
            const data = JSON.parse(dataLine.slice(5).trim());

            if (eventType === "tool_call") {
              patch((m) => ({
                ...m,
                toolCalls: [...m.toolCalls, { tool: data.tool, status: "running" }],
              }));
            } else if (eventType === "tool_result") {
              patch((m) => ({
                ...m,
                toolCalls: m.toolCalls.map((t) =>
                  t.tool === data.tool && t.status === "running"
                    ? { ...t, status: "done", content: data.content }
                    : t
                ),
              }));
            } else if (eventType === "text_delta") {
              patch((m) => ({ ...m, content: m.content + data.content }));
            } else if (eventType === "error") {
              patch((m) => ({ ...m, error: data.detail, streaming: false }));
            } else if (eventType === "done") {
              onSessionId(data.session_id);
              patch((m) => ({ ...m, streaming: false }));
            }
          }
        }
      } catch (e) {
        if ((e as Error).name !== "AbortError") {
          patch((m) => ({ ...m, streaming: false, error: "Connection lost. Please try again." }));
        }
      } finally {
        setIsStreaming(false);
      }
    },
    [sessionId, onSessionId]
  );

  return { messages, send, isStreaming, loadHistory, setMessages };
}
