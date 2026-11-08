import { useEffect, useState } from 'react'
import UserIdModal from './components/UserIdModal.jsx'
import Header from './components/Header.jsx'
import Tabs from './components/Tabs.jsx'
import UploadTab from './components/UploadTab.jsx'
import DocumentsTab from './components/DocumentsTab.jsx'
import IngestionTab from './components/IngestionTab.jsx'
import GraphTab from './components/GraphTab.jsx'
import ChatTab from './components/ChatTab.jsx'
import SettingsTab from './components/SettingsTab.jsx'
import styles from './App.module.css'
import {
  clearStoredAuth,
  fetchCurrentUser,
  getStoredAuth,
  uploadDocument,
} from './api.js'

export default function App() {
  const [user, setUser] = useState(() => getStoredAuth().user)
  const [activeTab, setActiveTab] = useState('settings')
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
    return (
      <UserIdModal
        onConfirm={(loggedInUser) => {
          setUser(loggedInUser)
          setActiveTab('settings')
        }}
      />
    )
  }

  const userId = user.email

  function handleTabChange(tab) {
    setActiveTab(tab)
  }

  function handleSignOut() {
    clearStoredAuth()
    setUser(null)
    setActiveTab('settings')
  }

  async function handleStartUpload(filesOrFile) {
    const files = Array.isArray(filesOrFile) ? filesOrFile : [filesOrFile]
    if (!files.length) return

    const totalDocs = files.length
    const completedResults = []
    setActiveTab('ingestion')

    for (let idx = 0; idx < totalDocs; idx += 1) {
      const file = files[idx]
      const docIndex = idx + 1

      setUploadState({
        status: 'uploading',
        currentDocIndex: docIndex,
        totalDocs,
        currentFilename: file.name,
        results: [...completedResults],
        result: null,
        error: null,
      })

      try {
        const data = await uploadDocument(file, userId, { docIndex, totalDocs })
        if (data?.result) {
          completedResults.push(data.result)
        }
      } catch (err) {
        setUploadState({
          status: 'error',
          currentDocIndex: docIndex,
          totalDocs,
          currentFilename: file.name,
          results: [...completedResults],
          result: null,
          error:
            totalDocs > 1
              ? `Document ${docIndex} of ${totalDocs} (${file.name}): ${err.message}`
              : err.message,
        })
        return
      }
    }

    const createdCount = completedResults.filter(
      (r) => !r.ingest_action || r.ingest_action === 'created'
    ).length
    const updatedCount = completedResults.filter((r) => r.ingest_action === 'updated').length
    const skippedCount = completedResults.filter(
      (r) => r.ingest_action === 'unchanged' || r.ingest_action === 'duplicate_content'
    ).length

    const summaryResult = {
      documents_count: completedResults.length,
      created_count: createdCount,
      updated_count: updatedCount,
      skipped_count: skippedCount,
      ingest_action: completedResults.length === 1 ? completedResults[0]?.ingest_action : undefined,
      action_detail: completedResults.length === 1 ? completedResults[0]?.action_detail : undefined,
      duplicate_of: completedResults.length === 1 ? completedResults[0]?.duplicate_of : undefined,
      filename:
        completedResults.length === 1
          ? completedResults[0]?.filename
          : completedResults.map((r) => r.filename).join(', '),
      chunks_created: completedResults.reduce((s, r) => s + (r.chunks_created || 0), 0),
      entities_extracted: completedResults.reduce((s, r) => s + (r.entities_extracted || 0), 0),
      relationships_extracted: completedResults.reduce(
        (s, r) => s + (r.relationships_extracted || 0),
        0
      ),
      characters_extracted: completedResults.reduce(
        (s, r) => s + (r.characters_extracted || 0),
        0
      ),
      documents: completedResults,
    }

    setUploadState({
      status: 'success',
      currentDocIndex: totalDocs,
      totalDocs,
      currentFilename: '',
      results: completedResults,
      result: summaryResult,
      error: null,
    })
  }

  const tabContent = {
    settings:  <SettingsTab  onContinueToUpload={() => setActiveTab('upload')} />,
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
