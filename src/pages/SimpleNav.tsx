import type React from "react";

const SimpleNav: React.FC = () => {
  return (
    <div className="min-h-screen bg-[#020202] text-white">
      {/* Header */}
      <header className="border-white/10 border-b">
        <div className="mx-auto max-w-7xl px-4 py-4">
          <div className="flex items-center justify-between">
            <h1 className="font-bold text-2xl text-white">Pandora Studio</h1>
            <div className="text-gray-400 text-sm">v1.0</div>
          </div>

          <nav className="flex items-center gap-6">
            <a
              className="rounded-lg border border-white/10 px-4 py-2 font-mono text-sm text-white transition-colors hover:border-white/20 hover:text-gray-200"
              href="/"
            >
              Главная
            </a>
            <a
              className="rounded-lg border border-yellow-500/30 bg-yellow-500/20 px-4 py-2 font-mono text-sm text-yellow-400 hover:border-yellow-500/50 hover:bg-yellow-500/30"
              href="/studio"
            >
              <svg
                className="mr-2 inline h-4 w-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
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
      </header>

      {/* Main Content */}
      <main className="mx-auto max-w-4xl px-4 py-12">
        <div className="mb-12 text-center">
          <h2 className="mb-6 font-bold text-4xl text-white">Добро пожаловать!</h2>
          <p className="mb-8 text-gray-300 text-xl">Выберите действие ниже</p>
        </div>

        {/* Action Cards */}
        <div className="mb-12 grid gap-8 md:grid-cols-2">
          <a
            className="group rounded-lg border border-white/10 bg-black/60 p-8 text-center backdrop-blur-md transition-all hover:bg-white/10"
            href="/"
          >
            <div className="mb-4 text-4xl">🏠</div>
            <h3 className="mb-2 font-bold text-white text-xl">На главную</h3>
            <p className="text-gray-400">Вернуться на главный экран</p>
          </a>

          <a
            className="group rounded-lg border border-white/10 bg-black/60 p-8 text-center backdrop-blur-md transition-all hover:bg-white/10"
            href="/studio"
          >
            <div className="mb-4 text-4xl">🎨</div>
            <h3 className="mb-2 font-bold text-white text-xl">Studio</h3>
            <p className="text-yellow-400">Требуются права доступа (Beta)</p>
          </a>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-white/10 border-t py-8">
        <div className="mx-auto max-w-7xl px-4 text-center">
          <p className="text-gray-400 text-sm">© 2024 Pandora Studio. Все права защищены.</p>
        </div>
      </footer>
    </div>
  );
};

export default SimpleNav;
