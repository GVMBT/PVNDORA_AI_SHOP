import React from 'react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '../ui/dialog'
import { Label } from '../ui/label'
import { Input } from '../ui/input'
import { Button } from '../ui/button'
import { Tabs, TabsList, TabsTrigger } from '../ui/tabs'
import { cn } from '../../lib/utils'

export function WithdrawDialog({
  open,
  onOpenChange,
  t,
  formatPrice,
  currency,
  profile,
  withdrawAmount,
  setWithdrawAmount,
  withdrawMethod,
  setWithdrawMethod,
  withdrawDetails,
  setWithdrawDetails,
  submitting,
  handleWithdraw,
  getMethodIcon,
  minWithdrawal,
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md bg-card/95 backdrop-blur-xl border-white/10">
        <DialogHeader>
          <DialogTitle>{t('profile.withdrawTitle')}</DialogTitle>
          <DialogDescription>{t('profile.withdrawDescription')}</DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label>{t('profile.amount')}</Label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">$</span>
              <Input
                type="number"
                className="pl-8"
                placeholder={formatPrice(minWithdrawal, currency)}
                value={withdrawAmount}
                onChange={(e) => setWithdrawAmount(e.target.value)}
              />
            </div>
            <p className="text-xs text-right text-muted-foreground">
              {t('profile.available')}: {formatPrice(profile?.balance || 0, currency)}
            </p>
          </div>

          <div className="space-y-2">
            <Label>{t('profile.paymentMethod')}</Label>
            <Tabs value={withdrawMethod} onValueChange={setWithdrawMethod}>
              <TabsList className="grid grid-cols-3 gap-2 bg-transparent p-0">
                {['card', 'phone', 'crypto'].map((method) => (
                  <TabsTrigger
                    key={method}
                    value={method}
                    className={cn(
                      'flex flex-col items-center gap-2 py-3 px-3 h-auto rounded-full border',
                      'data-[state=active]:bg-primary data-[state=active]:text-black data-[state=active]:border-primary data-[state=active]:shadow-[0_10px_30px_rgba(0,245,212,0.25)]',
                      'data-[state=inactive]:bg-white/5 data-[state=inactive]:text-muted-foreground data-[state=inactive]:border-white/10'
                    )}
                  >
                    {getMethodIcon(method)}
                    <span className="text-[10px] font-medium uppercase">{t(`profile.method.${method}`)}</span>
                  </TabsTrigger>
                ))}
              </TabsList>
            </Tabs>
          </div>

          <div className="space-y-2">
            <Label>{t('profile.paymentDetails')}</Label>
            <Input
              placeholder={
                withdrawMethod === 'card'
                  ? '4276 **** **** ****'
                  : withdrawMethod === 'phone'
                    ? '+7 900 000 00 00'
                    : 'Wallet Address'
              }
              value={withdrawDetails}
              onChange={(e) => setWithdrawDetails(e.target.value)}
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>{t('common.cancel')}</Button>
          <Button onClick={handleWithdraw} disabled={submitting} className="bg-primary text-black hover:bg-primary/90">
            {submitting ? t('common.loading') : t('profile.requestWithdrawal')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export default WithdrawDialog
