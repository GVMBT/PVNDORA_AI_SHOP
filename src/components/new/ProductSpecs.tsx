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
  if (num === 1) {
    return "день";
  }
  if (num >= 2 && num <= 4) {
    return "дня";
  }
  return "дней";
};

const getRuHoursPlural = (num: number): string => {
  if (num === 1) {
    return "час";
  }
  if (num >= 2 && num <= 4) {
    return "часа";
  }
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
    <div className="group relative flex items-center justify-between border-white/5 border-b py-2 last:border-0">
      <span className="flex items-center gap-1 text-[10px] text-gray-500 tracking-wider">
        <span className="hidden uppercase sm:inline">{label}:</span>
        <span className="sm:hidden">{humanLabel}:</span>
        {tooltip && (
          <button
            className="text-gray-600 transition-colors hover:text-pandora-cyan"
            onClick={() => setShowTooltip(!showTooltip)}
            onMouseEnter={() => setShowTooltip(true)}
            onMouseLeave={() => setShowTooltip(false)}
            type="button"
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
        <div className="absolute top-full left-0 z-50 max-w-[200px] whitespace-normal border border-white/20 bg-black px-2 py-1 text-[9px] text-gray-400">
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

// Regex for parsing allocation queue (moved to top level for performance)
const ALLOCATION_QUEUE_REGEX = /~?(\d+)H?/;

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
  if (humanValues[value]) {
    return humanValues[value];
  }

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
    const match = ALLOCATION_QUEUE_REGEX.exec(value);
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
      animate={{ opacity: 1, x: 0 }}
      className="space-y-0 font-mono text-xs"
      exit={{ opacity: 0, x: 10 }}
      initial={{ opacity: 0, x: -10 }}
      key="specs"
    >
      <SpecRow
        humanLabel={humanLabels.ACCESS_PROTOCOL.label}
        humanValue={getHumanValue(accessProtocol)}
        label="ACCESS_PROTOCOL"
        tooltip={humanLabels.ACCESS_PROTOCOL.tooltip}
        value={accessProtocol}
        valueColor={nodeStatusColor}
      />
      <SpecRow
        humanLabel={humanLabels.UPTIME_ASSURANCE.label}
        humanValue={getHumanValue(warrantyLabel)}
        label="UPTIME_ASSURANCE"
        tooltip={humanLabels.UPTIME_ASSURANCE.tooltip}
        value={warrantyLabel}
        valueColor="text-pandora-cyan"
      />
      <SpecRow
        humanLabel={humanLabels.SESSION_DURATION.label}
        humanValue={getHumanValue(durationLabel)}
        label="SESSION_DURATION"
        tooltip={humanLabels.SESSION_DURATION.tooltip}
        value={durationLabel}
      />
      <SpecRow
        humanLabel={humanLabels.DEPLOY_MODE.label}
        humanValue={getHumanValue(deliveryLabel)}
        label="DEPLOY_MODE"
        tooltip={humanLabels.DEPLOY_MODE.tooltip}
        value={deliveryLabel}
        valueColor={nodeStatusColor}
      />
      <SpecRow
        humanLabel={humanLabels.SECURE_UPLINK.label}
        humanValue="AES-256"
        label="SECURE_UPLINK"
        tooltip={humanLabels.SECURE_UPLINK.tooltip}
        value="AES-256-GCM"
      />
      <SpecRow
        humanLabel={humanLabels.NODE_STATUS.label}
        humanValue={getHumanValue(nodeStatus)}
        label="NODE_STATUS"
        tooltip={humanLabels.NODE_STATUS.tooltip}
        value={nodeStatus}
        valueColor={nodeStatusColor}
      />
    </motion.div>
  );
};

export default memo(ProductSpecs);
