import React from 'react'
import { Badge } from '../ui/badge'

export function UserInfo({ user, isPartner }) {
  return (
    <div className="flex items-center gap-4 px-2">
      <div className="w-16 h-16 rounded-full bg-gradient-to-br from-primary to-blue-600 p-[2px]">
        <div className="w-full h-full rounded-full bg-background flex items-center justify-center text-2xl font-bold overflow-hidden">
          {user?.photo_url ? <img src={user.photo_url} alt="ava" className="w-full h-full object-cover" /> : (user?.username?.[0] || 'U')}
        </div>
      </div>
      <div>
        <h1 className="text-xl font-bold flex items-center gap-2">
          {user?.first_name}{' '}
          {isPartner && <Badge variant="secondary" className="bg-purple-500/20 text-purple-400 text-[10px] h-5">VIP</Badge>}
        </h1>
        <p className="text-muted-foreground text-sm">@{user?.username || 'user'}</p>
      </div>
    </div>
  )
}

export default UserInfo
