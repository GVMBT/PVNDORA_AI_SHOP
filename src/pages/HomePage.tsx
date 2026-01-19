import type React from "react";

const HomePage: React.FC = () => {
  return (
    <div className="min-h-screen bg-[#020202] text-white">
      {/* Header */}
      <header className="border-white/10 border-b">
        <div className="mx-auto max-w-7xl px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <h1 className="font-bold text-2xl text-white">Pandora</h1>
              <span className="text-gray-400 text-sm">v1.0</span>
            </div>

            <nav className="flex items-center gap-6">
              <a className="border-white border-b-2 pb-1 font-mono text-sm text-white" href="/">
                Главная
              </a>
              <a
                className="flex items-center gap-2 font-mono text-gray-300 text-sm transition-colors hover:text-yellow-400"
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
          <div className="absolute inset-0 bg-[length:100%_4px,3px_100%] bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.1)_50%),linear-gradient(90deg,rgba(255,0,0,0.06),rgba(0,255,0,0.02),rgba(0,0,255,0.06))] opacity-20" />
        </div>

        <div className="relative mx-auto max-w-6xl px-4 text-center">
          <h2 className="mb-6 font-bold text-5xl text-white tracking-tight md:text-6xl">
            Добро пожаловать в{" "}
            <span className="bg-gradient-to-r from-pandora-cyan via-blue-400 to-purple-500 bg-clip-text text-transparent text-transparent">
              Pandora
            </span>
          </h2>
          <p className="mx-auto mb-8 max-w-3xl text-gray-300 text-xl leading-relaxed">
            Платформа следующего поколения для создания уникального контента с помощью
            искусственного интеллекта
          </p>

          <div className="flex flex-col items-center justify-center gap-6 sm:flex-row">
            <a
              className="group relative inline-flex transform items-center gap-3 rounded-lg bg-gradient-to-r from-yellow-500 to-orange-600 px-8 py-4 font-bold text-white shadow-lg transition-all duration-300 hover:scale-105 hover:from-yellow-400 hover:to-orange-500 hover:shadow-yellow-500/25"
              href="/studio"
            >
              <svg
                className="h-6 w-6 transition-transform duration-300 group-hover:rotate-12"
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
              <span>Попробовать Studio</span>
              <div className="absolute inset-0 rounded-lg bg-white/10 opacity-0 transition-opacity duration-300 group-hover:opacity-100" />
            </a>

            <a
              className="group inline-flex items-center gap-3 rounded-lg border border-white/10 bg-black/60 px-8 py-4 font-mono text-white backdrop-blur-md transition-all duration-300 hover:border-white/20 hover:bg-white/10"
              href="/navigation"
            >
              <svg
                className="h-6 w-6 transition-transform duration-300 group-hover:translate-x-1"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  d="M4 6h16M4 12h16M4 18h16"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                />
              </svg>
              <span>Узнать больше</span>
            </a>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-20">
        <div className="mx-auto max-w-6xl px-4">
          <h3 className="mb-12 text-center font-bold text-3xl text-white">Возможности платформы</h3>

          <div className="grid gap-8 md:grid-cols-3">
            <div className="group rounded-lg border border-white/5 bg-black/40 p-6 text-center backdrop-blur-sm transition-all duration-300 hover:bg-white/5">
              <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-br from-blue-500/20 to-blue-600/20 transition-transform duration-300 group-hover:scale-110">
                <svg
                  className="h-8 w-8 text-blue-400"
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
              <h4 className="mb-2 font-bold text-white text-xl">Генерация видео</h4>
              <p className="text-gray-400 text-sm">VEO 3.1, SORA</p>
            </div>

            <div className="group rounded-lg border border-white/5 bg-black/40 p-6 text-center backdrop-blur-sm transition-all duration-300 hover:bg-white/5">
              <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-br from-green-500/20 to-green-600/20 transition-transform duration-300 group-hover:scale-110">
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
              <h4 className="mb-2 font-bold text-white text-xl">Генерация изображений</h4>
              <p className="text-gray-400 text-sm">IMAGEN 3, Midjourney</p>
            </div>

            <div className="group rounded-lg border border-white/5 bg-black/40 p-6 text-center backdrop-blur-sm transition-all duration-300 hover:bg-white/5">
              <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-br from-purple-500/20 to-purple-600/20 transition-transform duration-300 group-hover:scale-110">
                <svg
                  className="h-8 w-8 text-purple-400"
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
              <h4 className="mb-2 font-bold text-white text-xl">Генерация аудио</h4>
              <p className="text-gray-400 text-sm">GEMINI Audio</p>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-white/10 border-t py-8">
        <div className="mx-auto max-w-6xl px-4 text-center">
          <p className="text-gray-400 text-sm">© 2024 Pandora. Все права защищены.</p>
        </div>
      </footer>
    </div>
  );
};

export default HomePage;
