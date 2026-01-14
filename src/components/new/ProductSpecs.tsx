/**
 * ProductSpecs Component
 *
 * Displays technical specifications in terminal list style.
 * Now with human-readable labels and tooltips.
 */

import { motion } from "framer-motion";
import { Info } from "lucide-react";
import type React from "react";
import { memo, useState } from "react";

// Helper for Russian pluralization (avoid nested ternaries)
const getRuDaysPlural = (num: number): string => {
  if (num === 1) return "день";
  if (num >= 2 && num <= 4) return "дня";
  return "дней";
};

const getRuHoursPlural = (num: number): string => {
  if (num === 1) return "час";
  if (num >= 2 && num <= 4) return "часа";
  return "часов";
};

interface SpecRowProps {
  label: string;
  humanLabel: string;
  value: string;
  humanValue: string;
  valueColor?: string;
  tooltip?: string;
}

const SpecRow: React.FC<SpecRowProps> = ({
  label,
  humanLabel,
  value,
  humanValue,
  valueColor = "text-white",
  tooltip,
}) => {
  const [showTooltip, setShowTooltip] = useState(false);

  return (
    <div className="flex justify-between items-center py-2 border-b border-white/5 last:border-0 relative group">
      <span className="text-gray-500 tracking-wider text-[10px] flex items-center gap-1">
        <span className="hidden sm:inline uppercase">{label}:</span>
        <span className="sm:hidden">{humanLabel}:</span>
        {tooltip && (
          <button
            type="button"
            onClick={() => setShowTooltip(!showTooltip)}
            onMouseEnter={() => setShowTooltip(true)}
            onMouseLeave={() => setShowTooltip(false)}
            className="text-gray-600 hover:text-pandora-cyan transition-colors"
          >
            <Info size={10} />
          </button>
        )}
      </span>
      <span className={`font-bold text-xs ${valueColor}`}>
        <span className="hidden sm:inline">{value}</span>
        <span className="sm:hidden">{humanValue}</span>
      </span>

      {/* Tooltip */}
      {tooltip && showTooltip && (
        <div className="absolute left-0 top-full z-50 bg-black border border-white/20 px-2 py-1 text-[9px] text-gray-400 max-w-[200px] whitespace-normal">
          {tooltip}
        </div>
      )}
    </div>
  );
};

interface ProductSpecsProps {
  accessProtocol: string;
  warrantyLabel: string;
  durationLabel: string;
  deliveryLabel: string;
  nodeStatus: string;
  nodeStatusColor: string;
}

// Map tech labels to human-readable
const humanLabels: Record<string, { label: string; tooltip: string }> = {
  ACCESS_PROTOCOL: { label: "Доступ", tooltip: "Способ получения товара" },
  UPTIME_ASSURANCE: { label: "Гарантия", tooltip: "Срок гарантийной замены" },
  SESSION_DURATION: { label: "Срок", tooltip: "Срок действия доступа" },
  DEPLOY_MODE: { label: "Доставка", tooltip: "Способ и время доставки" },
  SECURE_UPLINK: { label: "Защита", tooltip: "Метод шифрования данных" },
  NODE_STATUS: { label: "Статус", tooltip: "Текущий статус товара" },
};

const humanValues: Record<string, string> = {
  DIRECT_ACCESS: "Моментально",
  ON_DEMAND: "По запросу",
  DISCONTINUED: "Недоступно",
  INSTANT_DEPLOY: "Мгновенно",
  UNAVAILABLE: "Нет в наличии",
  OPERATIONAL: "В наличии",
  STANDBY: "Под заказ",
  DISABLED: "Недоступен",
  UNSPECIFIED: "Не указано",
  UNBOUNDED: "Бессрочно",
  "AES-256-GCM": "AES-256",
  GRID_ONLINE: "Готов",
  RESOURCE_QUEUE: "Очередь",
  OFFLINE: "Офлайн",
};

const getHumanValue = (value: string): string => {
  // Check exact match first
  if (humanValues[value]) return humanValues[value];

  // Handle dynamic values like "3 DAYS" or "24 HOURS"
  if (value.includes("DAYS")) {
    const num = Number.parseInt(value, 10);
    if (!Number.isNaN(num)) {
      return `${num} ${getRuDaysPlural(num)}`;
    }
  }
  if (value.includes("HOURS")) {
    const num = Number.parseInt(value, 10);
    if (!Number.isNaN(num)) {
      return `${num} ${getRuHoursPlural(num)}`;
    }
  }
  if (value.includes("ALLOCATION_QUEUE")) {
    const regex = /~?(\d+)H?/;
    const match = regex.exec(value);
    if (match) {
      const hours = Number.parseInt(match[1], 10);
      return `~${hours} ч`;
    }
  }

  return value;
};

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
      <SpecRow
        label="ACCESS_PROTOCOL"
        humanLabel={humanLabels.ACCESS_PROTOCOL.label}
        value={accessProtocol}
        humanValue={getHumanValue(accessProtocol)}
        valueColor={nodeStatusColor}
        tooltip={humanLabels.ACCESS_PROTOCOL.tooltip}
      />
      <SpecRow
        label="UPTIME_ASSURANCE"
        humanLabel={humanLabels.UPTIME_ASSURANCE.label}
        value={warrantyLabel}
        humanValue={getHumanValue(warrantyLabel)}
        valueColor="text-pandora-cyan"
        tooltip={humanLabels.UPTIME_ASSURANCE.tooltip}
      />
      <SpecRow
        label="SESSION_DURATION"
        humanLabel={humanLabels.SESSION_DURATION.label}
        value={durationLabel}
        humanValue={getHumanValue(durationLabel)}
        tooltip={humanLabels.SESSION_DURATION.tooltip}
      />
      <SpecRow
        label="DEPLOY_MODE"
        humanLabel={humanLabels.DEPLOY_MODE.label}
        value={deliveryLabel}
        humanValue={getHumanValue(deliveryLabel)}
        valueColor={nodeStatusColor}
        tooltip={humanLabels.DEPLOY_MODE.tooltip}
      />
      <SpecRow
        label="SECURE_UPLINK"
        humanLabel={humanLabels.SECURE_UPLINK.label}
        value="AES-256-GCM"
        humanValue="AES-256"
        tooltip={humanLabels.SECURE_UPLINK.tooltip}
      />
      <SpecRow
        label="NODE_STATUS"
        humanLabel={humanLabels.NODE_STATUS.label}
        value={nodeStatus}
        humanValue={getHumanValue(nodeStatus)}
        valueColor={nodeStatusColor}
        tooltip={humanLabels.NODE_STATUS.tooltip}
      />
    </motion.div>
  );
};

export default memo(ProductSpecs);
