import type React from "react";

const PandoraBox: React.FC = () => {
  return (
    <div className="w-full h-full absolute inset-0 pointer-events-none overflow-visible flex items-center justify-center">
      <style>{`
        .levitation {
            animation: float 6s ease-in-out infinite;
        }
        .core-pulse {
            animation: core-pulse 3s ease-in-out infinite; /* Faster pulse for unstable feel */
        }
        .holo-flicker {
            animation: flicker 4s infinite;
        }
        .spin-slow {
            animation: spin 30s linear infinite;
            transform-origin: center;
            transform-box: fill-box;
        }
        .spin-fast {
            animation: spin 15s linear infinite reverse;
            transform-origin: center;
            transform-box: fill-box;
        }
        .particle {
            animation: rise 2.5s infinite linear;
        }
        .p1 { animation-delay: 0.5s; }
        .p2 { animation-delay: 1.2s; }
        .p3 { animation-delay: 2.5s; }
        .p4 { animation-delay: 0.8s; }
        .p5 { animation-delay: 1.5s; }
        .p6 { animation-delay: 0.2s; }

        /* --- Outer Panel Animations (The Shell) --- */
        .panel-top { animation: panel-top-move 6s ease-in-out infinite; }
        .panel-right { animation: panel-right-move 6s ease-in-out infinite; }
        .panel-left { animation: panel-left-move 6s ease-in-out infinite; }

        /* --- Inner Panel Animations (The Core Shield - Smaller Amplitude) --- */
        .inner-top { animation: inner-top-move 6s ease-in-out infinite; }
        .inner-right { animation: inner-right-move 6s ease-in-out infinite; }
        .inner-left { animation: inner-left-move 6s ease-in-out infinite; }

        /* Outer Movements */
        @keyframes panel-top-move {
            0%, 100% { transform: translate(0, -4px); }
            50% { transform: translate(0, -16px); } /* Opened wider */
        }
        @keyframes panel-right-move {
            0%, 100% { transform: translate(2px, 2px); }
            50% { transform: translate(14px, 8px); } /* Opened wider */
        }
        @keyframes panel-left-move {
            0%, 100% { transform: translate(-2px, 2px); }
            50% { transform: translate(-14px, 8px); } /* Opened wider */
        }

        /* Inner Movements */
        @keyframes inner-top-move {
            0%, 100% { transform: translate(0, -1px); }
            50% { transform: translate(0, -5px); } 
        }
        @keyframes inner-right-move {
            0%, 100% { transform: translate(1px, 1px); }
            50% { transform: translate(5px, 3px); } 
        }
        @keyframes inner-left-move {
            0%, 100% { transform: translate(-1px, 1px); }
            50% { transform: translate(-5px, 3px); } 
        }

        @keyframes float {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-20px); }
        }
        @keyframes core-pulse {
            0%, 100% { opacity: 0.6; transform: scale(0.9); filter: blur(0px); }
            50% { opacity: 1; transform: scale(1.15); filter: blur(2px); }
        }
        @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
        @keyframes rise {
            0% { transform: translateY(0) scale(1); opacity: 0; }
            20% { opacity: 1; }
            100% { transform: translateY(-160px) scale(0); opacity: 0; }
        }
        @keyframes flicker {
            0%, 100% { opacity: 0.3; }
            5% { opacity: 0.1; }
            10% { opacity: 0.3; }
            15% { opacity: 0.05; }
            20% { opacity: 0.3; }
            50% { opacity: 0.2; }
            80% { opacity: 0.4; }
        }
      `}</style>

      <svg
        viewBox="0 0 800 600"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="w-full h-full scale-150 md:scale-125 lg:scale-135 object-cover transform transition-transform duration-1000 origin-center overflow-visible"
        preserveAspectRatio="xMidYMid slice"
      >
        <defs>
          <filter id="glow-intense" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="4" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>

          <filter id="blur-soft" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="3" />
          </filter>

          {/* === 1. PREMIUM TECH TEXTURE (Matte Mesh) === */}
          <pattern id="tech-mesh" x="0" y="0" width="8" height="8" patternUnits="userSpaceOnUse">
            <rect width="8" height="8" fill="#050505" />
            <rect x="3" y="3" width="1" height="1" fill="#151515" />
          </pattern>

          <linearGradient id="volume-fade" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#222" stopOpacity="0.2" />
            <stop offset="100%" stopColor="#000" stopOpacity="0.8" />
          </linearGradient>

          <linearGradient id="neon-stream" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#00FFFF" stopOpacity="0" />
            <stop offset="50%" stopColor="#00FFFF" stopOpacity="0.8" />
            <stop offset="100%" stopColor="#00FFFF" stopOpacity="0" />
          </linearGradient>

          <radialGradient id="core-light">
            <stop offset="0%" stopColor="#FFFFFF" />
            <stop offset="20%" stopColor="#00FFFF" />
            <stop offset="60%" stopColor="#008888" stopOpacity="0.5" />
            <stop offset="100%" stopColor="#000000" stopOpacity="0" />
          </radialGradient>

          {/* MASK FOR FLOOR FADING */}
          <linearGradient id="floor-fade-grad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0.5" stopColor="white" stopOpacity="1" />
            <stop offset="1" stopColor="white" stopOpacity="0" />
          </linearGradient>
          <mask id="floor-mask">
            <rect x="-400" y="-400" width="800" height="800" fill="url(#floor-fade-grad)" />
          </mask>
        </defs>

        {/* === 1. ENVIRONMENT / FLOOR (Shifted Upwards) === */}
        {/* Adjusted Translate Y from 480 to 420 to prevent bottom clipping */}
        <g transform="translate(400, 420) scale(1, 0.35)" opacity="0.6" mask="url(#floor-mask)">
          <circle
            cx="0"
            cy="0"
            r="150"
            stroke="#00FFFF"
            strokeWidth="1"
            strokeOpacity="0.1"
            strokeDasharray="5 5"
          />
          <circle cx="0" cy="0" r="280" stroke="#00FFFF" strokeWidth="0.5" strokeOpacity="0.05" />
          {/* Radial Lines */}
          <path d="M-300 0 L300 0" stroke="#00FFFF" strokeOpacity="0.05" />
          <path d="M0 -300 L0 300" stroke="#00FFFF" strokeOpacity="0.05" />
        </g>

        {/* === 2. BACKGROUND HUD ELEMENTS === */}
        <g transform="translate(400, 300)">
          <g className="spin-slow" opacity="0.15">
            <path d="M-180 0 A180 180 0 0 1 180 0" stroke="#00FFFF" strokeWidth="1" fill="none" />
            <path
              d="M-170 0 A170 170 0 0 0 170 0"
              stroke="#00FFFF"
              strokeWidth="1"
              strokeDasharray="10 20"
              fill="none"
            />
          </g>
        </g>

        {/* === 3. THE ARTIFACT (Main Group) === */}
        <g className="levitation">
          {/* TRANSLATE TO CENTER OF CUBE */}
          <g transform="translate(300, 200)">
            {/* --- INNER CORE (More Intense) --- */}
            <g className="core-pulse">
              <circle
                cx="100"
                cy="110"
                r="45"
                fill="url(#core-light)"
                filter="url(#glow-intense)"
              />
              {/* Beams shooting up */}
              <path
                d="M100 20 L100 200"
                stroke="#00FFFF"
                strokeWidth="4"
                opacity="0.8"
                filter="url(#glow-intense)"
              />
              <path
                d="M80 50 L120 170"
                stroke="#00FFFF"
                strokeWidth="1"
                opacity="0.4"
                filter="url(#glow-intense)"
              />
            </g>

            {/* --- INNER SHELL --- */}
            <g className="inner-right">
              <path d="M100 110 L170 75 V 150 L100 180 Z" fill="#000000" stroke="#111" />
            </g>
            <g className="inner-left">
              <path d="M100 110 L30 75 V 150 L100 180 Z" fill="#000000" stroke="#111" />
            </g>
            <g className="inner-top">
              <path d="M100 110 L170 75 L100 40 L30 75 Z" fill="#000000" stroke="#111" />
            </g>

            {/* --- OUTER PANELS --- */}

            {/* 1. TOP LID */}
            <g className="panel-top">
              <path d="M100 20 L180 60 L100 100 L20 60 Z" fill="url(#tech-mesh)" />
              <path d="M100 20 L180 60 L100 100 L20 60 Z" fill="url(#volume-fade)" opacity="0.5" />
              <path
                d="M100 20 L180 60 L100 100 L20 60 Z"
                fill="none"
                stroke="#00FFFF"
                strokeWidth="0.8"
                strokeOpacity="0.4"
              />
              <path d="M100 35 L165 65" stroke="#00FFFF" strokeWidth="0.5" strokeOpacity="0.2" />
              <path d="M100 35 L35 65" stroke="#00FFFF" strokeWidth="0.5" strokeOpacity="0.2" />
              <circle cx="100" cy="60" r="3" fill="#000" stroke="#00FFFF" strokeWidth="1" />
            </g>

            {/* 2. RIGHT PANEL */}
            <g className="panel-right">
              <path d="M100 100 L180 60 V 150 L100 190 Z" fill="url(#tech-mesh)" />
              <path d="M100 100 L180 60 V 150 L100 190 Z" fill="url(#volume-fade)" opacity="0.5" />
              <path
                d="M100 100 L180 60 V 150 L100 190 Z"
                fill="none"
                stroke="#00FFFF"
                strokeWidth="0.8"
                strokeOpacity="0.4"
              />
              <path
                d="M165 80 V 130"
                stroke="#00FFFF"
                strokeWidth="1.5"
                opacity="0.6"
                filter="url(#glow-intense)"
              />
              <rect x="110" y="115" width="2" height="2" fill="#333" />
              <rect x="110" y="125" width="2" height="2" fill="#333" />
            </g>

            {/* 3. LEFT PANEL */}
            <g className="panel-left">
              <path d="M100 100 L20 60 V 150 L100 190 Z" fill="url(#tech-mesh)" />
              <path d="M100 100 L20 60 V 150 L100 190 Z" fill="url(#volume-fade)" opacity="0.5" />
              <path
                d="M100 100 L20 60 V 150 L100 190 Z"
                fill="none"
                stroke="#00FFFF"
                strokeWidth="0.8"
                strokeOpacity="0.4"
              />
              <path
                d="M35 80 V 130"
                stroke="#00FFFF"
                strokeWidth="1.5"
                opacity="0.6"
                filter="url(#glow-intense)"
              />
              <rect x="88" y="115" width="2" height="2" fill="#333" />
              <rect x="88" y="125" width="2" height="2" fill="#333" />
            </g>

            {/* --- HOLOGRAPHIC OVERLAY (Containment Grid) --- */}
            <g className="holo-flicker" transform="translate(0, 0)">
              <path
                d="M100 15 L185 58 L185 155 L100 195 L15 155 L15 58 Z"
                fill="none"
                stroke="#ff0000"
                strokeWidth="0.5"
                strokeOpacity="0.1"
                strokeDasharray="4 2"
              />
            </g>
          </g>

          {/* === 4. DATA PARTICLES RISING FROM CRACKS (MORE INTENSE) === */}
          <g transform="translate(300, 200)">
            <rect x="98" y="80" width="1" height="1" fill="#00FFFF" className="particle p1" />
            <rect x="105" y="90" width="1" height="3" fill="#00FFFF" className="particle p2" />
            <rect x="90" y="85" width="1" height="1" fill="#fff" className="particle p3" />
            <path
              d="M100 80 L100 60"
              stroke="url(#neon-stream)"
              strokeWidth="0.5"
              className="particle p4"
            />

            {/* Additional Particles for 'Breach' effect */}
            <rect x="80" y="100" width="2" height="1" fill="#00FFFF" className="particle p5" />
            <rect x="120" y="70" width="1" height="2" fill="#fff" className="particle p6" />
          </g>
        </g>
      </svg>
    </div>
  );
};

export default PandoraBox;
