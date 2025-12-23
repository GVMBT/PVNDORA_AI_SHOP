/**
 * ProductFiles Component
 * 
 * Displays files included in the product package.
 */

import React, { memo } from 'react';
import { motion } from 'framer-motion';
import { FileKey, FileText, Terminal, Globe, Lock } from 'lucide-react';
import type { ProductFile } from '../../types/component';

interface ProductFilesProps {
  files: ProductFile[];
}

const ProductFiles: React.FC<ProductFilesProps> = ({ files }) => {
  return (
    <motion.div 
      key="files"
      initial={{ opacity: 0, y: 5 }} 
      animate={{ opacity: 1, y: 0 }} 
      exit={{ opacity: 0, y: -5 }}
      className="space-y-2"
    >
      <div className="text-[10px] font-mono text-gray-500 mb-2 uppercase">
        Files included in payload:
      </div>
      {files.length === 0 && (
        <div className="text-[10px] text-gray-600 font-mono uppercase">
          No attached payload
        </div>
      )}
      {files.map((file, i) => (
        <div 
          key={i} 
          className="flex items-center justify-between bg-[#0e0e0e] border border-white/10 p-3 hover:border-pandora-cyan/30 transition-colors"
        >
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-white/5 flex items-center justify-center rounded-sm">
              {file.type === 'key' && <FileKey size={14} className="text-yellow-500" />}
              {file.type === 'doc' && <FileText size={14} className="text-blue-500" />}
              {file.type === 'config' && <Terminal size={14} className="text-gray-400" />}
              {file.type === 'net' && <Globe size={14} className="text-green-500" />}
              {!file.type && <Lock size={14} className="text-gray-500" />}
            </div>
            <div>
              <div className="text-xs font-bold text-white">{file.name}</div>
              <div className="text-[9px] text-gray-600 font-mono uppercase">
                {file.type || 'doc'} FILE // {file.size}
              </div>
            </div>
          </div>
          <div className="text-gray-600">
            <Lock size={12} />
          </div>
        </div>
      ))}
    </motion.div>
  );
};

export default memo(ProductFiles);





























