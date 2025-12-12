import { Settings, MoreVertical, Copy, Edit2, Send, ChevronRight, Trash2 } from "lucide-react";
import { useState, useRef, useEffect, useCallback } from "react";
import { useChat } from "../hooks/useChat";

export default function ChatPanel({ activeDocuments = [] }: { activeDocuments?: string[] }) {
  const [input, setInput] = useState("");
  const [showMenu, setShowMenu] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const quickActionsRef = useRef<HTMLDivElement>(null);

  const { messages, send, status } = useChat(
    import.meta.env.VITE_API_BASE || "/api",
    "user-123"
  );

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setShowMenu(false);
      }
    };

    if (showMenu) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => {
        document.removeEventListener("mousedown", handleClickOutside);
      };
    }
  }, [showMenu]);

  const handleSend = () => {
    if (input.trim()) {
      send(input, activeDocuments);
      setInput("");
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text).then(
      () => {
        alert("Текст скопирован в буфер обмена!");
      },
      (err) => {
        console.error("Ошибка при копировании в буфер обмена: ", err);
      }
    );
  };

  const scrollQuickActions = useCallback((direction: "left" | "right") => {
    if (quickActionsRef.current) {
      const scrollAmount = direction === "right" ? 150 : -150;
      quickActionsRef.current.scrollBy({
        left: scrollAmount,
        behavior: "smooth",
      });
    }
  }, []);

  return (
    <div className="flex flex-col h-full bg-white border border-gray-300 rounded-xl overflow-hidden">
      <div className="flex items-center gap-2 px-4 py-3 border-b border-gray-300">
        <span className="flex-1 text-sm font-normal text-black">Чат</span>
        {/*Скрыл кнопку настроек, пока ее функционал не определен*/}
        {/*<button className="p-2 rounded-2xl hover:bg-gray-100 transition-colors">*/}
        {/*  <Settings className="w-4 h-4 text-gray-400" strokeWidth={2} />*/}
        {/*</button>*/}
        <div className="relative" ref={menuRef}>
          <button
            onClick={() => setShowMenu(!showMenu)}
            className="p-2 rounded-2xl hover:bg-gray-100 transition-colors"
          >
            <MoreVertical className="w-4 h-4 text-gray-400" strokeWidth={2} />
          </button>
          {showMenu && (
            <div className="absolute right-0 mt-1 w-48 bg-white border border-gray-300 rounded-lg shadow-lg z-50">
              <button
                onClick={() => {
                  // if you want to clear server-side/chat history, implement an API call
                  setShowMenu(false);
                }}
                className="w-full flex items-center gap-2 px-4 py-2 text-xs text-red-600 hover:bg-gray-100 transition-colors"
              >
                <Trash2 className="w-4 h-4" />
                Удаление чата
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto flex flex-col gap-2 p-3">
        {messages.map((message: any) => (
          <div
            key={message.id}
            className={`flex ${message.type === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`flex flex-col gap-2 max-w-xs lg:max-w-md ${
                message.type === "user" ? "items-end" : "items-start"
              }`}
            >
              <p
                className={`text-xs leading-relaxed rounded-lg p-3 ${
                  message.type === "user"
                    ? "bg-gray-100 text-black text-right"
                    : "bg-white text-black text-left border border-gray-300"
                }`}
              >
                {message.text}
              </p>
              <div className="flex gap-1">
                <button
                  className="p-1 rounded-lg hover:bg-gray-100 transition-colors"
                  onClick={() => copyToClipboard(message.text)}
                >
                  <Copy className="w-3.5 h-3.5 text-gray-400" strokeWidth={2} />
                </button>
                {message.type === "user" && (
                  <button className="p-1 rounded-lg hover:bg-gray-100 transition-colors">
                    <Edit2 className="w-3.5 h-3.5 text-gray-400" strokeWidth={2} />
                  </button>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="border-t border-gray-300 p-3 bg-white">
        <div className="flex items-center gap-2 mb-3 bg-gray-100 rounded-lg px-3 py-2 border border-gray-300">
          <input
            type="text"
            placeholder="Введите текст..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === "Enter" && handleSend()}
            className="flex-1 bg-transparent text-xs outline-none text-black placeholder-gray-400"
          />
          <span className="text-xs text-gray-300 whitespace-nowrap">4 документа</span>
          <button
            onClick={handleSend}
            className="p-1 hover:opacity-70 transition-opacity flex-shrink-0"
          >
            <ChevronRight className="w-4 h-4 text-gray-400" strokeWidth={2} />
          </button>
        </div>

        <div className="relative">
          <div ref={quickActionsRef} className="flex gap-2 overflow-hidden pb-2">
            {[1, 2, 3, 4].map((i) => (
              <button
                key={i}
                className="px-3 py-2 text-xs border border-gray-300 rounded-lg hover:bg-gray-100 transition-colors whitespace-nowrap flex-shrink-0 text-black bg-white"
              >
                Составь план нового документа
              </button>
            ))}
          </div>

          <div className="absolute left-0 top-0 bottom-0 w-12 bg-gradient-to-r from-black/40 to-transparent rounded-lg flex items-center justify-center pointer-events-none">
            <button
              onClick={() => scrollQuickActions("left")}
              className="p-1 hover:opacity-70 transition-opacity pointer-events-auto"
            >
              <ChevronRight className="w-5 h-5 text-white rotate-180" strokeWidth={2} />
            </button>
          </div>

          <div className="absolute right-0 top-0 bottom-0 w-12 bg-gradient-to-l from-black/40 to-transparent rounded-lg flex items-center justify-center pointer-events-none">
            <button
              onClick={() => scrollQuickActions("right")}
              className="p-1 hover:opacity-70 transition-opacity pointer-events-auto"
            >
              <ChevronRight className="w-5 h-5 text-white" strokeWidth={2} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
