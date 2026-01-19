import type React from "react";
import { Navigate } from "react-router-dom";

const StudioPage: React.FC = () => {
  // временная проверка роли админа
  const isAdmin =
    localStorage.getItem("userRole") === "admin" || localStorage.getItem("userRole") === "beta";

  if (!isAdmin) {
    return (
      <div className="min-h-screen bg-[#020202] text-white flex items-center justify-center font-mono">
        <div className="text-center max-w-md mx-auto p-8">
          <div className="mb-8">
            <div className="w-20 h-20 mx-auto mb-4 border-2 border-yellow-500/30 rounded-full flex items-center justify-center">
              <svg
                className="w-12 h-12 text-yellow-500"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                role="img"
                aria-label="Beta icon"
              >
                <title>Beta icon</title>
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 9v2m0 4v-6m0 4v6m0-10V7m0 4h8a2 2 0 002-2V7a2 2 0 00-2-2h-4a2 2 0 00-2 2v10a2 2 0 002 2h4a2 2 0 002-2V7a2 2 0 00-2-2h-4z"
                />
              </svg>
            </div>
            <h1 className="text-3xl font-bold text-white mb-4">STUDIO IS IN BETA</h1>
          </div>

          <div className="bg-black/60 backdrop-blur-md border border-white/10 rounded-lg p-6 mb-6">
            <h2 className="text-xl text-yellow-400 font-bold mb-4">🔒 Access Restricted</h2>
            <p className="text-gray-300 mb-6 leading-relaxed">
              Studio находится в закрытой бете. Доступ ограничен администраторами и
              бета-тестировщиками.
            </p>
            <div className="space-y-3 text-sm">
              <div className="flex items-center gap-3 p-3 bg-white/5 rounded border border-white/10">
                <div className="w-8 h-8 bg-yellow-500/20 rounded-full flex items-center justify-center">
                  <svg
                    className="w-5 h-5 text-yellow-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                    role="img"
                    aria-label="Admin access icon"
                  >
                    <title>Admin access icon</title>
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0"
                    />
                  </svg>
                </div>
                <div>
                  <div className="font-bold text-white">Для администраторов</div>
                  <div className="text-gray-400 text-xs">Полный доступ к функциям генерации</div>
                </div>
              </div>

              <div className="flex items-center gap-3 p-3 bg-white/5 rounded border border-white/10">
                <div className="w-8 h-8 bg-blue-500/20 rounded-full flex items-center justify-center">
                  <svg
                    className="w-5 h-5 text-blue-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                    role="img"
                    aria-label="Beta tester access icon"
                  >
                    <title>Beta tester access icon</title>
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M15 12a3 3 0 11-6 0 3 3 0 016 0zm-4 8a3 3 0 11-6 0 3 3 0 016 0zm-4-8a3 3 0 11-6 0 3 3 0 016 0z"
                    />
                  </svg>
                </div>
                <div>
                  <div className="font-bold text-white">Для бета-тестеровщиков</div>
                  <div className="text-gray-400 text-xs">Ограниченный доступ к функциям</div>
                </div>
              </div>
            </div>

            <div className="border-t border-white/10 pt-4">
              <p className="text-gray-400 text-xs mb-2">Если вы должны иметь доступ, пожалуйста:</p>
              <ol className="text-gray-300 text-sm space-y-2 list-decimal list-inside">
                <li>Убедитесь что вы вошли как администратор</li>
                <li>Очистите кэш браузера (Ctrl+F5)</li>
                <li>Проверьте консоль браузера на ошибки</li>
                <li>Свяжитесь с командой для получения доступа</li>
              </ol>
            </div>
          </div>

          <div className="mt-8">
            <button
              type="button"
              onClick={() => window.history.back()}
              className="px-6 py-3 bg-white/10 hover:bg-white/20 text-white border border-white/20 hover:border-white/40 rounded-lg transition-all duration-200 font-mono text-sm"
            >
              ← Назад к главному
            </button>
          </div>
        </div>

        {/* Фоновый эффект */}
        <div className="fixed inset-0 pointer-events-none">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_30%,_rgba(255,255,0,0.1)_0%,_rgba(0,0,0,0)_60%)]" />
          <div className="absolute inset-0 bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.1)_50%),linear-gradient(90deg,rgba(255,0,0,0.06),rgba(0,255,0,0.02),rgba(0,0,255,0.06))] bg-[length:100%_4px,3px_100%] opacity-20" />
        </div>
      </div>
    );
  }

  // Если админ - перенаправляем на страницу студии
  return <Navigate to="/studio" replace />;
};

export default StudioPage;
