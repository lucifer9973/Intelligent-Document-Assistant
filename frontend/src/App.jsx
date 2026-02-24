import React, { useState, useEffect } from 'react'
import Upload from './components/Upload'
import Chat from './components/Chat'
import MemoryModal from './components/MemoryModal'
import { client } from './api'

export default function App(){
  const [connected, setConnected] = useState(false)
  const [showMemory, setShowMemory] = useState(false)

  useEffect(()=>{
    let cancelled = false

    async function checkHealth(){
      try{
        const r = await client.get('/health')
        if(!cancelled) setConnected(r.status===200)
      }catch(e){
        if(!cancelled) setConnected(false)
      }
    }

    checkHealth()
    const timer = setInterval(checkHealth, 5000)
    return ()=>{
      cancelled = true
      clearInterval(timer)
    }
  },[])

  return (
    <div className="app-grid">
      <aside className="sidebar">
        <h1>Document Assistant</h1>
        <Upload />
        <div className="sidebar-actions">
          <button onClick={()=>setShowMemory(true)}>Memory</button>
          <button onClick={async ()=>{await client.post('/reset'); window.location.reload()}}>Reset</button>
        </div>
      </aside>

      <main className="main">
        <div className="header">{connected? 'Connected to API' : 'Not connected'}</div>
        <Chat />
      </main>

      <MemoryModal open={showMemory} onClose={()=>setShowMemory(false)} />
    </div>
  )
}
