import { useEffect, useState } from 'react'
import UserIdModal from './components/UserIdModal.jsx'
import Header from './components/Header.jsx'
import Tabs from './components/Tabs.jsx'
import UploadTab from './components/UploadTab.jsx'
import DocumentsTab from './components/DocumentsTab.jsx'
import IngestionTab from './components/IngestionTab.jsx'
import GraphTab from './components/GraphTab.jsx'
import ChatTab from './components/ChatTab.jsx'
import styles from './App.module.css'
import {
  clearStoredAuth,
  fetchCurrentUser,
  getStoredAuth,
  uploadDocument,
} from './api.js'

export default function App() {
  const [user, setUser] = useState(() => getStoredAuth().user)
  const [activeTab, setActiveTab] = useState('upload')
  const [uploadState, setUploadState] = useState({ status: 'idle', result: null, error: null })

  useEffect(() => {
    const { token } = getStoredAuth()
    if (!token) return

    fetchCurrentUser()
      .then((res) => {
        if (res?.user) setUser(res.user)
      })
      .catch(() => {
        clearStoredAuth()
        setUser(null)
      })
  }, [])

  // Show the Neon PostgreSQL Sign In / Sign Up screen until authenticated
  if (!user) {
    return <UserIdModal onConfirm={(loggedInUser) => setUser(loggedInUser)} />
  }

  const userId = user.email

  function handleTabChange(tab) {
    setActiveTab(tab)
  }

  function handleSignOut() {
    clearStoredAuth()
    setUser(null)
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
    upload:    <UploadTab    userId={userId} onStartUpload={handleStartUpload} />,
    documents: <DocumentsTab userId={userId} />,
    ingestion: <IngestionTab uploadState={uploadState} />,
    chat:      <ChatTab      userId={userId} />,
    graph:     <GraphTab     userId={userId} />,
  }

  return (
    <div className={styles.app}>
      <Header user={user} userId={userId} onChangeUser={handleSignOut} />

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
            Where <span style={{ color: 'var(--accent)', fontWeight: 600 }}>Knowledge Connects</span>,{' '}
            <span style={{ color: 'var(--accent2)', fontWeight: 600 }}>Agents Reason</span>, and{' '}
            <span style={{ color: 'var(--accent)', fontWeight: 600 }}>Intelligence Emerges</span>.
          </p>
        </div>
      </footer>
    </div>
  )
}
