import React, { useState, useEffect } from 'react'
import { useAdmin } from '../hooks/useAdmin'
import { useLocale } from '../hooks/useLocale'
import { useTelegram } from '../hooks/useTelegram'
import { ArrowLeft, BarChart2, DollarSign, ShoppingBag, TrendingUp } from 'lucide-react'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Badge } from '../components/ui/badge'
import { Skeleton } from '../components/ui/skeleton'

export default function AdminAnalyticsPage({ onBack }) {
  const { getAnalytics, loading } = useAdmin()
  const { formatPrice } = useLocale()
  const { showAlert } = useTelegram()
  
  const [analytics, setAnalytics] = useState(null)
  const [days, setDays] = useState(7)

  useEffect(() => {
    loadAnalytics()
  }, [days])

  const loadAnalytics = async () => {
    try {
      const data = await getAnalytics(days)
      setAnalytics(data)
    } catch (err) {
      await showAlert(`Error: ${err.message}`)
    }
  }

  const StatCard = ({ title, value, icon: Icon, trend }) => (
    <Card>
      <CardContent className="p-4 flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-muted-foreground mb-1">{title}</p>
          <h3 className="text-2xl font-bold">{value}</h3>
        </div>
        <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center text-primary">
          <Icon className="h-6 w-6" />
        </div>
      </CardContent>
    </Card>
  )

  return (
    <div className="p-4 pb-20 space-y-6">
      <div className="flex items-center gap-4 sticky top-0 bg-background/80 backdrop-blur-md py-2 z-10 border-b border-border/50">
        <Button variant="ghost" size="icon" onClick={onBack}>
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <h1 className="text-xl font-bold">Analytics</h1>
      </div>

      <div className="flex p-1 bg-secondary/50 rounded-lg">
        {[7, 30, 90].map((d) => (
          <button
            key={d}
            onClick={() => setDays(d)}
            className={`flex-1 py-1.5 text-sm font-medium rounded-md transition-all ${
              days === d
                ? 'bg-background shadow-sm text-foreground'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            {d} Days
          </button>
        ))}
      </div>

      {loading ? (
        <div className="space-y-4">
          <Skeleton className="h-24 w-full rounded-xl" />
          <Skeleton className="h-24 w-full rounded-xl" />
          <Skeleton className="h-48 w-full rounded-xl" />
        </div>
      ) : analytics ? (
        <div className="space-y-4">
          <div className="grid gap-4">
            <StatCard 
              title="Total Revenue" 
              value={formatPrice(analytics.total_revenue || 0)} 
              icon={DollarSign}
            />
            <StatCard 
              title="Total Orders" 
              value={analytics.total_orders || 0} 
              icon={ShoppingBag}
            />
            <StatCard 
              title="Avg. Order Value" 
              value={formatPrice(analytics.avg_order_value || 0)} 
              icon={TrendingUp}
            />
          </div>

          {analytics.top_products && analytics.top_products.length > 0 && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-lg font-semibold flex items-center gap-2">
                  <BarChart2 className="h-5 w-5 text-primary" />
                  Top Products
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {analytics.top_products.map((product, idx) => (
                    <div key={idx} className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <span className="flex h-6 w-6 items-center justify-center rounded-full bg-secondary text-xs font-medium text-muted-foreground">
                          {idx + 1}
                        </span>
                        <span className="font-medium text-sm">{product.name}</span>
                      </div>
                      <Badge variant="secondary">{product.count} sold</Badge>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-12 text-center space-y-4">
          <div className="p-4 rounded-full bg-secondary text-muted-foreground">
            <BarChart2 className="h-12 w-12" />
          </div>
          <p className="text-muted-foreground">No analytics data available</p>
        </div>
      )}
    </div>
  )
}
