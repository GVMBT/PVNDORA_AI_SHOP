import { motion } from "framer-motion";
import { useEffect, useState } from "react";

export const Scanline = () => (
  <div className="absolute inset-0 pointer-events-none z-0">
    {/* CRT Scanlines */}
    <div className="absolute inset-0 bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.15)_50%)] bg-[length:100%_3px] opacity-30" />
    {/* RGB Shift */}
    <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(255,0,0,0.03),rgba(0,255,0,0.01),rgba(0,0,255,0.03))] bg-[length:3px_100%] opacity-40" />
    {/* Animated scan beam */}
    <motion.div
      className="absolute left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-pandora-cyan/20 to-transparent"
      animate={{ top: ["0%", "100%"] }}
      transition={{ duration: 8, repeat: Infinity, ease: "linear" }}
    />
  </div>
);

export const HexGrid = () => (
  <div className="absolute inset-0 pointer-events-none">
    {/* Primary Grid */}
    <div
      className="absolute inset-0 opacity-[0.04]"
      style={{
        backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%2300FFFF' fill-opacity='1'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
      }}
    />
    {/* Perspective Grid Lines */}
    <div
      className="absolute inset-0 opacity-[0.02]"
      style={{
        backgroundImage: `
          linear-gradient(rgba(0,255,255,0.3) 1px, transparent 1px),
          linear-gradient(90deg, rgba(0,255,255,0.3) 1px, transparent 1px)
        `,
        backgroundSize: "80px 80px",
      }}
    />
  </div>
);

/** Animated corner data streams */
export const DataStream = ({ position }: { position: "left" | "right" }) => {
  const isLeft = position === "left";
  return (
    <div
      className={`absolute top-20 ${isLeft ? "left-4" : "right-4"} w-32 pointer-events-none hidden lg:block`}
    >
      <div className="space-y-1 font-mono text-[8px] text-pandora-cyan/40">
        {["RENDER", "BUFFER", "NEURAL", "CODEC", "FRAME", "SYNC"].map((label, i) => (
          <motion.div
            key={`data-${label}`}
            initial={{ opacity: 0 }}
            animate={{ opacity: [0.2, 0.6, 0.2] }}
            transition={{ duration: 2, repeat: Infinity, delay: i * 0.3 }}
            className={`flex ${isLeft ? "justify-start" : "justify-end"}`}
          >
            <span className="tracking-wider">
              {isLeft
                ? `0x${Math.random().toString(16).slice(2, 10).toUpperCase()}`
                : `SYS.${label}`}
            </span>
          </motion.div>
        ))}
      </div>
    </div>
  );
};

/** Glowing orb indicator */
export const StatusOrb = ({ status }: { status: "idle" | "processing" | "ready" }) => {
  const colors = {
    idle: "bg-gray-500 shadow-gray-500/30",
    processing: "bg-pandora-cyan animate-pulse shadow-pandora-cyan/50",
    ready: "bg-green-500 shadow-green-500/50",
  };
  return (
    <div className={`w-2 h-2 rounded-full ${colors[status]} shadow-[0_0_10px_currentColor]`} />
  );
};

export const HUDCorner = ({
  position,
  active,
}: {
  position: "tl" | "tr" | "bl" | "br";
  active?: boolean;
}) => {
  const styles = {
    tl: "top-0 left-0 border-t-2 border-l-2",
    tr: "top-0 right-0 border-t-2 border-r-2",
    bl: "bottom-0 left-0 border-b-2 border-l-2",
    br: "bottom-0 right-0 border-b-2 border-r-2",
  };
  return (
    <motion.div
      initial={{ opacity: 0.5 }}
      animate={{ opacity: active ? 1 : 0.5, scale: active ? 1.1 : 1 }}
      className={`absolute w-6 h-6 border-pandora-cyan/50 ${styles[position]} z-20 transition-all duration-300`}
    />
  );
};

export const DecryptText = ({
  text,
  speed = 30,
  className = "",
}: {
  text: string;
  speed?: number;
  className?: string;
}) => {
  const [display, setDisplay] = useState("");
  useEffect(() => {
    // Safety check: ensure text is a valid string
    if (!text || typeof text !== "string") {
      setDisplay("");
      return;
    }

    let i = 0;
    const interval = setInterval(() => {
      setDisplay(
        text
          .split("")
          .map((char, index) => {
            if (index < i) return char;
            return String.fromCodePoint(33 + Math.random() * 93);
          })
          .join("")
      );
      i += 1 / 3;
      if (i > text.length) clearInterval(interval);
    }, speed);
    return () => clearInterval(interval);
  }, [text, speed]);
  return <span className={className}>{display}</span>;
};
