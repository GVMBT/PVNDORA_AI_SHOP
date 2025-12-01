import React, { useState, useEffect } from 'react'
import { useAdmin } from '../hooks/useAdmin'
import { useTelegram } from '../hooks/useTelegram'
import { ArrowLeft, MessageSquare, CheckCircle, XCircle, AlertCircle } from 'lucide-react'
import { Button } from '../components/ui/button'
import { Card, CardContent } from '../components/ui/card'
import { Badge } from '../components/ui/badge'
import { Skeleton } from '../components/ui/skeleton'

export default function AdminTicketsPage({ onBack }) {
  const { getTickets, resolveTicket, loading } = useAdmin()
  const { showAlert, hapticFeedback } = useTelegram()
  
  const [tickets, setTickets] = useState([])
  const [statusFilter, setStatusFilter] = useState('open')

  useEffect(() => {
    loadTickets()
  }, [statusFilter])

  const loadTickets = async () => {
    try {
      const data = await getTickets(statusFilter)
      setTickets(data.tickets || [])
    } catch (err) {
      await showAlert(`Error: ${err.message}`)
    }
  }

  const handleResolve = async (ticketId, approve) => {
    hapticFeedback('impact', 'medium')
    try {
      await resolveTicket(ticketId, approve)
      await showAlert(approve ? 'Ticket approved' : 'Ticket rejected')
      loadTickets()
    } catch (err) {
      await showAlert(`Error: ${err.message}`)
    }
  }

  return (
    <div className="p-4 pb-20 space-y-6">
      <div className="flex items-center gap-4 sticky top-0 bg-background/80 backdrop-blur-md py-2 z-10 border-b border-border/50">
        <Button variant="ghost" size="icon" onClick={onBack}>
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <h1 className="text-xl font-bold">Support Tickets</h1>
      </div>

      <div className="flex gap-2 overflow-x-auto pb-2 no-scrollbar">
        {['open', 'approved', 'rejected', 'closed'].map((status) => (
          <Badge
            key={status}
            variant={statusFilter === status ? 'default' : 'outline'}
            className="cursor-pointer whitespace-nowrap capitalize px-3 py-1"
            onClick={() => setStatusFilter(status)}
          >
            {status}
          </Badge>
        ))}
      </div>

      {loading && !tickets.length ? (
        <div className="space-y-4">
          {[1, 2, 3].map(i => <Skeleton key={i} className="h-32 w-full rounded-xl" />)}
        </div>
      ) : tickets.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 text-center space-y-4">
          <div className="p-4 rounded-full bg-secondary text-muted-foreground">
            <MessageSquare className="h-12 w-12" />
          </div>
          <p className="text-muted-foreground">No tickets found</p>
        </div>
      ) : (
        <div className="space-y-4">
          {tickets.map((ticket) => (
            <Card key={ticket.id} className="overflow-hidden">
              <CardContent className="p-4 space-y-4">
                <div className="flex justify-between items-start">
                  <div className="flex items-center gap-2">
                    <Badge 
                      variant={
                        ticket.status === 'open' ? 'warning' :
                        ticket.status === 'approved' ? 'success' :
                        ticket.status === 'rejected' ? 'destructive' : 'secondary'
                      }
                      className="capitalize"
                    >
                      {ticket.status}
                    </Badge>
                    <span className="text-xs text-muted-foreground bg-secondary px-2 py-0.5 rounded-full">
                      {ticket.issue_type || 'General'}
                    </span>
                  </div>
                </div>
                
                <p className="text-sm leading-relaxed">
                  {ticket.description || 'No description provided'}
                </p>
                
                {ticket.admin_comment && (
                  <div className="text-sm bg-secondary/30 p-3 rounded-lg text-muted-foreground italic border border-border/50">
                    Admin: {ticket.admin_comment}
                  </div>
                )}

                {ticket.status === 'open' && (
                  <div className="grid grid-cols-2 gap-3 pt-2 border-t border-border/50">
                    <Button 
                      variant="outline" 
                      className="border-green-500/20 text-green-500 hover:bg-green-500/10 hover:text-green-500"
                      onClick={() => handleResolve(ticket.id, true)}
                    >
                      <CheckCircle className="h-4 w-4 mr-2" />
                      Approve
                    </Button>
                    <Button 
                      variant="outline" 
                      className="border-destructive/20 text-destructive hover:bg-destructive/10 hover:text-destructive"
                      onClick={() => handleResolve(ticket.id, false)}
                    >
                      <XCircle className="h-4 w-4 mr-2" />
                      Reject
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
