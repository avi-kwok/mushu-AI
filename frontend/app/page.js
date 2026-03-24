"use client";
import { useState, useRef, useEffect } from "react";

export default function Home() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function send() {
    const text = input.trim();
    if (!text || loading) return;

    setLoading(true);

    const nextHistory = [...messages, { role: "user", content: text }];
    setMessages([...nextHistory, { role: "assistant", content: "" }]);
    setInput("");

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Accept": "text/event-stream",
        },
        body: JSON.stringify({ messages: nextHistory }),
      });

      if (!res.ok || !res.body) {
        const errText = await res.text().catch(() => "");
        throw new Error(`Backend error ${res.status}: ${errText}`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split("\n\n");
        buffer = events.pop() ?? "";

        for (const event of events) {
          const lines = event.split("\n");
          for (const line of lines) {
            if (!line.startsWith("data:")) continue;
            const payload = line.startsWith("data: ") ? line.slice(6) : line.slice(5);
            if (!payload) continue;
            if (payload === "[DONE]") { setLoading(false); return; }

            let token = "";
            try { const obj = JSON.parse(payload); token = obj.t ?? ""; }
            catch { continue; }
            if (!token) continue;

            setMessages((prev) => {
              const next = [...prev];
              const last = next[next.length - 1];
              if (!last || last.role !== "assistant") return next;
              next[next.length - 1] = { ...last, content: last.content + token };
              return next;
            });
          }
        }
      }
    } catch (e) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `⚠️ Error: ${e?.message ?? String(e)}` },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex flex-col py-12 px-6">
      {/* Header */}
      <div className="max-w-2xl mx-auto w-full mb-8">
        <h1 className="text-3xl sm:text-4xl font-bold text-green-300">
          Mushu Kwok AI
        </h1>
        <p className="text-sm text-slate-600 dark:text-slate-400 mt-2 leading-relaxed">
          Ask Mushu anything - Avidan Kwok's real life dog in AI form
        </p>
      </div>

      {/* Chat window */}
      <div className="max-w-2xl mx-auto w-full flex-1 flex flex-col gap-4">
        <div className="rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/50 p-6 min-h-80 flex flex-col gap-4 overflow-y-auto max-h-[520px]">
          {messages.length === 0 ? (
            <p className="text-slate-500 dark:text-slate-400 text-sm">Ask something to start…</p>
          ) : (
            messages.map((m, i) => (
              <div
                key={i}
                className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
              >
                {m.role === "assistant" && (
                  <span className="text-xs font-semibold text-green-300 uppercase tracking-widest mr-2 mt-1 shrink-0">
                    Mushu
                  </span>
                )}
                <div
                  className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                    m.role === "user"
                      ? "bg-emerald-950/50 border border-emerald-700 text-emerald-300 rounded-tr-sm"
                      : "bg-stone-100 dark:bg-slate-700/60 text-slate-800 dark:text-slate-200 rounded-tl-sm border border-slate-200 dark:border-slate-600"
                  }`}
                >
                  {m.content || (
                    <span className="inline-flex gap-1 items-center text-slate-400">
                      <span className="w-1.5 h-1.5 bg-green-300 rounded-full animate-bounce [animation-delay:0ms]" />
                      <span className="w-1.5 h-1.5 bg-green-300 rounded-full animate-bounce [animation-delay:150ms]" />
                      <span className="w-1.5 h-1.5 bg-green-300 rounded-full animate-bounce [animation-delay:300ms]" />
                    </span>
                  )}
                </div>
              </div>
            ))
          )}
          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div className="flex gap-3">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send()}
            disabled={loading}
            placeholder="Ask something about Mushu…"
            className="flex-1 px-4 py-3 rounded-xl border border-slate-700 bg-slate-800/50 text-slate-100 placeholder-slate-500 text-sm focus:outline-none focus:border-green-300/60 transition-colors disabled:opacity-50"
          />
          <button
            onClick={send}
            disabled={loading || !input.trim()}
            className="px-5 py-3 bg-green-300/20 hover:bg-green-300/30 border border-green-300/40 disabled:opacity-40 disabled:cursor-not-allowed text-green-300 text-sm font-medium rounded-xl transition-colors"
          >
            {loading ? "…" : "Send"}
          </button>
        </div>

        {/* Disclaimer */}
        <p className="text-xs text-slate-500 dark:text-slate-500 leading-relaxed">
          <span className="font-semibold text-slate-600 dark:text-slate-400">Disclaimer: </span>
          This GenAI can make mistakes. Information about Mushu Kwok may be incorrect and should not be considered factual. Do not share personal information.
        </p>
      </div>
    </div>
  );
}
