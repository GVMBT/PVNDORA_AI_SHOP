/**
 * PartnerModal Component
 * 
 * Modal for managing partner settings.
 */

import React, { useState, memo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, User, CheckCircle } from 'lucide-react';
import type { UserData } from './types';

interface PartnerModalProps {
  partner: UserData | null;
  onClose: () => void;
  onSave: (partner: UserData) => void;
}

const PartnerModal: React.FC<PartnerModalProps> = ({
  partner,
  onClose,
  onSave,
}) => {
  const [editingPartner, setEditingPartner] = useState<UserData | null>(partner);

  if (!editingPartner) return null;

  const togglePartnerVip = () => {
    setEditingPartner({
      ...editingPartner,
      level: editingPartner.level === 'ARCHITECT' ? 'PROXY' : 'ARCHITECT',
    });
  };

  const toggleRewardType = () => {
    setEditingPartner({
      ...editingPartner,
      rewardType: editingPartner.rewardType === 'commission' ? 'discount' : 'commission',
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
        <div 
          className="absolute inset-0 bg-black/80 backdrop-blur-sm" 
          onClick={onClose} 
        />
        <motion.div 
          initial={{ scale: 0.9 }} 
          animate={{ scale: 1 }} 
          className="relative w-full max-w-lg bg-[#080808] border border-white/20 p-6 shadow-2xl"
        >
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-xl font-display font-bold text-white">MANAGE PARTNER</h3>
            <button onClick={onClose}>
              <X size={20} className="text-gray-500" />
            </button>
          </div>
          <div className="space-y-6">
            <div className="flex items-center gap-4 bg-white/5 p-4 rounded-sm">
              <div className="w-12 h-12 bg-black border border-white/10 flex items-center justify-center rounded-full">
                <User size={24} />
              </div>
              <div>
                <div className="font-bold text-white text-lg">
                  {editingPartner.handle || editingPartner.username}
                </div>
                <div className="text-xs text-gray-500">ID: #{editingPartner.id}</div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="bg-black p-3 border border-white/10">
                <label className="text-[9px] text-gray-500 block mb-2">PARTNER LEVEL</label>
                <div 
                  className="flex items-center gap-2 cursor-pointer" 
                  onClick={togglePartnerVip}
                >
                  <div className={`w-4 h-4 border border-white/30 flex items-center justify-center ${
                    editingPartner.level === 'ARCHITECT' ? 'bg-pandora-cyan border-pandora-cyan' : ''
                  }`}>
                    {editingPartner.level === 'ARCHITECT' && (
                      <CheckCircle size={10} className="text-black" />
                    )}
                  </div>
                  <span className={`text-xs font-bold ${
                    editingPartner.level === 'ARCHITECT' ? 'text-pandora-cyan' : 'text-gray-400'
                  }`}>
                    ARCHITECT STATUS
                  </span>
                </div>
              </div>
              <div className="bg-black p-3 border border-white/10">
                <label className="text-[9px] text-gray-500 block mb-2">REWARD TYPE</label>
                <div 
                  className="flex items-center gap-2 cursor-pointer" 
                  onClick={toggleRewardType}
                >
                  <div className={`w-8 h-4 rounded-full relative transition-colors ${
                    editingPartner.rewardType === 'commission' ? 'bg-green-500' : 'bg-purple-500'
                  }`}>
                    <div className={`absolute top-0.5 w-3 h-3 bg-white rounded-full transition-all ${
                      editingPartner.rewardType === 'commission' ? 'left-0.5' : 'left-4.5'
                    }`} />
                  </div>
                  <span className="text-xs font-bold text-white">
                    {editingPartner.rewardType === 'commission' ? 'CASH' : 'DISCOUNT'}
                  </span>
                </div>
              </div>
            </div>
            
            <button 
              onClick={handleSave} 
              className="w-full bg-pandora-cyan text-black font-bold py-3 uppercase tracking-widest text-xs"
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
