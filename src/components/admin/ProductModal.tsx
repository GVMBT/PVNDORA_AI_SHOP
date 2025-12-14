/**
 * ProductModal Component
 * 
 * Modal for creating/editing products.
 */

import React, { useState, useRef, memo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Save, Plus, Terminal, Image as ImageIcon, Upload, Video } from 'lucide-react';
import type { ProductData } from './types';

interface ProductModalProps {
  isOpen: boolean;
  product: Partial<ProductData> | null;
  onClose: () => void;
  onSave: (product: Partial<ProductData>) => void;
}

type ProductTab = 'general' | 'inventory';

const ProductModal: React.FC<ProductModalProps> = ({
  isOpen,
  product,
  onClose,
  onSave,
}) => {
  const [activeTab, setActiveTab] = useState<ProductTab>('general');
  const [inventoryText, setInventoryText] = useState('');
  const [editingProduct, setEditingProduct] = useState<Partial<ProductData>>(
    product || {
      name: '',
      price: 0,
      stock: 0,
      category: 'Text',
      image: 'https://images.unsplash.com/photo-1550751827-4bd374c3f58b?q=80&w=800&auto=format&fit=crop',
    }
  );
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setEditingProduct({ ...editingProduct, image: reader.result as string });
      };
      reader.readAsDataURL(file);
    }
  };

  const triggerFileInput = () => {
    fileInputRef.current?.click();
  };

  const handleStockUpdate = () => {
    const lines = inventoryText.split('\n').filter(line => line.trim() !== '');
    if (editingProduct) {
      setEditingProduct({ 
        ...editingProduct, 
        stock: (editingProduct.stock || 0) + lines.length 
      });
    }
    setInventoryText('');
  };

  if (!isOpen) return null;

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
          className="relative w-full max-w-2xl bg-[#080808] border border-white/20 p-6 shadow-2xl max-h-[90vh] overflow-y-auto"
        >
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-xl font-display font-bold text-white">
              {editingProduct?.name ? `EDIT: ${editingProduct.name}` : 'NEW PRODUCT'}
            </h3>
            <button onClick={onClose}>
              <X size={20} className="text-gray-500" />
            </button>
          </div>

          {/* Tabs */}
          <div className="flex gap-4 border-b border-white/10 mb-6">
            <button 
              onClick={() => setActiveTab('general')} 
              className={`pb-2 text-xs font-bold uppercase ${
                activeTab === 'general' 
                  ? 'text-pandora-cyan border-b-2 border-pandora-cyan' 
                  : 'text-gray-500'
              }`}
            >
              General Info
            </button>
            <button 
              onClick={() => setActiveTab('inventory')} 
              className={`pb-2 text-xs font-bold uppercase ${
                activeTab === 'inventory' 
                  ? 'text-pandora-cyan border-b-2 border-pandora-cyan' 
                  : 'text-gray-500'
              }`}
            >
              Inventory (Stock)
            </button>
          </div>

          {activeTab === 'general' ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Media Section */}
              <div className="col-span-1 md:col-span-2 bg-[#050505] p-4 border border-white/10 mb-2">
                <h4 className="text-xs font-mono text-gray-500 uppercase mb-3 flex items-center gap-2">
                  <ImageIcon size={14} /> Media Assets
                </h4>
                <div className="flex gap-4 items-start">
                  {/* Image Upload Area */}
                  <div 
                    className="relative group w-32 h-32 bg-black border border-white/20 flex items-center justify-center cursor-pointer hover:border-pandora-cyan transition-colors" 
                    onClick={triggerFileInput}
                  >
                    {editingProduct?.image ? (
                      <img 
                        src={editingProduct.image} 
                        className="w-full h-full object-cover opacity-80 group-hover:opacity-100 transition-opacity" 
                        alt="Product" 
                      />
                    ) : (
                      <div className="text-center text-gray-500 group-hover:text-pandora-cyan">
                        <Upload size={24} className="mx-auto mb-1" />
                        <span className="text-[9px] uppercase">Upload</span>
                      </div>
                    )}
                    <input 
                      type="file" 
                      ref={fileInputRef} 
                      className="hidden" 
                      accept="image/*"
                      onChange={handleImageUpload}
                    />
                  </div>

                  {/* Video Input */}
                  <div className="flex-1 space-y-3">
                    <div>
                      <label className="text-[10px] text-gray-500 block mb-1 uppercase">
                        Image URL (Fallback)
                      </label>
                      <input 
                        type="text" 
                        value={editingProduct?.image || ''} 
                        onChange={(e) => setEditingProduct({...editingProduct, image: e.target.value})}
                        className="w-full bg-black border border-white/20 p-2 text-xs text-white focus:border-pandora-cyan outline-none" 
                        placeholder="https://..."
                      />
                    </div>
                    <div>
                      <label className="text-[10px] text-gray-500 block mb-1 uppercase flex items-center gap-1">
                        <Video size={10} /> Video Instruction URL
                      </label>
                      <input 
                        type="text" 
                        value={editingProduct?.video || ''}
                        onChange={(e) => setEditingProduct({...editingProduct, video: e.target.value})}
                        className="w-full bg-black border border-white/20 p-2 text-xs text-white focus:border-pandora-cyan outline-none" 
                        placeholder="https://youtube.com/..."
                      />
                    </div>
                  </div>
                </div>
              </div>

              <div className="col-span-1 md:col-span-2">
                <label className="text-[10px] text-gray-500 block mb-1 uppercase">Product Name *</label>
                <input 
                  type="text" 
                  value={editingProduct?.name || ''}
                  onChange={(e) => setEditingProduct({...editingProduct, name: e.target.value})}
                  className="w-full bg-black border border-white/20 p-2 text-xs text-white focus:border-pandora-cyan outline-none" 
                />
              </div>

              <div className="col-span-1 md:col-span-2">
                <label className="text-[10px] text-gray-500 block mb-1 uppercase">Description</label>
                <textarea 
                  value={editingProduct?.description || ''}
                  onChange={(e) => setEditingProduct({...editingProduct, description: e.target.value})}
                  className="w-full h-20 bg-black border border-white/20 p-2 text-xs text-white focus:border-pandora-cyan outline-none resize-none" 
                  placeholder="Short description..." 
                />
              </div>

              <div>
                <label className="text-[10px] text-gray-500 block mb-1 uppercase">Price (₽) *</label>
                <input 
                  type="number" 
                  value={editingProduct?.price || 0}
                  onChange={(e) => setEditingProduct({...editingProduct, price: Number(e.target.value)})}
                  className="w-full bg-black border border-white/20 p-2 text-xs text-white focus:border-pandora-cyan outline-none" 
                />
              </div>
              <div>
                <label className="text-[10px] text-gray-500 block mb-1 uppercase">MSRP (Strike Price)</label>
                <input 
                  type="number" 
                  value={editingProduct?.msrp || 0}
                  onChange={(e) => setEditingProduct({...editingProduct, msrp: Number(e.target.value)})}
                  className="w-full bg-black border border-white/20 p-2 text-xs text-white focus:border-pandora-cyan outline-none" 
                />
              </div>

              <div>
                <label className="text-[10px] text-gray-500 block mb-1 uppercase">Type</label>
                <select 
                  value={editingProduct?.type || 'instant'}
                  onChange={(e) => setEditingProduct({...editingProduct, type: e.target.value})}
                  className="w-full bg-black border border-white/20 p-2 text-xs text-white focus:border-pandora-cyan outline-none"
                >
                  <option value="instant">Instant Delivery</option>
                  <option value="preorder">Pre-order</option>
                  <option value="manual">Manual</option>
                </select>
              </div>
              <div>
                <label className="text-[10px] text-gray-500 block mb-1 uppercase">Stock (Manual)</label>
                <input 
                  type="number" 
                  value={editingProduct?.stock || 0}
                  onChange={(e) => setEditingProduct({...editingProduct, stock: Number(e.target.value)})}
                  className="w-full bg-black border border-white/20 p-2 text-xs text-white focus:border-pandora-cyan outline-none" 
                />
              </div>

              <div>
                <label className="text-[10px] text-gray-500 block mb-1 uppercase">Category</label>
                <select 
                  value={editingProduct?.category || 'Text'}
                  onChange={(e) => setEditingProduct({...editingProduct, category: e.target.value})}
                  className="w-full bg-black border border-white/20 p-2 text-xs text-white focus:border-pandora-cyan outline-none"
                >
                  <option>Text</option>
                  <option>Video</option>
                  <option>Image</option>
                  <option>Code</option>
                  <option>Audio</option>
                </select>
              </div>
              <div className="flex items-center gap-2 border border-white/20 p-2 bg-black">
                <input 
                  type="checkbox" 
                  checked={editingProduct?.vpn || false}
                  onChange={(e) => setEditingProduct({...editingProduct, vpn: e.target.checked})}
                  className="accent-pandora-cyan w-4 h-4" 
                />
                <label className="text-xs text-white uppercase font-bold">VPN Required</label>
              </div>

              <div>
                <label className="text-[10px] text-gray-500 block mb-1 uppercase">Fulfillment (Hours)</label>
                <input 
                  type="number" 
                  value={editingProduct?.fulfillment || 0}
                  onChange={(e) => setEditingProduct({...editingProduct, fulfillment: Number(e.target.value)})}
                  className="w-full bg-black border border-white/20 p-2 text-xs text-white focus:border-pandora-cyan outline-none" 
                />
              </div>
              <div>
                <label className="text-[10px] text-gray-500 block mb-1 uppercase">Warranty (Hours)</label>
                <input 
                  type="number" 
                  value={editingProduct?.warranty || 24}
                  onChange={(e) => setEditingProduct({...editingProduct, warranty: Number(e.target.value)})}
                  className="w-full bg-black border border-white/20 p-2 text-xs text-white focus:border-pandora-cyan outline-none" 
                />
              </div>
              <div>
                <label className="text-[10px] text-gray-500 block mb-1 uppercase">Duration (Days)</label>
                <input 
                  type="number" 
                  value={editingProduct?.duration || 30}
                  onChange={(e) => setEditingProduct({...editingProduct, duration: Number(e.target.value)})}
                  className="w-full bg-black border border-white/20 p-2 text-xs text-white focus:border-pandora-cyan outline-none" 
                />
              </div>

              <div className="col-span-1 md:col-span-2">
                <label className="text-[10px] text-gray-500 block mb-1 uppercase">Access Instructions</label>
                <textarea 
                  value={editingProduct?.instructions || ''}
                  onChange={(e) => setEditingProduct({...editingProduct, instructions: e.target.value})}
                  className="w-full h-24 bg-black border border-white/20 p-2 text-xs text-white focus:border-pandora-cyan outline-none resize-none" 
                  placeholder="1. Download..." 
                />
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="bg-[#050505] p-4 border border-green-500/20 rounded-sm">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-xs font-mono text-green-500 flex items-center gap-2">
                    <Terminal size={12} /> BULK KEY UPLOAD
                  </span>
                  <span className="text-[10px] text-gray-500">
                    {inventoryText.split('\n').filter(l => l.trim()).length} ITEMS DETECTED
                  </span>
                </div>
                <textarea 
                  value={inventoryText}
                  onChange={(e) => setInventoryText(e.target.value)}
                  placeholder={`Paste keys here, one per line:\nuser:pass\napi_key_1\napi_key_2`}
                  className="w-full h-48 bg-black border border-white/10 p-3 text-xs font-mono text-green-400 focus:border-green-500/50 outline-none resize-none"
                />
              </div>
              <div className="flex justify-end">
                <button 
                  onClick={handleStockUpdate}
                  className="bg-green-600 hover:bg-green-500 text-black font-bold py-2 px-6 text-xs uppercase flex items-center gap-2"
                >
                  <Plus size={14} /> Parse & Add to Stock
                </button>
              </div>
            </div>
          )}

          <div className="mt-8 pt-4 border-t border-white/10 flex justify-end gap-3">
            <button 
              onClick={onClose} 
              className="px-4 py-2 border border-white/10 text-xs font-bold text-gray-400 hover:text-white"
            >
              CANCEL
            </button>
            <button 
              onClick={() => onSave(editingProduct)} 
              className="px-4 py-2 bg-pandora-cyan text-black text-xs font-bold hover:bg-white flex items-center gap-2"
            >
              <Save size={14} /> SAVE PRODUCT
            </button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};

export default memo(ProductModal);


