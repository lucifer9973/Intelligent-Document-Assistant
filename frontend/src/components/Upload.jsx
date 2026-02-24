import React, { useState } from 'react'
import { client } from '../api'

export default function Upload(){
  const [uploading, setUploading] = useState(false)
  const [message, setMessage] = useState('')

  async function handleFile(e){
    const input = e.target
    const file = e.target.files[0]
    if(!file) return
    setUploading(true)
    setMessage('Uploading...')
    const fd = new FormData()
    fd.append('file', file, file.name)
    try{
      const r = await client.post('/upload', fd, { headers: {'Content-Type':'multipart/form-data'} })
      setMessage(r.data.message || 'Uploaded')
    }catch(err){
      const detail = err?.response?.data?.detail
      setMessage(typeof detail === 'string' ? detail : (detail ? JSON.stringify(detail) : 'Upload failed'))
    }finally{
      setUploading(false)
      // Allow selecting the same file again to trigger onChange.
      input.value = ''
    }
  }

  return (
    <div className="upload">
      <input id="fileinput" type="file" onChange={handleFile} />
      <label htmlFor="fileinput" className="upload-label">Click to upload or drag & drop</label>
      {uploading && <div className="uploading">{message}</div>}
      {!uploading && message && <div className="upload-msg">{message}</div>}
    </div>
  )
}
