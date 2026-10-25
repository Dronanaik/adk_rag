import type { GraphEdgeItem, GraphNodeItem } from "../../types/api";

export interface SubgraphCanvasProps {
  nodes: GraphNodeItem[];
  edges: GraphEdgeItem[];
  selectedNodeId: string;
  maxHops: number;
  onSelectNode: (node: GraphNodeItem) => void;
}

interface NodeCoordinate {
  node: GraphNodeItem;
  x: number;
  y: number;
}

function computeRadialLayout(
  nodes: GraphNodeItem[],
  selectedNodeId: string,
): NodeCoordinate[] {
  const centerX = 320;
  const centerY = 130;
  const radius = 90;
  const centerNode = nodes.find((n) => n.id === selectedNodeId) ?? nodes[0];
  const outerNodes = nodes.filter((n) => n.id !== centerNode?.id);

  const coords: NodeCoordinate[] = [];
  if (centerNode) {
    coords.push({ node: centerNode, x: centerX, y: centerY });
  }

  outerNodes.forEach((node, idx) => {
    const angle = (2 * Math.PI * idx) / Math.max(outerNodes.length, 1);
    coords.push({
      node,
      x: Math.round(centerX + radius * Math.cos(angle)),
      y: Math.round(centerY + radius * Math.sin(angle)),
    });
  });

  return coords;
}

export function SubgraphCanvas({
  nodes,
  edges,
  selectedNodeId,
  maxHops,
  onSelectNode,
}: SubgraphCanvasProps) {
  const coords = computeRadialLayout(nodes, selectedNodeId);
  const coordById = new Map<string, NodeCoordinate>(
    coords.map((item) => [item.node.id, item]),
  );

  return (
    <section
      aria-label="Interactive Subgraph Canvas"
      className="flex flex-col gap-2"
      style={{
        padding: "var(--space-4)",
        borderRadius: "var(--radius-lg)",
        backgroundColor: "var(--bg-surface)",
        border: "1px solid var(--border-subtle)",
        boxShadow: "var(--shadow-sm)",
      }}
    >
      <div className="flex items-center justify-between">
        <span
          style={{
            fontSize: "var(--text-xs)",
            fontWeight: 600,
            color: "var(--provenance-kg-fg)",
          }}
        >
          2D Ego-Network Topology ({String(maxHops)}-Hop Bounded Traversal)
        </span>
        <span
          className="font-mono-tabular"
          style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)" }}
        >
          Nodes: {String(nodes.length)} · Edges: {String(edges.length)}
        </span>
      </div>

      <svg
        viewBox="0 0 640 260"
        role="img"
        aria-label="Knowledge graph node-link diagram"
        style={{
          width: "100%",
          height: "240px",
          borderRadius: "var(--radius-md)",
          backgroundColor: "var(--bg-canvas)",
          border: "1px solid var(--border-subtle)",
        }}
      >
        {edges.map((edge) => {
          const src = coordById.get(edge.source_node_id);
          const dst = coordById.get(edge.target_node_id);
          if (!src || !dst) return null;
          const midX = (src.x + dst.x) / 2;
          const midY = (src.y + dst.y) / 2 - 8;
          return (
            <g key={edge.id}>
              <line
                x1={src.x}
                y1={src.y}
                x2={dst.x}
                y2={dst.y}
                stroke="var(--provenance-kg-border)"
                strokeWidth="2"
              />
              <text
                x={midX}
                y={midY}
                textAnchor="middle"
                fill="var(--provenance-kg-fg)"
                fontSize="10"
              >
                {edge.relation_type}
              </text>
            </g>
          );
        })}

        {coords.map(({ node, x, y }) => {
          const isCenter = node.id === selectedNodeId;
          return (
            <g
              key={node.id}
              onClick={() => onSelectNode(node)}
              style={{ cursor: "pointer" }}
            >
              <circle
                cx={x}
                cy={y}
                r={isCenter ? 22 : 16}
                fill={
                  isCenter
                    ? "var(--provenance-kg-fg)"
                    : "var(--provenance-kg-bg)"
                }
                stroke="var(--provenance-kg-border)"
                strokeWidth="2"
              />
              <text
                x={x}
                y={y + 34}
                textAnchor="middle"
                fill="var(--text-primary)"
                fontSize="11"
                fontWeight={isCenter ? "700" : "500"}
              >
                {node.canonical_name}
              </text>
            </g>
          );
        })}
      </svg>
    </section>
  );
}

