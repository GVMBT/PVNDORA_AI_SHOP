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
import { cn } from '../../lib/utils'
import { CreditCard, Smartphone, Bitcoin, Wallet } from 'lucide-react'

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
  const methods = [
    { id: 'card', label: t?.('profile.method.card') || 'Card', icon: CreditCard },
    { id: 'phone', label: t?.('profile.method.phone') || 'Phone', icon: Smartphone },
    { id: 'crypto', label: t?.('profile.method.crypto') || 'Crypto', icon: Bitcoin },
  ]

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md w-[95vw] bg-[#1a1b1e] border-white/10 p-0 overflow-hidden gap-0 rounded-3xl">
        <div className="p-6 space-y-6">
           <DialogHeader className="space-y-3 text-center sm:text-left">
             <DialogTitle className="text-xl font-bold">{t('profile.withdrawTitle')}</DialogTitle>
             <DialogDescription className="text-muted-foreground text-sm">
               {t('profile.withdrawDescription')}
             </DialogDescription>
           </DialogHeader>

           <div className="space-y-5">
             {/* Amount Input */}
             <div className="space-y-2">
               <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">{t('profile.amount')}</Label>
               <div className="relative">
                 <div className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground font-semibold">$</div>
                 <Input
                   type="number"
                   className="pl-8 h-12 bg-secondary/10 border-white/5 rounded-xl text-lg font-bold focus-visible:ring-primary/50"
                   placeholder={formatPrice(minWithdrawal, currency)}
                   value={withdrawAmount}
                   onChange={(e) => setWithdrawAmount(e.target.value)}
                 />
                 <div className="absolute right-4 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">
                   {t('profile.available')}: {formatPrice(profile?.balance || 0, currency)}
                 </div>
               </div>
             </div>

             {/* Method Selection */}
             <div className="space-y-2">
               <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">{t('profile.paymentMethod')}</Label>
               <div className="grid grid-cols-3 gap-2">
                 {methods.map((method) => {
                   const Icon = method.icon || Wallet
                   const isActive = withdrawMethod === method.id
                   return (
                     <button
                       key={method.id}
                       onClick={() => setWithdrawMethod(method.id)}
                       className={cn(
                         "flex flex-col items-center justify-center gap-2 py-3 rounded-xl border transition-all duration-200",
                         isActive 
                           ? "bg-primary text-primary-foreground border-primary shadow-[0_0_20px_-5px_rgba(0,245,212,0.4)]" 
                           : "bg-secondary/10 text-muted-foreground border-transparent hover:bg-secondary/20"
                       )}
                     >
                       <Icon className="h-5 w-5" />
                       <span className="text-[10px] font-bold uppercase">{method.label}</span>
                     </button>
                   )
                 })}
               </div>
             </div>

             {/* Details Input */}
             <div className="space-y-2">
               <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">{t('profile.paymentDetails')}</Label>
               <Input
                 className="h-12 bg-secondary/10 border-white/5 rounded-xl font-medium focus-visible:ring-primary/50"
                 placeholder={
                   withdrawMethod === 'card'
                     ? '4276 **** **** ****'
                     : withdrawMethod === 'phone'
                       ? '+7 900 000 00 00'
                       : 'Wallet Address (TRC20/BTC...)'
                 }
                 value={withdrawDetails}
                 onChange={(e) => setWithdrawDetails(e.target.value)}
               />
             </div>
           </div>
        </div>

        <DialogFooter className="p-4 bg-secondary/5 border-t border-white/5 sm:justify-between flex-row gap-2">
           <Button variant="ghost" onClick={() => onOpenChange(false)} className="flex-1 h-12 rounded-xl text-muted-foreground hover:bg-white/5">
             {t('common.cancel')}
           </Button>
           <Button 
             onClick={handleWithdraw} 
             disabled={submitting} 
             className="flex-1 h-12 rounded-xl bg-primary text-black font-bold hover:bg-primary/90 shadow-lg shadow-primary/20"
           >
             {submitting ? t('common.loading') : t('profile.requestWithdrawal')}
           </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export default WithdrawDialog
