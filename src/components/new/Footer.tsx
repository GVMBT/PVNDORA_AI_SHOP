import { CreditCard, FileText, HelpCircle, Mail, MessageCircle, Shield } from "lucide-react";
import type React from "react";
import { memo } from "react";
import { useLocale } from "../../hooks/useLocale";

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
      onNavigate("support");
    }
  };

  const currentYear = new Date().getFullYear();

  return (
    <footer className="relative overflow-hidden border-white/10 border-t bg-[#050505]">
      {/* =========================================================================
          DESKTOP LAYOUT (Hidden on Mobile)
          Standardized Padding: md:pl-28
         ========================================================================= */}
      <div className="relative z-10 hidden pt-16 pb-16 transition-all duration-300 md:block md:pl-28">
        <div className="mx-auto max-w-7xl px-6">
          <div className="mb-16 grid grid-cols-4 gap-12">
            {/* Brand Column */}
            <div className="col-span-1">
              <h2 className="mb-4 flex items-center gap-2 font-bold font-display text-2xl text-white">
                PVNDORA
              </h2>
              <p className="mb-6 font-mono text-gray-500 text-xs leading-relaxed">
                {t("footer.brandDescription")}
              </p>
              <div className="flex gap-4">
                <button
                  className="flex h-10 w-10 items-center justify-center rounded-sm border border-white/10 text-gray-400 transition-all hover:border-pandora-cyan hover:text-pandora-cyan"
                  onClick={handleSupportClick}
                  type="button"
                >
                  <MessageCircle size={18} />
                </button>
                <button
                  className="flex h-10 w-10 items-center justify-center rounded-sm border border-white/10 text-gray-400 transition-all hover:border-pandora-cyan hover:text-pandora-cyan"
                  onClick={() => globalThis.open("mailto:support@pvndora.app")}
                  type="button"
                >
                  <Mail size={18} />
                </button>
              </div>
            </div>

            {/* Links Column 1 */}
            <div>
              <h3 className="mb-6 flex items-center gap-2 font-bold text-white text-xs uppercase tracking-wider">
                <HelpCircle className="text-pandora-cyan" size={14} />
                {t("footer.customers")}
              </h3>
              <ul className="space-y-3 font-mono text-gray-500 text-xs">
                <li>
                  <button
                    className="text-left transition-colors hover:text-pandora-cyan"
                    onClick={() => onNavigate("faq")}
                    type="button"
                  >
                    {t("footer.faq")}
                  </button>
                </li>
                <li>
                  <button
                    className="text-left transition-colors hover:text-pandora-cyan"
                    onClick={handleSupportClick}
                    type="button"
                  >
                    {t("footer.techSupport")}
                  </button>
                </li>
                <li>
                  <button
                    className="text-left transition-colors hover:text-pandora-cyan"
                    onClick={() => onNavigate("payment")}
                    type="button"
                  >
                    {t("footer.paymentDelivery")}
                  </button>
                </li>
              </ul>
            </div>

            {/* Links Column 2 */}
            <div>
              <h3 className="mb-6 flex items-center gap-2 font-bold text-white text-xs uppercase tracking-wider">
                <FileText className="text-pandora-cyan" size={14} />
                {t("footer.legalInfo")}
              </h3>
              <ul className="space-y-3 font-mono text-gray-500 text-xs">
                <li>
                  <button
                    className="text-left transition-colors hover:text-pandora-cyan"
                    onClick={() => onNavigate("terms")}
                    type="button"
                  >
                    {t("footer.termsOfService")}
                  </button>
                </li>
                <li>
                  <button
                    className="text-left transition-colors hover:text-pandora-cyan"
                    onClick={() => onNavigate("privacy")}
                    type="button"
                  >
                    {t("footer.privacyPolicy")}
                  </button>
                </li>
                <li>
                  <button
                    className="text-left transition-colors hover:text-pandora-cyan"
                    onClick={() => onNavigate("refund")}
                    type="button"
                  >
                    {t("footer.refundPolicy")}
                  </button>
                </li>
              </ul>
            </div>

            {/* Support CTA */}
            <div>
              <div className="rounded-sm border border-white/10 bg-white/5 p-6">
                <h4 className="mb-2 font-bold text-sm text-white">{t("footer.needHelp")}</h4>
                <p className="mb-4 font-mono text-gray-500 text-xs">
                  {t("footer.supportAvailable")}
                </p>
                <button
                  className="w-full bg-white py-3 font-bold text-black text-xs uppercase tracking-wider transition-colors hover:bg-pandora-cyan"
                  onClick={handleSupportClick}
                  type="button"
                >
                  {t("footer.openTicket")}
                </button>
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between gap-4 border-white/10 border-t pt-8 font-mono text-[10px] text-gray-600">
            <div>{t("footer.copyright", { year: currentYear })}</div>
            <div className="flex items-center gap-6">
              <span className="flex items-center gap-1">
                <Shield size={10} /> {t("footer.sslEncrypted")}
              </span>
              <span className="flex items-center gap-1">
                <CreditCard size={10} /> {t("footer.securePayment")}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* =========================================================================
          MOBILE LAYOUT (Compact & Minimal)
          Visible only on small screens. Padded bottom for Navbar.
         ========================================================================= */}
      <div className="relative z-10 px-5 py-10 pb-32 md:hidden">
        <div className="flex flex-col gap-10">
          {/* 1. Compact Brand Header */}
          <div className="text-center">
            <h2 className="mb-1.5 font-bold font-display text-2xl text-white tracking-wider">
              PVNDORA
            </h2>
            <div className="font-mono text-[10px] text-pandora-cyan uppercase leading-tight tracking-wider">
              {t("footer.decentralizedMarket")}
            </div>
          </div>

          {/* 2. Compact Links Grid (2 Columns) */}
          <div className="grid grid-cols-2 gap-6 border-white/10 border-y py-10">
            {/* Left: Support */}
            <div className="space-y-3.5">
              <h4 className="mb-4 flex items-center gap-1.5 font-bold text-[10px] text-white uppercase tracking-wider">
                <HelpCircle className="text-pandora-cyan" size={11} /> {t("footer.support")}
              </h4>
              <ul className="space-y-2.5 font-mono text-gray-400 text-xs">
                <li>
                  <button
                    className="w-full text-left transition-colors hover:text-white"
                    onClick={() => onNavigate("faq")}
                    type="button"
                  >
                    FAQ
                  </button>
                </li>
                <li>
                  <button
                    className="w-full text-left transition-colors hover:text-white"
                    onClick={handleSupportClick}
                    type="button"
                  >
                    {t("footer.contacts")}
                  </button>
                </li>
                <li>
                  <button
                    className="w-full text-left transition-colors hover:text-white"
                    onClick={() => onNavigate("payment")}
                    type="button"
                  >
                    {t("footer.paymentInfo")}
                  </button>
                </li>
              </ul>
            </div>

            {/* Right: Legal */}
            <div className="space-y-3.5">
              <h4 className="mb-4 flex items-center justify-end gap-1.5 font-bold text-[10px] text-white uppercase tracking-wider">
                {t("footer.legal")} <FileText className="text-pandora-cyan" size={11} />
              </h4>
              <ul className="space-y-2.5 text-right font-mono text-gray-400 text-xs">
                <li>
                  <button
                    className="w-full text-right transition-colors hover:text-white"
                    onClick={() => onNavigate("terms")}
                    type="button"
                  >
                    {t("footer.termsOfService")}
                  </button>
                </li>
                <li>
                  <button
                    className="w-full text-right transition-colors hover:text-white"
                    onClick={() => onNavigate("privacy")}
                    type="button"
                  >
                    {t("footer.privacyPolicy")}
                  </button>
                </li>
                <li>
                  <button
                    className="w-full text-right transition-colors hover:text-white"
                    onClick={() => onNavigate("refund")}
                    type="button"
                  >
                    {t("footer.refundPolicy")}
                  </button>
                </li>
              </ul>
            </div>
          </div>

          {/* 3. Bottom Credits */}
          <div className="flex flex-col items-center gap-3 text-center font-mono text-[9px] text-gray-500">
            <div className="flex items-center gap-5">
              <span className="flex items-center gap-1.5">
                <Shield className="text-gray-400" size={9} />
                <span>{t("footer.sslSecure")}</span>
              </span>
              <span className="flex items-center gap-1.5">
                <CreditCard className="text-gray-400" size={9} />
                <span>{t("footer.verified")}</span>
              </span>
            </div>
            <p className="text-gray-600">
              © {currentYear} PVNDORA. {t("footer.allSystems")}
            </p>
          </div>
        </div>
      </div>
    </footer>
  );
};

const Footer = memo(FooterComponent);
export default Footer;
