-- Add FAQ content for PVNDORA project
-- Categories: general, payment, delivery, warranty

INSERT INTO faq (question, answer, category, language_code, priority, is_active) VALUES
-- General questions
('Что такое PVNDORA?', 
'PVNDORA — это сервис для доступа к премиум AI подпискам и цифровым активам. Мы предоставляем лицензионные ключи, инвайты и готовые аккаунты для ChatGPT Plus, Claude Pro, Midjourney и других AI сервисов.', 
'general', 'ru', 10, true),

('Как работает сервис?', 
'Вы выбираете нужную подписку в каталоге, оплачиваете заказ, и получаете данные для доступа в течение нескольких минут. Все товары доставляются автоматически в электронном виде.', 
'general', 'ru', 9, true),

('Безопасно ли покупать у вас?', 
'Да, все платежи обрабатываются через защищённые платёжные шлюзы. Мы не храним данные ваших карт. Все товары проверяются перед продажей и имеют гарантию валидности.', 
'general', 'ru', 8, true),

('Какие способы оплаты доступны?', 
'Мы принимаем банковские карты (Visa, Mastercard, МИР), СБП (Система быстрых платежей), криптовалюты (Bitcoin, USDT, Ethereum) и QR-коды (НСПК).', 
'payment', 'ru', 10, true),

('Сколько времени занимает доставка?', 
'Большинство товаров доставляются автоматически в течение 1-5 минут после оплаты. В редких случаях доставка может занять до 24 часов. Вы получите уведомление в Telegram с данными для доступа.', 
'delivery', 'ru', 10, true),

('Что делать, если товар не работает?', 
'Если товар не работает в течение гарантийного срока, создайте тикет поддержки через бота или напишите @gvmbt158. Мы заменим товар или вернём средства в течение 24-72 часов.', 
'warranty', 'ru', 10, true),

('Какова гарантия на товары?', 
'Гарантия зависит от типа товара: триалы — 1 день, годовые подписки — 14 дней. В течение гарантийного срока мы гарантируем работоспособность товара и готовы заменить его или вернуть средства.', 
'warranty', 'ru', 9, true),

('Можно ли вернуть деньги?', 
'Возврат средств возможен в следующих случаях: товар не был доставлен в течение 48 часов, товар не соответствует описанию, технические проблемы, которые мы не смогли решить в течение 72 часов. Свяжитесь с поддержкой @gvmbt158 для оформления возврата.', 
'payment', 'ru', 8, true),

('Как работает реферальная программа?', 
'Приглашайте друзей по реферальной ссылке и получайте 20% с их покупок (1 уровень). Также вы получаете бонусы с покупок рефералов ваших рефералов (2-3 уровень). Все бонусы начисляются на ваш баланс и могут быть выведены.', 
'general', 'ru', 7, true),

('Как вывести средства?', 
'Средства можно вывести на банковскую карту, СБП или криптовалюту. Минимальная сумма вывода — 500₽. Заявка обрабатывается в течение 24 часов. Перейдите в раздел "Профиль" для оформления вывода.', 
'payment', 'ru', 6, true),

('Что делать, если товар закончился?', 
'Если товара нет в наличии, вы можете встать в очередь ожидания. Мы уведомим вас, когда товар снова появится. Также доступны предзаказы для некоторых товаров.', 
'delivery', 'ru', 7, true),

('Как связаться с поддержкой?', 
'Вы можете написать нашему AI-ассистенту прямо в Telegram боте или связаться с технической поддержкой @gvmbt158. Поддержка работает круглосуточно, 24/7.', 
'general', 'ru', 5, true);

-- Add English translations
INSERT INTO faq (question, answer, category, language_code, priority, is_active) VALUES
('What is PVNDORA?', 
'PVNDORA is a service for accessing premium AI subscriptions and digital assets. We provide licensed keys, invites, and ready accounts for ChatGPT Plus, Claude Pro, Midjourney, and other AI services.', 
'general', 'en', 10, true),

('How does the service work?', 
'You choose the subscription you need in the catalog, pay for the order, and receive access credentials within a few minutes. All products are delivered automatically in digital format.', 
'general', 'en', 9, true),

('Is it safe to buy from you?', 
'Yes, all payments are processed through secure payment gateways (1Plat, Freekassa). We do not store your card data. All products are verified before sale and have a validity guarantee.', 
'general', 'en', 8, true),

('What payment methods are available?', 
'We accept bank cards (Visa, Mastercard, MIR), SBP (Fast Payment System), cryptocurrencies (Bitcoin, USDT, Ethereum), and QR codes (NSPK).', 
'payment', 'en', 10, true),

('How long does delivery take?', 
'Most products are delivered automatically within 1-5 minutes after payment. In rare cases, delivery may take up to 24 hours. You will receive a notification in Telegram with access credentials.', 
'delivery', 'en', 10, true),

('What if the product doesn''t work?', 
'If the product doesn''t work within the warranty period, create a support ticket through the bot or contact @gvmbt158. We will replace the product or refund within 24-72 hours.', 
'warranty', 'en', 10, true);
