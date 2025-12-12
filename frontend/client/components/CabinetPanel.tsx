import { Layout, File, Plus } from "lucide-react";
import { useState } from "react";

interface CabinetFile {
  id: string;
  name: string;
}

export default function CabinetPanel() {
  const [files] = useState<CabinetFile[]>(
    Array.from({ length: 18 }, (_, i) => ({
      id: `cabinet-file-${i}`,
      name: "file.txt",
    }))
  );

  return (
    <div className="flex flex-col h-full bg-white border border-gray-300 rounded-xl overflow-hidden">
      <div className="flex items-center gap-2 px-4 py-3 border-b border-gray-300">
        <span className="flex-1 text-sm font-normal text-black">Кабинет</span>
        <button className="p-2 rounded-2xl hover:bg-gray-100 transition-colors">
          <Layout className="w-4 h-4 text-gray-400" strokeWidth={2} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto">
        <div className="flex flex-col gap-0">
          {files.map((file, index) => (
            <div
              key={file.id}
              className={`flex items-center gap-2 px-3 py-1.5 hover:bg-gray-100 transition-colors ${
                index < files.length - 1 ? "border-b border-gray-200" : ""
              }`}
            >
              <File className="w-4 h-4 text-gray-400 flex-shrink-0" strokeWidth={2} />
              <span className="text-xs font-normal text-black flex-1 truncate">
                {file.name}
              </span>
            </div>
          ))}
        </div>
      </div>

      <div className="border-t border-gray-300 p-2">
        <button className="w-full flex items-center justify-center gap-2 px-3 py-2 text-xs rounded-2xl border border-gray-400 hover:bg-gray-100 transition-colors text-black">
          <Plus className="w-4 h-4" strokeWidth={2} />
          Добавить заметку
        </button>
      </div>
    </div>
  );
}
