import styles from './Tabs.module.css'

const TAB_CONFIG = [
  { id: 'upload',    label: 'Upload',            icon: '📤', desc: 'Add documents' },
  { id: 'documents', label: 'Documents',          icon: '📂', desc: 'Manage & delete' },
  { id: 'ingestion', label: 'Ingestion Pipeline', icon: '⚙️',  desc: 'Pipeline status' },
  { id: 'chat',      label: 'Chat',               icon: '💬', desc: 'Ask questions' },
]

export default function Tabs({ activeTab, onTabChange }) {
  return (
    <nav className={styles.tabBar} role="tablist" aria-label="Main navigation">
      {TAB_CONFIG.map((tab) => (
        <button
          key={tab.id}
          role="tab"
          id={`tab-${tab.id}`}
          aria-selected={activeTab === tab.id}
          aria-controls={`panel-${tab.id}`}
          className={`${styles.tab} ${activeTab === tab.id ? styles.active : ''}`}
          onClick={() => onTabChange(tab.id)}
        >
          <span className={styles.tabIcon}>{tab.icon}</span>
          <span className={styles.tabContent}>
            <span className={styles.tabLabel}>{tab.label}</span>
            <span className={styles.tabDesc}>{tab.desc}</span>
          </span>
          {activeTab === tab.id && <span className={styles.activeIndicator} />}
        </button>
      ))}
    </nav>
  )
}
