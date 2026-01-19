import { useCallback, useState } from "react";

interface SimpleLocale {
  [key: string]: string;
}

const locales: SimpleLocale = {
  en: {
    "modal.errors.insufficientFunds": "Insufficient funds",
  },
  ru: {
    "modal.errors.insufficientFunds": "Недостаточно средств",
  },
};

export const useLocale = () => {
  const [locale, setLocale] = useState<string>("en");

  const t = useCallback(
    (key: string): string => {
      return locales[locale]?.[key] || key;
    },
    [locale]
  );

  return { t, locale, setLocale };
};
