/**
 * Partner Application Modal
 *
 * Cyberpunk-styled form for users to apply for Elite Operator (VIP) status.
 * Matches PVNDORA's sci-fi neon aesthetic.
 */

import React, { useState, useCallback, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  X,
  Send,
  Loader2,
  CheckCircle,
  AlertCircle,
  Shield,
  Zap,
  Users,
  Trophy,
} from "lucide-react";

interface PartnerApplicationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: PartnerApplicationData) => Promise<{ success: boolean; message?: string }>;
  existingApplication?: {
    status: string;
    created_at: string;
    admin_comment?: string;
  } | null;
}

export interface PartnerApplicationData {
  email: string;
  phone: string;
  source: string;
  audienceSize: string;
  description: string;
  expectedVolume?: string;
  socialLinks?: Record<string, string>;
}

const AUDIENCE_SOURCES = [
  { value: "telegram", label: "Telegram-сеть" },
  { value: "youtube", label: "YouTube-канал" },
  { value: "instagram", label: "Instagram" },
  { value: "tiktok", label: "TikTok" },
  { value: "twitter", label: "Twitter/X" },
  { value: "website", label: "Веб-портал" },
  { value: "other", label: "Другой источник" },
];

const AUDIENCE_SIZES = [
  { value: "1-1000", label: "< 1K агентов" },
  { value: "1000-5000", label: "1K - 5K агентов" },
  { value: "5000-10000", label: "5K - 10K агентов" },
  { value: "10000-50000", label: "10K - 50K агентов" },
  { value: "50000+", label: "50K+ агентов" },
];

const BENEFITS = [
  { icon: Zap, text: "Повышенные комиссии до 15%" },
  { icon: Shield, text: "Приоритетная поддержка 24/7" },
  { icon: Users, text: "Персональный куратор" },
  { icon: Trophy, text: "Эксклюзивные модули" },
];

export const PartnerApplicationModal: React.FC<PartnerApplicationModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  existingApplication,
}) => {
  const [formData, setFormData] = useState<PartnerApplicationData>({
    email: "",
    phone: "",
    source: "",
    audienceSize: "",
    description: "",
    expectedVolume: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Reset form state when modal opens
  useEffect(() => {
    if (isOpen && !existingApplication) {
      setSubmitted(false);
      setError(null);
      setFormData({
        email: "",
        phone: "",
        source: "",
        audienceSize: "",
        description: "",
        expectedVolume: "",
      });
    }
  }, [isOpen, existingApplication]);

  const handleChange = useCallback((field: keyof PartnerApplicationData, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    setError(null);
  }, []);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();

      if (
        !formData.email ||
        !formData.phone ||
        !formData.source ||
        !formData.audienceSize ||
        !formData.description
      ) {
        setError("ОШИБКА: Заполните все обязательные поля");
        return;
      }

      if (!formData.email.includes("@")) {
        setError("ОШИБКА: Некорректный формат email");
        return;
      }

      setSubmitting(true);
      setError(null);

      try {
        const result = await onSubmit(formData);
        if (result.success) {
          setSubmitted(true);
        } else {
          setError(result.message || "СБОЙ ПЕРЕДАЧИ: Повторите попытку");
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "КРИТИЧЕСКАЯ ОШИБКА");
      } finally {
        setSubmitting(false);
      }
    },
    [formData, onSubmit]
  );

  // Show existing application status
  if (existingApplication) {
    const statusInfo = {
      pending: {
        color: "text-yellow-400 border-yellow-400/30",
        bg: "bg-yellow-400/10",
        text: "ОБРАБОТКА...",
        subtext: "Заявка на рассмотрении",
      },
      approved: {
        color: "text-green-400 border-green-400/30",
        bg: "bg-green-400/10",
        text: "ОДОБРЕНО",
        subtext: "Добро пожаловать в элиту",
      },
      rejected: {
        color: "text-red-400 border-red-400/30",
        bg: "bg-red-400/10",
        text: "ОТКЛОНЕНО",
        subtext: "Заявка не прошла проверку",
      },
    }[existingApplication.status] || {
      color: "text-gray-400 border-gray-400/30",
      bg: "bg-gray-400/10",
      text: existingApplication.status,
      subtext: "",
    };

    return (
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/90 backdrop-blur-md"
            onClick={onClose}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0, y: 20 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.9, opacity: 0, y: 20 }}
              className={`relative bg-black/80 border ${statusInfo.color} p-6 w-full max-w-md overflow-hidden`}
              onClick={(e) => e.stopPropagation()}
            >
              {/* Scanlines overlay */}
              <div className="absolute inset-0 pointer-events-none bg-[repeating-linear-gradient(0deg,rgba(0,0,0,0.1)_0px,rgba(0,0,0,0.1)_1px,transparent_1px,transparent_2px)]" />

              {/* Corner accents */}
              <div className="absolute top-0 left-0 w-4 h-4 border-l-2 border-t-2 border-current opacity-50" />
              <div className="absolute top-0 right-0 w-4 h-4 border-r-2 border-t-2 border-current opacity-50" />
              <div className="absolute bottom-0 left-0 w-4 h-4 border-l-2 border-b-2 border-current opacity-50" />
              <div className="absolute bottom-0 right-0 w-4 h-4 border-r-2 border-b-2 border-current opacity-50" />

              <div className="relative z-10">
                <div className="flex items-center justify-between mb-6">
                  <div className="text-[10px] font-mono tracking-widest text-gray-500">
                    STATUS_CHECK // ELITE_PROGRAM
                  </div>
                  <button
                    onClick={onClose}
                    className="text-gray-500 hover:text-white transition-colors"
                  >
                    <X size={18} />
                  </button>
                </div>

                <div className="text-center py-6">
                  <div
                    className={`inline-flex items-center justify-center w-20 h-20 ${statusInfo.bg} border ${statusInfo.color} mb-4`}
                  >
                    {existingApplication.status === "pending" ? (
                      <Loader2 className="w-10 h-10 animate-spin" />
                    ) : existingApplication.status === "approved" ? (
                      <CheckCircle className="w-10 h-10" />
                    ) : (
                      <AlertCircle className="w-10 h-10" />
                    )}
                  </div>
                  <p
                    className={`text-2xl font-mono font-bold tracking-wider ${statusInfo.color.split(" ")[0]}`}
                  >
                    {statusInfo.text}
                  </p>
                  <p className="text-gray-500 text-sm mt-2 font-mono">{statusInfo.subtext}</p>
                  <p className="text-gray-600 text-xs mt-4 font-mono">
                    TIMESTAMP:{" "}
                    {new Date(existingApplication.created_at).toLocaleDateString("ru-RU")}
                  </p>
                  {existingApplication.admin_comment && (
                    <div className="mt-4 p-3 bg-white/5 border border-white/10 text-xs text-gray-400 font-mono text-left">
                      <span className="text-pandora-cyan">&gt;</span>{" "}
                      {existingApplication.admin_comment}
                    </div>
                  )}
                </div>

                <button
                  onClick={onClose}
                  className="w-full py-3 bg-white/5 hover:bg-white/10 border border-white/20 text-white font-mono text-sm uppercase tracking-wider transition-all"
                >
                  Закрыть терминал
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    );
  }

  // Show success state
  if (submitted) {
    return (
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/90 backdrop-blur-md"
            onClick={onClose}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0, y: 20 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.9, opacity: 0, y: 20 }}
              className="relative bg-black/80 border border-green-400/30 p-6 w-full max-w-md text-center overflow-hidden"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Glow effect */}
              <div className="absolute inset-0 bg-green-400/5" />

              <div className="relative z-10">
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ type: "spring", delay: 0.2 }}
                  className="inline-flex items-center justify-center w-20 h-20 bg-green-400/10 border border-green-400/30 mb-4"
                >
                  <CheckCircle className="w-10 h-10 text-green-400" />
                </motion.div>

                <h2 className="text-xl font-mono font-bold text-green-400 mb-2 tracking-wider">
                  ЗАПРОС ПРИНЯТ
                </h2>
                <p className="text-gray-400 mb-6 font-mono text-sm">
                  Ваша заявка в очереди на обработку.
                  <br />
                  Ожидайте ответ в течение 24-48 часов.
                </p>

                <button
                  onClick={onClose}
                  className="w-full py-3 bg-green-400/20 hover:bg-green-400/30 border border-green-400/50 text-green-400 font-mono text-sm uppercase tracking-wider transition-all"
                >
                  Подтвердить
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    );
  }

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/90 backdrop-blur-md overflow-y-auto"
          onClick={onClose}
        >
          <motion.div
            initial={{ scale: 0.95, opacity: 0, y: 20 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            exit={{ scale: 0.95, opacity: 0, y: 20 }}
            className="relative bg-black/80 border border-pandora-cyan/30 w-full max-w-lg my-8 overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header bar */}
            <div className="bg-pandora-cyan/10 border-b border-pandora-cyan/30 px-4 py-3 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Shield className="text-pandora-cyan" size={18} />
                <span className="text-xs font-mono text-pandora-cyan tracking-wider">
                  ELITE_OPERATOR // РЕГИСТРАЦИЯ
                </span>
              </div>
              <button
                onClick={onClose}
                className="text-gray-500 hover:text-pandora-cyan transition-colors"
              >
                <X size={18} />
              </button>
            </div>

            <div className="p-6">
              {/* Benefits Grid */}
              <div className="grid grid-cols-2 gap-3 mb-6">
                {BENEFITS.map((benefit, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.1 }}
                    className="bg-white/5 border border-white/10 p-3 flex items-center gap-2"
                  >
                    <benefit.icon size={14} className="text-pandora-cyan flex-shrink-0" />
                    <span className="text-[11px] font-mono text-gray-300">{benefit.text}</span>
                  </motion.div>
                ))}
              </div>

              {/* Form */}
              <form onSubmit={handleSubmit} className="space-y-4">
                {/* Email */}
                <div>
                  <label className="block text-[10px] font-mono text-gray-500 mb-1 tracking-wider">
                    EMAIL_ADDRESS *
                  </label>
                  <input
                    type="email"
                    value={formData.email}
                    onChange={(e) => handleChange("email", e.target.value)}
                    className="w-full bg-black/50 border border-white/20 px-3 py-2.5 text-white text-sm font-mono focus:border-pandora-cyan focus:outline-none focus:bg-pandora-cyan/5 transition-all placeholder:text-gray-600"
                    placeholder="operator@network.sys"
                  />
                </div>

                {/* Phone */}
                <div>
                  <label className="block text-[10px] font-mono text-gray-500 mb-1 tracking-wider">
                    CONTACT_LINE *
                  </label>
                  <input
                    type="tel"
                    value={formData.phone}
                    onChange={(e) => handleChange("phone", e.target.value)}
                    className="w-full bg-black/50 border border-white/20 px-3 py-2.5 text-white text-sm font-mono focus:border-pandora-cyan focus:outline-none focus:bg-pandora-cyan/5 transition-all placeholder:text-gray-600"
                    placeholder="+7 (XXX) XXX-XX-XX"
                  />
                </div>

                {/* Source & Audience - 2 column */}
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[10px] font-mono text-gray-500 mb-1 tracking-wider">
                      NETWORK_SOURCE *
                    </label>
                    <select
                      value={formData.source}
                      onChange={(e) => handleChange("source", e.target.value)}
                      className="w-full bg-black/50 border border-white/20 px-3 py-2.5 text-white text-sm font-mono focus:border-pandora-cyan focus:outline-none appearance-none cursor-pointer"
                    >
                      <option value="" className="bg-black">
                        Выбрать...
                      </option>
                      {AUDIENCE_SOURCES.map((s) => (
                        <option key={s.value} value={s.value} className="bg-black">
                          {s.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-[10px] font-mono text-gray-500 mb-1 tracking-wider">
                      NETWORK_SIZE *
                    </label>
                    <select
                      value={formData.audienceSize}
                      onChange={(e) => handleChange("audienceSize", e.target.value)}
                      className="w-full bg-black/50 border border-white/20 px-3 py-2.5 text-white text-sm font-mono focus:border-pandora-cyan focus:outline-none appearance-none cursor-pointer"
                    >
                      <option value="" className="bg-black">
                        Выбрать...
                      </option>
                      {AUDIENCE_SIZES.map((s) => (
                        <option key={s.value} value={s.value} className="bg-black">
                          {s.label}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                {/* Description */}
                <div>
                  <label className="block text-[10px] font-mono text-gray-500 mb-1 tracking-wider">
                    MISSION_BRIEF *
                  </label>
                  <textarea
                    value={formData.description}
                    onChange={(e) => handleChange("description", e.target.value)}
                    className="w-full bg-black/50 border border-white/20 px-3 py-2.5 text-white text-sm font-mono focus:border-pandora-cyan focus:outline-none focus:bg-pandora-cyan/5 transition-all resize-none placeholder:text-gray-600"
                    rows={3}
                    placeholder="Опишите вашу деятельность, контент, аудиторию..."
                  />
                </div>

                {/* Expected Volume (optional) */}
                <div>
                  <label className="block text-[10px] font-mono text-gray-500 mb-1 tracking-wider">
                    PROJECTED_OUTPUT <span className="text-gray-600">(опционально)</span>
                  </label>
                  <input
                    type="text"
                    value={formData.expectedVolume || ""}
                    onChange={(e) => handleChange("expectedVolume", e.target.value)}
                    className="w-full bg-black/50 border border-white/20 px-3 py-2.5 text-white text-sm font-mono focus:border-pandora-cyan focus:outline-none focus:bg-pandora-cyan/5 transition-all placeholder:text-gray-600"
                    placeholder="10-20 операций/месяц"
                  />
                </div>

                {/* Error */}
                {error && (
                  <motion.div
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    className="flex items-center gap-2 text-red-400 text-xs font-mono bg-red-400/10 border border-red-400/30 p-3"
                  >
                    <AlertCircle size={14} />
                    {error}
                  </motion.div>
                )}

                {/* Submit */}
                <button
                  type="submit"
                  disabled={submitting}
                  className="w-full py-3.5 bg-pandora-cyan/20 hover:bg-pandora-cyan/30 disabled:bg-gray-800 disabled:cursor-not-allowed border border-pandora-cyan/50 hover:border-pandora-cyan text-pandora-cyan font-mono text-sm uppercase tracking-wider transition-all flex items-center justify-center gap-2 group"
                >
                  {submitting ? (
                    <>
                      <Loader2 size={16} className="animate-spin" />
                      <span>ПЕРЕДАЧА ДАННЫХ...</span>
                    </>
                  ) : (
                    <>
                      <Send size={16} className="group-hover:translate-x-1 transition-transform" />
                      <span>ОТПРАВИТЬ ЗАПРОС</span>
                    </>
                  )}
                </button>
              </form>

              {/* Footer note */}
              <p className="text-[10px] font-mono text-gray-600 text-center mt-4">
                После одобрения вы получите уведомление в Telegram
              </p>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default PartnerApplicationModal;
