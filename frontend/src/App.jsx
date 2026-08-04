import { useState } from 'react'
import UserIdModal from './components/UserIdModal.jsx'
import Header from './components/Header.jsx'
import Tabs from './components/Tabs.jsx'
import UploadTab from './components/UploadTab.jsx'
import DocumentsTab from './components/DocumentsTab.jsx'
import IngestionTab from './components/IngestionTab.jsx'
import ChatTab from './components/ChatTab.jsx'
import styles from './App.module.css'
import { uploadDocument } from './api.js'

export default function App() {
  const [userId, setUserId] = useState(null)
  const [activeTab, setActiveTab] = useState('upload')
  const [uploadState, setUploadState] = useState({ status: 'idle', result: null, error: null })

  // Show the User ID gate until a user logs in
  if (!userId) {
    return <UserIdModal onConfirm={(id) => setUserId(id)} />
  }

  function handleTabChange(tab) {
    setActiveTab(tab)
  }

  function handleChangeUser() {
    setUserId(null)
    setActiveTab('upload')
  }

  async function handleStartUpload(file) {
    setActiveTab('ingestion')
    setUploadState({ status: 'uploading', result: null, error: null })
    try {
      const data = await uploadDocument(file, userId)
      setUploadState({ status: 'success', result: data.result, error: null })
    } catch (err) {
      setUploadState({ status: 'error', result: null, error: err.message })
    }
  }

  const tabContent = {
    upload:    <UploadTab   userId={userId} onStartUpload={handleStartUpload} />,
    documents: <DocumentsTab userId={userId} />,
    ingestion: <IngestionTab uploadState={uploadState} />,
    chat:      <ChatTab     userId={userId} />,
  }

  return (
    <div className={styles.app}>
      <Header userId={userId} onChangeUser={handleChangeUser} />

      <main className={styles.main}>
        <div className="container">
          <Tabs activeTab={activeTab} onTabChange={handleTabChange} />

          {/* Tab panels */}
          <div
            className={styles.tabPanel}
            role="tabpanel"
            id={`panel-${activeTab}`}
            aria-labelledby={`tab-${activeTab}`}
          >
            {tabContent[activeTab]}
          </div>
        </div>
      </main>

      <footer className={styles.footer}>
        <div className="container">
          <p>
            ADK RAG &mdash; Built with{' '}
            <span style={{ color: 'var(--accent-primary)' }}>Google ADK</span>,{' '}
            <span style={{ color: 'var(--accent-secondary)' }}>Gemini</span>, and{' '}
            <span style={{ color: 'var(--accent-primary)' }}>ChromaDB</span>
          </p>
        </div>
      </footer>
    </div>
  )
}
