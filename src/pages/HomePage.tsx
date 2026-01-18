import type React from "react";

const HomePage: React.FC = () => {
  return (
    <div className="min-h-screen bg-[#020202] text-white">
      {/* Header */}
      <header className="border-b border-white/10">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <h1 className="text-2xl font-bold text-white">Pandora</h1>
              <span className="text-gray-400 text-sm">v1.0</span>
            </div>

            <nav className="flex items-center gap-6">
              <a href="/" className="text-white font-mono text-sm border-b-2 border-white pb-1">
                Главная
              </a>
              <a
                href="/studio"
                className="text-gray-300 hover:text-yellow-400 transition-colors font-mono text-sm flex items-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9.663 17h4.673M12 3v1m6.364 1.636l.636.636 4.636 4.636M21 12h-3m0 0v-3m0 3h3"
                  />
                </svg>
                Studio
              </a>
            </nav>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative py-20">
        {/* Background Effects */}
        <div className="absolute inset-0">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_30%,_rgba(255,255,0,0.1)_0%,_rgba(0,0,0,0)_60%)]" />
          <div className="absolute inset-0 bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.1)_50%),linear-gradient(90deg,rgba(255,0,0,0.06),rgba(0,255,0,0.02),rgba(0,0,255,0.06))] bg-[length:100%_4px,3px_100%] opacity-20" />
        </div>

        <div className="relative max-w-6xl mx-auto px-4 text-center">
          <h2 className="text-5xl md:text-6xl font-bold text-white mb-6 tracking-tight">
            Добро пожаловать в{" "}
            <span className="text-transparent bg-clip-text text-transparent bg-gradient-to-r from-pandora-cyan via-blue-400 to-purple-500">
              Pandora
            </span>
          </h2>
          <p className="text-xl text-gray-300 mb-8 max-w-3xl mx-auto leading-relaxed">
            Платформа следующего поколения для создания уникального контента с помощью
            искусственного интеллекта
          </p>

          <div className="flex flex-col sm:flex-row gap-6 justify-center items-center">
            <a
              href="/studio"
              className="group relative inline-flex items-center gap-3 px-8 py-4 bg-gradient-to-r from-yellow-500 to-orange-600 hover:from-yellow-400 hover:to-orange-500 text-white font-bold rounded-lg transition-all duration-300 transform hover:scale-105 shadow-lg hover:shadow-yellow-500/25"
            >
              <svg
                className="w-6 h-6 group-hover:rotate-12 transition-transform duration-300"
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
              <span>Попробовать Studio</span>
              <div className="absolute inset-0 bg-white/10 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
            </a>

            <a
              href="/navigation"
              className="group inline-flex items-center gap-3 px-8 py-4 bg-black/60 backdrop-blur-md border border-white/10 hover:bg-white/10 hover:border-white/20 text-white font-mono rounded-lg transition-all duration-300"
            >
              <svg
                className="w-6 h-6 group-hover:translate-x-1 transition-transform duration-300"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 6h16M4 12h16M4 18h16"
                />
              </svg>
              <span>Узнать больше</span>
            </a>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-20">
        <div className="max-w-6xl mx-auto px-4">
          <h3 className="text-3xl font-bold text-white mb-12 text-center">Возможности платформы</h3>

          <div className="grid md:grid-cols-3 gap-8">
            <div className="bg-black/40 backdrop-blur-sm border border-white/5 rounded-lg p-6 text-center group hover:bg-white/5 transition-all duration-300">
              <div className="w-16 h-16 mx-auto mb-4 bg-gradient-to-br from-blue-500/20 to-blue-600/20 rounded-full flex items-center justify-center group-hover:scale-110 transition-transform duration-300">
                <svg
                  className="w-8 h-8 text-blue-400"
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
              <h4 className="text-xl font-bold text-white mb-2">Генерация видео</h4>
              <p className="text-gray-400 text-sm">VEO 3.1, SORA</p>
            </div>

            <div className="bg-black/40 backdrop-blur-sm border border-white/5 rounded-lg p-6 text-center group hover:bg-white/5 transition-all duration-300">
              <div className="w-16 h-16 mx-auto mb-4 bg-gradient-to-br from-green-500/20 to-green-600/20 rounded-full flex items-center justify-center group-hover:scale-110 transition-transform duration-300">
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
              <h4 className="text-xl font-bold text-white mb-2">Генерация изображений</h4>
              <p className="text-gray-400 text-sm">IMAGEN 3, Midjourney</p>
            </div>

            <div className="bg-black/40 backdrop-blur-sm border border-white/5 rounded-lg p-6 text-center group hover:bg-white/5 transition-all duration-300">
              <div className="w-16 h-16 mx-auto mb-4 bg-gradient-to-br from-purple-500/20 to-purple-600/20 rounded-full flex items-center justify-center group-hover:scale-110 transition-transform duration-300">
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
                    d="M9 19V6l12-3v13M9 19c-5.1.5-9-10-9-10s5 4.9 10 10 10a9 9 0 0010 9c0 2.5-1 5-4.3 6z"
                  />
                </svg>
              </div>
              <h4 className="text-xl font-bold text-white mb-2">Генерация аудио</h4>
              <p className="text-gray-400 text-sm">GEMINI Audio</p>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/10 py-8">
        <div className="max-w-6xl mx-auto px-4 text-center">
          <p className="text-gray-400 text-sm">© 2024 Pandora. Все права защищены.</p>
        </div>
      </footer>
    </div>
  );
};

export default HomePage;
