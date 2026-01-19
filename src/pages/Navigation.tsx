import type React from "react";

const Navigation: React.FC = () => {
  return (
    <div className="min-h-screen bg-[#020202] text-white">
      {/* Header */}
      <header className="border-white/10 border-b">
        <div className="mx-auto max-w-7xl px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <h1 className="font-bold text-2xl text-white">Pandora Studio</h1>
            </div>

            <nav className="flex items-center gap-6">
              <a
                className="font-mono text-gray-300 text-sm transition-colors hover:text-white"
                href="/"
              >
                Главная
              </a>
              <a
                className="flex items-center gap-2 rounded border border-yellow-500/30 bg-yellow-500/20 px-4 py-2 font-mono text-sm text-yellow-400 transition-all hover:border-yellow-500/50 hover:bg-yellow-500/30"
                href="/studio"
              >
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    d="M9.663 17h4.673M12 3v1m6.364 1.636l.636.636 4.636 4.636M21 12h-3m0 0v-3m0 3h3"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                  />
                </svg>
                Studio (BETA)
              </a>
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="mx-auto max-w-4xl px-4 py-12">
        <div className="mb-12 text-center">
          <h2 className="mb-6 font-bold text-4xl text-white">Добро пожаловать в Pandora Studio</h2>
          <p className="mx-auto mb-8 max-w-2xl text-gray-300 text-lg">
            Экспериментальная платформа для генерации контента с помощью нейросетей
          </p>
        </div>

        {/* Cards */}
        <div className="mb-12 grid gap-8 md:grid-cols-2">
          <div className="rounded-lg border border-white/10 bg-black/60 p-6 backdrop-blur-md">
            <div className="mb-4 flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-blue-500/20">
                <svg
                  className="h-6 w-6 text-blue-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    d="M15 10l4.553-2.276A8 8 0 010-11.448 0l-5.392 5.392L8.447 18.654a2 2 0 11-2.828 0l-4.582-4.582a6 6 0 110 8l6-6a6 6 0 000-12zM6 16v6l6-6"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                  />
                </svg>
              </div>
              <div>
                <h3 className="mb-2 font-bold text-white text-xl">Главная страница</h3>
                <p className="text-gray-400 text-sm">Основная информация и навигация</p>
              </div>
            </div>

            <div className="space-y-4">
              <a
                className="block w-full rounded-lg border border-white/10 bg-white/5 p-4 text-center transition-all hover:border-white/20 hover:bg-white/10"
                href="/"
              >
                <div className="font-mono text-white">Перейти на главную</div>
              </a>
            </div>
          </div>

          <div className="rounded-lg border border-white/10 bg-black/60 p-6 backdrop-blur-md">
            <div className="mb-4 flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-yellow-500/20">
                <svg
                  className="h-6 w-6 text-yellow-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    d="M12 9v2m0 4v-6m0 4v6m0-10V7m0 4h8a2 2 0 002-2V7a2 2 0 00-2-2h-4a2 2 0 00-2 2v10a2 2 0 002 2h4a2 2 0 002-2V7a2 2 0 00-2-2h-4z"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                  />
                </svg>
              </div>
              <div>
                <h3 className="mb-2 font-bold text-white text-xl">Studio</h3>
                <p className="text-gray-400 text-sm">Генерация видео, изображений и аудио</p>
              </div>
            </div>

            <div className="space-y-4">
              <a
                className="block w-full rounded-lg border border-yellow-500/30 bg-yellow-500/10 p-4 text-center transition-all hover:border-yellow-500/50 hover:bg-yellow-500/20"
                href="/studio"
              >
                <div className="font-mono text-yellow-400">Перейти в Studio</div>
                <div className="mt-1 text-xs text-yellow-500/60">Требуется права доступа</div>
              </a>
            </div>
          </div>
        </div>

        {/* Features */}
        <div className="rounded-lg border border-white/5 bg-black/40 p-8 backdrop-blur-sm">
          <h3 className="mb-6 text-center font-bold text-2xl text-white">Возможности Studio</h3>
          <div className="grid gap-6 md:grid-cols-3">
            <div className="text-center">
              <div className="mx-auto mb-3 flex h-16 w-16 items-center justify-center rounded-full bg-green-500/20">
                <svg
                  className="h-8 w-8 text-green-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    d="M21 15a2 2 0 11-4 0 2 2 0 014 0zM17 8H7a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2V10a2 2 0 00-2-2z"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                  />
                </svg>
              </div>
              <h4 className="mb-2 font-bold text-white">Генерация видео</h4>
              <p className="text-gray-400 text-sm">VEO 3.1, SORA и другие модели</p>
            </div>

            <div className="text-center">
              <div className="mx-auto mb-3 flex h-16 w-16 items-center justify-center rounded-full bg-purple-500/20">
                <svg
                  className="h-8 w-8 text-purple-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    d="M4 16l4.586-4.586a2 2 0 11-2.828 0l-4.414-4.582a2 2 0 00-3.575 2l-1.629-1.63a2 2 0 000 2.828z"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                  />
                </svg>
              </div>
              <h4 className="mb-2 font-bold text-white">Генерация изображений</h4>
              <p className="text-gray-400 text-sm">IMAGEN 3, Midjourney</p>
            </div>

            <div className="text-center">
              <div className="mx-auto mb-3 flex h-16 w-16 items-center justify-center rounded-full bg-red-500/20">
                <svg
                  className="h-8 w-8 text-red-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    d="M9 19V6l12-3v13M9 19c-5.1.5-9-10-9-10s5 4.9 10 10 10a9 9 0 0010 9c0 2.5-1 5-4.3 6z"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                  />
                </svg>
              </div>
              <h4 className="mb-2 font-bold text-white">Генерация аудио</h4>
              <p className="text-gray-400 text-sm">GEMINI Audio</p>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="mt-16 border-white/10 border-t">
        <div className="mx-auto max-w-7xl px-4 py-6">
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
