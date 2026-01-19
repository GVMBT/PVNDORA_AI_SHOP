/**
 * PartnerModal Component
 *
 * Modal for managing partner settings.
 */

import { AnimatePresence, motion } from "framer-motion";
import { CheckCircle, User, X } from "lucide-react";
import type React from "react";
import { memo, useState } from "react";
import type { UserData } from "./types";

interface PartnerModalProps {
  partner: UserData | null;
  onClose: () => void;
  onSave: (partner: UserData) => void;
}

const PartnerModal: React.FC<PartnerModalProps> = ({ partner, onClose, onSave }) => {
  const [editingPartner, setEditingPartner] = useState<UserData | null>(partner);

  if (!editingPartner) {
    return null;
  }

  const togglePartnerVip = () => {
    setEditingPartner({
      ...editingPartner,
      level: editingPartner.level === "ARCHITECT" ? "PROXY" : "ARCHITECT",
    });
  };

  const toggleRewardType = () => {
    setEditingPartner({
      ...editingPartner,
      rewardType: editingPartner.rewardType === "commission" ? "discount" : "commission",
    });
  };

  const handleSave = () => {
    if (editingPartner) {
      onSave(editingPartner);
    }
    onClose();
  };

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-[100] flex items-center justify-center px-4">
        <button
          aria-label="Close modal"
          className="absolute inset-0 cursor-default bg-black/80 backdrop-blur-sm"
          onClick={onClose}
          type="button"
        />
        <motion.div
          animate={{ scale: 1 }}
          className="relative w-full max-w-lg border border-white/20 bg-[#080808] p-6 shadow-2xl"
          initial={{ scale: 0.9 }}
        >
          <div className="mb-6 flex items-center justify-between">
            <h3 className="font-bold font-display text-white text-xl">MANAGE PARTNER</h3>
            <button onClick={onClose} type="button">
              <X className="text-gray-500" size={20} />
            </button>
          </div>
          <div className="space-y-6">
            <div className="flex items-center gap-4 rounded-sm bg-white/5 p-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-full border border-white/10 bg-black">
                <User size={24} />
              </div>
              <div>
                <div className="font-bold text-lg text-white">
                  {editingPartner.handle || editingPartner.username}
                </div>
                <div className="text-gray-500 text-xs">ID: #{editingPartner.id}</div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="border border-white/10 bg-black p-3">
                <span className="mb-2 block text-[9px] text-gray-500">PARTNER LEVEL</span>
                <button
                  className="flex cursor-pointer items-center gap-2"
                  onClick={togglePartnerVip}
                  type="button"
                >
                  <div
                    className={`flex h-4 w-4 items-center justify-center border border-white/30 ${
                      editingPartner.level === "ARCHITECT"
                        ? "border-pandora-cyan bg-pandora-cyan"
                        : ""
                    }`}
                  >
                    {editingPartner.level === "ARCHITECT" && (
                      <CheckCircle className="text-black" size={10} />
                    )}
                  </div>
                  <span
                    className={`font-bold text-xs ${
                      editingPartner.level === "ARCHITECT" ? "text-pandora-cyan" : "text-gray-400"
                    }`}
                  >
                    ARCHITECT STATUS
                  </span>
                </button>
              </div>
              <div className="border border-white/10 bg-black p-3">
                <span className="mb-2 block text-[9px] text-gray-500">REWARD TYPE</span>
                <button
                  className="flex cursor-pointer items-center gap-2"
                  onClick={toggleRewardType}
                  type="button"
                >
                  <div
                    className={`relative h-4 w-8 rounded-full transition-colors ${
                      editingPartner.rewardType === "commission" ? "bg-green-500" : "bg-purple-500"
                    }`}
                  >
                    <div
                      className={`absolute top-0.5 h-3 w-3 rounded-full bg-white transition-all ${
                        editingPartner.rewardType === "commission" ? "left-0.5" : "left-4.5"
                      }`}
                    />
                  </div>
                  <span className="font-bold text-white text-xs">
                    {editingPartner.rewardType === "commission" ? "CASH" : "DISCOUNT"}
                  </span>
                </button>
              </div>
            </div>

            <button
              className="w-full bg-pandora-cyan py-3 font-bold text-black text-xs uppercase tracking-widest"
              onClick={handleSave}
              type="button"
            >
              SAVE SETTINGS
            </button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};

export default memo(PartnerModal);
