# Telegram Apps SDK 3.11.8 — Полезные функции для PVNDORA

## 📦 Установлено
- `@telegram-apps/sdk@3.11.8` (последняя версия на 08.01.2026)

---

## 🎯 Приоритетные функции для магазина подписок

### 1. **Theme Params** — Адаптация под тему Telegram
**Зачем:** Автоматическая адаптация цветов под тему пользователя (светлая/тёмная)

```typescript
import {
  themeParamsBackgroundColor,
  themeParamsTextColor,
  themeParamsButtonColor,
  themeParamsAccentTextColor,
  themeParamsLinkColor,
} from '@telegram-apps/sdk';

// Получить цвета темы
const bgColor = themeParamsBackgroundColor(); // RGB | undefined
const textColor = themeParamsTextColor();
const buttonColor = themeParamsButtonColor();
const accentColor = themeParamsAccentTextColor();
const linkColor = themeParamsLinkColor();
```

**Применение:**
- Динамическая цветовая схема для карточек продуктов
- Кнопки оплаты в цветах Telegram
- Адаптация модальных окон под тему

---

### 2. **Haptic Feedback** — Тактильная обратная связь
**Зачем:** Улучшение UX при покупках, добавлении в корзину, успешных операциях

```typescript
import {
  hapticFeedbackImpactOccurred,
  hapticFeedbackNotificationOccurred,
  hapticFeedbackSelectionChanged,
} from '@telegram-apps/sdk';

// Лёгкая вибрация при выборе
hapticFeedbackSelectionChanged();

// Средняя вибрация при действии
hapticFeedbackImpactOccurred('medium');

// Успешная операция
hapticFeedbackNotificationOccurred('success');

// Ошибка
hapticFeedbackNotificationOccurred('error');
```

**Применение:**
- ✅ Добавление товара в корзину → `selectionChanged`
- ✅ Успешная оплата → `notificationOccurred('success')`
- ✅ Ошибка оплаты → `notificationOccurred('error')`
- ✅ Прокрутка каталога → `selectionChanged`

---

### 3. **Back Button** — Навигация назад
**Зачем:** Управление кнопкой "Назад" в Telegram Mini App

```typescript
import { backButton } from '@telegram-apps/sdk';

// Инициализация
backButton.mount();

// Показать/скрыть
backButton.show();
backButton.hide();

// Обработчик клика
const off = backButton.onClick(() => {
  // Навигация назад или закрытие модального окна
  window.history.back();
  off(); // Отписаться после первого клика
});
```

**Применение:**
- Показывать кнопку "Назад" в модальных окнах (чек-аут, детали продукта)
- Скрывать на главной странице
- Обработка навигации в многошаговых формах

---

### 4. **Main Button** — Главная кнопка внизу экрана
**Зачем:** Кнопка "Оплатить" или "Добавить в корзину" внизу экрана

```typescript
import {
  onMainButtonClick,
  offMainButtonClick,
  setMainButtonText,
  setMainButtonParams,
  showMainButton,
  hideMainButton,
} from '@telegram-apps/sdk';

// Настроить кнопку
setMainButtonText('Оплатить $29.99');
setMainButtonParams({
  color: '#0088cc',
  text_color: '#ffffff',
});

// Показать
showMainButton();

// Обработчик
const off = onMainButtonClick(() => {
  // Обработка оплаты
  processPayment();
  off();
});
```

**Применение:**
- Кнопка "Оплатить" в корзине
- Кнопка "Добавить в корзину" на странице продукта
- Кнопка "Подтвердить заказ" в чек-ауте

---

### 5. **Viewport Safe Area** — Безопасные зоны экрана
**Зачем:** Корректное отображение на устройствах с вырезами (notch)

```typescript
import {
  viewportSafeAreaInsets,
  viewportSafeAreaInsetTop,
  viewportSafeAreaInsetBottom,
} from '@telegram-apps/sdk';

// Получить отступы
const insets = viewportSafeAreaInsets();
// { top: 44, bottom: 34, left: 0, right: 0 }

const topInset = viewportSafeAreaInsetTop(); // 44
const bottomInset = viewportSafeAreaInsetBottom(); // 34
```

**Применение:**
- Отступы для навигации
- Отступы для нижней панели с кнопкой оплаты
- Адаптация под iPhone с вырезом

---

### 6. **Init Data** — Данные пользователя
**Зачем:** Получение информации о пользователе без дополнительных запросов

```typescript
import {
  initDataUser,
  initDataRaw,
} from '@telegram-apps/sdk';

// Получить данные пользователя
const user = initDataUser();
// {
//   id: 78262681,
//   firstName: 'Pavel',
//   lastName: 'Durov',
//   username: 'durove',
//   languageCode: 'ru',
//   isPremium: true,
//   photoUrl: 'https://...',
//   allowsWriteToPm: true,
// }

// Сырые данные для отправки на сервер
const rawData = initDataRaw(); // 'user=...&chat=...&...'
```

**Применение:**
- Автоматическое определение языка пользователя
- Проверка Premium статуса (скидки для Premium)
- Отображение аватара пользователя
- Отправка на сервер для верификации

---

### 7. **Cloud Storage** — Облачное хранилище
**Зачем:** Сохранение настроек пользователя в облаке Telegram (синхронизация между устройствами)

```typescript
import {
  setCloudStorageItem,
  getCloudStorageItem,
  deleteCloudStorageItem,
} from '@telegram-apps/sdk';

// Сохранить настройки
await setCloudStorageItem('preferred_currency', 'USD');
await setCloudStorageItem('cart_items', JSON.stringify([...]));

// Получить настройки
const currency = await getCloudStorageItem('preferred_currency');
const cart = await getCloudStorageItem('cart_items');

// Удалить
await deleteCloudStorageItem('old_key');
```

**Применение:**
- Сохранение предпочтительной валюты
- Сохранение избранных товаров
- Настройки уведомлений
- История просмотров

---

### 8. **Popup** — Всплывающие окна
**Зачем:** Нативные всплывающие окна для подтверждений и уведомлений

```typescript
import {
  openPopup,
  closePopup,
  isPopupOpened,
} from '@telegram-apps/sdk';

if (openPopup.isAvailable()) {
  await openPopup({
    title: 'Подтверждение',
    message: 'Вы уверены, что хотите удалить товар из корзины?',
    buttons: [
      { id: 'delete', type: 'destructive', text: 'Удалить' },
      { id: 'cancel', type: 'default', text: 'Отмена' },
    ],
  });
}
```

**Применение:**
- Подтверждение удаления из корзины
- Подтверждение отмены заказа
- Уведомления об успешной оплате
- Предупреждения о недостатке средств

---

### 9. **QR Scanner** — Сканер QR-кодов
**Зачем:** Сканирование промокодов, реферальных кодов, ссылок на товары

```typescript
import {
  openQrScanner,
  closeQrScanner,
  isQrScannerOpened,
} from '@telegram-apps/sdk';

if (openQrScanner.isAvailable()) {
  const qr = await openQrScanner({
    text: 'Отсканируйте промокод',
    onCaptured(qr) {
      // Обработка QR-кода
      if (qr.startsWith('PROMO_')) {
        applyPromoCode(qr);
        closeQrScanner();
      }
    },
  });
}
```

**Применение:**
- Сканирование промокодов
- Сканирование реферальных ссылок
- Быстрое добавление товара по QR-коду

---

### 10. **Invoice** — Нативные счета Telegram
**Зачем:** Интеграция с платежной системой Telegram (если планируется)

```typescript
import {
  openInvoice,
  isInvoiceOpened,
} from '@telegram-apps/sdk';

if (openInvoice.isAvailable()) {
  const status = await openInvoice('invoice_id_from_telegram');
  // status: 'paid' | 'cancelled' | 'pending' | 'failed'
}
```

**Применение:**
- Альтернативный способ оплаты через Telegram
- Интеграция с Telegram Stars (если доступно)

---

## 🔧 Утилиты

### **init()** — Инициализация SDK
```typescript
import { init } from '@telegram-apps/sdk';

// Вызвать один раз при загрузке приложения
init();
```

---

## 📊 Приоритет внедрения

### Высокий приоритет (сразу):
1. ✅ **Theme Params** — улучшение визуального опыта
2. ✅ **Haptic Feedback** — тактильная обратная связь
3. ✅ **Back Button** — навигация
4. ✅ **Main Button** — кнопка оплаты

### Средний приоритет (после основных):
5. **Viewport Safe Area** — адаптация под устройства
6. **Init Data** — оптимизация (уже частично используется)
7. **Cloud Storage** — синхронизация настроек

### Низкий приоритет (по необходимости):
8. **Popup** — нативные всплывающие окна
9. **QR Scanner** — сканирование промокодов
10. **Invoice** — если планируется интеграция с Telegram Payments

---

## 💡 Примеры интеграции

### Пример 1: Кнопка "Оплатить" в корзине
```typescript
import { 
  showMainButton, 
  setMainButtonText, 
  onMainButtonClick 
} from '@telegram-apps/sdk';
import { hapticFeedbackNotificationOccurred } from '@telegram-apps/sdk';

// В компоненте корзины
useEffect(() => {
  const total = calculateTotal();
  setMainButtonText(`Оплатить $${total.toFixed(2)}`);
  showMainButton();
  
  const off = onMainButtonClick(async () => {
    hapticFeedbackNotificationOccurred('success');
    await processCheckout();
    off();
  });
  
  return () => off();
}, [cartItems]);
```

### Пример 2: Адаптация цветов под тему
```typescript
import { themeParamsBackgroundColor, themeParamsTextColor } from '@telegram-apps/sdk';

const ProductCard = () => {
  const bgColor = themeParamsBackgroundColor() || '#ffffff';
  const textColor = themeParamsTextColor() || '#000000';
  
  return (
    <div style={{ backgroundColor: bgColor, color: textColor }}>
      {/* Контент */}
    </div>
  );
};
```

### Пример 3: Тактильная обратная связь при покупке
```typescript
import { hapticFeedbackNotificationOccurred } from '@telegram-apps/sdk';

const handleAddToCart = () => {
  hapticFeedbackSelectionChanged(); // Лёгкая вибрация
  addToCart(product);
};

const handlePurchase = async () => {
  try {
    await processPayment();
    hapticFeedbackNotificationOccurred('success'); // Успех
  } catch (error) {
    hapticFeedbackNotificationOccurred('error'); // Ошибка
  }
};
```

---

## 📚 Документация
- [Официальная документация](https://docs.telegram-mini-apps.com/packages/telegram-apps-sdk/3-x)
- [GitHub репозиторий](https://github.com/Telegram-Mini-Apps/telegram-apps)

---

## ⚠️ Важно
- Все функции проверяют доступность через `.isAvailable()` или `.isSupported()`
- Всегда используйте fallback для старых версий Telegram
- Инициализируйте SDK один раз при загрузке приложения через `init()`
