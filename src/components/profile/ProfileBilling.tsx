/**
 * ProfileBilling Component
 * 
 * Displays billing logs and transaction history with localization and currency conversion.
 */

import React, { memo, useMemo } from 'react';
import { useLocale } from '../../hooks/useLocale';
import { formatPrice } from '../../utils/currency';
import type { BillingLogData } from './types';

interface ProfileBillingProps {
  logs: BillingLogData[];
  currency?: string;
  exchangeRate?: number;
}

const ProfileBilling: React.FC<ProfileBillingProps> = ({ 
  logs,
  currency = 'USD',
  exchangeRate = 1
}) => {
  const { t, language } = useLocale();

  // Format and localize logs
  const localizedLogs = useMemo(() => {
    return logs.map(log => {
      // Parse transaction type from source for localization
      const sourceKey = log.transactionType?.toLowerCase() || 'system';
      const localizedSource = t(`profile.billing.transaction.${sourceKey}`) || log.source;
      
      // Parse amount (remove sign, convert)
      const amountNum = parseFloat(log.amount.replace(/[+\-,]/g, '')) || 0;
      const isIncome = log.type === 'INCOME';
      
      // Convert amount using exchange rate
      const convertedAmount = amountNum * exchangeRate;
      const formattedAmount = `${isIncome ? '+' : '-'}${formatPrice(convertedAmount, currency)}`;
      
      return {
        ...log,
        localizedSource,
        formattedAmount,
      };
    });
  }, [logs, t, currency, exchangeRate]);

  // Localized type labels
  const typeLabels: Record<string, string> = {
    INCOME: language === 'ru' ? 'ДОХОД' : 'INCOME',
    OUTCOME: language === 'ru' ? 'РАСХОД' : 'OUTCOME',
    SYSTEM: language === 'ru' ? 'СИСТЕМА' : 'SYSTEM',
  };

  return (
    <div className="border border-white/10 bg-[#050505] shadow-[0_0_50px_rgba(0,0,0,0.5)]">
      <div className="bg-[#0a0a0a] border-b border-white/10 p-2 px-4">
        <div className="text-[10px] font-mono font-bold uppercase text-pandora-cyan">
          {t('profile.billing.title')}
        </div>
      </div>

      <div className="p-0 font-mono text-xs">
        <div className="divide-y divide-white/5">
          {localizedLogs.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-gray-600">
              <span className="uppercase tracking-widest text-[10px]">
                {t('profile.billing.noTransactions')}
              </span>
            </div>
          ) : (
            localizedLogs.map((log, i) => (
              <div key={i} className="px-4 py-3 hover:bg-white/5 transition-colors">
                {/* Row 1: ID, Type, Amount */}
                <div className="flex items-center justify-between gap-2 mb-1">
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="text-gray-500 text-[10px] font-mono shrink-0">{log.id}</span>
                    <span className={`px-1 text-[8px] border whitespace-nowrap shrink-0 ${
                      log.type === 'INCOME' ? 'text-green-500 border-green-500/30' :
                      log.type === 'OUTCOME' ? 'text-blue-500 border-blue-500/30' :
                      'text-cyan-500 border-cyan-500/30'
                    }`}>
                      {typeLabels[log.type] || log.type}
                    </span>
                  </div>
                  <div className={`font-bold text-xs shrink-0 ${
                    log.type === 'INCOME' ? 'text-green-400' : 'text-white'
                  }`}>
                    {log.formattedAmount}
                  </div>
                </div>
                {/* Row 2: Source + Date */}
                <div className="flex items-center justify-between gap-2">
                  <span className="text-gray-300 text-[10px] truncate" title={log.localizedSource}>
                    {log.localizedSource}
                  </span>
                  <span className="text-gray-500 text-[9px] shrink-0">
                    {log.date}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

export default memo(ProfileBilling);





































