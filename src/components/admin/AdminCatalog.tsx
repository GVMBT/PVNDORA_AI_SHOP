/**
 * AdminCatalog Component
 * 
 * Catalog management view for products.
 */

import React, { memo } from 'react';
import { Search, Plus, Edit } from 'lucide-react';
import StockIndicator from './StockIndicator';
import type { ProductData } from './types';

interface AdminCatalogProps {
  products: ProductData[];
  onEditProduct: (product: ProductData) => void;
  onNewProduct: () => void;
}

const AdminCatalog: React.FC<AdminCatalogProps> = ({
  products,
  onEditProduct,
  onNewProduct,
}) => {
  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row justify-between items-center gap-4 bg-[#0e0e0e] border border-white/10 p-4 rounded-sm">
        <div className="relative w-full md:w-auto">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" size={14} />
          <input 
            type="text" 
            placeholder="Search SKU..." 
            className="w-full md:w-64 bg-black border border-white/20 pl-9 pr-4 py-2 text-xs font-mono text-white focus:border-pandora-cyan outline-none" 
          />
        </div>
        <button 
          onClick={onNewProduct} 
          className="w-full md:w-auto flex items-center justify-center gap-2 bg-pandora-cyan text-black px-4 py-2 text-xs font-bold uppercase hover:bg-white transition-colors"
        >
          <Plus size={14} /> Add Product
        </button>
      </div>

      {/* Desktop Table */}
      <div className="hidden md:block bg-[#0e0e0e] border border-white/10 rounded-sm overflow-hidden">
        <table className="w-full text-left text-xs font-mono">
          <thead className="bg-white/5 text-gray-400 uppercase">
            <tr>
              <th className="p-4">Name</th>
              <th className="p-4">Category</th>
              <th className="p-4">Price / MSRP</th>
              <th className="p-4">Stock</th>
              <th className="p-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5 text-gray-300">
            {products.map(p => (
              <tr key={p.id} className="hover:bg-white/5 transition-colors">
                <td className="p-4 font-bold text-white flex items-center gap-3">
                  <div className="w-8 h-8 rounded-sm overflow-hidden bg-black border border-white/10">
                    <img src={p.image} alt="" className="w-full h-full object-cover" />
                  </div>
                  {p.name}
                </td>
                <td className="p-4">
                  <span className="text-[10px] bg-white/5 px-2 py-1 rounded">{p.category}</span>
                </td>
                <td className="p-4">
                  <div>{p.price} ₽</div>
                  {p.msrp && (
                    <div className="text-[10px] text-gray-500 line-through">{p.msrp} ₽</div>
                  )}
                </td>
                <td className="p-4">
                  <StockIndicator stock={p.stock} />
                </td>
                <td className="p-4 text-right">
                  <button 
                    onClick={() => onEditProduct(p)} 
                    className="hover:text-pandora-cyan p-1"
                  >
                    <Edit size={14} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Mobile Cards */}
      <div className="md:hidden space-y-4">
        {products.map(p => (
          <div 
            key={p.id} 
            className="bg-[#0e0e0e] border border-white/10 p-4 flex justify-between items-center"
          >
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-sm overflow-hidden bg-black border border-white/10 shrink-0">
                <img src={p.image} alt="" className="w-full h-full object-cover" />
              </div>
              <div>
                <div className="font-bold text-white mb-1">{p.name}</div>
                <div className="text-xs text-gray-500 mb-2">{p.category} • {p.price} ₽</div>
                <StockIndicator stock={p.stock} />
              </div>
            </div>
            <button 
              onClick={() => onEditProduct(p)} 
              className="p-2 border border-white/10 rounded-full text-gray-400 hover:text-white hover:border-pandora-cyan"
            >
              <Edit size={16} />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};

export default memo(AdminCatalog);


