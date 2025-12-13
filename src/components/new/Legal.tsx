
import React from 'react';
import { ArrowLeft, FileText, Shield, HelpCircle, Mail, Terminal, ChevronRight } from 'lucide-react';
import { motion } from 'framer-motion';
import { useLocale } from '../../hooks/useLocale';

interface LegalProps {
  doc: string;
  onBack: () => void;
}

// Legal documents content with Russian and English versions
const legalContent = {
  terms: {
    ru: {
      title: 'Пользовательское соглашение',
      content: (
        <div className="space-y-6 text-gray-400 font-mono text-xs md:text-sm leading-relaxed">
          <p>1. ОБЩИЕ ПОЛОЖЕНИЯ</p>
          <p>1.1. Настоящее Пользовательское соглашение (далее — Соглашение) регулирует отношения между сервисом PVNDORA (далее — Исполнитель) и пользователем сети Интернет (далее — Пользователь), возникающие при предоставлении доступа к премиум подпискам на платформы искусственного интеллекта и цифровые сервисы.</p>
          <p>1.2. Используя сервис, Пользователь подтверждает, что он ознакомился с условиями настоящего Соглашения и принимает их в полном объеме без каких-либо исключений.</p>
          
          <p>2. ПРЕДМЕТ СОГЛАШЕНИЯ</p>
          <p>2.1. Исполнитель предоставляет Пользователю доступ к премиум подпискам на платформы искусственного интеллекта и цифровые сервисы посредством передачи лицензионных ключей, инвайт-ссылок или учетных данных для доступа к готовым аккаунтам.</p>
          <p>2.2. Сервис является реселлером (перепродавцом) подписок на сторонние SaaS-платформы (включая, но не ограничиваясь: OpenAI ChatGPT, Anthropic Claude, Midjourney, GitHub Copilot и другие). Все услуги предоставляются на условиях оригинальных провайдеров.</p>
          <p>2.3. Пользователь обязуется соблюдать условия использования оригинальных сервисов и платформ, к которым предоставляется доступ. Исполнитель не является аффилированным лицом оригинальных провайдеров.</p>

          <p>3. ПРАВА И ОБЯЗАННОСТИ СТОРОН</p>
          <p>3.1. Пользователь обязуется использовать полученные данные доступа только в законных целях и не передавать их третьим лицам без разрешения Исполнителя.</p>
          <p>3.2. Исполнитель обязуется обеспечить предоставление доступа в течение 24 часов с момента подтверждения транзакции, если иное не указано в описании товара.</p>
          <p>3.3. Пользователь несет полную ответственность за использование полученных данных доступа в соответствии с условиями оригинальных провайдеров.</p>

          <p>4. ОТВЕТСТВЕННОСТЬ</p>
          <p>4.1. Исполнитель не несет ответственности за изменения в алгоритмах работы, функционале или условиях использования сервисов, производимых их оригинальными разработчиками.</p>
          <p>4.2. Исполнитель не несет ответственности за ограничение доступа к сервисам со стороны оригинальных провайдеров, включая блокировки аккаунтов по их усмотрению.</p>
          <p>4.3. Все споры разрешаются путем переговоров, при недостижении согласия — в соответствии с действующим законодательством.</p>
        </div>
      )
    },
    en: {
      title: 'Terms of Service',
      content: (
        <div className="space-y-6 text-gray-400 font-mono text-xs md:text-sm leading-relaxed">
          <p>1. GENERAL PROVISIONS</p>
          <p>1.1. This User Agreement (hereinafter — Agreement) governs the relationship between PVNDORA service (hereinafter — Provider) and Internet user (hereinafter — User) arising from the provision of access to premium subscriptions to artificial intelligence platforms and digital services.</p>
          <p>1.2. By using the service, the User confirms that they have read the terms of this Agreement and accept them in full without any exceptions.</p>
          
          <p>2. SUBJECT OF THE AGREEMENT</p>
          <p>2.1. The Provider grants the User access to premium subscriptions to artificial intelligence platforms and digital services by providing license keys, invite links, or credentials for access to ready-made accounts.</p>
          <p>2.2. The service is a reseller of subscriptions to third-party SaaS platforms (including, but not limited to: OpenAI ChatGPT, Anthropic Claude, Midjourney, GitHub Copilot, and others). All services are provided under the terms of the original providers.</p>
          <p>2.3. The User undertakes to comply with the terms of use of the original services and platforms to which access is provided. The Provider is not affiliated with the original providers.</p>

          <p>3. RIGHTS AND OBLIGATIONS OF THE PARTIES</p>
          <p>3.1. The User undertakes to use the received access data only for lawful purposes and not to transfer them to third parties without the Provider's permission.</p>
          <p>3.2. The Provider undertakes to provide access within 24 hours of transaction confirmation, unless otherwise specified in the product description.</p>
          <p>3.3. The User is fully responsible for the use of the received access data in accordance with the terms of the original providers.</p>

          <p>4. LIABILITY</p>
          <p>4.1. The Provider is not responsible for changes in algorithms, functionality, or terms of use of services made by their original developers.</p>
          <p>4.2. The Provider is not responsible for restrictions on access to services by original providers, including account blocking at their discretion.</p>
          <p>4.3. All disputes are resolved through negotiations, and if no agreement is reached — in accordance with applicable law.</p>
        </div>
      )
    }
  },
  privacy: {
    ru: {
      title: 'Политика конфиденциальности',
      content: (
        <div className="space-y-6 text-gray-400 font-mono text-xs md:text-sm leading-relaxed">
          <p>1. СБОР ДАННЫХ</p>
          <p>1.1. Мы собираем минимально необходимый набор данных для исполнения обязательств перед Пользователем:</p>
          <p>— Telegram ID и username (для идентификации и связи)</p>
          <p>— История заказов и покупок (для обработки заказов и доставки товаров)</p>
          <p>— Контактная информация (если предоставлена пользователем)</p>
          <p>— Технические данные (IP-адрес, тип устройства, cookies для обеспечения безопасности)</p>
          <p>1.2. Мы НЕ собираем данные банковских карт, пароли или другую конфиденциальную финансовую информацию. Все платежные данные обрабатываются сторонними платежными системами (CrystalPay и другие).</p>
          
          <p>2. ИСПОЛЬЗОВАНИЕ ДАННЫХ</p>
          <p>2.1. Данные используются исключительно для:</p>
          <p>— Обработки заказов и доставки товаров</p>
          <p>— Связи с Пользователем по вопросам заказов</p>
          <p>— Улучшения качества сервиса</p>
          <p>— Предоставления технической поддержки</p>
          <p>— Анализа использования сервиса (в анонимном виде)</p>
          <p>2.2. Мы не передаем личные данные третьим лицам, за исключением случаев, предусмотренных законодательством.</p>

          <p>3. БЕЗОПАСНОСТЬ</p>
          <p>3.1. Все данные передаются по защищенному протоколу SSL/TLS. Платежные данные обрабатываются на стороне платежных шлюзов (CrystalPay, внутренний баланс) и не сохраняются на наших серверах.</p>
          <p>3.2. Доступ к персональным данным имеют только уполномоченные сотрудники, необходимые для выполнения обязательств перед Пользователем.</p>
          <p>3.3. Мы применяем меры для защиты данных от несанкционированного доступа, изменения, раскрытия или уничтожения.</p>

          <p>4. ПРАВА ПОЛЬЗОВАТЕЛЯ</p>
          <p>4.1. Пользователь имеет право запросить копию своих данных, их удаление или исправление неточных данных.</p>
          <p>4.2. Для реализации прав пользователя необходимо обратиться в службу поддержки: support@pvndora.app</p>
          <p>4.3. Пользователь имеет право отозвать согласие на обработку персональных данных, что может повлечь невозможность использования сервиса.</p>
          <p>4.4. Пользователь имеет право подать жалобу в надзорный орган в случае нарушения его прав.</p>
        </div>
      )
    },
    en: {
      title: 'Privacy Policy',
      content: (
        <div className="space-y-6 text-gray-400 font-mono text-xs md:text-sm leading-relaxed">
          <p>1. DATA COLLECTION</p>
          <p>1.1. We collect the minimum necessary data to fulfill our obligations to the User:</p>
          <p>— Telegram ID and username (for identification and communication)</p>
          <p>— Order and purchase history (for order processing and delivery)</p>
          <p>— Contact information (if provided by the user)</p>
          <p>— Technical data (IP address, device type, cookies for security)</p>
          <p>1.2. We do NOT collect bank card data, passwords, or other confidential financial information. All payment data is processed by third-party payment systems (CrystalPay and others).</p>
          
          <p>2. DATA USAGE</p>
          <p>2.1. Data is used exclusively for:</p>
          <p>— Order processing and delivery of goods</p>
          <p>— Contacting the User regarding orders</p>
          <p>— Improving service quality</p>
          <p>— Providing technical support</p>
          <p>— Analyzing service usage (anonymously)</p>
          <p>2.2. We do not transfer personal data to third parties, except as required by law.</p>

          <p>3. SECURITY</p>
          <p>3.1. All data is transmitted via secure SSL/TLS protocol. Payment data is processed by payment gateways (CrystalPay, internal balance) and is not stored on our servers.</p>
          <p>3.2. Only authorized employees necessary to fulfill obligations to the User have access to personal data.</p>
          <p>3.3. We apply measures to protect data from unauthorized access, modification, disclosure, or destruction.</p>

          <p>4. USER RIGHTS</p>
          <p>4.1. The User has the right to request a copy of their data, its deletion, or correction of inaccurate data.</p>
          <p>4.2. To exercise user rights, please contact support: support@pvndora.app</p>
          <p>4.3. The User has the right to withdraw consent to personal data processing, which may result in the inability to use the service.</p>
          <p>4.4. The User has the right to file a complaint with a supervisory authority if their rights are violated.</p>
        </div>
      )
    }
  },
  refund: {
    ru: {
      title: 'Политика возврата',
      content: (
        <div className="space-y-6 text-gray-400 font-mono text-xs md:text-sm leading-relaxed">
          <p>1. ЦИФРОВЫЕ УСЛУГИ</p>
          <p>1.1. В соответствии с законодательством, цифровые услуги по предоставлению доступа к подпискам на сторонние SaaS-платформы, к которым был предоставлен доступ, возврату и обмену не подлежат, так как они потребляются в момент предоставления.</p>
          <p>1.2. После передачи лицензионного ключа, инвайт-ссылки или учетных данных доступ считается оказанным.</p>
          
          <p>2. ГАРАНТИЙНЫЕ СЛУЧАИ</p>
          <p>2.1. Если предоставленный доступ оказался невалидным (технический сбой) на момент выдачи, Пользователь имеет право на замену или возврат средств в течение гарантийного срока.</p>
          <p>2.2. Если доступ не был предоставлен в течение 48 часов после оплаты (для товаров с автоматической доставкой), Пользователь имеет право на возврат средств.</p>
          <p>2.3. Претензии принимаются в течение гарантийного срока (указан в карточке услуги) через службу поддержки: support@pvndora.app</p>
          
          <p>3. ПРОЦЕДУРА ВОЗВРАТА</p>
          <p>3.1. Возврат средств осуществляется на тот же платежный инструмент, с которого была произведена оплата, в течение 3-7 рабочих дней после принятия решения о возврате.</p>
          <p>3.2. Для возврата средств необходимо обратиться в службу поддержки с указанием номера заказа и причины возврата.</p>
          <p>3.3. Возврат средств для криптовалютных платежей может занять до 7 рабочих дней.</p>
        </div>
      )
    },
    en: {
      title: 'Refund Policy',
      content: (
        <div className="space-y-6 text-gray-400 font-mono text-xs md:text-sm leading-relaxed">
          <p>1. DIGITAL SERVICES</p>
          <p>1.1. In accordance with the law, digital services for providing access to subscriptions to third-party SaaS platforms, to which access has been provided, are not subject to return or exchange, as they are consumed at the time of provision.</p>
          <p>1.2. After providing a license key, invite link, or credentials, access is considered to have been provided.</p>
          
          <p>2. WARRANTY CASES</p>
          <p>2.1. If the provided access was invalid (technical failure) at the time of delivery, the User has the right to replacement or refund within the warranty period.</p>
          <p>2.2. If access was not provided within 48 hours after payment (for products with automatic delivery), the User has the right to a refund.</p>
          <p>2.3. Claims are accepted within the warranty period (specified in the service card) through support: support@pvndora.app</p>
          
          <p>3. REFUND PROCEDURE</p>
          <p>3.1. Refunds are made to the same payment instrument from which payment was made, within 3-7 business days after the refund decision is made.</p>
          <p>3.2. To request a refund, please contact support with the order number and reason for refund.</p>
          <p>3.3. Refunds for cryptocurrency payments may take up to 7 business days.</p>
        </div>
      )
    }
  },
  payment: {
    ru: {
      title: 'Оплата и доставка',
      content: (
        <div className="space-y-6 text-gray-400 font-mono text-xs md:text-sm leading-relaxed">
          <p>1. ПРОЦЕСС ОПЛАТЫ</p>
          <p>Выбор товара → Переход к оплате → Выбор метода оплаты (внутренний баланс / внешний платежный шлюз) → Проведение платежа → Автоматический возврат в магазин.</p>
          
          <p>2. БЕЗОПАСНОСТЬ ПЛАТЕЖЕЙ</p>
          <p>Оплата происходит через защищенные платежные шлюзы. Мы принимаем оплату через внутренний баланс пользователя или через внешние платежные системы (CrystalPay и другие). Платежные данные обрабатываются на стороне платежных шлюзов и не сохраняются на наших серверах.</p>
          
          <p>3. ДОСТАВКА</p>
          <p>Доставка осуществляется в электронном виде. Данные для подключения (лицензионные ключи, инвайт-ссылки или учетные данные) отображаются в разделе "Orders" и дублируются на email, если указан.</p>
        </div>
      )
    },
    en: {
      title: 'Payment and Delivery',
      content: (
        <div className="space-y-6 text-gray-400 font-mono text-xs md:text-sm leading-relaxed">
          <p>1. PAYMENT PROCESS</p>
          <p>Product selection → Proceed to checkout → Choose payment method (internal balance / external payment gateway) → Complete payment → Automatic return to store.</p>
          
          <p>2. PAYMENT SECURITY</p>
          <p>Payments are processed through secure payment gateways. We accept payments via user internal balance or through external payment systems (CrystalPay and others). Payment data is processed by payment gateways and is not stored on our servers.</p>
          
          <p>3. DELIVERY</p>
          <p>Delivery is made electronically. Access credentials (license keys, invite links, or account credentials) are displayed in the "Orders" section and duplicated via email if provided.</p>
        </div>
      )
    }
  }
};

const Legal: React.FC<LegalProps> = ({ doc, onBack }) => {
  const { locale } = useLocale();
  
  const renderContent = () => {
    // Get content based on document type and locale (default to English if not Russian)
    const isRussian = locale === 'ru';
    const docLocale = isRussian ? 'ru' : 'en';
    
    switch (doc) {
      case 'terms':
        const termsContent = legalContent.terms[docLocale as 'ru' | 'en'];
        return (
          <div>
            <h2 className="text-white font-display text-xl mb-4">{termsContent.title}</h2>
            {termsContent.content}
          </div>
        );
      case 'privacy':
        const privacyContent = legalContent.privacy[docLocale as 'ru' | 'en'];
        return (
          <div>
            <h2 className="text-white font-display text-xl mb-4">{privacyContent.title}</h2>
            {privacyContent.content}
          </div>
        );
      case 'refund':
        const refundContent = legalContent.refund[docLocale as 'ru' | 'en'];
        return (
          <div>
            <h2 className="text-white font-display text-xl mb-4">{refundContent.title}</h2>
            {refundContent.content}
          </div>
        );
      case 'payment':
        const paymentContent = legalContent.payment[docLocale as 'ru' | 'en'];
        return (
          <div>
            <h2 className="text-white font-display text-xl mb-4">{paymentContent.title}</h2>
            {paymentContent.content}
          </div>
        );
      case 'faq':
        return (
          <div className="space-y-8">
             <h2 className="text-white font-display text-xl mb-6">FAQ {isRussian ? '(Частые вопросы)' : '(Frequently Asked Questions)'}</h2>
             
             <div className="border border-white/10 p-4 bg-white/5">
                <h3 className="text-white font-bold mb-2">{isRussian ? 'Как быстро я получу доступ?' : 'How quickly will I receive access?'}</h3>
                <p className="text-gray-400 font-mono text-xs">{isRussian ? 'В 99% случаев выдача происходит мгновенно после оплаты. Данные отобразятся в личном кабинете и придут на почту.' : 'In 99% of cases, delivery happens instantly after payment. Data will be displayed in your account and sent via email.'}</p>
             </div>
             
             <div className="border border-white/10 p-4 bg-white/5">
                <h3 className="text-white font-bold mb-2">{isRussian ? 'Нужен ли VPN?' : 'Do I need a VPN?'}</h3>
                <p className="text-gray-400 font-mono text-xs">{isRussian ? 'Зависит от ресурса. В карточке каждой услуги мы указываем требования к подключению.' : 'Depends on the service. We specify connection requirements in each service card.'}</p>
             </div>

             <div className="border border-white/10 p-4 bg-white/5">
                <h3 className="text-white font-bold mb-2">{isRussian ? 'Что делать, если доступ не работает?' : 'What if access does not work?'}</h3>
                <p className="text-gray-400 font-mono text-xs">{isRussian ? 'Напишите в нашу поддержку (support@pvndora.app). Мы проверим токен и, если он невалиден, выдадим замену.' : 'Contact our support (support@pvndora.app). We will check the token and, if invalid, provide a replacement.'}</p>
             </div>

             <div className="border border-white/10 p-4 bg-white/5">
                <h3 className="text-white font-bold mb-2">{isRussian ? 'Какие способы оплаты доступны?' : 'What payment methods are available?'}</h3>
                <p className="text-gray-400 font-mono text-xs">{isRussian ? 'Мы принимаем оплату через внутренний баланс или внешние платежные системы (CrystalPay) с поддержкой банковских карт, криптовалют (USDT, BTC) и других методов.' : 'We accept payments via internal balance or external payment systems (CrystalPay) supporting bank cards, cryptocurrencies (USDT, BTC), and other methods.'}</p>
             </div>
          </div>
        );
      case 'support':
        return (
          <div className="space-y-8">
             <h2 className="text-white font-display text-xl mb-6">{isRussian ? 'Техническая поддержка' : 'Technical Support'}</h2>
             
             <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="border border-white/10 p-6 bg-[#0a0a0a] flex flex-col items-center text-center">
                    <div className="w-12 h-12 bg-pandora-cyan text-black rounded-full flex items-center justify-center mb-4">
                        <Terminal size={24} />
                    </div>
                    <h3 className="text-white font-bold mb-2">Telegram Support</h3>
                    <p className="text-gray-500 text-xs font-mono mb-4">{isRussian ? 'Самый быстрый способ получить ответ.' : 'The fastest way to get an answer.'}</p>
                    <a href="https://t.me/pvndora_support" target="_blank" rel="noopener noreferrer" className="text-pandora-cyan font-bold hover:underline">@pvndora_support</a>
                </div>

                <div className="border border-white/10 p-6 bg-[#0a0a0a] flex flex-col items-center text-center">
                    <div className="w-12 h-12 bg-white/10 text-white rounded-full flex items-center justify-center mb-4">
                        <Mail size={24} />
                    </div>
                    <h3 className="text-white font-bold mb-2">Email</h3>
                    <p className="text-gray-500 text-xs font-mono mb-4">{isRussian ? 'Для деловых предложений и жалоб.' : 'For business inquiries and complaints.'}</p>
                    <a href="mailto:support@pvndora.app" className="text-white font-bold hover:underline">support@pvndora.app</a>
                </div>
             </div>

             <div className="bg-white/5 p-4 border-l-2 border-pandora-cyan">
                <p className="text-gray-300 text-sm">{isRussian ? 'Время работы поддержки: ' : 'Support hours: '}<span className="text-white font-bold">{isRussian ? '10:00 - 22:00 (МСК)' : '10:00 - 22:00 (MSC)'}</span>{isRussian ? ', без выходных.' : ', daily.'}</p>
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
                  <span>LAST_UPDATED: 2024.12.13</span>
              </div>
          </div>

      </div>
    </motion.div>
  );
};

export default Legal;
