import { Upload, FolderOpen, GitBranch, MessageSquare } from 'lucide-react'
import styles from './Tabs.module.css'

const TAB_CONFIG = [
  { id: 'upload',    label: 'Upload',            Icon: Upload,        desc: 'Add documents' },
  { id: 'ingestion', label: 'Ingestion Pipeline', Icon: GitBranch,     desc: 'Pipeline status' },
  { id: 'documents', label: 'Documents',          Icon: FolderOpen,    desc: 'Manage & delete' },
  { id: 'chat',      label: 'Chat',               Icon: MessageSquare, desc: 'Ask questions' },
]

export default function Tabs({ activeTab, onTabChange }) {
  return (
    <nav className={styles.tabBar} role="tablist" aria-label="Main navigation">
      {TAB_CONFIG.map(({ id, label, Icon, desc }) => {
        const active = activeTab === id
        return (
          <button
            key={id}
            role="tab"
            id={`tab-${id}`}
            aria-selected={active}
            aria-controls={`panel-${id}`}
            className={`${styles.tab} ${active ? styles.active : ''}`}
            onClick={() => onTabChange(id)}
          >
            <span className={styles.tabIconWrap}>
              <Icon size={17} strokeWidth={active ? 2.2 : 1.8} />
            </span>
            <span className={styles.tabContent}>
              <span className={styles.tabLabel}>{label}</span>
              <span className={styles.tabDesc}>{desc}</span>
            </span>
            {active && <span className={styles.activeBar} />}
          </button>
        )
      })}
    </nav>
  )
}
