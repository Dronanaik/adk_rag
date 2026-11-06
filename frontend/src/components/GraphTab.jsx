import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Share2,
  Search,
  RefreshCw,
  AlertCircle,
  Sparkles,
  ArrowRight,
  Layers,
  GitCommit,
  FileText,
  X,
} from 'lucide-react'
import { getKnowledgeGraph } from '../api.js'
import styles from './GraphTab.module.css'

const TYPE_COLORS = {
  Technology:   { bg: '#082f38', border: '#22d3ee', text: '#67e8f9', dot: '#22d3ee' },
  Model:        { bg: '#093026', border: '#34d399', text: '#6ee7b7', dot: '#34d399' },
  Concept:      { bg: '#2e2208', border: '#fbbf24', text: '#fde68a', dot: '#fbbf24' },
  Organization: { bg: '#0c2742', border: '#38bdf8', text: '#7dd3fc', dot: '#38bdf8' },
  Person:       { bg: '#331c08', border: '#fb923c', text: '#fdba74', dot: '#fb923c' },
  Metric:       { bg: '#0b3323', border: '#10b981', text: '#a7f3d0', dot: '#10b981' },
  Location:     { bg: '#321028', border: '#f472b6', text: '#f9a8d4', dot: '#f472b6' },
  Event:        { bg: '#36111b', border: '#fb7185', text: '#fda4af', dot: '#fb7185' },
}

function getTypeStyle(type) {
  return TYPE_COLORS[type] || { bg: '#0d2922', border: '#34d399', text: '#a7f3d0', dot: '#34d399' }
}

/**
 * Deterministic radial/concentric force-inspired layout for SVG graph visualization.
 */
function computeGraphLayout(nodes, edges, width = 760, height = 420) {
  if (!nodes.length) return { positionedNodes: [], positionedEdges: [] }

  const centerX = width / 2
  const centerY = height / 2
  const maxNodes = nodes.slice(0, 36)
  const nodeMap = new Map()

  maxNodes.forEach((node, idx) => {
    let x = centerX
    let y = centerY

    if (idx === 0 && maxNodes.length > 1) {
      // Highest-degree hub in center
      x = centerX
      y = centerY
    } else {
      const ring = idx <= 10 ? 1 : idx <= 22 ? 2 : 3
      const ringItems =
        ring === 1
          ? Math.min(10, maxNodes.length - 1)
          : ring === 2
          ? Math.min(12, Math.max(1, maxNodes.length - 11))
          : Math.max(1, maxNodes.length - 23)
      const indexInRing = ring === 1 ? idx - 1 : ring === 2 ? idx - 11 : idx - 23
      const angle = (2 * Math.PI * indexInRing) / ringItems - Math.PI / 2
      const rx = ring === 1 ? 135 : ring === 2 ? 245 : 325
      const ry = ring === 1 ? 95 : ring === 2 ? 155 : 185
      x = centerX + rx * Math.cos(angle)
      y = centerY + ry * Math.sin(angle)
    }

    const positioned = { ...node, x, y }
    nodeMap.set(node.name, positioned)
  })

  const positionedEdges = []
  edges.forEach((edge, i) => {
    const src = nodeMap.get(edge.source)
    const tgt = nodeMap.get(edge.target)
    if (src && tgt && src.name !== tgt.name) {
      positionedEdges.push({
        ...edge,
        id: `edge-${i}`,
        x1: src.x,
        y1: src.y,
        x2: tgt.x,
        y2: tgt.y,
      })
    }
  })

  return {
    positionedNodes: Array.from(nodeMap.values()),
    positionedEdges,
  }
}

export default function GraphTab({ userId }) {
  const [graphData, setGraphData] = useState({
    configured: true,
    nodes: [],
    edges: [],
    stats: { entities: 0, relationships: 0 },
  })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [selectedType, setSelectedType] = useState('All')
  const [selectedNode, setSelectedNode] = useState(null)

  const fetchGraph = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await getKnowledgeGraph(userId)
      setGraphData(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [userId])

  useEffect(() => {
    fetchGraph()
  }, [fetchGraph])

  const entityTypes = useMemo(() => {
    const counts = new Set(['All'])
    graphData.nodes?.forEach(n => {
      if (n.entity_type) counts.add(n.entity_type)
    })
    return Array.from(counts)
  }, [graphData.nodes])

  const filteredNodes = useMemo(() => {
    const q = searchInput.trim().toLowerCase()
    return (graphData.nodes || []).filter(n => {
      const matchesType = selectedType === 'All' || n.entity_type === selectedType
      const matchesQuery =
        !q ||
        n.name.toLowerCase().includes(q) ||
        (n.description || '').toLowerCase().includes(q) ||
        (n.entity_type || '').toLowerCase().includes(q)
      return matchesType && matchesQuery
    })
  }, [graphData.nodes, searchInput, selectedType])

  const filteredNodeNames = useMemo(
    () => new Set(filteredNodes.map(n => n.name)),
    [filteredNodes]
  )

  const filteredEdges = useMemo(() => {
    const q = searchInput.trim().toLowerCase()
    return (graphData.edges || []).filter(e => {
      if (selectedNode) {
        return e.source === selectedNode.name || e.target === selectedNode.name
      }
      const endpointMatch =
        filteredNodeNames.has(e.source) || filteredNodeNames.has(e.target)
      if (!q) return endpointMatch
      return (
        endpointMatch ||
        (e.relation_type || '').toLowerCase().includes(q) ||
        (e.fact || '').toLowerCase().includes(q)
      )
    })
  }, [graphData.edges, filteredNodeNames, searchInput, selectedNode])

  const { positionedNodes, positionedEdges } = useMemo(
    () => computeGraphLayout(filteredNodes, graphData.edges || []),
    [filteredNodes, graphData.edges]
  )

  return (
    <div className={`${styles.wrap} fade-in`}>
      {/* Header */}
      <div className={styles.headerRow}>
        <div>
          <h2 className={styles.title}>Neo4j Knowledge Graph Explorer</h2>
          <p className={styles.sub}>
            Explore domain entities and semantic relationships automatically extracted from your documents by Gemini and stored in Neo4j.
          </p>
        </div>
        <button
          className="btn btn-secondary"
          onClick={fetchGraph}
          disabled={loading}
          id="refresh-graph-btn"
        >
          <RefreshCw size={16} className={loading ? 'spinner' : ''} /> Refresh Graph
        </button>
      </div>

      {/* Summary metrics */}
      <div className={styles.statsGrid}>
        <div className={`glass-card ${styles.statCard}`}>
          <div className={`${styles.statIcon} ${styles.indigo}`}>
            <Share2 size={22} />
          </div>
          <div>
            <div className={styles.statLabel}>Total Entities</div>
            <div className={styles.statValue}>
              {loading ? '…' : graphData.stats?.entities ?? 0}
            </div>
          </div>
        </div>

        <div className={`glass-card ${styles.statCard}`}>
          <div className={`${styles.statIcon} ${styles.teal}`}>
            <GitCommit size={22} />
          </div>
          <div>
            <div className={styles.statLabel}>Relationships</div>
            <div className={styles.statValue}>
              {loading ? '…' : graphData.stats?.relationships ?? 0}
            </div>
          </div>
        </div>

        <div className={`glass-card ${styles.statCard}`}>
          <div className={`${styles.statIcon} ${styles.indigo}`}>
            <Layers size={22} />
          </div>
          <div>
            <div className={styles.statLabel}>Entity Categories</div>
            <div className={styles.statValue}>
              {loading ? '…' : Math.max(0, entityTypes.length - 1)}
            </div>
          </div>
        </div>
      </div>

      {error && (
        <div className="alert alert-error">
          <AlertCircle size={18} /> {error}
        </div>
      )}

      {!loading && graphData.configured === false && (
        <div className="alert alert-warning">
          <AlertCircle size={18} />
          <span>
            Neo4j is not configured yet. Set <code>NEO4J_URI</code>, <code>NEO4J_USERNAME</code>, and <code>NEO4J_PASSWORD</code> in your <code>.env</code> file to enable Knowledge Graph extraction and visualization.
          </span>
        </div>
      )}

      {/* Search & Category Filter Bar */}
      <div className={`glass-card ${styles.filterBar}`}>
        <div className={styles.searchWrap}>
          <Search size={17} className={styles.searchIcon} />
          <input
            type="text"
            className={`input ${styles.searchInput}`}
            placeholder="Filter entities, relationships, or facts (e.g. Transformer, Attention)…"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
          />
          {searchInput && (
            <button
              className={styles.clearBtn}
              onClick={() => setSearchInput('')}
              title="Clear filter"
            >
              <X size={15} />
            </button>
          )}
        </div>

        <div className={styles.typePills}>
          {entityTypes.map(type => (
            <button
              key={type}
              className={`${styles.typePill} ${selectedType === type ? styles.typePillActive : ''}`}
              onClick={() => {
                setSelectedType(type)
                setSelectedNode(null)
              }}
            >
              {type}
            </button>
          ))}
        </div>
      </div>

      {/* Empty State */}
      {!loading && (graphData.nodes?.length || 0) === 0 && !error && (
        <div className="empty-state glass-card">
          <span className="empty-state-icon">
            <Share2 size={48} strokeWidth={1.3} color="#22d3ee" />
          </span>
          <p style={{ fontWeight: 700, color: 'var(--text-primary)', fontSize: '1.05rem' }}>
            No Knowledge Graph entities yet
          </p>
          <p style={{ fontSize: '0.88rem', maxWidth: '460px' }}>
            Upload a document in the <strong>Upload</strong> tab to automatically extract entities and relationships into Neo4j.
          </p>
        </div>
      )}

      {/* Interactive SVG Graph + Selected Node Inspector */}
      {positionedNodes.length > 0 && (
        <div className={styles.graphLayout}>
          <div className={`glass-card ${styles.canvasCard}`}>
            <div className={styles.canvasHeader}>
              <div className={styles.canvasTitleWrap}>
                <Sparkles size={16} color="var(--accent-primary)" />
                <span className={styles.canvasTitle}>Interactive Entity Topology</span>
              </div>
              <span className={styles.canvasHint}>
                Click any node to inspect its 1-hop relationships
              </span>
            </div>

            <div className={styles.svgContainer}>
              <svg
                viewBox="0 0 760 420"
                className={styles.svgGraph}
                role="img"
                aria-label="Neo4j Entity Relationship Graph"
              >
                <defs>
                  <marker
                    id="arrow-default"
                    viewBox="0 0 10 10"
                    refX="22"
                    refY="5"
                    markerWidth="6"
                    markerHeight="6"
                    orient="auto-start-reverse"
                  >
                    <path d="M 0 1 L 10 5 L 0 9 z" fill="rgba(52, 211, 153, 0.45)" />
                  </marker>
                  <marker
                    id="arrow-active"
                    viewBox="0 0 10 10"
                    refX="22"
                    refY="5"
                    markerWidth="6"
                    markerHeight="6"
                    orient="auto-start-reverse"
                  >
                    <path d="M 0 1 L 10 5 L 0 9 z" fill="#fbbf24" />
                  </marker>
                </defs>

                {/* Edges */}
                {positionedEdges.map(edge => {
                  const isHighlighted =
                    selectedNode &&
                    (edge.source === selectedNode.name || edge.target === selectedNode.name)
                  const isDimmed = selectedNode && !isHighlighted
                  const midX = (edge.x1 + edge.x2) / 2
                  const midY = (edge.y1 + edge.y2) / 2

                  return (
                    <g key={edge.id} style={{ opacity: isDimmed ? 0.2 : 1 }}>
                      <line
                        x1={edge.x1}
                        y1={edge.y1}
                        x2={edge.x2}
                        y2={edge.y2}
                        stroke={isHighlighted ? '#fbbf24' : 'rgba(52, 211, 153, 0.35)'}
                        strokeWidth={isHighlighted ? 2.2 : 1.3}
                        markerEnd={isHighlighted ? 'url(#arrow-active)' : 'url(#arrow-default)'}
                      />
                      {isHighlighted && (
                        <text
                          x={midX}
                          y={midY - 5}
                          textAnchor="middle"
                          className={styles.edgeLabel}
                        >
                          {edge.relation_type}
                        </text>
                      )}
                    </g>
                  )
                })}

                {/* Nodes */}
                {positionedNodes.map(node => {
                  const style = getTypeStyle(node.entity_type)
                  const isSelected = selectedNode?.name === node.name
                  const isConnected =
                    selectedNode &&
                    positionedEdges.some(
                      e =>
                        (e.source === selectedNode.name && e.target === node.name) ||
                        (e.target === selectedNode.name && e.source === node.name)
                    )
                  const isDimmed = selectedNode && !isSelected && !isConnected
                  const radius = isSelected ? 18 : Math.min(16, 11 + Math.sqrt(node.degree || 1) * 1.4)

                  return (
                    <g
                      key={node.id || node.name}
                      transform={`translate(${node.x}, ${node.y})`}
                      className={styles.svgNode}
                      style={{ opacity: isDimmed ? 0.3 : 1 }}
                      onClick={() =>
                        setSelectedNode(prev => (prev?.name === node.name ? null : node))
                      }
                    >
                      {isSelected && (
                        <circle
                          r={radius + 6}
                          fill="none"
                          stroke={style.dot}
                          strokeWidth="2"
                          strokeDasharray="3 2"
                        />
                      )}
                      <circle
                        r={radius}
                        fill={style.bg}
                        stroke={style.dot}
                        strokeWidth={isSelected ? 2.8 : 2}
                      />
                      <circle r={4} fill={style.dot} />
                      <text
                        y={radius + 14}
                        textAnchor="middle"
                        className={`${styles.nodeLabel} ${isSelected ? styles.nodeLabelActive : ''}`}
                      >
                        {node.name.length > 20 ? `${node.name.slice(0, 18)}…` : node.name}
                      </text>
                    </g>
                  )
                })}
              </svg>
            </div>
          </div>

          {/* Entity & Relationship Lists */}
          <div className={styles.detailsColumn}>
            {selectedNode && (
              <div className={`glass-card ${styles.selectedCard}`}>
                <div className={styles.selectedHeader}>
                  <div>
                    <span
                      className={styles.entityBadge}
                      style={{
                        background: getTypeStyle(selectedNode.entity_type).bg,
                        color: getTypeStyle(selectedNode.entity_type).text,
                        borderColor: getTypeStyle(selectedNode.entity_type).border,
                      }}
                    >
                      {selectedNode.entity_type || 'Concept'}
                    </span>
                    <h3 className={styles.selectedName}>{selectedNode.name}</h3>
                  </div>
                  <button
                    className="btn btn-ghost btn-sm"
                    onClick={() => setSelectedNode(null)}
                  >
                    <X size={14} /> Clear
                  </button>
                </div>
                {selectedNode.description && (
                  <p className={styles.selectedDesc}>{selectedNode.description}</p>
                )}
              </div>
            )}

            {/* Relationships Card */}
            <div className={`glass-card ${styles.listCard}`}>
              <div className={styles.listHeader}>
                <h3 className={styles.listTitle}>
                  {selectedNode
                    ? `Relationships for "${selectedNode.name}"`
                    : 'Extracted Relationship Facts'}
                </h3>
                <span className="badge badge-teal">{filteredEdges.length} triples</span>
              </div>

              {filteredEdges.length === 0 ? (
                <p className={styles.emptyList}>No matching relationships found.</p>
              ) : (
                <div className={styles.relList}>
                  {filteredEdges.slice(0, 25).map((rel, idx) => (
                    <div key={idx} className={styles.relItem}>
                      <div className={styles.relTriple}>
                        <span
                          className={styles.relEntity}
                          onClick={() => {
                            const found = graphData.nodes.find(n => n.name === rel.source)
                            if (found) setSelectedNode(found)
                          }}
                        >
                          {rel.source}
                        </span>
                        <span className={styles.relBadge}>
                          {rel.relation_type} <ArrowRight size={11} />
                        </span>
                        <span
                          className={styles.relEntity}
                          onClick={() => {
                            const found = graphData.nodes.find(n => n.name === rel.target)
                            if (found) setSelectedNode(found)
                          }}
                        >
                          {rel.target}
                        </span>
                      </div>
                      {rel.fact && <p className={styles.relFact}>{rel.fact}</p>}
                      {rel.filename && (
                        <div className={styles.relSource}>
                          <FileText size={11} /> {rel.filename}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
