
import React from 'react';
import { ArrowLeft, FileText, Shield, HelpCircle, Mail, Terminal, ChevronRight } from 'lucide-react';
import { motion } from 'framer-motion';

interface LegalProps {
  doc: string;
  onBack: () => void;
}

const Legal: React.FC<LegalProps> = ({ doc, onBack }) => {
  
  const renderContent = () => {
    switch (doc) {
      case 'terms':
        return (
          <div className="space-y-6 text-gray-400 font-mono text-xs md:text-sm leading-relaxed">
            <h2 className="text-white font-display text-xl mb-4">Пользовательское соглашение</h2>
            <p>1. ОБЩИЕ ПОЛОЖЕНИЯ</p>
            <p>1.1. Настоящее Пользовательское соглашение (далее — Соглашение) регулирует отношения между сервисом PVNDORA (далее — Исполнитель) и пользователем сети Интернет (далее — Пользователь), возникающие при аренде вычислительных мощностей нейросетей.</p>
            <p>1.2. Используя сервис, Пользователь подтверждает, что он ознакомился с условиями настоящего Соглашения и принимает их в полном объеме без каких-либо исключений.</p>
            
            <p>2. ПРЕДМЕТ СОГЛАШЕНИЯ</p>
            <p>2.1. Исполнитель предоставляет Пользователю доступ к облачным вычислительным мощностям нейросетей (включая, но не ограничиваясь Veo 3.1, Nano banana pro) посредством передачи ключей авторизации и API-токенов.</p>
            <p>2.2. Сервис действует как поставщик инфраструктуры. Все ресурсы предоставляются "как есть".</p>

            <p>3. ПРАВА И ОБЯЗАННОСТИ СТОРОН</p>
            <p>3.1. Пользователь обязуется использовать полученные ресурсы только в законных целях и не передавать данные доступа третьим лицам.</p>
            <p>3.2. Исполнитель обязуется обеспечить выделение мощностей в течение 24 часов с момента подтверждения транзакции.</p>

            <p>4. ОТВЕТСТВЕННОСТЬ</p>
            <p>4.1. Исполнитель не несет ответственности за изменения в алгоритмах работы нейросетей, производимых их разработчиками.</p>
          </div>
        );
      case 'privacy':
        return (
          <div className="space-y-6 text-gray-400 font-mono text-xs md:text-sm leading-relaxed">
            <h2 className="text-white font-display text-xl mb-4">Политика конфиденциальности</h2>
            <p>1. СБОР ДАННЫХ</p>
            <p>1.1. Мы собираем минимально необходимый набор данных для исполнения обязательств перед Пользователем: адрес электронной почты (для доставки реквизитов доступа) и технические данные сессии (cookies).</p>
            
            <p>2. ИСПОЛЬЗОВАНИЕ ДАННЫХ</p>
            <p>2.1. Данные используются исключительно для обработки заказов, обеспечения безопасности подключения и предоставления технической поддержки.</p>
            <p>2.2. Мы не передаем личные данные третьим лицам, за исключением случаев, предусмотренных законодательством.</p>

            <p>3. БЕЗОПАСНОСТЬ</p>
            <p>3.1. Все данные передаются по защищенному протоколу SSL. Платежные данные обрабатываются на стороне платежного шлюза и не сохраняются на наших серверах.</p>
          </div>
        );
      case 'refund':
        return (
          <div className="space-y-6 text-gray-400 font-mono text-xs md:text-sm leading-relaxed">
            <h2 className="text-white font-display text-xl mb-4">Политика возврата</h2>
            <p>1. ЦИФРОВЫЕ УСЛУГИ</p>
            <p>1.1. В соответствии с законодательством, услуги по предоставлению вычислительных мощностей, к которым был предоставлен доступ, возврату и обмену не подлежат, так как они потребляются в момент предоставления.</p>
            
            <p>2. ГАРАНТИЙНЫЕ СЛУЧАИ</p>
            <p>2.1. Если предоставленный доступ оказался невалидным (технический сбой) на момент выдачи, Пользователь имеет право на замену или возврат средств.</p>
            <p>2.2. Претензии принимаются в течение гарантийного срока (указан в карточке услуги) через службу поддержки.</p>
            
            <p>3. ПРОЦЕДУРА ВОЗВРАТА</p>
            <p>3.1. Возврат средств осуществляется на тот же платежный инструмент, с которого была произведена оплата, в течение 3-7 рабочих дней после принятия решения.</p>
          </div>
        );
      case 'faq':
        return (
          <div className="space-y-8">
             <h2 className="text-white font-display text-xl mb-6">FAQ (Частые вопросы)</h2>
             
             <div className="border border-white/10 p-4 bg-white/5">
                <h3 className="text-white font-bold mb-2">Как быстро я получу доступ?</h3>
                <p className="text-gray-400 font-mono text-xs">В 99% случаев выдача происходит мгновенно после оплаты. Данные отобразятся в личном кабинете и придут на почту.</p>
             </div>
             
             <div className="border border-white/10 p-4 bg-white/5">
                <h3 className="text-white font-bold mb-2">Нужен ли VPN?</h3>
                <p className="text-gray-400 font-mono text-xs">Зависит от ресурса. В карточке каждой услуги мы указываем требования к подключению.</p>
             </div>

             <div className="border border-white/10 p-4 bg-white/5">
                <h3 className="text-white font-bold mb-2">Что делать, если доступ не работает?</h3>
                <p className="text-gray-400 font-mono text-xs">Напишите в нашу поддержку (раздел Support). Мы проверим токен и, если он невалиден, выдадим замену.</p>
             </div>

             <div className="border border-white/10 p-4 bg-white/5">
                <h3 className="text-white font-bold mb-2">Какие способы оплаты доступны?</h3>
                <p className="text-gray-400 font-mono text-xs">Мы принимаем банковские карты (РФ и мир), криптовалюты (USDT, BTC) и переводы через СБП.</p>
             </div>
          </div>
        );
      case 'payment':
        return (
            <div className="space-y-6 text-gray-400 font-mono text-xs md:text-sm leading-relaxed">
            <h2 className="text-white font-display text-xl mb-4">Оплата и доставка</h2>
            <p>1. ПРОЦЕСС ОПЛАТЫ</p>
            <p>Выбор тарифа → Переход к оплате → Выбор метода (Карта/Крипто) → Проведение платежа → Автоматический возврат в магазин.</p>
            
            <p>2. БЕЗОПАСНОСТЬ ПЛАТЕЖЕЙ</p>
            <p>Оплата происходит через защищенный платежный шлюз. Мы не получаем и не храним данные ваших карт.</p>
            
            <p>3. ДОСТАВКА</p>
            <p>Доставка осуществляется в электронном виде. Данные для подключения отображаются в разделе "Orders" и дублируются на email.</p>
            </div>
        );
      case 'support':
        return (
          <div className="space-y-8">
             <h2 className="text-white font-display text-xl mb-6">Техническая поддержка</h2>
             
             <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="border border-white/10 p-6 bg-[#0a0a0a] flex flex-col items-center text-center">
                    <div className="w-12 h-12 bg-pandora-cyan text-black rounded-full flex items-center justify-center mb-4">
                        <Terminal size={24} />
                    </div>
                    <h3 className="text-white font-bold mb-2">Telegram Support</h3>
                    <p className="text-gray-500 text-xs font-mono mb-4">Самый быстрый способ получить ответ.</p>
                    <a href="#" className="text-pandora-cyan font-bold hover:underline">@pvndora_support</a>
                </div>

                <div className="border border-white/10 p-6 bg-[#0a0a0a] flex flex-col items-center text-center">
                    <div className="w-12 h-12 bg-white/10 text-white rounded-full flex items-center justify-center mb-4">
                        <Mail size={24} />
                    </div>
                    <h3 className="text-white font-bold mb-2">Email</h3>
                    <p className="text-gray-500 text-xs font-mono mb-4">Для деловых предложений и жалоб.</p>
                    <a href="mailto:support@pvndora.io" className="text-white font-bold hover:underline">support@pvndora.io</a>
                </div>
             </div>

             <div className="bg-white/5 p-4 border-l-2 border-pandora-cyan">
                <p className="text-gray-300 text-sm">Время работы поддержки: <span className="text-white font-bold">10:00 - 22:00 (МСК)</span>, без выходных.</p>
             </div>
          </div>
        );
      default:
        return <div>Document not found</div>;
    }
  };

  const getTitle = () => {
      switch(doc) {
          case 'terms': return 'TERMS_OF_SERVICE';
          case 'privacy': return 'PRIVACY_POLICY';
          case 'faq': return 'FAQ_DATABASE';
          case 'support': return 'SUPPORT_CENTER';
          case 'refund': return 'REFUND_POLICY';
          case 'payment': return 'PAYMENT_INFO';
          default: return 'SYSTEM_DOC';
      }
  }

  return (
    <motion.div 
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="min-h-screen text-white pt-24 pb-32 px-4 md:px-8 md:pl-28 relative"
    >
        <div className="max-w-4xl mx-auto relative z-10">
            
            {/* === UNIFIED HEADER (Leaderboard Style) === */}
            <div className="mb-8 md:mb-16">
                <button onClick={onBack} className="flex items-center gap-2 text-[10px] font-mono text-gray-500 hover:text-pandora-cyan mb-4 transition-colors">
                    <ArrowLeft size={12} /> RETURN_TO_BASE
                </button>
                <h1 className="text-3xl sm:text-4xl md:text-6xl font-display font-black text-white uppercase tracking-tighter leading-[0.9] mb-4">
                    LEGAL <br/> <span className="text-transparent bg-clip-text bg-gradient-to-r from-pandora-cyan to-white/50">PROTOCOL</span>
                </h1>
                <div className="flex items-center gap-2 text-[10px] font-mono text-pandora-cyan tracking-widest uppercase">
                     <Shield size={12} />
                     <span>DOCUMENT_ID: {getTitle()}</span>
                </div>
            </div>

            {/* Document Container */}
            <div className="bg-[#080808] border border-white/10 p-8 md:p-12 relative overflow-hidden shadow-2xl">
                
                {/* Decor */}
                <div className="absolute top-0 right-0 p-4 opacity-20">
                    {doc === 'support' ? <HelpCircle size={64} /> : doc === 'faq' ? <HelpCircle size={64} /> : <FileText size={64} />}
                </div>
                
                {renderContent()}

                {/* Footer Signature */}
                <div className="mt-12 pt-8 border-t border-white/5 flex justify-between items-center text-[10px] font-mono text-gray-600">
                    <span>DOC_HASH: {Math.random().toString(36).substr(2, 12).toUpperCase()}</span>
                    <span>LAST_UPDATED: 2024.12.01</span>
                </div>
            </div>

        </div>
    </motion.div>
  );
};

export default Legal;
