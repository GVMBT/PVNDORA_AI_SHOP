
import React, { memo } from 'react';
import { MessageCircle, Mail, FileText, Shield, HelpCircle, CreditCard, ChevronRight } from 'lucide-react';
import { useLocale } from '../../hooks/useLocale';

interface FooterProps {
  onNavigate: (page: string) => void;
  onOpenSupport?: () => void;
}

const FooterComponent: React.FC<FooterProps> = ({ onNavigate, onOpenSupport }) => {
  const { t } = useLocale();
  
  const handleSupportClick = () => {
      if (onOpenSupport) {
          onOpenSupport();
      } else {
          onNavigate('support');
      }
  };

  const currentYear = new Date().getFullYear();

  return (
    <footer className="bg-[#050505] border-t border-white/10 relative overflow-hidden">
      
      {/* =========================================================================
          DESKTOP LAYOUT (Hidden on Mobile)
          Standardized Padding: md:pl-28
         ========================================================================= */}
      <div className="hidden md:block pt-16 pb-16 md:pl-28 relative z-10 transition-all duration-300">
          <div className="max-w-7xl mx-auto px-6">
            <div className="grid grid-cols-4 gap-12 mb-16">
                
                {/* Brand Column */}
                <div className="col-span-1">
                    <h2 className="text-2xl font-display font-bold text-white mb-4 flex items-center gap-2">
                        PVNDORA
                    </h2>
                    <p className="text-gray-500 text-xs font-mono leading-relaxed mb-6">
                        {t('footer.brandDescription')}
                    </p>
                    <div className="flex gap-4">
                        <button 
                            onClick={handleSupportClick}
                            className="w-10 h-10 border border-white/10 rounded-sm flex items-center justify-center text-gray-400 hover:text-pandora-cyan hover:border-pandora-cyan transition-all"
                        >
                            <MessageCircle size={18} />
                        </button>
                        <button 
                            onClick={() => window.open('mailto:support@pvndora.app')}
                            className="w-10 h-10 border border-white/10 rounded-sm flex items-center justify-center text-gray-400 hover:text-pandora-cyan hover:border-pandora-cyan transition-all"
                        >
                            <Mail size={18} />
                        </button>
                    </div>
                </div>

                {/* Links Column 1 */}
                <div>
                    <h3 className="text-white font-bold uppercase tracking-wider text-xs mb-6 flex items-center gap-2">
                        <HelpCircle size={14} className="text-pandora-cyan" />
                        {t('footer.customers')}
                    </h3>
                    <ul className="space-y-3 text-xs font-mono text-gray-500">
                        <li><button onClick={() => onNavigate('faq')} className="hover:text-pandora-cyan transition-colors text-left">{t('footer.faq')}</button></li>
                        <li><button onClick={handleSupportClick} className="hover:text-pandora-cyan transition-colors text-left">{t('footer.techSupport')}</button></li>
                        <li><button onClick={() => onNavigate('payment')} className="hover:text-pandora-cyan transition-colors text-left">{t('footer.paymentDelivery')}</button></li>
                    </ul>
                </div>

                {/* Links Column 2 */}
                <div>
                    <h3 className="text-white font-bold uppercase tracking-wider text-xs mb-6 flex items-center gap-2">
                        <FileText size={14} className="text-pandora-cyan" />
                        {t('footer.legalInfo')}
                    </h3>
                    <ul className="space-y-3 text-xs font-mono text-gray-500">
                        <li><button onClick={() => onNavigate('terms')} className="hover:text-pandora-cyan transition-colors text-left">{t('footer.termsOfService')}</button></li>
                        <li><button onClick={() => onNavigate('privacy')} className="hover:text-pandora-cyan transition-colors text-left">{t('footer.privacyPolicy')}</button></li>
                        <li><button onClick={() => onNavigate('refund')} className="hover:text-pandora-cyan transition-colors text-left">{t('footer.refundPolicy')}</button></li>
                        <li><button onClick={() => onNavigate('payment')} className="hover:text-pandora-cyan transition-colors text-left">{t('footer.paymentInfo')}</button></li>
                    </ul>
                </div>

                {/* Support CTA */}
                <div>
                    <div className="bg-white/5 border border-white/10 p-6 rounded-sm">
                        <h4 className="text-white font-bold mb-2 text-sm">{t('footer.needHelp')}</h4>
                        <p className="text-xs text-gray-500 mb-4 font-mono">{t('footer.supportAvailable')}</p>
                        <button onClick={handleSupportClick} className="w-full bg-white text-black font-bold py-3 text-xs uppercase tracking-wider hover:bg-pandora-cyan transition-colors">
                            {t('footer.openTicket')}
                        </button>
                    </div>
                </div>
            </div>

            <div className="border-t border-white/10 pt-8 flex justify-between items-center gap-4 text-[10px] text-gray-600 font-mono">
                <div>{t('footer.copyright', { year: currentYear })}</div>
                <div className="flex gap-6 items-center">
                    <span className="flex items-center gap-1"><Shield size={10} /> {t('footer.sslEncrypted')}</span>
                    <span className="flex items-center gap-1"><CreditCard size={10} /> {t('footer.securePayment')}</span>
                </div>
            </div>
          </div>
      </div>

      {/* =========================================================================
          MOBILE LAYOUT (Compact & Minimal)
          Visible only on small screens. Padded bottom for Navbar.
         ========================================================================= */}
      <div className="md:hidden py-12 px-6 pb-32 relative z-10">
          
          <div className="flex flex-col gap-8">
             
             {/* 1. Compact Brand Header */}
             <div className="text-center opacity-80">
                <h2 className="text-xl font-display font-bold text-white tracking-widest">PVNDORA</h2>
                <div className="text-[10px] text-pandora-cyan font-mono uppercase tracking-widest mt-1">{t('footer.decentralizedMarket')}</div>
             </div>

             {/* 2. Compact Links Grid (2 Columns) */}
             <div className="grid grid-cols-2 gap-4 border-y border-white/5 py-8">
                
                {/* Left: Support */}
                <div className="space-y-4">
                    <h4 className="text-[10px] font-bold text-gray-500 uppercase flex items-center gap-1.5">
                        <HelpCircle size={10} /> {t('footer.support')}
                    </h4>
                    <ul className="space-y-3 text-xs font-mono text-gray-300">
                        <li><button onClick={() => onNavigate('faq')} className="hover:text-white transition-colors">FAQ</button></li>
                        <li><button onClick={handleSupportClick} className="hover:text-white transition-colors">{t('footer.contacts')}</button></li>
                        <li><button onClick={() => onNavigate('payment')} className="hover:text-white transition-colors">{t('footer.paymentInfo')}</button></li>
                    </ul>
                </div>

                {/* Right: Legal */}
                <div className="space-y-4 text-right">
                    <h4 className="text-[10px] font-bold text-gray-500 uppercase flex items-center justify-end gap-1.5">
                        {t('footer.legal')} <FileText size={10} /> 
                    </h4>
                    <ul className="space-y-3 text-xs font-mono text-gray-300">
                        <li><button onClick={() => onNavigate('terms')} className="hover:text-white transition-colors">{t('footer.termsOfService')}</button></li>
                        <li><button onClick={() => onNavigate('privacy')} className="hover:text-white transition-colors">{t('footer.privacyPolicy')}</button></li>
                        <li><button onClick={() => onNavigate('refund')} className="hover:text-white transition-colors">{t('footer.refundPolicy')}</button></li>
                        <li><button onClick={() => onNavigate('payment')} className="hover:text-white transition-colors">{t('footer.paymentInfo')}</button></li>
                    </ul>
                </div>
             </div>

             {/* 3. Bottom Credits */}
             <div className="flex flex-col items-center gap-2 text-[9px] font-mono text-gray-600 text-center">
                 <div className="flex gap-4">
                     <span className="flex items-center gap-1"><Shield size={8} /> {t('footer.sslSecure')}</span>
                     <span className="flex items-center gap-1"><CreditCard size={8} /> {t('footer.verified')}</span>
                 </div>
                 <p>© {currentYear} PVNDORA. {t('footer.allSystems')}</p>
             </div>
          </div>

      </div>
    </footer>
  );
};

const Footer = memo(FooterComponent);
export default Footer;
