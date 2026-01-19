import type React from "react";
import { Navigate } from "react-router-dom";

const StudioPage: React.FC = () => {
  // временная проверка роли админа
  const isAdmin =
    localStorage.getItem("userRole") === "admin" || localStorage.getItem("userRole") === "beta";

  if (!isAdmin) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#020202] font-mono text-white">
        <div className="mx-auto max-w-md p-8 text-center">
          <div className="mb-8">
            <div className="mx-auto mb-4 flex h-20 w-20 items-center justify-center rounded-full border-2 border-yellow-500/30">
              <svg
                aria-label="Beta icon"
                className="h-12 w-12 text-yellow-500"
                fill="none"
                role="img"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <title>Beta icon</title>
                <path
                  d="M12 9v2m0 4v-6m0 4v6m0-10V7m0 4h8a2 2 0 002-2V7a2 2 0 00-2-2h-4a2 2 0 00-2 2v10a2 2 0 002 2h4a2 2 0 002-2V7a2 2 0 00-2-2h-4z"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                />
              </svg>
            </div>
            <h1 className="mb-4 font-bold text-3xl text-white">STUDIO IS IN BETA</h1>
          </div>

          <div className="mb-6 rounded-lg border border-white/10 bg-black/60 p-6 backdrop-blur-md">
            <h2 className="mb-4 font-bold text-xl text-yellow-400">🔒 Access Restricted</h2>
            <p className="mb-6 text-gray-300 leading-relaxed">
              Studio находится в закрытой бете. Доступ ограничен администраторами и
              бета-тестировщиками.
            </p>
            <div className="space-y-3 text-sm">
              <div className="flex items-center gap-3 rounded border border-white/10 bg-white/5 p-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-yellow-500/20">
                  <svg
                    aria-label="Admin access icon"
                    className="h-5 w-5 text-yellow-400"
                    fill="none"
                    role="img"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <title>Admin access icon</title>
                    <path
                      d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                    />
                  </svg>
                </div>
                <div>
                  <div className="font-bold text-white">Для администраторов</div>
                  <div className="text-gray-400 text-xs">Полный доступ к функциям генерации</div>
                </div>
              </div>

              <div className="flex items-center gap-3 rounded border border-white/10 bg-white/5 p-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-500/20">
                  <svg
                    aria-label="Beta tester access icon"
                    className="h-5 w-5 text-blue-400"
                    fill="none"
                    role="img"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <title>Beta tester access icon</title>
                    <path
                      d="M15 12a3 3 0 11-6 0 3 3 0 016 0zm-4 8a3 3 0 11-6 0 3 3 0 016 0zm-4-8a3 3 0 11-6 0 3 3 0 016 0z"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                    />
                  </svg>
                </div>
                <div>
                  <div className="font-bold text-white">Для бета-тестеровщиков</div>
                  <div className="text-gray-400 text-xs">Ограниченный доступ к функциям</div>
                </div>
              </div>
            </div>

            <div className="border-white/10 border-t pt-4">
              <p className="mb-2 text-gray-400 text-xs">Если вы должны иметь доступ, пожалуйста:</p>
              <ol className="list-inside list-decimal space-y-2 text-gray-300 text-sm">
                <li>Убедитесь что вы вошли как администратор</li>
                <li>Очистите кэш браузера (Ctrl+F5)</li>
                <li>Проверьте консоль браузера на ошибки</li>
                <li>Свяжитесь с командой для получения доступа</li>
              </ol>
            </div>
          </div>

          <div className="mt-8">
            <button
              className="rounded-lg border border-white/20 bg-white/10 px-6 py-3 font-mono text-sm text-white transition-all duration-200 hover:border-white/40 hover:bg-white/20"
              onClick={() => window.history.back()}
              type="button"
            >
              ← Назад к главному
            </button>
          </div>
        </div>

        {/* Фоновый эффект */}
        <div className="pointer-events-none fixed inset-0">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_30%,_rgba(255,255,0,0.1)_0%,_rgba(0,0,0,0)_60%)]" />
          <div className="absolute inset-0 bg-[length:100%_4px,3px_100%] bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.1)_50%),linear-gradient(90deg,rgba(255,0,0,0.06),rgba(0,255,0,0.02),rgba(0,0,255,0.06))] opacity-20" />
        </div>
      </div>
    );
  }

  // Если админ - перенаправляем на страницу студии
  return <Navigate replace to="/studio" />;
};

export default StudioPage;
