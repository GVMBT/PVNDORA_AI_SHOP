import type React from "react";

const Navigation: React.FC = () => {
  return (
    <div className="min-h-screen bg-[#020202] text-white">
      {/* Header */}
      <header className="border-b border-white/10">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <h1 className="text-2xl font-bold text-white">Pandora Studio</h1>
            </div>

            <nav className="flex items-center gap-6">
              <a
                href="/"
                className="text-gray-300 hover:text-white transition-colors font-mono text-sm"
              >
                Главная
              </a>
              <a
                href="/studio"
                className="px-4 py-2 bg-yellow-500/20 border border-yellow-500/30 text-yellow-400 hover:bg-yellow-500/30 hover:border-yellow-500/50 transition-all rounded font-mono text-sm flex items-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9.663 17h4.673M12 3v1m6.364 1.636l.636.636 4.636 4.636M21 12h-3m0 0v-3m0 3h3"
                  />
                </svg>
                Studio (BETA)
              </a>
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-4 py-12">
        <div className="text-center mb-12">
          <h2 className="text-4xl font-bold text-white mb-6">Добро пожаловать в Pandora Studio</h2>
          <p className="text-gray-300 text-lg mb-8 max-w-2xl mx-auto">
            Экспериментальная платформа для генерации контента с помощью нейросетей
          </p>
        </div>

        {/* Cards */}
        <div className="grid md:grid-cols-2 gap-8 mb-12">
          <div className="bg-black/60 backdrop-blur-md border border-white/10 rounded-lg p-6">
            <div className="flex items-center gap-4 mb-4">
              <div className="w-12 h-12 bg-blue-500/20 rounded-full flex items-center justify-center">
                <svg
                  className="w-6 h-6 text-blue-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M15 10l4.553-2.276A8 8 0 010-11.448 0l-5.392 5.392L8.447 18.654a2 2 0 11-2.828 0l-4.582-4.582a6 6 0 110 8l6-6a6 6 0 000-12zM6 16v6l6-6"
                  />
                </svg>
              </div>
              <div>
                <h3 className="text-xl font-bold text-white mb-2">Главная страница</h3>
                <p className="text-gray-400 text-sm">Основная информация и навигация</p>
              </div>
            </div>

            <div className="space-y-4">
              <a
                href="/"
                className="block w-full p-4 bg-white/5 hover:bg-white/10 border border-white/10 hover:border-white/20 rounded-lg transition-all text-center"
              >
                <div className="text-white font-mono">Перейти на главную</div>
              </a>
            </div>
          </div>

          <div className="bg-black/60 backdrop-blur-md border border-white/10 rounded-lg p-6">
            <div className="flex items-center gap-4 mb-4">
              <div className="w-12 h-12 bg-yellow-500/20 rounded-full flex items-center justify-center">
                <svg
                  className="w-6 h-6 text-yellow-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 9v2m0 4v-6m0 4v6m0-10V7m0 4h8a2 2 0 002-2V7a2 2 0 00-2-2h-4a2 2 0 00-2 2v10a2 2 0 002 2h4a2 2 0 002-2V7a2 2 0 00-2-2h-4z"
                  />
                </svg>
              </div>
              <div>
                <h3 className="text-xl font-bold text-white mb-2">Studio</h3>
                <p className="text-gray-400 text-sm">Генерация видео, изображений и аудио</p>
              </div>
            </div>

            <div className="space-y-4">
              <a
                href="/studio"
                className="block w-full p-4 bg-yellow-500/10 hover:bg-yellow-500/20 border border-yellow-500/30 hover:border-yellow-500/50 rounded-lg transition-all text-center"
              >
                <div className="text-yellow-400 font-mono">Перейти в Studio</div>
                <div className="text-yellow-500/60 text-xs mt-1">Требуется права доступа</div>
              </a>
            </div>
          </div>
        </div>

        {/* Features */}
        <div className="bg-black/40 backdrop-blur-sm border border-white/5 rounded-lg p-8">
          <h3 className="text-2xl font-bold text-white mb-6 text-center">Возможности Studio</h3>
          <div className="grid md:grid-cols-3 gap-6">
            <div className="text-center">
              <div className="w-16 h-16 mx-auto mb-3 bg-green-500/20 rounded-full flex items-center justify-center">
                <svg
                  className="w-8 h-8 text-green-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M21 15a2 2 0 11-4 0 2 2 0 014 0zM17 8H7a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2V10a2 2 0 00-2-2z"
                  />
                </svg>
              </div>
              <h4 className="text-white font-bold mb-2">Генерация видео</h4>
              <p className="text-gray-400 text-sm">VEO 3.1, SORA и другие модели</p>
            </div>

            <div className="text-center">
              <div className="w-16 h-16 mx-auto mb-3 bg-purple-500/20 rounded-full flex items-center justify-center">
                <svg
                  className="w-8 h-8 text-purple-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 16l4.586-4.586a2 2 0 11-2.828 0l-4.414-4.582a2 2 0 00-3.575 2l-1.629-1.63a2 2 0 000 2.828z"
                  />
                </svg>
              </div>
              <h4 className="text-white font-bold mb-2">Генерация изображений</h4>
              <p className="text-gray-400 text-sm">IMAGEN 3, Midjourney</p>
            </div>

            <div className="text-center">
              <div className="w-16 h-16 mx-auto mb-3 bg-red-500/20 rounded-full flex items-center justify-center">
                <svg
                  className="w-8 h-8 text-red-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 19V6l12-3v13M9 19c-5.1.5-9-10-9-10s5 4.9 10 10 10a9 9 0 0010 9c0 2.5-1 5-4.3 6z"
                  />
                </svg>
              </div>
              <h4 className="text-white font-bold mb-2">Генерация аудио</h4>
              <p className="text-gray-400 text-sm">GEMINI Audio</p>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-white/10 mt-16">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <div className="text-center text-gray-400 text-sm">
            <p>Pandora Studio — Бета версия</p>
            <p className="mt-2 text-xs">© 2024 Все права защищены</p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Navigation;
