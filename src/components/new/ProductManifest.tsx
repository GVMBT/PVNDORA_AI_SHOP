/**
 * ProductManifest Component
 *
 * Displays product description and deployment instructions.
 */

import { motion } from "framer-motion";
import type React from "react";
import { memo } from "react";

interface ProductManifestProps {
  description: string;
  instructions?: string | null;
}

const ProductManifest: React.FC<ProductManifestProps> = ({ description, instructions }) => {
  return (
    <motion.div
      animate={{ opacity: 1, y: 0 }}
      className="space-y-4 font-mono text-gray-400 text-xs leading-relaxed"
      exit={{ opacity: 0, y: -5 }}
      initial={{ opacity: 0, y: 5 }}
      key="manifest"
    >
      <div className="border-pandora-cyan border-l-2 bg-white/[0.02] p-4">
        <h4 className="mb-2 font-bold text-[10px] text-white uppercase tracking-wider">
          Module Description
        </h4>
        <p>{description}</p>
      </div>
      <div className="border-white/20 border-l-2 bg-white/[0.02] p-4">
        <h4 className="mb-2 font-bold text-[10px] text-white uppercase tracking-wider">
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
