import React, { useState, useEffect } from 'react'
import { useAdmin } from '../hooks/useAdmin'
import { useTelegram } from '../hooks/useTelegram'

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
      await showAlert(`Ошибка: ${err.message}`)
    }
  }

  const handleResolve = async (ticketId, approve) => {
    hapticFeedback('impact', 'medium')
    try {
      await resolveTicket(ticketId, approve)
      await showAlert(approve ? 'Тикет одобрен' : 'Тикет отклонён')
      loadTickets()
    } catch (err) {
      await showAlert(`Ошибка: ${err.message}`)
    }
  }

  return (
    <div className="p-4">
      <div className="flex items-center justify-between mb-6">
        <button onClick={onBack} className="text-[var(--color-primary)]">← Назад</button>
        <h1 className="text-xl font-bold">Тикеты</h1>
      </div>

      <div className="flex gap-2 mb-4">
        {['open', 'approved', 'rejected', 'closed'].map((status) => (
          <button
            key={status}
            onClick={() => setStatusFilter(status)}
            className={`px-4 py-2 rounded-full text-sm ${
              statusFilter === status
                ? 'bg-[var(--color-primary)] text-white'
                : 'bg-[var(--color-bg-elevated)] text-[var(--color-text-muted)]'
            }`}
          >
            {status === 'open' ? 'Открытые' : status === 'approved' ? 'Одобрены' : status === 'rejected' ? 'Отклонены' : 'Закрыты'}
          </button>
        ))}
      </div>

      {loading && !tickets.length ? (
        <div className="text-center py-8">Загрузка...</div>
      ) : tickets.length === 0 ? (
        <div className="card text-center py-8">
          <p className="text-[var(--color-text-muted)]">Нет тикетов</p>
        </div>
      ) : (
        <div className="space-y-3">
          {tickets.map((ticket) => (
            <div key={ticket.id} className="card">
              <div className="flex items-start justify-between mb-3">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <span className={`badge ${
                      ticket.status === 'open' ? 'badge-warning' :
                      ticket.status === 'approved' ? 'badge-success' :
                      ticket.status === 'rejected' ? 'badge-error' : ''
                    }`}>
                      {ticket.status}
                    </span>
                    <span className="text-sm text-[var(--color-text-muted)]">
                      {ticket.issue_type || 'Общий'}
                    </span>
                  </div>
                  <p className="text-[var(--color-text)] mb-2">
                    {ticket.description || 'Нет описания'}
                  </p>
                  {ticket.admin_comment && (
                    <p className="text-sm text-[var(--color-text-muted)] italic">
                      Комментарий: {ticket.admin_comment}
                    </p>
                  )}
                </div>
              </div>
              {ticket.status === 'open' && (
                <div className="flex gap-2 mt-3">
                  <button
                    onClick={() => handleResolve(ticket.id, true)}
                    className="btn btn-success flex-1 text-sm"
                  >
                    ✓ Одобрить
                  </button>
                  <button
                    onClick={() => handleResolve(ticket.id, false)}
                    className="btn btn-secondary flex-1 text-sm"
                  >
                    ✗ Отклонить
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

