
import React from 'react';
import PandoraBox from './PandoraBox';
import { Terminal, Zap, Unlock, Cpu, Network, Activity, ShieldCheck, Lock } from 'lucide-react';
import { motion } from 'framer-motion';

const Hero: React.FC = () => {
  const scrollToCatalog = () => {
    const catalog = document.getElementById('catalog');
    if (catalog) {
      catalog.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <section className="relative w-full min-h-[100dvh] bg-transparent flex flex-col z-40 overflow-visible">
      
      {/* Layout Adjustments for Navbars - Standardized to md:pl-28 */}
      <div className="flex-1 flex flex-col md:pl-28 pb-20 md:pb-0 transition-all duration-300 relative z-10"> 
          
          {/* BACKGROUND ART */}
          <div className="absolute top-0 bottom-0 left-0 right-0 md:left-20 z-0 opacity-80 md:opacity-100 transition-opacity duration-500">
              <PandoraBox />
          </div>

          {/* CONTENT UI */}
          <div className="relative z-20 flex-1 flex flex-col items-center justify-center text-center px-4 sm:px-6 gap-6 sm:gap-10 py-20">
            
            {/* Context Badge: Safe Narrative */}
            <motion.div 
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
              className="flex items-center gap-2 sm:gap-3 px-3 py-1.5 rounded-full border border-pandora-cyan/30 bg-black/60 backdrop-blur-md shadow-[0_0_15px_rgba(0,255,255,0.1)] scale-90 sm:scale-100"
            >
                <div className="flex items-center gap-1.5">
                    <ShieldCheck size={10} className="text-pandora-cyan" />
                    <span className="text-[9px] sm:text-[10px] font-mono text-pandora-cyan tracking-widest uppercase font-bold">SYSTEM: ONLINE</span>
                </div>
                <div className="w-px h-3 bg-white/10" />
                <span className="text-[9px] sm:text-[10px] font-mono text-gray-400">NODE_SYNCHRONIZED</span>
            </motion.div>

            {/* Main Text Block */}
            <motion.div 
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.8 }}
              className="relative w-full max-w-4xl mx-auto"
            >
                <div className="relative inline-block">
                    <h1 className="font-display font-black text-5xl sm:text-7xl md:text-9xl text-white tracking-tighter relative z-10 leading-[0.9] drop-shadow-2xl">
                        PVNDORA
                    </h1>
                </div>
                
                {/* Subtitle / Value Prop */}
                <div className="mt-8 space-y-4 px-4">
                    <p className="font-mono text-[10px] sm:text-sm text-pandora-cyan uppercase tracking-[0.2em] sm:tracking-[0.3em] drop-shadow-[0_0_5px_rgba(0,255,255,0.5)]">
                        DECENTRALIZED COMPUTE MARKETPLACE
                    </p>
                    <p className="text-xs sm:text-sm text-gray-400 max-w-[280px] xs:max-w-sm sm:max-w-lg mx-auto leading-relaxed font-body">
                        Мгновенный доступ к премиальным мощностям Veo 3.1, Claude Max и Nano Banana Pro.
                        Автоматизированная выдача ключей. Гарантия валидности.
                        <br/>
                        <span className="text-white/60 italic mt-2 block">"Unlocking the full potential of generative AI."</span>
                    </p>
                </div>
            </motion.div>


            {/* Stats / Tech Badges */}
            <motion.div 
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8, delay: 0.4 }}
                className="hidden sm:flex flex-wrap justify-center gap-3 mb-4"
            >
                <div className="flex items-center gap-2 px-3 py-2 rounded-sm bg-white/5 backdrop-blur-md border border-white/10 text-[10px] font-mono text-gray-300">
                    <Network size={12} className="text-pandora-cyan" />
                    <span>CHANNEL: ENCRYPTED</span>
                </div>
                <div className="flex items-center gap-2 px-3 py-2 rounded-sm bg-white/5 backdrop-blur-md border border-white/10 text-[10px] font-mono text-gray-300">
                    <Cpu size={12} className="text-pandora-cyan" />
                    <span>RESOURCES: ALLOCATED</span>
                </div>
            </motion.div>

            {/* CTA Button */}
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.6 }}
              className="mt-4 sm:mt-0 relative"
            >
              <button 
                id="open-pandora"
                onClick={scrollToCatalog}
                className="group relative px-8 sm:px-12 py-4 sm:py-5 bg-white text-black font-display font-black text-xs sm:text-sm tracking-[0.2em] uppercase transition-all duration-300 hover:bg-pandora-cyan hover:shadow-[0_0_40px_rgba(0,255,255,0.6)] overflow-hidden clip-path-polygon"
              >
                <span className="relative z-10 flex items-center justify-center gap-3">
                    <Zap size={16} className="fill-black sm:w-[18px] sm:h-[18px]" />
                    INITIALIZE ACCESS
                </span>
                
                {/* Glitch Effect Overlay */}
                <div className="absolute inset-0 bg-pandora-cyan opacity-0 group-hover:opacity-100 mix-blend-overlay transition-opacity duration-100" />
              </button>
              
              <div className="mt-4 text-[9px] text-gray-600 font-mono flex items-center justify-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
                  INSTANT DELIVERY PROTOCOL ACTIVE
              </div>
            </motion.div>

          </div>
      </div>

      {/* Footer Metadata (HUD Style) */}
      <div className="absolute bottom-12 left-0 right-0 z-50 w-full flex justify-between px-6 md:pl-32 pr-6 opacity-80 pointer-events-none hidden md:flex text-[9px] font-mono text-pandora-cyan">
          <div className="flex gap-6">
              <span className="flex items-center gap-1"><Activity size={10} /> UPTIME: 99.9%</span>
              <span>GATEWAY: SECURE</span>
          </div>
          <div className="flex gap-6">
              <span>SECTOR: PUBLIC</span>
              <span>NODE_ID: #PNDR-OFFICIAL</span>
          </div>
      </div>

    </section>
  );
};

export default Hero;
