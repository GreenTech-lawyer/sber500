import Header from "./Header";
import DocumentsPanel from "./DocumentsPanel";
import ChatPanel from "./ChatPanel";
import CabinetPanel from "./CabinetPanel";
import { useState, useEffect } from "react";

export interface FileItem {
  id: string;
  name: string;
  checked: boolean;
}

export default function MainLayout() {
  const [mobileView, setMobileView] = useState<"docs" | "chat" | "cabinet">("chat");

  // files state loaded from backend
  const [files, setFiles] = useState<FileItem[]>([]);

  // NOTE: session_id should come from auth/session context; using fallback for now
  const sessionId = "session-1"; // TODO: replace with real session id

  useEffect(() => {
    const loadFiles = async () => {
      try {
        const apiBase = (import.meta.env.VITE_API_BASE || "/api");
        const res = await fetch(`${apiBase}/files-for-session/${sessionId}`);
        if (!res.ok) throw new Error("Failed to fetch files");
        const data = await res.json(); // expected iterable of object_ids or file metadata

        // if backend returns only object ids, map them to FileItem; if richer metadata is returned, adapt
        const mapped: FileItem[] = (data || []).map((obj: any) => {
          const objectId = typeof obj === "string" ? obj : obj.object_id || obj.file_id || obj.id;
          const name = typeof obj === "string" ? (objectId.includes("_") ? objectId.split(/_(.+)/)[1] : objectId) : (obj.filename || obj.name || (objectId.includes("_") ? objectId.split(/_(.+)/)[1] : objectId));
          return { id: objectId, name, checked: false };
        });
        setFiles(mapped);
      } catch (err) {
        console.warn(err);
      }
    };
    loadFiles();
  }, [sessionId]);

  // selected file names
  const activeDocuments = files.filter((f) => f.checked).map((f) => f.name);

  const toggleFile = (id: string) => {
    setFiles((files) => files.map((f) => (f.id === id ? { ...f, checked: !f.checked } : f)));
  };

  const addFile = (file: FileItem) => {
    setFiles((prev) => [file, ...prev]);
  };

  return (
    <div className="flex flex-col h-screen bg-white">
      <Header />

      <div className="hidden md:flex flex-1 gap-3 p-3 overflow-hidden bg-white">
        <div className="flex-[0.75] min-w-0">
          <DocumentsPanel files={files} toggleFile={toggleFile} addFile={addFile} />
        </div>
        <div className="flex-[1.5] min-w-0">
          <ChatPanel activeDocuments={activeDocuments} />
        </div>
        <div className="flex-[0.75] min-w-0">
          <CabinetPanel />
        </div>
      </div>

      <div className="md:hidden flex-1 flex flex-col overflow-hidden">
        <div className="flex items-center gap-2 px-3 py-2 border-b border-gray-300 bg-white">
          <button
            onClick={() => setMobileView("docs")}
            className={`px-3 py-1.5 text-xs rounded-lg whitespace-nowrap font-medium transition-colors ${
              mobileView === "docs"
                ? "bg-black text-white"
                : "text-black hover:bg-gray-100"
            }`}
          >
            Документы
          </button>
          <button
            onClick={() => setMobileView("chat")}
            className={`px-3 py-1.5 text-xs rounded-lg whitespace-nowrap font-medium transition-colors ${
              mobileView === "chat"
                ? "bg-black text-white"
                : "text-black hover:bg-gray-100"
            }`}
          >
            Чат
          </button>
          <button
            onClick={() => setMobileView("cabinet")}
            className={`px-3 py-1.5 text-xs rounded-lg whitespace-nowrap font-medium transition-colors ${
              mobileView === "cabinet"
                ? "bg-black text-white"
                : "text-black hover:bg-gray-100"
            }`}
          >
            Кабинет
          </button>
        </div>

        <div className="flex-1 overflow-hidden p-3">
          {mobileView === "docs" && <DocumentsPanel files={files} toggleFile={toggleFile} addFile={addFile} />}
          {mobileView === "chat" && <ChatPanel activeDocuments={activeDocuments} />}
          {mobileView === "cabinet" && <CabinetPanel />}
        </div>
      </div>
    </div>
  );
}
