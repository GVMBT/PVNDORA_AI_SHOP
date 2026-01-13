import React, { memo } from "react";
import { Activity, Headphones, Lock, ShieldCheck, Zap } from "lucide-react";
import { motion } from "framer-motion";
import { useLocale } from "../../hooks/useLocale";

const GuaranteesComponent: React.FC = () => {
  const { t } = useLocale();

  const FEATURES = [
    {
      id: 1,
      titleKey: "guarantees.features.delivery.title",
      descriptionKey: "guarantees.features.delivery.description",
      icon: <Zap className="w-8 h-8 text-pandora-cyan" />,
      statKey: "guarantees.features.delivery.stat",
    },
    {
      id: 2,
      titleKey: "guarantees.features.validity.title",
      descriptionKey: "guarantees.features.validity.description",
      icon: <ShieldCheck className="w-8 h-8 text-pandora-cyan" />,
      statKey: "guarantees.features.validity.stat",
    },
    {
      id: 3,
      titleKey: "guarantees.features.support.title",
      descriptionKey: "guarantees.features.support.description",
      icon: <Headphones className="w-8 h-8 text-pandora-cyan" />,
      statKey: "guarantees.features.support.stat",
    },
  ];

  return (
    <section className="relative w-full text-white pt-0 pb-24 px-6 md:pl-28 overflow-hidden z-20 bg-transparent">
      {/* Visual smoothing for the grid entering this section */}
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-[#050505]/20 to-[#050505] pointer-events-none z-0" />

      <div className="max-w-7xl mx-auto relative z-10">
        {/* --- HEADER --- */}
        <div className="mb-16 md:mb-24">
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.7 }}
          >
            <div className="flex items-center gap-2 mb-2 text-pandora-cyan/70 font-mono text-xs tracking-widest">
              <Lock size={12} />
              <span>{t("guarantees.secureConnection")}</span>
            </div>
            <h2 className="text-3xl md:text-5xl font-display font-bold text-white uppercase tracking-tight flex flex-col md:block">
              <span>{t("guarantees.security")}</span>
              <span className="text-gray-600 mx-2 hidden md:inline">//</span>
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-pandora-cyan to-white">
                {t("guarantees.guaranteesTitle")}
              </span>
            </h2>
            <div className="h-1 w-24 bg-pandora-cyan mt-6 rounded-full shadow-[0_0_15px_#00FFFF]" />
          </motion.div>
        </div>

        {/* --- GRID --- */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {FEATURES.map((feature, index) => (
            <motion.div
              key={feature.id}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: index * 0.2 }}
              className="group relative"
            >
              {/* Card Container */}
              <div className="h-full bg-[#080808]/80 backdrop-blur-sm border border-white/10 p-8 relative overflow-hidden transition-all duration-500 hover:border-pandora-cyan/50 hover:bg-[#0c0c0c]/90">
                {/* Hover Glow Background */}
                <div className="absolute inset-0 bg-gradient-to-b from-pandora-cyan/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />

                {/* Tech Corners */}
                <div className="absolute top-0 right-0 w-4 h-4 border-t border-r border-white/20 group-hover:border-pandora-cyan transition-colors" />
                <div className="absolute bottom-0 left-0 w-4 h-4 border-b border-l border-white/20 group-hover:border-pandora-cyan transition-colors" />

                {/* Header Icon Area */}
                <div className="relative mb-6">
                  <div className="w-16 h-16 rounded-full bg-white/5 border border-white/10 flex items-center justify-center group-hover:scale-110 group-hover:border-pandora-cyan/30 group-hover:shadow-[0_0_20px_rgba(0,255,255,0.2)] transition-all duration-500">
                    {feature.icon}
                  </div>
                  {/* Connector Line */}
                  <div className="absolute left-8 top-16 w-px h-12 bg-gradient-to-b from-white/10 to-transparent group-hover:from-pandora-cyan/50 transition-colors" />
                </div>

                {/* Content */}
                <div className="relative z-10">
                  <h3 className="text-xl font-display font-bold text-white mb-3 group-hover:text-pandora-cyan transition-colors">
                    {t(feature.titleKey)}
                  </h3>
                  <p className="text-gray-400 font-body leading-relaxed mb-8">
                    {t(feature.descriptionKey)}
                  </p>
                </div>

                {/* Footer Stat (Tech feel) */}
                <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-white/5 flex items-center justify-between bg-black/20">
                  <div className="flex items-center gap-2">
                    <Activity
                      size={14}
                      className="text-gray-600 group-hover:text-pandora-cyan transition-colors"
                    />
                    <span className="font-mono text-[10px] text-pandora-cyan tracking-wider">
                      {t(feature.statKey)}
                    </span>
                  </div>
                  <div className="w-2 h-2 bg-gray-800 rounded-full group-hover:bg-green-500 transition-colors shadow-[0_0_5px_rgba(0,255,0,0.5)]" />
                </div>
              </div>
            </motion.div>
          ))}
        </div>

        {/* --- SYSTEM DECORATION --- */}
        <div className="mt-20 border-t border-white/10 pt-6 flex justify-between items-center opacity-40 font-mono text-[10px]">
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
