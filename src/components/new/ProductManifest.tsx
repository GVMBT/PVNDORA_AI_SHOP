/**
 * ProductManifest Component
 * 
 * Displays product description and deployment instructions.
 */

import React, { memo } from 'react';
import { motion } from 'framer-motion';

interface ProductManifestProps {
  description: string;
  instructions?: string | null;
}

const ProductManifest: React.FC<ProductManifestProps> = ({ description, instructions }) => {
  return (
    <motion.div 
      key="manifest"
      initial={{ opacity: 0, y: 5 }} 
      animate={{ opacity: 1, y: 0 }} 
      exit={{ opacity: 0, y: -5 }}
      className="space-y-4 font-mono text-xs leading-relaxed text-gray-400"
    >
      <div className="p-4 bg-white/[0.02] border-l-2 border-pandora-cyan">
        <h4 className="text-white font-bold mb-2 uppercase text-[10px] tracking-wider">
          Module Description
        </h4>
        <p>{description}</p>
      </div>
      <div className="p-4 bg-white/[0.02] border-l-2 border-white/20">
        <h4 className="text-white font-bold mb-2 uppercase text-[10px] tracking-wider">
          Deployment Instructions
        </h4>
        <p className="whitespace-pre-wrap">
          {instructions || "Standard deployment protocols apply. Check attached documentation."}
        </p>
      </div>
    </motion.div>
  );
};

export default memo(ProductManifest);










