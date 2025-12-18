import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Star, Send } from 'lucide-react';

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
  itemId,
  itemName,
  orderId,
  rating,
  reviewText,
  isSubmitting,
  onClose,
  onRatingChange,
  onTextChange,
  onSubmit
}) => {
  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center px-4">
          <motion.div 
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            onClick={onClose}
            className="absolute inset-0 bg-black/80 backdrop-blur-sm"
          />
          <motion.div 
            initial={{ scale: 0.9, opacity: 0, y: 20 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            exit={{ scale: 0.9, opacity: 0, y: 20 }}
            className="relative w-full max-w-md bg-[#0a0a0a] border border-white/20 p-6 shadow-[0_0_50px_rgba(0,0,0,0.8)]"
          >
            <div className="flex justify-between items-start mb-6 border-b border-white/10 pb-4">
              <div>
                <h3 className="text-lg font-display font-bold text-white uppercase">Submit Evaluation</h3>
                <p className="text-[10px] font-mono text-pandora-cyan mt-1">TARGET: {itemName}</p>
              </div>
              <button onClick={onClose} className="text-gray-500 hover:text-white">
                <X size={20} />
              </button>
            </div>

            {/* Rating */}
            <div className="mb-6 flex flex-col items-center">
              <span className="text-xs font-mono text-gray-500 mb-2 uppercase tracking-widest">Quality Assessment</span>
              <div className="flex gap-2">
                {[1, 2, 3, 4, 5].map((star) => (
                  <button 
                    key={star} 
                    onClick={() => onRatingChange(star)}
                    className="hover:scale-110 transition-transform focus:outline-none"
                  >
                    <Star 
                      size={24} 
                      fill={star <= rating ? "#00FFFF" : "none"} 
                      className={star <= rating ? "text-pandora-cyan drop-shadow-[0_0_5px_#00FFFF]" : "text-gray-700"} 
                    />
                  </button>
                ))}
              </div>
            </div>

            {/* Text Area */}
            <div className="mb-6 relative group">
              <textarea 
                value={reviewText}
                onChange={(e) => onTextChange(e.target.value)}
                placeholder="Describe your experience with this module..."
                className="w-full h-32 bg-black border border-white/20 p-3 text-sm text-white font-mono focus:border-pandora-cyan outline-none resize-none placeholder:text-gray-700"
              />
              <div className="absolute bottom-2 right-2 text-[10px] text-gray-600 font-mono">
                {reviewText.length} CHARS
              </div>
            </div>

            <button 
              onClick={onSubmit}
              disabled={isSubmitting}
              className="w-full bg-white/5 hover:bg-pandora-cyan border border-white/20 hover:border-pandora-cyan text-white hover:text-black font-bold py-3 uppercase tracking-widest transition-all flex items-center justify-center gap-2 group/btn disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting ? (
                <>
                  <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
                  UPLOADING...
                </>
              ) : (
                <>
                  <Send size={16} />
                  UPLOAD_PACKET
                </>
              )}
            </button>

            {/* Decorative Corners */}
            <div className="absolute top-0 left-0 w-2 h-2 border-t border-l border-pandora-cyan" />
            <div className="absolute bottom-0 right-0 w-2 h-2 border-b border-r border-pandora-cyan" />
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};

export default OrderReviewModal;













