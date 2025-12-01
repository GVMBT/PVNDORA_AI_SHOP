// OG Image generation using Satori + resvg-js (Node.js compatible)
// Uses jsDelivr CDN for fonts (works in Russia without VPN)
import satori from 'satori';
import { Resvg } from '@resvg/resvg-js';

const translations = {
  ru: {
    locale: 'ru-RU',
    badge: 'ЭКОНОМЛЮ ВМЕСТЕ С PVNDORA',
    savedPrefix: 'Я сэкономил',
    savedSuffix: 'на тарифах нейросетей',
    rankLabel: 'Место в рейтинге',
    cta: 'Оплачиваю тарифы нейросетей за 20% от их стоимости',
    handlePrefix: 'через',
  },
  en: {
    locale: 'en-US',
    badge: 'SAVING WITH PVNDORA',
    savedPrefix: 'I saved',
    savedSuffix: 'on AI subscriptions',
    rankLabel: 'Leaderboard rank',
    cta: 'Get AI subscriptions for 20% of their cost',
    handlePrefix: 'via',
  },
};

function pickLocale(lang) {
  const normalized = lang?.toLowerCase?.() || '';
  if (normalized.startsWith('ru')) return 'ru';
  return 'en';
}

// Font sources - prioritize CDNs that work in Russia
// Latin and Cyrillic subsets for proper Russian support
const FONT_SOURCES_LATIN = [
  'https://cdn.jsdelivr.net/npm/@fontsource/inter@5.0.8/files/inter-latin-600-normal.woff',
  'https://unpkg.com/@fontsource/inter@5.0.8/files/inter-latin-600-normal.woff',
];

const FONT_SOURCES_CYRILLIC = [
  'https://cdn.jsdelivr.net/npm/@fontsource/inter@5.0.8/files/inter-cyrillic-600-normal.woff',
  'https://unpkg.com/@fontsource/inter@5.0.8/files/inter-cyrillic-600-normal.woff',
];

// Fallback: Full Inter font with all glyphs from GitHub
const FONT_SOURCES_FULL = [
  'https://raw.githubusercontent.com/rsms/inter/v4.0/docs/font-files/Inter-SemiBold.woff',
  'https://cdn.jsdelivr.net/gh/nicolo/inter-font@master/Inter%20(TTF%20hinted)/Inter-SemiBold.ttf',
];

async function loadFontFromSources(sources) {
  for (const url of sources) {
    try {
      const response = await fetch(url, {
        headers: { 'User-Agent': 'Mozilla/5.0' },
      });
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      
      const data = await response.arrayBuffer();
      if (data.byteLength > 1000) {
        console.log(`Font loaded successfully from: ${url}`);
        return data;
      }
    } catch (error) {
      console.warn(`Failed to load font from ${url}:`, error.message);
    }
  }
  return null;
}

// Cache fonts at module level
let fontCacheLatin = null;
let fontCacheCyrillic = null;
let fontCacheFull = null;

async function getFonts() {
  // Try to load subset fonts first (smaller, faster)
  if (!fontCacheLatin) {
    fontCacheLatin = await loadFontFromSources(FONT_SOURCES_LATIN);
  }
  if (!fontCacheCyrillic) {
    fontCacheCyrillic = await loadFontFromSources(FONT_SOURCES_CYRILLIC);
  }
  
  // If both subsets loaded, use them
  if (fontCacheLatin && fontCacheCyrillic) {
    return [
      { name: 'Inter', data: fontCacheLatin, weight: 600, style: 'normal' },
      { name: 'Inter', data: fontCacheCyrillic, weight: 600, style: 'normal' },
    ];
  }
  
  // Fallback to full font
  if (!fontCacheFull) {
    fontCacheFull = await loadFontFromSources(FONT_SOURCES_FULL);
  }
  
  if (fontCacheFull) {
    return [{ name: 'Inter', data: fontCacheFull, weight: 600, style: 'normal' }];
  }
  
  throw new Error('Failed to load any font sources');
}

export default async function handler(req, res) {
  const url = new URL(req.url, `http://${req.headers.host}`);
  const searchParams = url.searchParams;
  
  // Debug endpoint
  if (searchParams.get('debug') === '1') {
    return res.json({ 
      status: 'ok', 
      runtime: 'nodejs', 
      lib: 'satori+resvg',
      fontSources: {
        latin: FONT_SOURCES_LATIN,
        cyrillic: FONT_SOURCES_CYRILLIC,
        full: FONT_SOURCES_FULL,
      },
    });
  }

  try {
    // Load fonts with Latin + Cyrillic support
    const fonts = await getFonts();

    const lang = pickLocale(searchParams.get('lang') || 'ru');
    const copy = translations[lang];

    const name = searchParams.get('name')?.slice(0, 40) || 
      (lang === 'ru' ? 'Пользователь' : 'User');
    const saved = Number(searchParams.get('saved') || '0');
    const rank = searchParams.get('rank') || '';
    
    // Use DiceBear for avatar (works globally)
    const avatar = searchParams.get('avatar') ||
      `https://api.dicebear.com/7.x/initials/png?seed=${encodeURIComponent(name)}&backgroundColor=6366f1`;
    
    const handle = searchParams.get('handle') || '@pvndora_ai_bot';

    const formatter = new Intl.NumberFormat(copy.locale, {
      maximumFractionDigits: 0,
    });
    const formattedSaved = formatter.format(Number.isFinite(saved) ? saved : 0);
    const currencySymbol = lang === 'ru' ? '₽' : '$';

    // Build Satori element structure
    const element = {
      type: 'div',
      props: {
        style: {
          width: '100%',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          alignItems: 'center',
          background: 'linear-gradient(145deg, #0c0a1d 0%, #1e1145 50%, #3b1d72 100%)',
          fontFamily: 'Inter',
          color: 'white',
          padding: '50px 60px',
        },
        children: [
          // Top badge
          {
            type: 'div',
            props: {
              style: {
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                backgroundColor: 'rgba(139, 92, 246, 0.3)',
                borderRadius: '30px',
                padding: '12px 30px',
                fontSize: '22px',
                letterSpacing: '0.15em',
                marginTop: '10px',
              },
              children: copy.badge,
            },
          },
          
          // Main content area
          {
            type: 'div',
            props: {
              style: {
                display: 'flex',
                alignItems: 'center',
                gap: '50px',
                marginTop: '20px',
              },
              children: [
                // Avatar with glow effect
                {
                  type: 'div',
                  props: {
                    style: {
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      borderRadius: '50%',
                      padding: '6px',
                      background: 'linear-gradient(135deg, #a855f7 0%, #6366f1 100%)',
                    },
                    children: {
                      type: 'img',
                      props: {
                        src: avatar,
                        width: 160,
                        height: 160,
                        style: {
                          borderRadius: '50%',
                          border: '4px solid #1e1145',
                        },
                      },
                    },
                  },
                },
                
                // Stats block
                {
                  type: 'div',
                  props: {
                    style: {
                      display: 'flex',
                      flexDirection: 'column',
                    },
                    children: [
                      // Saved amount - big number
                      {
                        type: 'div',
                        props: {
                          style: {
                            fontSize: '72px',
                            fontWeight: 600,
                            lineHeight: 1.1,
                            background: 'linear-gradient(90deg, #fff 0%, #c4b5fd 100%)',
                            backgroundClip: 'text',
                            color: 'transparent',
                          },
                          children: `${formattedSaved}${currencySymbol}`,
                        },
                      },
                      // Saved text
                      {
                        type: 'div',
                        props: {
                          style: {
                            fontSize: '28px',
                            opacity: 0.85,
                            marginTop: '8px',
                          },
                          children: `${copy.savedPrefix} ${copy.savedSuffix}`,
                        },
                      },
                      // Rank if available
                      rank ? {
                        type: 'div',
                        props: {
                          style: {
                            display: 'flex',
                            alignItems: 'center',
                            gap: '12px',
                            marginTop: '20px',
                            color: '#fbbf24',
                          },
                          children: [
                            {
                              type: 'span',
                              props: {
                                style: { fontSize: '24px' },
                                children: `🏆 ${copy.rankLabel}:`,
                              },
                            },
                            {
                              type: 'span',
                              props: {
                                style: { 
                                  fontSize: '42px', 
                                  fontWeight: 600,
                                },
                                children: `#${rank}`,
                              },
                            },
                          ],
                        },
                      } : null,
                    ].filter(Boolean),
                  },
                },
              ],
            },
          },
          
          // Bottom CTA and branding
          {
            type: 'div',
            props: {
              style: {
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '16px',
                marginBottom: '10px',
              },
              children: [
                // CTA text
                {
                  type: 'div',
                  props: {
                    style: {
                      fontSize: '26px',
                      color: '#c4b5fd',
                      textAlign: 'center',
                    },
                    children: copy.cta,
                  },
                },
                // Bot handle
                {
                  type: 'div',
                  props: {
                    style: {
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                      fontSize: '22px',
                      opacity: 0.7,
                    },
                    children: [
                      {
                        type: 'span',
                        props: {
                          children: `${copy.handlePrefix} ${handle}`,
                        },
                      },
                      {
                        type: 'span',
                        props: {
                          style: { margin: '0 12px' },
                          children: '•',
                        },
                      },
                      {
                        type: 'span',
                        props: {
                          children: 'PVNDORA',
                        },
                      },
                    ],
                  },
                },
              ],
            },
          },
        ],
      },
    };

    // Generate SVG using Satori
    const svg = await satori(element, {
      width: 1200,
      height: 630,
      fonts: fonts,
    });

    // Convert SVG to PNG using resvg-js
    const resvg = new Resvg(svg, {
      fitTo: {
        mode: 'width',
        value: 1200,
      },
    });
    const pngData = resvg.render();
    const pngBuffer = pngData.asPng();

    // Set headers for caching
    res.setHeader('Content-Type', 'image/png');
    res.setHeader('Cache-Control', 'public, max-age=86400, s-maxage=604800');
    res.setHeader('CDN-Cache-Control', 'public, max-age=604800');
    res.send(Buffer.from(pngBuffer));
    
  } catch (error) {
    console.error('OG Image generation error:', error);
    res.status(500).json({
      error: 'Failed to generate image',
      message: error.message,
      hint: 'Check font loading and dependencies',
    });
  }
}
