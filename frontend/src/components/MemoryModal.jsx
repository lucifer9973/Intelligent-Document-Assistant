import React, { useEffect, useState } from 'react'
import { client } from '../api'

export default function MemoryModal({open, onClose}){
  const [history, setHistory] = useState([])

  useEffect(()=>{
    if(!open) return
    (async ()=>{
      try{
        const r = await client.get('/memory')
        setHistory(r.data.history||[])
      }catch(e){
        setHistory([])
      }
    })()
  },[open])

  if(!open) return null
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={e=>e.stopPropagation()}>
        <button className="close" onClick={onClose}>X</button>
        <h3>Conversation Memory</h3>
        <div className="memory-list">
          {history.length===0 && <div className="empty">No conversation history</div>}
          {history.map((h,i)=>(
            <div key={i} className="memory-item">
              <strong>Q{i+1}:</strong> {h.query}
              <div><strong>A:</strong> {h.response?.slice(0,200)}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
