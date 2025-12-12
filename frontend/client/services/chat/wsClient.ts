export type WSStatus = "open" | "closed" | "reconnecting";

export function createWS(
  url: string,
  onMessage: (msg: any) => void,
  onStatus?: (status: WSStatus) => void
) {
  let ws: WebSocket | null = null;
  let manuallyClosed = false;

  const connect = () => {
    onStatus?.("reconnecting");

    ws = new WebSocket(url);

    ws.onopen = () => {
      onStatus?.("open");
    };

    ws.onclose = () => {
      onStatus?.("closed");

      if (!manuallyClosed) {
        setTimeout(connect, 1500); // авто-реконнект
      }
    };

    ws.onmessage = (event) => {
      try {
        onMessage(JSON.parse(event.data));
      } catch (err) {
        console.error("WS parse error:", err);
      }
    };
  };

  connect();

  return {
    send: (data: any) => {
      if (ws?.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(data));
      }
    },
    close: () => {
      manuallyClosed = true;
      ws?.close();
    },
  };
}
