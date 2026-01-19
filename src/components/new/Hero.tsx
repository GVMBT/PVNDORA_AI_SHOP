import { motion } from "framer-motion";
import { Activity, Cpu, Network, ShieldCheck } from "lucide-react";
import type React from "react";
import { memo } from "react";
import { useLocale } from "../../hooks/useLocale";
import PandoraBox from "./PandoraBox";

const HeroComponent: React.FC = () => {
  const { t } = useLocale();

  return (
    <section className="relative z-40 flex min-h-[100dvh] w-full flex-col overflow-visible bg-transparent">
      {/* Layout Adjustments for Navbars - Standardized to md:pl-28 */}
      <div className="relative z-10 flex flex-1 flex-col pb-20 transition-all duration-300 md:pb-0 md:pl-28">
        {/* BACKGROUND ART */}
        <div className="absolute top-0 right-0 bottom-0 left-0 z-0 opacity-80 transition-opacity duration-500 md:left-20 md:opacity-100">
          <PandoraBox />
        </div>

        {/* CONTENT UI */}
        <div className="relative z-20 flex flex-1 flex-col items-center justify-center gap-6 px-4 py-20 text-center sm:gap-10 sm:px-6">
          {/* Context Badge: Safe Narrative */}
          <motion.div
            animate={{ opacity: 1, y: 0 }}
            className="flex scale-90 items-center gap-2 rounded-full border border-pandora-cyan/30 bg-black/60 px-3 py-1.5 shadow-[0_0_15px_rgba(0,255,255,0.1)] backdrop-blur-md sm:scale-100 sm:gap-3"
            initial={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.6 }}
          >
            <div className="flex items-center gap-1.5">
              <ShieldCheck className="text-pandora-cyan" size={10} />
              <span className="font-bold font-mono text-[9px] text-pandora-cyan uppercase tracking-widest sm:text-[10px]">
                {t("hero.systemOnline")}
              </span>
            </div>
            <div className="h-3 w-px bg-white/10" />
            <span className="font-mono text-[9px] text-gray-400 sm:text-[10px]">
              {t("hero.nodeSynced")}
            </span>
          </motion.div>

          {/* Main Text Block */}
          <motion.div
            animate={{ opacity: 1, scale: 1 }}
            className="relative mx-auto w-full max-w-4xl"
            initial={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.8 }}
          >
            <div className="relative inline-block">
              <h1 className="relative z-10 font-black font-display text-5xl text-white leading-[0.9] tracking-tighter drop-shadow-2xl sm:text-7xl md:text-9xl">
                PVNDORA
              </h1>
            </div>

            {/* Subtitle / Value Prop */}
            <div className="mt-8 space-y-4 px-4">
              <p className="font-mono text-[10px] text-pandora-cyan uppercase tracking-[0.2em] drop-shadow-[0_0_5px_rgba(0,255,255,0.5)] sm:text-sm sm:tracking-[0.3em]">
                {t("hero.subtitle")}
              </p>
              <p className="mx-auto max-w-[280px] xs:max-w-sm font-body text-gray-400 text-xs leading-relaxed sm:max-w-lg sm:text-sm">
                {t("hero.description")}
                <br />
                <span className="mt-2 block text-white/60 italic">"{t("hero.quote")}"</span>
              </p>
            </div>
          </motion.div>

          {/* Stats / Tech Badges */}
          <motion.div
            animate={{ opacity: 1, y: 0 }}
            className="mb-4 hidden flex-wrap justify-center gap-3 sm:flex"
            initial={{ opacity: 0, y: 10 }}
            transition={{ duration: 0.8, delay: 0.4 }}
          >
            <div className="flex items-center gap-2 rounded-sm border border-white/10 bg-white/5 px-3 py-2 font-mono text-[10px] text-gray-300 backdrop-blur-md">
              <Network className="text-pandora-cyan" size={12} />
              <span>{t("hero.channelEncrypted")}</span>
            </div>
            <div className="flex items-center gap-2 rounded-sm border border-white/10 bg-white/5 px-3 py-2 font-mono text-[10px] text-gray-300 backdrop-blur-md">
              <Cpu className="text-pandora-cyan" size={12} />
              <span>{t("hero.resourcesAllocated")}</span>
            </div>
          </motion.div>

          {/* Instant Delivery Badge */}
          <motion.div
            animate={{ opacity: 1, y: 0 }}
            className="mt-4 sm:mt-0"
            initial={{ opacity: 0, y: 20 }}
            transition={{ duration: 0.8, delay: 0.6 }}
          >
            <div className="flex items-center justify-center gap-2 font-mono text-[9px] text-gray-500">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-green-500" />
              {t("hero.instantDelivery")}
            </div>
          </motion.div>
        </div>
      </div>

      {/* Footer Metadata (HUD Style) */}
      <div className="pointer-events-none absolute right-0 bottom-12 left-0 z-50 flex hidden w-full justify-between px-6 pr-6 font-mono text-[9px] text-pandora-cyan opacity-80 md:flex md:pl-32">
        <div className="flex gap-6">
          <span className="flex items-center gap-1">
            <Activity size={10} /> {t("hero.uptime")}
          </span>
          <span>{t("hero.gatewaySecure")}</span>
        </div>
        <div className="flex gap-6">
          <span>{t("hero.sectorPublic")}</span>
          <span>{t("hero.nodeId")}</span>
        </div>
      </div>
    </section>
  );
};

const Hero = memo(HeroComponent);
export default Hero;
