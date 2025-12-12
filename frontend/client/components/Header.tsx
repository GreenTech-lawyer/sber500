import { Settings } from "lucide-react";

export default function Header() {
  return (
    <header className="flex items-center justify-center h-16 px-4 md:px-6 bg-white border-b border-gray-300 relative">
      <img
        src="https://api.builder.io/api/v1/image/assets/TEMP/c491a86f91376d5bf28231b75948d6ba42e4de49?width=96"
        alt="Logo"
        className="absolute left-4 md:left-6 w-10 h-10 md:w-12 md:h-12"
      />
      <h1 className="text-base md:text-lg font-normal text-black">
        Цифровой Юрист
      </h1>

      <button className="absolute right-4 md:right-6 flex items-center gap-2 px-3 md:px-4 py-2 rounded-2xl hover:bg-gray-100 transition-colors">
        <span className="hidden md:inline text-base font-normal text-black">
          Настройки
        </span>
        <Settings className="w-4 h-4 md:w-5 md:h-5 text-gray-400" strokeWidth={2} />
      </button>
    </header>
  );
}
