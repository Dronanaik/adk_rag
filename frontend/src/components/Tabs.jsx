import { Upload, FolderOpen, GitBranch, Share2, MessageSquare } from 'lucide-react'
import styles from './Tabs.module.css'

const TAB_CONFIG = [
  { id: 'upload',     label: 'Upload',             Icon: Upload,         desc: 'Add documents' },
  { id: 'ingestion',  label: 'Ingestion Pipeline', Icon: GitBranch,      desc: 'Neon + Neo4j status' },
  { id: 'documents',  label: 'Documents',          Icon: FolderOpen,     desc: 'Manage & delete' },
  { id: 'chat',       label: 'Agentic Chat',       Icon: MessageSquare,  desc: 'Hybrid RAG + Graph' },
  { id: 'graph',      label: 'Knowledge Graph',    Icon: Share2,         desc: 'Neo4j entities & links' },
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
