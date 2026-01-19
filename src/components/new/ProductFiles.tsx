/**
 * ProductFiles Component
 *
 * Displays files included in the product package.
 */

import { motion } from "framer-motion";
import { FileKey, FileText, Globe, Lock, Terminal } from "lucide-react";
import type React from "react";
import { memo } from "react";
import type { ProductFile } from "../../types/component";

interface ProductFilesProps {
  files: ProductFile[];
}

const ProductFiles: React.FC<ProductFilesProps> = ({ files }) => {
  return (
    <motion.div
      animate={{ opacity: 1, y: 0 }}
      className="space-y-2"
      exit={{ opacity: 0, y: -5 }}
      initial={{ opacity: 0, y: 5 }}
      key="files"
    >
      <div className="mb-2 font-mono text-[10px] text-gray-500 uppercase">
        Files included in payload:
      </div>
      {files.length === 0 && (
        <div className="font-mono text-[10px] text-gray-600 uppercase">No attached payload</div>
      )}
      {files.map((file) => (
        <div
          className="flex items-center justify-between border border-white/10 bg-[#0e0e0e] p-3 transition-colors hover:border-pandora-cyan/30"
          key={file.name}
        >
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-sm bg-white/5">
              {file.type === "key" && <FileKey className="text-yellow-500" size={14} />}
              {file.type === "doc" && <FileText className="text-blue-500" size={14} />}
              {file.type === "config" && <Terminal className="text-gray-400" size={14} />}
              {file.type === "net" && <Globe className="text-green-500" size={14} />}
              {!file.type && <Lock className="text-gray-500" size={14} />}
            </div>
            <div>
              <div className="font-bold text-white text-xs">{file.name}</div>
              <div className="font-mono text-[9px] text-gray-600 uppercase">
                {file.type || "doc"} FILE | {file.size}
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
