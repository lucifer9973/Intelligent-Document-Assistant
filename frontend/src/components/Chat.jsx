import React, { useState, useEffect } from 'react'
import { client } from '../api'

export default function Chat(){
  const [messages, setMessages] = useState([])
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)

  function addMessage(text, role='user'){
    setMessages(m=>[...m,{text,role}])
  }

  async function send(){
    if(!query) return
    addMessage(query,'user')
    setLoading(true)
    setQuery('')
    try{
      const r = await client.post('/query',{query,stream:false})
      addMessage(r.data.response||'No response','assistant')
    }catch(e){
      addMessage(e?.response?.data?.detail||'Error','assistant')
    }finally{setLoading(false)}
  }

  return (
    <div className="chat">
      <div className="messages">
        {messages.length===0 && <div className="empty">Upload a document to get started</div>}
        {messages.map((m,i)=>(
          <div key={i} className={`msg ${m.role}`}><div className="bubble">{m.text}</div></div>
        ))}
      </div>
      <div className="composer">
        <input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Ask about your documents..." onKeyDown={e=>{if(e.key==='Enter')send()}} />
        <button onClick={send} disabled={loading}>{loading? '...' : 'Send'}</button>
      </div>
    </div>
  )
}
