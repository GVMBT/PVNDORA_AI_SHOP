// OG Image generation using Satori + resvg-js (Node.js compatible)
// Uses jsDelivr CDN for fonts (works in Russia without VPN)

import { Resvg } from "@resvg/resvg-js";
import satori from "satori";

// Custom background image URL (hosted on the webapp)
const BACKGROUND_IMAGE_URL = "https://pvndora.app/assets/og-background.jpeg";

const translations = {
  ru: {
    locale: "ru-RU",
    badge: "ЭКОНОМЛЮ ВМЕСТЕ С PVNDORA",
    savedPrefix: "Я сэкономил",
    savedSuffix: "на тарифах нейросетей",
    rankLabel: "Место в рейтинге",
    cta: "Получите доступ к топовым нейросетям в 5 раз дешевле официальных тарифов",
    handlePrefix: "через",
  },
  en: {
    locale: "en-US",
    badge: "SAVING WITH PVNDORA",
    savedPrefix: "I saved",
    savedSuffix: "on AI subscriptions",
    rankLabel: "Leaderboard rank",
    cta: "Get access to top AI tools at 5x cheaper than official prices",
    handlePrefix: "via",
  },
};

function pickLocale(lang) {
  const normalized = lang?.toLowerCase?.() || "";
  if (normalized.startsWith("ru")) {
    return "ru";
  }
  return "en";
}

// Font sources - use FULL Inter font with ALL glyphs (Latin + Cyrillic + more)
// CDNFonts works in Russia (unlike Google Fonts)
const FONT_SOURCES = [
  // CDNFonts - Full Inter with Cyrillic (works in Russia)
  "https://fonts.cdnfonts.com/s/19795/Inter-SemiBold.woff",
  // jsDelivr fontsource fallback (full Cyrillic)
  "https://cdn.jsdelivr.net/fontsource/fonts/inter@latest/cyrillic-600-normal.woff",
  // Bunny CDN - Google Fonts alternative (works in Russia)
  "https://fonts.bunny.net/inter/files/inter-cyrillic-600-normal.woff",
];

// Module-level font cache
let fontCache = null;

async function loadFont() {
  if (fontCache) {
    return fontCache;
  }

  for (const url of FONT_SOURCES) {
    try {
      const response = await fetch(url, {
        headers: { "User-Agent": "Mozilla/5.0 (compatible; Vercel OG)" },
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.arrayBuffer();
      // Full font should be > 50KB, subsets are ~10-30KB, reject anything < 50KB
      if (data.byteLength > 50_000) {
        console.log(`Font loaded: ${url} (${data.byteLength} bytes)`);
        fontCache = data;
        return data;
      }
      console.warn(`Font file too small (${data.byteLength} bytes), likely incomplete: ${url}`);
    } catch (error) {
      console.warn(`Font load failed ${url}:`, error.message);
    }
  }

  throw new Error("Failed to load font from any source");
}

export default async function handler(req, res) {
  const url = new URL(req.url, `http://${req.headers.host}`);
  const searchParams = url.searchParams;

  // Debug endpoint
  if (searchParams.get("debug") === "1") {
    return res.json({
      status: "ok",
      runtime: "nodejs",
      lib: "satori+resvg",
      fontSources: FONT_SOURCES,
      fontCached: !!fontCache,
    });
  }

  try {
    // Load font with full Cyrillic support
    const fontData = await loadFont();
    const fonts = [{ name: "Inter", data: fontData, weight: 600, style: "normal" }];

    const lang = pickLocale(searchParams.get("lang") || "ru");
    const copy = translations[lang];

    const name =
      searchParams.get("name")?.slice(0, 40) || (lang === "ru" ? "Пользователь" : "User");
    const saved = Number(searchParams.get("saved") || "0");
    const rank = searchParams.get("rank") || "";

    // Use DiceBear for avatar (works globally)
    const avatar =
      searchParams.get("avatar") ||
      `https://api.dicebear.com/7.x/initials/png?seed=${encodeURIComponent(name)}&backgroundColor=6366f1`;

    const handle = searchParams.get("handle") || "@pvndora_ai_bot";

    const formatter = new Intl.NumberFormat(copy.locale, {
      maximumFractionDigits: 0,
    });
    const formattedSaved = formatter.format(Number.isFinite(saved) ? saved : 0);
    const currencySymbol = lang === "ru" ? "₽" : "$";

    // Build Satori element structure with custom background
    const element = {
      type: "div",
      props: {
        style: {
          width: "100%",
          height: "100%",
          display: "flex",
          position: "relative",
          fontFamily: "Inter",
          color: "white",
        },
        children: [
          // Background image
          {
            type: "img",
            props: {
              src: BACKGROUND_IMAGE_URL,
              style: {
                position: "absolute",
                top: 0,
                left: 0,
                width: "100%",
                height: "100%",
                objectFit: "cover",
              },
            },
          },

          // Content overlay
          {
            type: "div",
            props: {
              style: {
                position: "absolute",
                top: 0,
                left: 0,
                width: "100%",
                height: "100%",
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
                alignItems: "center",
                padding: "40px 60px",
              },
              children: [
                // Top badge
                {
                  type: "div",
                  props: {
                    style: {
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      backgroundColor: "rgba(30, 20, 45, 0.85)",
                      border: "1px solid rgba(139, 92, 246, 0.5)",
                      borderRadius: "30px",
                      padding: "12px 30px",
                      fontSize: "20px",
                      letterSpacing: "0.12em",
                    },
                    children: copy.badge,
                  },
                },

                // Main content area
                {
                  type: "div",
                  props: {
                    style: {
                      display: "flex",
                      alignItems: "center",
                      gap: "50px",
                    },
                    children: [
                      // Avatar with glow effect (positioned to overlap with purple circle)
                      {
                        type: "div",
                        props: {
                          style: {
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            borderRadius: "50%",
                            padding: "5px",
                            background: "linear-gradient(135deg, #a855f7 0%, #6366f1 100%)",
                            boxShadow: "0 0 40px rgba(168, 85, 247, 0.5)",
                          },
                          children: {
                            type: "img",
                            props: {
                              src: avatar,
                              width: 130,
                              height: 130,
                              style: {
                                borderRadius: "50%",
                                border: "3px solid #1e1145",
                              },
                            },
                          },
                        },
                      },

                      // Stats block
                      {
                        type: "div",
                        props: {
                          style: {
                            display: "flex",
                            flexDirection: "column",
                          },
                          children: [
                            // Saved amount - big number with gradient
                            {
                              type: "div",
                              props: {
                                style: {
                                  fontSize: "68px",
                                  fontWeight: 600,
                                  lineHeight: 1.1,
                                  color: "#ffffff",
                                  textShadow: "0 0 30px rgba(168, 85, 247, 0.5)",
                                },
                                children: `${formattedSaved}${currencySymbol}`,
                              },
                            },
                            // Saved text
                            {
                              type: "div",
                              props: {
                                style: {
                                  fontSize: "24px",
                                  color: "rgba(255, 255, 255, 0.85)",
                                  marginTop: "8px",
                                },
                                children: `${copy.savedPrefix} ${copy.savedSuffix}`,
                              },
                            },
                            // Rank if available
                            rank
                              ? {
                                  type: "div",
                                  props: {
                                    style: {
                                      display: "flex",
                                      alignItems: "center",
                                      gap: "10px",
                                      marginTop: "16px",
                                    },
                                    children: [
                                      {
                                        type: "span",
                                        props: {
                                          style: {
                                            fontSize: "22px",
                                            color: "#fbbf24",
                                          },
                                          children: `🏆 ${copy.rankLabel}:`,
                                        },
                                      },
                                      {
                                        type: "span",
                                        props: {
                                          style: {
                                            fontSize: "38px",
                                            fontWeight: 600,
                                            color: "#fbbf24",
                                          },
                                          children: `#${rank}`,
                                        },
                                      },
                                    ],
                                  },
                                }
                              : null,
                          ].filter(Boolean),
                        },
                      },
                    ],
                  },
                },

                // Bottom CTA and branding
                {
                  type: "div",
                  props: {
                    style: {
                      display: "flex",
                      flexDirection: "column",
                      alignItems: "center",
                      gap: "10px",
                    },
                    children: [
                      // CTA text
                      {
                        type: "div",
                        props: {
                          style: {
                            fontSize: "22px",
                            color: "rgba(255, 255, 255, 0.9)",
                            textAlign: "center",
                            maxWidth: "800px",
                          },
                          children: copy.cta,
                        },
                      },
                      // Bot handle
                      {
                        type: "div",
                        props: {
                          style: {
                            display: "flex",
                            alignItems: "center",
                            gap: "8px",
                            fontSize: "18px",
                            color: "rgba(255, 255, 255, 0.6)",
                          },
                          children: [
                            {
                              type: "span",
                              props: {
                                children: `${copy.handlePrefix} ${handle}`,
                              },
                            },
                            {
                              type: "span",
                              props: {
                                style: { margin: "0 8px" },
                                children: "•",
                              },
                            },
                            {
                              type: "span",
                              props: {
                                children: "PVNDORA",
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
          },
        ],
      },
    };

    // Generate SVG using Satori
    const svg = await satori(element, {
      width: 1200,
      height: 630,
      fonts,
    });

    // Convert SVG to PNG using resvg-js
    const resvg = new Resvg(svg, {
      fitTo: {
        mode: "width",
        value: 1200,
      },
    });
    const pngData = resvg.render();
    const pngBuffer = pngData.asPng();

    // Set headers for caching
    res.setHeader("Content-Type", "image/png");
    res.setHeader("Cache-Control", "public, max-age=86400, s-maxage=604800");
    res.setHeader("CDN-Cache-Control", "public, max-age=604800");
    res.send(Buffer.from(pngBuffer));
  } catch (error) {
    console.error("OG Image generation error:", error);
    res.status(500).json({
      error: "Failed to generate image",
      message: error.message,
      hint: "Check font loading and dependencies",
    });
  }
}
