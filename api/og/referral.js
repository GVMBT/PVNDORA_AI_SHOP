// OG Image generation using Satori + resvg-js (Node.js compatible)
import satori from 'satori';
import { Resvg } from '@resvg/resvg-js';

const translations = {
  ru: {
    locale: 'ru-RU',
    badge: 'Экономлю вместе с PVNDORA',
    savedPrefix: 'Я сэкономил',
    savedSuffix: 'на тарифах нейросетей',
    rankLabel: 'Место в рейтинге',
    cta: 'Подключай тарифы нейросетей за 20% от их стоимости',
    handlePrefix: 'через',
  },
  en: {
    locale: 'en-US',
    badge: 'Saving with PVNDORA',
    savedPrefix: 'I saved',
    savedSuffix: 'on AI subscriptions',
    rankLabel: 'Leaderboard position',
    cta: 'Get AI subscriptions for 20% of their cost',
    handlePrefix: 'via',
  },
};

function pickLocale(lang) {
  const normalized = lang?.toLowerCase?.() || '';
  if (normalized.startsWith('ru')) return 'ru';
  return 'en';
}

// Helper to get font from Google Fonts CSS API
async function getGoogleFont() {
  const cssUrl = 'https://fonts.googleapis.com/css2?family=Inter:wght@600';
  const cssResponse = await fetch(cssUrl, {
    headers: {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
  });
  const css = await cssResponse.text();
  
  // Extract woff2 URL from CSS
  const match = css.match(/src:\s*url\(([^)]+\.woff2)\)/);
  if (!match) {
    throw new Error('Could not extract font URL from Google Fonts CSS');
  }
  
  const fontResponse = await fetch(match[1]);
  return await fontResponse.arrayBuffer();
}

export default async function handler(req, res) {
  const url = new URL(req.url, `http://${req.headers.host}`);
  const searchParams = url.searchParams;
  
  // Debug endpoint
  if (searchParams.get('debug') === '1') {
    return res.json({ status: 'ok', runtime: 'nodejs', lib: 'satori+resvg' });
  }

  try {
    // Load font
    const fontData = await getGoogleFont();

    const lang = pickLocale(searchParams.get('lang') || 'ru');
    const copy = translations[lang];

    const name =
      searchParams.get('name')?.slice(0, 40) || (lang === 'ru' ? 'Пользователь' : 'PVNDORA User');
    const saved = Number(searchParams.get('saved') || '0');
    const rank = searchParams.get('rank') || '';
    const avatar =
      searchParams.get('avatar') ||
      `https://api.dicebear.com/7.x/initials/png?seed=${encodeURIComponent(name)}`;
    const handle = searchParams.get('handle') || '@pvndora_ai_bot';

    const formatter = new Intl.NumberFormat(copy.locale, {
      maximumFractionDigits: 0,
    });
    const formattedSaved = formatter.format(Number.isFinite(saved) ? saved : 0);

    // Satori element (JSX-like object notation)
    const element = {
      type: 'div',
      props: {
        style: {
          width: '100%',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          background: 'linear-gradient(135deg, #0f172a 0%, #4c1d95 100%)',
          fontFamily: 'Inter',
          color: 'white',
          padding: '60px',
          position: 'relative',
        },
        children: [
          // Top badge
          {
            type: 'div',
            props: {
              style: {
                fontSize: '28px',
                textTransform: 'uppercase',
                letterSpacing: '0.1em',
                opacity: 0.8,
                marginBottom: '30px',
              },
              children: copy.badge,
            },
          },
          // Main content
          {
            type: 'div',
            props: {
              style: {
                display: 'flex',
                alignItems: 'center',
                gap: '50px',
              },
              children: [
                // Avatar
                {
                  type: 'img',
                  props: {
                    src: avatar,
                    width: 180,
                    height: 180,
                    style: {
                      borderRadius: '50%',
                      border: '4px solid rgba(255,255,255,0.3)',
                    },
                  },
                },
                // Stats
                {
                  type: 'div',
                  props: {
                    style: {
                      display: 'flex',
                      flexDirection: 'column',
                    },
                    children: [
                      {
                        type: 'div',
                        props: {
                          style: {
                            fontSize: '64px',
                            fontWeight: 700,
                            marginBottom: '10px',
                          },
                          children: `${copy.savedPrefix} ${formattedSaved}₽`,
                        },
                      },
                      {
                        type: 'div',
                        props: {
                          style: {
                            fontSize: '36px',
                            opacity: 0.9,
                            marginBottom: '20px',
                          },
                          children: copy.savedSuffix,
                        },
                      },
                      rank ? {
                        type: 'div',
                        props: {
                          style: {
                            display: 'flex',
                            alignItems: 'center',
                            gap: '14px',
                            color: '#facc15',
                          },
                          children: [
                            {
                              type: 'span',
                              props: {
                                style: { fontSize: '26px' },
                                children: copy.rankLabel,
                              },
                            },
                            {
                              type: 'span',
                              props: {
                                style: { fontSize: '48px', fontWeight: 700 },
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
          // Footer
          {
            type: 'div',
            props: {
              style: {
                position: 'absolute',
                bottom: '40px',
                left: '60px',
                right: '60px',
                display: 'flex',
                justifyContent: 'space-between',
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
                    children: 'PVNDORA • AI Marketplace',
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
      fonts: [
        {
          name: 'Inter',
          data: fontData,
          weight: 600,
          style: 'normal',
        },
      ],
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

    res.setHeader('Content-Type', 'image/png');
    res.setHeader('Cache-Control', 'public, immutable, no-transform, max-age=31536000');
    res.send(Buffer.from(pngBuffer));
  } catch (error) {
    console.error('OG Image generation error:', error);
    res.status(500).json({
      error: error.message,
      stack: error.stack,
    });
  }
}
