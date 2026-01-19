/**
 * Partner Application Modal
 *
 * Cyberpunk-styled form for users to apply for Elite Operator (VIP) status.
 * Matches PVNDORA's sci-fi neon aesthetic.
 */

import { AnimatePresence, motion } from "framer-motion";
import {
  AlertCircle,
  CheckCircle,
  Loader2,
  Send,
  Shield,
  Trophy,
  Users,
  X,
  Zap,
} from "lucide-react";
import type React from "react";
import { useCallback, useEffect, useState } from "react";

// Helper to get status icon (avoid nested ternary)
const getStatusIcon = (status: string) => {
  if (status === "pending") return <Loader2 className="h-10 w-10 animate-spin" />;
  if (status === "approved") return <CheckCircle className="h-10 w-10" />;
  return <AlertCircle className="h-10 w-10" />;
};

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
        !(
          formData.email &&
          formData.phone &&
          formData.source &&
          formData.audienceSize &&
          formData.description
        )
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
            animate={{ opacity: 1 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 p-4 backdrop-blur-md"
            exit={{ opacity: 0 }}
            initial={{ opacity: 0 }}
            onClick={onClose}
          >
            <motion.div
              animate={{ scale: 1, opacity: 1, y: 0 }}
              className={`relative border bg-black/80 ${statusInfo.color} w-full max-w-md overflow-hidden p-6`}
              exit={{ scale: 0.9, opacity: 0, y: 20 }}
              initial={{ scale: 0.9, opacity: 0, y: 20 }}
              onClick={(e) => e.stopPropagation()}
            >
              {/* Scanlines overlay */}
              <div className="pointer-events-none absolute inset-0 bg-[repeating-linear-gradient(0deg,rgba(0,0,0,0.1)_0px,rgba(0,0,0,0.1)_1px,transparent_1px,transparent_2px)]" />

              {/* Corner accents */}
              <div className="absolute top-0 left-0 h-4 w-4 border-current border-t-2 border-l-2 opacity-50" />
              <div className="absolute top-0 right-0 h-4 w-4 border-current border-t-2 border-r-2 opacity-50" />
              <div className="absolute bottom-0 left-0 h-4 w-4 border-current border-b-2 border-l-2 opacity-50" />
              <div className="absolute right-0 bottom-0 h-4 w-4 border-current border-r-2 border-b-2 opacity-50" />

              <div className="relative z-10">
                <div className="mb-6 flex items-center justify-between">
                  <div className="font-mono text-[10px] text-gray-500 tracking-widest">
                    STATUS_CHECK | ELITE_PROGRAM
                  </div>
                  <button
                    className="text-gray-500 transition-colors hover:text-white"
                    onClick={onClose}
                    type="button"
                  >
                    <X size={18} />
                  </button>
                </div>

                <div className="py-6 text-center">
                  <div
                    className={`inline-flex h-20 w-20 items-center justify-center ${statusInfo.bg} border ${statusInfo.color} mb-4`}
                  >
                    {getStatusIcon(existingApplication.status)}
                  </div>
                  <p
                    className={`font-bold font-mono text-2xl tracking-wider ${statusInfo.color.split(" ")[0]}`}
                  >
                    {statusInfo.text}
                  </p>
                  <p className="mt-2 font-mono text-gray-500 text-sm">{statusInfo.subtext}</p>
                  <p className="mt-4 font-mono text-gray-600 text-xs">
                    TIMESTAMP:{" "}
                    {new Date(existingApplication.created_at).toLocaleDateString("ru-RU")}
                  </p>
                  {existingApplication.admin_comment && (
                    <div className="mt-4 border border-white/10 bg-white/5 p-3 text-left font-mono text-gray-400 text-xs">
                      <span className="text-pandora-cyan">&gt;</span>{" "}
                      {existingApplication.admin_comment}
                    </div>
                  )}
                </div>

                <button
                  className="w-full border border-white/20 bg-white/5 py-3 font-mono text-sm text-white uppercase tracking-wider transition-all hover:bg-white/10"
                  onClick={onClose}
                  type="button"
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
            animate={{ opacity: 1 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 p-4 backdrop-blur-md"
            exit={{ opacity: 0 }}
            initial={{ opacity: 0 }}
            onClick={onClose}
          >
            <motion.div
              animate={{ scale: 1, opacity: 1, y: 0 }}
              className="relative w-full max-w-md overflow-hidden border border-green-400/30 bg-black/80 p-6 text-center"
              exit={{ scale: 0.9, opacity: 0, y: 20 }}
              initial={{ scale: 0.9, opacity: 0, y: 20 }}
              onClick={(e) => e.stopPropagation()}
            >
              {/* Glow effect */}
              <div className="absolute inset-0 bg-green-400/5" />

              <div className="relative z-10">
                <motion.div
                  animate={{ scale: 1 }}
                  className="mb-4 inline-flex h-20 w-20 items-center justify-center border border-green-400/30 bg-green-400/10"
                  initial={{ scale: 0 }}
                  transition={{ type: "spring", delay: 0.2 }}
                >
                  <CheckCircle className="h-10 w-10 text-green-400" />
                </motion.div>

                <h2 className="mb-2 font-bold font-mono text-green-400 text-xl tracking-wider">
                  ЗАПРОС ПРИНЯТ
                </h2>
                <p className="mb-6 font-mono text-gray-400 text-sm">
                  Ваша заявка в очереди на обработку.
                  <br />
                  Ожидайте ответ в течение 24-48 часов.
                </p>

                <button
                  className="w-full border border-green-400/50 bg-green-400/20 py-3 font-mono text-green-400 text-sm uppercase tracking-wider transition-all hover:bg-green-400/30"
                  onClick={onClose}
                  type="button"
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
          animate={{ opacity: 1 }}
          className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/90 p-4 backdrop-blur-md"
          exit={{ opacity: 0 }}
          initial={{ opacity: 0 }}
          onClick={onClose}
        >
          <motion.div
            animate={{ scale: 1, opacity: 1, y: 0 }}
            className="relative my-8 w-full max-w-lg overflow-hidden border border-pandora-cyan/30 bg-black/80"
            exit={{ scale: 0.95, opacity: 0, y: 20 }}
            initial={{ scale: 0.95, opacity: 0, y: 20 }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header bar */}
            <div className="flex items-center justify-between border-pandora-cyan/30 border-b bg-pandora-cyan/10 px-4 py-3">
              <div className="flex items-center gap-3">
                <Shield className="text-pandora-cyan" size={18} />
                <span className="font-mono text-pandora-cyan text-xs tracking-wider">
                  ELITE_OPERATOR | РЕГИСТРАЦИЯ
                </span>
              </div>
              <button
                className="text-gray-500 transition-colors hover:text-pandora-cyan"
                onClick={onClose}
                type="button"
              >
                <X size={18} />
              </button>
            </div>

            <div className="p-6">
              {/* Benefits Grid */}
              <div className="mb-6 grid grid-cols-2 gap-3">
                {BENEFITS.map((benefit) => (
                  <motion.div
                    animate={{ opacity: 1, y: 0 }}
                    className="flex items-center gap-2 border border-white/10 bg-white/5 p-3"
                    initial={{ opacity: 0, y: 10 }}
                    key={benefit.text}
                  >
                    <benefit.icon className="flex-shrink-0 text-pandora-cyan" size={14} />
                    <span className="font-mono text-[11px] text-gray-300">{benefit.text}</span>
                  </motion.div>
                ))}
              </div>

              {/* Form */}
              <form className="space-y-4" onSubmit={handleSubmit}>
                {/* Email */}
                <div>
                  <label
                    className="mb-1 block font-mono text-[10px] text-gray-500 tracking-wider"
                    htmlFor="partner-email"
                  >
                    EMAIL_ADDRESS *
                  </label>
                  <input
                    className="w-full border border-white/20 bg-black/50 px-3 py-2.5 font-mono text-sm text-white transition-all placeholder:text-gray-600 focus:border-pandora-cyan focus:bg-pandora-cyan/5 focus:outline-none"
                    id="partner-email"
                    onChange={(e) => handleChange("email", e.target.value)}
                    placeholder="operator@network.sys"
                    type="email"
                    value={formData.email}
                  />
                </div>

                {/* Phone */}
                <div>
                  <label
                    className="mb-1 block font-mono text-[10px] text-gray-500 tracking-wider"
                    htmlFor="partner-phone"
                  >
                    CONTACT_LINE *
                  </label>
                  <input
                    className="w-full border border-white/20 bg-black/50 px-3 py-2.5 font-mono text-sm text-white transition-all placeholder:text-gray-600 focus:border-pandora-cyan focus:bg-pandora-cyan/5 focus:outline-none"
                    id="partner-phone"
                    onChange={(e) => handleChange("phone", e.target.value)}
                    placeholder="+7 (XXX) XXX-XX-XX"
                    type="tel"
                    value={formData.phone}
                  />
                </div>

                {/* Source & Audience - 2 column */}
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label
                      className="mb-1 block font-mono text-[10px] text-gray-500 tracking-wider"
                      htmlFor="partner-source"
                    >
                      NETWORK_SOURCE *
                    </label>
                    <select
                      className="w-full cursor-pointer appearance-none border border-white/20 bg-black/50 px-3 py-2.5 font-mono text-sm text-white focus:border-pandora-cyan focus:outline-none"
                      id="partner-source"
                      onChange={(e) => handleChange("source", e.target.value)}
                      value={formData.source}
                    >
                      <option className="bg-black" value="">
                        Выбрать...
                      </option>
                      {AUDIENCE_SOURCES.map((s) => (
                        <option className="bg-black" key={s.value} value={s.value}>
                          {s.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label
                      className="mb-1 block font-mono text-[10px] text-gray-500 tracking-wider"
                      htmlFor="partner-audience-size"
                    >
                      NETWORK_SIZE *
                    </label>
                    <select
                      className="w-full cursor-pointer appearance-none border border-white/20 bg-black/50 px-3 py-2.5 font-mono text-sm text-white focus:border-pandora-cyan focus:outline-none"
                      id="partner-audience-size"
                      onChange={(e) => handleChange("audienceSize", e.target.value)}
                      value={formData.audienceSize}
                    >
                      <option className="bg-black" value="">
                        Выбрать...
                      </option>
                      {AUDIENCE_SIZES.map((s) => (
                        <option className="bg-black" key={s.value} value={s.value}>
                          {s.label}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                {/* Description */}
                <div>
                  <label
                    className="mb-1 block font-mono text-[10px] text-gray-500 tracking-wider"
                    htmlFor="partner-description"
                  >
                    MISSION_BRIEF *
                  </label>
                  <textarea
                    className="w-full resize-none border border-white/20 bg-black/50 px-3 py-2.5 font-mono text-sm text-white transition-all placeholder:text-gray-600 focus:border-pandora-cyan focus:bg-pandora-cyan/5 focus:outline-none"
                    id="partner-description"
                    onChange={(e) => handleChange("description", e.target.value)}
                    placeholder="Опишите вашу деятельность, контент, аудиторию..."
                    rows={3}
                    value={formData.description}
                  />
                </div>

                {/* Expected Volume (optional) */}
                <div>
                  <label
                    className="mb-1 block font-mono text-[10px] text-gray-500 tracking-wider"
                    htmlFor="partner-volume"
                  >
                    PROJECTED_OUTPUT <span className="text-gray-600">(опционально)</span>
                  </label>
                  <input
                    className="w-full border border-white/20 bg-black/50 px-3 py-2.5 font-mono text-sm text-white transition-all placeholder:text-gray-600 focus:border-pandora-cyan focus:bg-pandora-cyan/5 focus:outline-none"
                    id="partner-volume"
                    onChange={(e) => handleChange("expectedVolume", e.target.value)}
                    placeholder="10-20 операций/месяц"
                    type="text"
                    value={formData.expectedVolume || ""}
                  />
                </div>

                {/* Error */}
                {error && (
                  <motion.div
                    animate={{ opacity: 1, x: 0 }}
                    className="flex items-center gap-2 border border-red-400/30 bg-red-400/10 p-3 font-mono text-red-400 text-xs"
                    initial={{ opacity: 0, x: -10 }}
                  >
                    <AlertCircle size={14} />
                    {error}
                  </motion.div>
                )}

                {/* Submit */}
                <button
                  className="group flex w-full items-center justify-center gap-2 border border-pandora-cyan/50 bg-pandora-cyan/20 py-3.5 font-mono text-pandora-cyan text-sm uppercase tracking-wider transition-all hover:border-pandora-cyan hover:bg-pandora-cyan/30 disabled:cursor-not-allowed disabled:bg-gray-800"
                  disabled={submitting}
                  type="submit"
                >
                  {submitting ? (
                    <>
                      <Loader2 className="animate-spin" size={16} />
                      <span>ПЕРЕДАЧА ДАННЫХ...</span>
                    </>
                  ) : (
                    <>
                      <Send className="transition-transform group-hover:translate-x-1" size={16} />
                      <span>ОТПРАВИТЬ ЗАПРОС</span>
                    </>
                  )}
                </button>
              </form>

              {/* Footer note */}
              <p className="mt-4 text-center font-mono text-[10px] text-gray-600">
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
