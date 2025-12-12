import { createWS } from "./wsClient";

export interface ChatMessage {
  id: string;
  type: "user" | "bot";
  text: string;
  ts?: number;
  active_documents: string[];
}

export interface ChatHistoryResponse {
  user_id: string;
  history: ChatMessage[];
}

export async function fetchChatHistory(
  baseUrl: string,
  userId: string
): Promise<ChatHistoryResponse> {
  const res = await fetch(`${baseUrl}/chat/history/${userId}`);

  if (!res.ok) {
    throw new Error("Failed to load chat history");
  }

  return res.json();
}

export function connectChatWS(
  baseUrl: string,
  userId: string,
  onBotMessage: (msg: ChatMessage) => void,
  onStatus?: (s: string) => void
) {
  const wsUrl = `${baseUrl.replace("http", "ws")}/chat/${userId}`;

  return createWS(
    wsUrl,
    (data) => {
      const reply = data.reply || data.text;

      if (!reply) return;

      onBotMessage({
        id: crypto.randomUUID(),
        type: "bot",
        text: reply,
        ts: Date.now(),
        active_documents: [],
      });
    },
    onStatus
  );
}
