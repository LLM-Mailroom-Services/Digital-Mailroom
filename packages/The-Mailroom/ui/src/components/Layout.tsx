import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import { pipelineWS } from '@/api/websocket'
import { useWSStore } from '@/stores/websocketStore'
import { usePipelineStore } from '@/stores/pipelineStore'
import type { Document, WSEvent } from '@/types/api'
import Sidebar from './Sidebar'

export default function Layout({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuthStore()
  const { setConnected, setLastEvent } = useWSStore()
  const { updateDocumentStage, addDocument } = usePipelineStore()
  const location = useLocation()
  const navigate = useNavigate()
  const [dark, setDark] = useState(() => localStorage.getItem('mailroom.ui.dark') === '1')

  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark)
    localStorage.setItem('mailroom.ui.dark', dark ? '1' : '0')
  }, [dark])

  useEffect(() => {
    pipelineWS.connect()
    const unsub = pipelineWS.onMessage((event: unknown) => {
      const payload = event as WSEvent
      setLastEvent(payload)
      setConnected(true)
      if (payload.type === 'stage_change' && typeof payload.doc_id === 'string') {
        updateDocumentStage(payload.doc_id, String(payload.to_stage || 'processing'))
      }
      if (payload.type === 'new_document' && payload.document && typeof payload.document === 'object') {
        const doc = payload.document as Document
        if (doc.doc_id) addDocument(doc)
      }
    })
    return () => {
      unsub()
      pipelineWS.disconnect()
    }
  }, [addDocument, setConnected, setLastEvent, updateDocumentStage])

  return (
    <div className="flex h-screen bg-background">
      <Sidebar
        user={user}
        currentPath={location.pathname}
        dark={dark}
        onToggleDark={() => setDark((value) => !value)}
        onLogout={() => {
          void logout().then(() => navigate('/login'))
        }}
      />
      <main className="flex-1 overflow-auto p-6">{children}</main>
    </div>
  )
}
