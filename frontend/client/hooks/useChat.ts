import { useEffect, useRef, useState } from "react";
import { connectChatWS, fetchChatHistory, ChatMessage } from "../services/chat/chatApi";

export function useChat(baseUrl: string, userId: string) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [status, setStatus] = useState<"open" | "closed" | "reconnecting">(
    "reconnecting"
  );

  const wsRef = useRef<ReturnType<typeof connectChatWS> | null>(null);

  // Подключение + история
  useEffect(() => {
    let mounted = true;

    // загрузка истории
    fetchChatHistory(baseUrl, userId)
      .then((historyResponse) => {
        if (mounted) setMessages(historyResponse.history || []);
      })
      .catch((e) => console.error(e));

    // WebSocket
    wsRef.current = connectChatWS(
      baseUrl,
      userId,
      (msg) => {
        setMessages((prev) => [...prev, msg]);
      },
      (s) => setStatus(s as any)
    );

    return () => {
      mounted = false;
      wsRef.current?.close();
    };
  }, [baseUrl, userId]);

  // Отправка сообщения
  const send = (text: string, active_documents: string[]) => {
    const ownMsg: ChatMessage = {
      id: crypto.randomUUID(),
      type: "user",
      text,
      ts: Date.now(),
      active_documents: active_documents,
    };

    setMessages((prev) => [...prev, ownMsg]);
    wsRef.current?.send({ message: text });
  };

  return {
    messages,
    send,
    status,

  };
}
