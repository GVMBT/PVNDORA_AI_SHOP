import type React from "react";

const SimpleNav: React.FC = () => {
  return (
    <div className="min-h-screen bg-[#020202] text-white">
      {/* Header */}
      <header className="border-b border-white/10">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold text-white">Pandora Studio</h1>
            <div className="text-gray-400 text-sm">v1.0</div>
          </div>

          <nav className="flex items-center gap-6">
            <a
              href="/"
              className="text-white hover:text-gray-200 transition-colors font-mono text-sm px-4 py-2 rounded-lg border border-white/10 hover:border-white/20"
            >
              Главная
            </a>
            <a
              href="/studio"
              className="px-4 py-2 bg-yellow-500/20 border border-yellow-500/30 text-yellow-400 hover:bg-yellow-500/30 hover:border-yellow-500/50 rounded-lg font-mono text-sm"
            >
              <svg
                className="w-4 h-4 inline mr-2"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
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
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-4 py-12">
        <div className="text-center mb-12">
          <h2 className="text-4xl font-bold text-white mb-6">Добро пожаловать!</h2>
          <p className="text-xl text-gray-300 mb-8">Выберите действие ниже</p>
        </div>

        {/* Action Cards */}
        <div className="grid md:grid-cols-2 gap-8 mb-12">
          <a
            href="/"
            className="bg-black/60 backdrop-blur-md border border-white/10 rounded-lg p-8 text-center hover:bg-white/10 transition-all group"
          >
            <div className="text-4xl mb-4">🏠</div>
            <h3 className="text-xl font-bold text-white mb-2">На главную</h3>
            <p className="text-gray-400">Вернуться на главный экран</p>
          </a>

          <a
            href="/studio"
            className="bg-black/60 backdrop-blur-md border border-white/10 rounded-lg p-8 text-center hover:bg-white/10 transition-all group"
          >
            <div className="text-4xl mb-4">🎨</div>
            <h3 className="text-xl font-bold text-white mb-2">Studio</h3>
            <p className="text-yellow-400">Требуются права доступа (Beta)</p>
          </a>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-white/10 py-8">
        <div className="max-w-7xl mx-auto px-4 text-center">
          <p className="text-gray-400 text-sm">© 2024 Pandora Studio. Все права защищены.</p>
        </div>
      </footer>
    </div>
  );
};

export default SimpleNav;
