/**
 * ProductSpecs Component
 * 
 * Displays technical specifications in terminal list style.
 */

import React, { memo } from 'react';
import { motion } from 'framer-motion';

interface SpecRowProps {
  label: string;
  value: string;
  valueColor?: string;
}

const SpecRow: React.FC<SpecRowProps> = ({ label, value, valueColor = 'text-white' }) => (
  <div className="flex justify-between items-center py-2 border-b border-white/5 last:border-0">
    <span className="text-gray-500 uppercase tracking-wider">{label}:</span>
    <span className={`font-bold ${valueColor}`}>{value}</span>
  </div>
);

interface ProductSpecsProps {
  accessProtocol: string;
  warrantyLabel: string;
  durationLabel: string;
  deliveryLabel: string;
  nodeStatus: string;
  nodeStatusColor: string;
}

const ProductSpecs: React.FC<ProductSpecsProps> = ({
  accessProtocol,
  warrantyLabel,
  durationLabel,
  deliveryLabel,
  nodeStatus,
  nodeStatusColor,
}) => {
  return (
    <motion.div 
      key="specs"
      initial={{ opacity: 0, x: -10 }} 
      animate={{ opacity: 1, x: 0 }} 
      exit={{ opacity: 0, x: 10 }}
      className="font-mono text-xs space-y-0"
    >
      <SpecRow label="ACCESS_PROTOCOL" value={accessProtocol} valueColor={nodeStatusColor} />
      <SpecRow label="UPTIME_ASSURANCE" value={warrantyLabel} valueColor="text-pandora-cyan" />
      <SpecRow label="SESSION_DURATION" value={durationLabel} />
      <SpecRow label="DEPLOY_MODE" value={deliveryLabel} valueColor={nodeStatusColor} />
      <SpecRow label="SECURE_UPLINK" value="AES-256-GCM" />
      <SpecRow label="NODE_STATUS" value={nodeStatus} valueColor={nodeStatusColor} />
    </motion.div>
  );
};

export default memo(ProductSpecs);
















