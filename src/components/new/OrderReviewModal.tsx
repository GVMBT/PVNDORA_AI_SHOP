import { AnimatePresence, motion } from "framer-motion";
import { Send, Star, X } from "lucide-react";
import type React from "react";
import { useLocale } from "../../hooks/useLocale";

interface ReviewModalProps {
  isOpen: boolean;
  itemId: number | string | null;
  itemName: string;
  orderId: string | null;
  rating: number;
  reviewText: string;
  isSubmitting: boolean;
  onClose: () => void;
  onRatingChange: (rating: number) => void;
  onTextChange: (text: string) => void;
  onSubmit: () => void;
}

const OrderReviewModal: React.FC<ReviewModalProps> = ({
  isOpen,
  itemId: _itemId,
  itemName,
  orderId: _orderId,
  rating,
  reviewText,
  isSubmitting,
  onClose,
  onRatingChange,
  onTextChange,
  onSubmit,
}) => {
  const { t } = useLocale();
  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center px-4">
          <motion.div
            animate={{ opacity: 1 }}
            className="absolute inset-0 bg-black/80 backdrop-blur-sm"
            exit={{ opacity: 0 }}
            initial={{ opacity: 0 }}
            onClick={onClose}
          />
          <motion.div
            animate={{ scale: 1, opacity: 1, y: 0 }}
            className="relative w-full max-w-md border border-white/20 bg-[#0a0a0a] p-6 shadow-[0_0_50px_rgba(0,0,0,0.8)]"
            exit={{ scale: 0.9, opacity: 0, y: 20 }}
            initial={{ scale: 0.9, opacity: 0, y: 20 }}
          >
            <div className="mb-6 flex items-start justify-between border-white/10 border-b pb-4">
              <div className="flex-1 pr-4">
                <h3 className="mb-1 font-bold font-display text-lg text-white uppercase">
                  {t("modal.review.title")}
                </h3>
                <p className="font-mono text-[10px] text-pandora-cyan uppercase tracking-wider">
                  {t("modal.review.target")}: {itemName}
                </p>
              </div>
              <button
                aria-label="Close"
                className="-mt-1 -mr-1 p-1 text-gray-500 transition-colors hover:text-white"
                onClick={onClose}
                type="button"
              >
                <X size={20} />
              </button>
            </div>

            {/* Rating */}
            <div className="mb-6 flex flex-col items-center">
              <span className="mb-3 font-mono text-gray-500 text-xs uppercase tracking-widest">
                {t("modal.review.qualityAssessment")}
              </span>
              <div className="flex gap-2">
                {[1, 2, 3, 4, 5].map((star) => (
                  <button
                    aria-label={`Rate ${star} stars`}
                    className="rounded transition-transform hover:scale-110 focus:outline-none focus:ring-2 focus:ring-pandora-cyan/50"
                    key={star}
                    onClick={() => onRatingChange(star)}
                    type="button"
                  >
                    <Star
                      className={
                        star <= rating
                          ? "text-pandora-cyan drop-shadow-[0_0_5px_#00FFFF]"
                          : "text-gray-700"
                      }
                      fill={star <= rating ? "#00FFFF" : "none"}
                      size={24}
                    />
                  </button>
                ))}
              </div>
            </div>

            {/* Text Area */}
            <div className="relative mb-6">
              <textarea
                className="h-32 w-full resize-none border border-white/20 bg-black p-3 font-mono text-sm text-white outline-none transition-colors placeholder:text-gray-700 focus:border-pandora-cyan focus:ring-1 focus:ring-pandora-cyan/50"
                maxLength={1000}
                onChange={(e) => onTextChange(e.target.value)}
                placeholder={t("modal.review.placeholder")}
                value={reviewText}
              />
              <div className="absolute right-2 bottom-2 font-mono text-[10px] text-gray-600">
                {reviewText.length} {t("modal.review.chars")}
              </div>
            </div>

            <button
              className="flex w-full items-center justify-center gap-2 border border-white/20 bg-white/5 py-3 font-bold text-white uppercase tracking-widest transition-all hover:border-pandora-cyan hover:bg-pandora-cyan hover:text-black disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:border-white/20 disabled:hover:bg-white/5 disabled:hover:text-white"
              disabled={isSubmitting || rating === 0}
              onClick={onSubmit}
              type="button"
            >
              {isSubmitting ? (
                <>
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                  {t("modal.review.uploading")}
                </>
              ) : (
                <>
                  <Send size={16} />
                  {t("modal.review.button")}
                </>
              )}
            </button>

            {/* Decorative Corners */}
            <div className="absolute top-0 left-0 h-2 w-2 border-pandora-cyan border-t border-l" />
            <div className="absolute right-0 bottom-0 h-2 w-2 border-pandora-cyan border-r border-b" />
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};

export default OrderReviewModal;
