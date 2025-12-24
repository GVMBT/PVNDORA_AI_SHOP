# Product Media System - Оптимизированные медиа для карточек и страниц товаров

## Обновление: Three.js Particle Visualizer

Добавлен компонент `ProductParticleVisualizer` для страницы товара (ProductDetail).
Это эффект в стиле IGLOO — частицы формируют форму логотипа продукта.

### Как это работает

1. **Загрузка SVG логотипа** → конвертация в 3D mesh через ExtrudeGeometry
2. **Surface Sampling** → генерация точек на поверхности логотипа
3. **Shader Animation** → частицы "текут" вверх как дым/энергия
4. **Mouse Parallax** → реакция на движение мыши

### Использование

```tsx
// В ProductDetail.tsx (уже интегрировано)
<ProductParticleVisualizer
  logoUrl="/logos/veo3.svg"  // SVG логотип продукта
  fallbackShape="torus"       // Fallback если SVG не загрузился
  color="#00FFFF"             // Цвет частиц
  backgroundColor="#0a0a0a"   // Фон
/>
```

### Добавление логотипа продукту

1. Создайте SVG логотип и загрузите в `/public/logos/` или CDN
2. Добавьте поле `logo_svg_url` в базу данных (таблица `products`)
3. API вернёт его, и ProductDetail автоматически покажет Three.js визуализацию

### Требования к SVG

- Простые формы (path, rect, circle)
- Без градиентов и эффектов
- Предпочтительно: одноцветные контуры
- Размер: ~100x100 viewBox

### Производительность

- Desktop: ~25,000 частиц
- Mobile: ~8,000 частиц (автоопределение)
- Lazy loading: Three.js загружается только при открытии ProductDetail

---

# Product Card Media - Оптимизированные медиа для карточек товаров

## Обзор

Компонент `ProductCardMedia` предоставляет оптимизированное решение для отображения медиа-контента в карточках товаров с поддержкой:
- Статических изображений (fallback)
- Видео-фонов (WebM/MP4)
- Canvas-частиц (легковесная альтернатива three.js)
- Интеграции с параллакс-эффектом

## Производительность

### Оптимизации

1. **Lazy Loading**
   - Видео и частицы загружаются только когда карточка видна в viewport
   - Используется Intersection Observer API

2. **Адаптивная производительность**
   - На мобильных устройствах: 15 частиц вместо 30
   - Ограничение DPR (device pixel ratio) до 2x
   - Автоматическое отключение частиц при низкой производительности

3. **Canvas оптимизации**
   - `desynchronized: true` для лучшей производительности
   - RequestAnimationFrame для плавной анимации
   - Fade-эффект вместо полной очистки canvas

4. **Видео оптимизации**
   - Автоматический fallback на изображение при ошибке загрузки
   - Preload="metadata" для экономии трафика
   - Muted и loop для автоматического воспроизведения

## Использование

### Базовое использование (только изображение)

```tsx
<ProductCardMedia
  image="/path/to/image.jpg"
  alt="Product name"
/>
```

### С видео-фоном

```tsx
<ProductCardMedia
  image="/path/to/image.jpg"  // Fallback изображение
  video="/path/to/video.webm" // Видео-фон
  alt="Product name"
/>
```

### С частицами (для популярных товаров)

```tsx
<ProductCardMedia
  image="/path/to/image.jpg"
  useParticles={true}  // Включает canvas-частицы
  alt="Product name"
/>
```

### С параллакс-эффектом

```tsx
import { useMotionValue } from 'framer-motion';

const cardX = useMotionValue(0);
const cardY = useMotionValue(0);

<ProductCardMedia
  image="/path/to/image.jpg"
  useParticles={true}
  parallaxX={cardX}  // Интеграция с framer-motion
  parallaxY={cardY}
  alt="Product name"
/>
```

## Рекомендации по видео

### Формат и кодирование

**Рекомендуемый формат: WebM (VP9)**

```bash
# Пример конвертации с FFmpeg (оптимизировано для веба)
ffmpeg -i input.mp4 \
  -c:v libvpx-vp9 \
  -b:v 500k \
  -maxrate 750k \
  -bufsize 1000k \
  -vf "scale=640:-1" \
  -an \
  -loop 0 \
  output.webm
```

**Параметры:**
- `-b:v 500k` - битрейт 500 kbps (можно снизить до 300k для экономии)
- `-maxrate 750k` - максимальный битрейт
- `-vf "scale=640:-1"` - разрешение 640px по ширине (подстраивается под карточку)
- `-an` - без аудио (экономия трафика)
- `-loop 0` - бесконечный цикл

### Альтернатива: MP4 (H.264)

```bash
ffmpeg -i input.mp4 \
  -c:v libx264 \
  -preset slow \
  -crf 28 \
  -vf "scale=640:-1" \
  -an \
  -movflags +faststart \
  output.mp4
```

**Параметры:**
- `-crf 28` - качество (18-28, выше = меньше размер)
- `-preset slow` - лучшее сжатие (медленнее кодирование)
- `-movflags +faststart` - оптимизация для веб-потока

### Размер файла

**Целевые размеры:**
- Для карточек товаров: **200-500 KB** на 3-5 секунд видео
- Разрешение: **640x360** или **640x480** (достаточно для карточек)
- Длительность: **3-10 секунд** (короткие loop-видео)

### Пример структуры файлов

```
/public/products/
  ├── product-1/
  │   ├── image.jpg (50-100 KB)
  │   ├── video.webm (300 KB)
  │   └── video.mp4 (400 KB, fallback)
  └── product-2/
      ├── image.jpg
      └── video.webm
```

## Рекомендации по частицам

### Когда использовать

- ✅ **Рекомендуется:** Для популярных/топовых товаров (`product.popular === true`)
- ✅ **Рекомендуется:** Для товаров с высоким приоритетом
- ❌ **Не рекомендуется:** Для всех товаров одновременно (нагрузка)

### Настройка количества частиц

По умолчанию:
- Desktop: 30 частиц
- Mobile: 15 частиц

Можно настроить в `ProductCardMedia.tsx`:

```typescript
const particleCount = window.innerWidth < 768 ? 15 : 30;
```

### Производительность частиц

- **CPU нагрузка:** ~2-5% на карточку (только при hover)
- **GPU нагрузка:** Минимальная (Canvas 2D)
- **Память:** ~1-2 MB на активную карточку

## Интеграция с API

### Добавление поля `video` в ProductData

```typescript
interface ProductData {
  // ... existing fields
  image: string;
  video?: string;  // Добавить опциональное поле
}
```

### Пример ответа API

```json
{
  "id": "123",
  "name": "Product Name",
  "image": "https://cdn.example.com/products/123/image.jpg",
  "video": "https://cdn.example.com/products/123/video.webm",
  "popular": true
}
```

## Сравнение вариантов

| Вариант | Размер | Производительность | Эффект |
|---------|--------|-------------------|--------|
| **Только изображение** | 50-100 KB | ⭐⭐⭐⭐⭐ | Базовый |
| **Видео (WebM)** | 200-500 KB | ⭐⭐⭐⭐ | Высокий |
| **Частицы (Canvas)** | +1-2 MB RAM | ⭐⭐⭐ | Средний |
| **Видео + Частицы** | 200-500 KB + RAM | ⭐⭐⭐ | Максимальный |
| **Three.js** | +500 KB bundle | ⭐⭐ | Высокий, но тяжелый |

## Рекомендации

### Для большинства товаров
```tsx
<ProductCardMedia
  image={product.image}
  alt={product.name}
/>
```

### Для популярных товаров
```tsx
<ProductCardMedia
  image={product.image}
  video={product.video}  // Опционально
  useParticles={product.popular}
  alt={product.name}
/>
```

### Для премиум-товаров
```tsx
<ProductCardMedia
  image={product.image}
  video={product.video}
  useParticles={true}
  parallaxX={cardX}
  parallaxY={cardY}
  alt={product.name}
/>
```

## Troubleshooting

### Видео не загружается
- Проверьте формат (WebM предпочтительнее)
- Убедитесь, что файл доступен по URL
- Проверьте CORS настройки CDN
- Компонент автоматически fallback на изображение

### Частицы тормозят
- Уменьшите количество частиц в `ProductCardMedia.tsx`
- Отключите частицы на мобильных устройствах
- Используйте только для популярных товаров

### Высокая нагрузка при множестве карточек
- Используйте lazy loading (уже встроен)
- Ограничьте использование частиц
- Используйте видео только для топ-товаров

## Примеры использования в Catalog.tsx

Компонент уже интегрирован в `ProductCard.tsx`:

```tsx
<ProductCardMedia
  image={product.image}
  video={product.video}
  useParticles={product.popular}
  parallaxX={cardX}
  parallaxY={cardY}
  alt={product.name}
/>
```

Частицы автоматически включаются для популярных товаров, параллакс работает на desktop.
