import { motion } from "framer-motion";
import { Activity, Headphones, Lock, ShieldCheck, Zap } from "lucide-react";
import type React from "react";
import { memo } from "react";
import { useLocale } from "../../hooks/useLocale";

const GuaranteesComponent: React.FC = () => {
  const { t } = useLocale();

  const FEATURES = [
    {
      id: 1,
      titleKey: "guarantees.features.delivery.title",
      descriptionKey: "guarantees.features.delivery.description",
      icon: <Zap className="h-8 w-8 text-pandora-cyan" />,
      statKey: "guarantees.features.delivery.stat",
    },
    {
      id: 2,
      titleKey: "guarantees.features.validity.title",
      descriptionKey: "guarantees.features.validity.description",
      icon: <ShieldCheck className="h-8 w-8 text-pandora-cyan" />,
      statKey: "guarantees.features.validity.stat",
    },
    {
      id: 3,
      titleKey: "guarantees.features.support.title",
      descriptionKey: "guarantees.features.support.description",
      icon: <Headphones className="h-8 w-8 text-pandora-cyan" />,
      statKey: "guarantees.features.support.stat",
    },
  ];

  return (
    <section className="relative z-20 w-full overflow-hidden bg-transparent px-6 pt-0 pb-24 text-white md:pl-28">
      {/* Visual smoothing for the grid entering this section */}
      <div className="pointer-events-none absolute inset-0 z-0 bg-gradient-to-b from-transparent via-[#050505]/20 to-[#050505]" />

      <div className="relative z-10 mx-auto max-w-7xl">
        {/* --- HEADER --- */}
        <div className="mb-16 md:mb-24">
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            transition={{ duration: 0.7 }}
            viewport={{ once: true }}
            whileInView={{ opacity: 1, x: 0 }}
          >
            <div className="mb-2 flex items-center gap-2 font-mono text-pandora-cyan/70 text-xs tracking-widest">
              <Lock size={12} />
              <span>{t("guarantees.secureConnection")}</span>
            </div>
            <h2 className="flex flex-col font-bold font-display text-3xl text-white uppercase tracking-tight md:block md:text-5xl">
              <span>{t("guarantees.security")}</span>
              <span className="mx-2 hidden text-gray-600 md:inline">{"//  "}</span>
              <span className="bg-gradient-to-r from-pandora-cyan to-white bg-clip-text text-transparent">
                {t("guarantees.guaranteesTitle")}
              </span>
            </h2>
            <div className="mt-6 h-1 w-24 rounded-full bg-pandora-cyan shadow-[0_0_15px_#00FFFF]" />
          </motion.div>
        </div>

        {/* --- GRID --- */}
        <div className="grid grid-cols-1 gap-8 md:grid-cols-3">
          {FEATURES.map((feature, index) => (
            <motion.div
              className="group relative"
              initial={{ opacity: 0, y: 30 }}
              key={feature.id}
              transition={{ duration: 0.5, delay: index * 0.2 }}
              viewport={{ once: true }}
              whileInView={{ opacity: 1, y: 0 }}
            >
              {/* Card Container */}
              <div className="relative h-full overflow-hidden border border-white/10 bg-[#080808]/80 p-8 backdrop-blur-sm transition-all duration-500 hover:border-pandora-cyan/50 hover:bg-[#0c0c0c]/90">
                {/* Hover Glow Background */}
                <div className="absolute inset-0 bg-gradient-to-b from-pandora-cyan/5 to-transparent opacity-0 transition-opacity duration-500 group-hover:opacity-100" />

                {/* Tech Corners */}
                <div className="absolute top-0 right-0 h-4 w-4 border-white/20 border-t border-r transition-colors group-hover:border-pandora-cyan" />
                <div className="absolute bottom-0 left-0 h-4 w-4 border-white/20 border-b border-l transition-colors group-hover:border-pandora-cyan" />

                {/* Header Icon Area */}
                <div className="relative mb-6">
                  <div className="flex h-16 w-16 items-center justify-center rounded-full border border-white/10 bg-white/5 transition-all duration-500 group-hover:scale-110 group-hover:border-pandora-cyan/30 group-hover:shadow-[0_0_20px_rgba(0,255,255,0.2)]">
                    {feature.icon}
                  </div>
                  {/* Connector Line */}
                  <div className="absolute top-16 left-8 h-12 w-px bg-gradient-to-b from-white/10 to-transparent transition-colors group-hover:from-pandora-cyan/50" />
                </div>

                {/* Content */}
                <div className="relative z-10">
                  <h3 className="mb-3 font-bold font-display text-white text-xl transition-colors group-hover:text-pandora-cyan">
                    {t(feature.titleKey)}
                  </h3>
                  <p className="mb-8 font-body text-gray-400 leading-relaxed">
                    {t(feature.descriptionKey)}
                  </p>
                </div>

                {/* Footer Stat (Tech feel) */}
                <div className="absolute right-0 bottom-0 left-0 flex items-center justify-between border-white/5 border-t bg-black/20 p-4">
                  <div className="flex items-center gap-2">
                    <Activity
                      className="text-gray-600 transition-colors group-hover:text-pandora-cyan"
                      size={14}
                    />
                    <span className="font-mono text-[10px] text-pandora-cyan tracking-wider">
                      {t(feature.statKey)}
                    </span>
                  </div>
                  <div className="h-2 w-2 rounded-full bg-gray-800 shadow-[0_0_5px_rgba(0,255,0,0.5)] transition-colors group-hover:bg-green-500" />
                </div>
              </div>
            </motion.div>
          ))}
        </div>

        {/* --- SYSTEM DECORATION --- */}
        <div className="mt-20 flex items-center justify-between border-white/10 border-t pt-6 font-mono text-[10px] opacity-40">
          <span>{t("guarantees.sslEncrypted")}</span>
          <span className="hidden sm:inline">{t("guarantees.nodesActive")}</span>
          <span>{t("guarantees.protocol")}</span>
        </div>
      </div>
    </section>
  );
};

const Guarantees = memo(GuaranteesComponent);
export default Guarantees;
