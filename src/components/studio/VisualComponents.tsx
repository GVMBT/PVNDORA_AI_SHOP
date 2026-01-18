import { motion } from "framer-motion";
import { useEffect, useState } from "react";

export const Scanline = () => (
  <div className="absolute inset-0 pointer-events-none z-0 bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.1)_50%),linear-gradient(90deg,rgba(255,0,0,0.06),rgba(0,255,0,0.02),rgba(0,0,255,0.06))] bg-[length:100%_4px,3px_100%] opacity-20" />
);

export const HexGrid = () => (
  <div
    className="absolute inset-0 pointer-events-none opacity-[0.03]"
    style={{
      backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%2300FFFF' fill-opacity='1'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
    }}
  />
);

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
