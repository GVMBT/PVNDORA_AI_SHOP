import React from 'react'
import cardIcon from '../../assets/icons/payments/visa-10.svg'
import sbpIcon from '../../assets/icons/payments/sbp.svg'
import cryptoIcon from '../../assets/icons/payments/tether-usdt-1.svg'

export const IconCard = () => (
  <div className="relative w-6 h-4 rounded-[6px] bg-gradient-to-r from-slate-800 to-slate-700">
    <div className="absolute left-1 top-[6px] w-3 h-[6px] rounded bg-yellow-400/90" />
    <div className="absolute right-1 bottom-[5px] w-[14px] h-[2px] bg-white/70" />
  </div>
)

export const IconSBP = () => (
  <div className="w-6 h-6 rounded-md bg-white flex items-center justify-center overflow-hidden border border-slate-200">
    <svg viewBox="0 0 64 64" className="w-5 h-5">
      <path fill="#7b61ff" d="M6 6h22l-8 14H6z" />
      <path fill="#00c3ff" d="M36 6h22L34 50l-8-14z" />
      <path fill="#ff8c37" d="M6 44h22l-8 14H6z" />
      <path fill="#13ce66" d="M36 44h22l-14 14-14-14z" />
    </svg>
  </div>
)

export const IconSBPQR = () => (
  <div className="w-6 h-6 rounded-md bg-white flex items-center justify-center overflow-hidden border border-slate-200">
    <svg viewBox="0 0 24 24" className="w-4 h-4 text-slate-700" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M5 3h4v4H5zM15 3h4v4h-4zM5 17h4v4H5zM15 17h4v4h-4z" />
      <path d="M9 5h6M9 19h6M5 9v6M19 9v6M9 9h6v6H9z" />
    </svg>
  </div>
)

export const IconCrypto = () => (
  <div className="w-6 h-6 rounded-full bg-[#26a17b]/10 text-[#26a17b] flex items-center justify-center border border-[#26a17b]/40">
    <span className="text-[11px] font-bold">USDT</span>
  </div>
)

export const METHOD_ICONS = {
  card: () => <img src={cardIcon} alt="Card" className="h-5" />,
  sbp: () => <img src={sbpIcon} alt="SBP" className="h-5" />,
  sbp_qr: () => <img src={sbpIcon} alt="SBP QR" className="h-5" />,
  crypto: () => <img src={cryptoIcon} alt="Crypto" className="h-5" />,
}

// Минимальные суммы по методам - fallback если API не вернул
export const MIN_BY_METHOD_FALLBACK = {
  card: 1000,
  sbp: 1000,
  sbp_qr: 10,
  crypto: 50,
}

