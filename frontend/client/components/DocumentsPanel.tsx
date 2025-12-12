import { Plus, LayoutGrid, CheckSquare, File } from "lucide-react";
import { FileItem } from "./MainLayout";
import { useState } from "react";

interface Props {
  files: FileItem[];
  toggleFile: (id: string) => void;
  addFile: (file: FileItem) => void; // new callback to add uploaded file to UI
}

export default function DocumentsPanel({ files, toggleFile, addFile }: Props) {
  const [uploading, setUploading] = useState(false);

  const handleAddFile = async () => {
    const fileInput = document.createElement("input");
    fileInput.type = "file";
    fileInput.accept = "*/*";
    fileInput.onchange = async () => {
      if (!fileInput.files || fileInput.files.length === 0) return;
      const file = fileInput.files[0];
      setUploading(true);
      try {
        // Получаем presigned URL от бэкенда с user_id
        const apiBase = (import.meta.env.VITE_API_BASE || "/api");
        const res = await fetch(apiBase + "/upload-url", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            filename: file.name,
            user_id: "user-123", // TODO сюда подставляем текущий user_id
            content_type: file.type,
          }),
        });
        if (!res.ok) throw new Error("Не удалось получить URL для загрузки");
        const data = await res.json(); // ожидаем { upload_url, object_id, bucket }

        // Загружаем файл напрямую на MinIO
        const uploadRes = await fetch(data.upload_url, {
          method: "PUT",
          headers: { "Content-Type": file.type },
          body: file,
        });
        if (!uploadRes.ok) throw new Error("Не удалось загрузить файл");

        console.log("Файл успешно загружен:", data.object_id);

        // Notify backend about uploaded file so it can be associated with session/user
        try {
          const notifyRes = await fetch(apiBase + "/notify-upload", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              object_id: data.object_id,
              bucket: data.bucket,
              user_id: "user-123",
              file_id: null,
              content_type: file.type,
            }),
          });
          if (!notifyRes.ok) {
            console.warn("notify-upload failed", await notifyRes.text());
          } else {
            // optimistic UI update: add file to list
            const objectId: string = data.object_id;
            const name = objectId.includes("_") ? objectId.split(/_(.+)/)[1] : objectId;
            addFile({ id: objectId, name, checked: false });
          }
        } catch (notifyErr) {
          console.warn("Failed to notify backend about upload", notifyErr);
        }
      } catch (err) {
        console.error(err);
        alert("Ошибка при загрузке файла");
      } finally {
        setUploading(false);
      }
    };
    fileInput.click();
  };

  return (
    <div className="flex flex-col h-full bg-white border border-gray-300 rounded-xl overflow-hidden">
      <div className="flex items-center gap-2 px-4 py-3 border-b border-gray-300">
        <span className="flex-1 text-sm font-normal text-black">Документы</span>
        <button
          className={`p-2 rounded-2xl hover:bg-gray-100 transition-colors ${uploading ? "opacity-50" : ""}`}
          onClick={handleAddFile}
          disabled={uploading}
        >
          <Plus className="w-4 h-4 text-gray-400" strokeWidth={2} />
        </button>
        <button className="p-2 rounded-2xl hover:bg-gray-100 transition-colors">
          <LayoutGrid className="w-4 h-4 text-gray-400" strokeWidth={2} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto">
        <div className="flex flex-col gap-0">
          {files.map((file, index) => (
            <button
              key={file.id}
              onClick={() => toggleFile(file.id)}
              className={`flex items-center gap-2 px-3 py-1.5 hover:bg-gray-100 transition-colors text-left w-full ${
                index < files.length - 1 ? "border-b border-gray-200" : ""
              }`}
            >
              <File className="w-4 h-4 text-gray-400 flex-shrink-0" strokeWidth={2} />
              <span className="text-xs font-normal text-black flex-1 truncate">{file.name}</span>
              {file.checked ? (
                <CheckSquare className="w-4 h-4 text-gray-400 flex-shrink-0" strokeWidth={2} />
              ) : (
                <div className="w-4 h-4 border border-gray-400 rounded" />
              )}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
