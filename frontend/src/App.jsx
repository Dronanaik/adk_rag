import { useState } from 'react'
import UserIdModal from './components/UserIdModal.jsx'
import Header from './components/Header.jsx'
import Tabs from './components/Tabs.jsx'
import UploadTab from './components/UploadTab.jsx'
import DocumentsTab from './components/DocumentsTab.jsx'
import IngestionTab from './components/IngestionTab.jsx'
import ChatTab from './components/ChatTab.jsx'
import styles from './App.module.css'

export default function App() {
  const [userId, setUserId] = useState(null)
  const [activeTab, setActiveTab] = useState('upload')

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

  const tabContent = {
    upload:    <UploadTab   userId={userId} />,
    documents: <DocumentsTab userId={userId} />,
    ingestion: <IngestionTab />,
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
