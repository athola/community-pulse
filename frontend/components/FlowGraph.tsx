import { useCallback, useRef, useEffect, useState } from 'react';
import { View, StyleSheet, Platform, Text, Pressable } from 'react-native';

// ForceGraph2D is loaded dynamically to avoid SSR issues
// The library accesses `window` immediately on import, which fails in Node.js

// Legend component for the graph
function GraphLegend({ expanded, onToggle }: { expanded: boolean; onToggle: () => void }) {
  return (
    <View style={legendStyles.container}>
      <Pressable style={legendStyles.toggle} onPress={onToggle}>
        <Text style={legendStyles.toggleText}>
          {expanded ? 'Hide Legend' : 'Legend'}
        </Text>
      </Pressable>

      {expanded && (
        <View style={legendStyles.content}>
          {/* Shapes Section */}
          <Text style={legendStyles.sectionTitle}>Shape = Velocity</Text>
          <View style={legendStyles.item}>
            <View style={[legendStyles.shapeCircle, { backgroundColor: '#94a3b8' }]} />
            <Text style={legendStyles.itemText}>Circle: Normal growth</Text>
          </View>
          <View style={legendStyles.item}>
            <View style={legendStyles.shapeDiamond} />
            <Text style={legendStyles.itemText}>Diamond: Fast growth (1.3x+)</Text>
          </View>
          <View style={legendStyles.item}>
            <View style={legendStyles.shapeHexagon} />
            <Text style={legendStyles.itemText}>Hexagon: Rapid growth (1.8x+)</Text>
          </View>

          {/* Colors Section */}
          <Text style={[legendStyles.sectionTitle, { marginTop: 12 }]}>Color = Pulse Score</Text>
          <View style={legendStyles.item}>
            <View style={[legendStyles.colorDot, { backgroundColor: '#6366f1' }]} />
            <Text style={legendStyles.itemText}>Indigo: Low (0-30)</Text>
          </View>
          <View style={legendStyles.item}>
            <View style={[legendStyles.colorDot, { backgroundColor: '#10b981' }]} />
            <Text style={legendStyles.itemText}>Emerald: Medium (30-50)</Text>
          </View>
          <View style={legendStyles.item}>
            <View style={[legendStyles.colorDot, { backgroundColor: '#f59e0b' }]} />
            <Text style={legendStyles.itemText}>Amber: High (50-75)</Text>
          </View>
          <View style={legendStyles.item}>
            <View style={[legendStyles.colorDot, { backgroundColor: '#ef4444' }]} />
            <Text style={legendStyles.itemText}>Red: Very Hot (75+)</Text>
          </View>

          {/* Effects Section */}
          <Text style={[legendStyles.sectionTitle, { marginTop: 12 }]}>Effects</Text>
          <View style={legendStyles.item}>
            <View style={legendStyles.glowIndicator} />
            <Text style={legendStyles.itemText}>Cyan glow: High velocity</Text>
          </View>
          <View style={legendStyles.item}>
            <View style={legendStyles.ringIndicator} />
            <Text style={legendStyles.itemText}>Purple ring: High centrality</Text>
          </View>
          <View style={legendStyles.item}>
            <View style={legendStyles.arrowIndicator} />
            <Text style={legendStyles.itemText}>Arrow: Growing topic</Text>
          </View>
        </View>
      )}
    </View>
  );
}

const legendStyles = StyleSheet.create({
  container: {
    marginTop: 8,
  },
  toggle: {
    backgroundColor: 'rgba(26, 31, 38, 0.9)',
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#2d3748',
    alignSelf: 'flex-end',
  },
  toggleText: {
    color: '#94a3b8',
    fontSize: 12,
    fontWeight: '600',
  },
  content: {
    backgroundColor: 'rgba(26, 31, 38, 0.95)',
    padding: 16,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#2d3748',
    marginTop: 8,
    minWidth: 220,
  },
  sectionTitle: {
    color: '#e2e8f0',
    fontSize: 11,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 1,
    marginBottom: 8,
  },
  item: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 6,
  },
  itemText: {
    color: '#94a3b8',
    fontSize: 11,
    marginLeft: 8,
  },
  shapeCircle: {
    width: 12,
    height: 12,
    borderRadius: 6,
  },
  shapeDiamond: {
    width: 12,
    height: 12,
    backgroundColor: '#94a3b8',
    transform: [{ rotate: '45deg' }],
  },
  shapeHexagon: {
    width: 14,
    height: 12,
    backgroundColor: '#94a3b8',
    borderRadius: 2,
  },
  colorDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
  },
  glowIndicator: {
    width: 12,
    height: 12,
    borderRadius: 6,
    backgroundColor: 'rgba(34, 211, 238, 0.3)',
    borderWidth: 2,
    borderColor: '#22d3ee',
  },
  ringIndicator: {
    width: 12,
    height: 12,
    borderRadius: 6,
    borderWidth: 2,
    borderColor: '#a855f7',
    borderStyle: 'dashed',
  },
  arrowIndicator: {
    width: 0,
    height: 0,
    borderLeftWidth: 6,
    borderRightWidth: 6,
    borderBottomWidth: 10,
    borderLeftColor: 'transparent',
    borderRightColor: 'transparent',
    borderBottomColor: '#e2e8f0',
  },
});

interface TopicNode {
  id: string;
  slug: string;
  label: string;
  pulse_score: number;
  velocity: number;
  centrality: number;
}

interface TopicEdge {
  source: string;
  target: string;
  weight: number;
}

interface FlowGraphProps {
  nodes: TopicNode[];
  edges: TopicEdge[];
  onNodeClick?: (node: TopicNode) => void;
}

const colors = {
  // Pulse score tiers - more distinct color palette
  low: '#6366f1',      // Indigo - cool, quiet
  mid: '#10b981',      // Emerald - moderate activity
  high: '#f59e0b',     // Amber - hot, trending
  hot: '#ef4444',      // Red - very hot

  // Accents
  text: '#e2e8f0',
  edge: '#2d3748',
  glow: '#22d3ee',     // Cyan glow for high velocity
  ring: '#a855f7',     // Purple ring for high centrality
};

function getNodeColor(pulseScore: number): string {
  if (pulseScore < 0.3) return colors.low;
  if (pulseScore < 0.5) return colors.mid;
  if (pulseScore < 0.75) return colors.high;
  return colors.hot;
}

// Get velocity indicator style
function getVelocityStyle(velocity: number): { shape: 'circle' | 'hexagon' | 'diamond'; glow: boolean } {
  if (velocity > 1.8) return { shape: 'hexagon', glow: true };
  if (velocity > 1.3) return { shape: 'diamond', glow: true };
  return { shape: 'circle', glow: false };
}

// Draw hexagon shape
function drawHexagon(ctx: CanvasRenderingContext2D, x: number, y: number, size: number) {
  const sides = 6;
  ctx.beginPath();
  for (let i = 0; i < sides; i++) {
    const angle = (i * 2 * Math.PI) / sides - Math.PI / 2;
    const px = x + size * Math.cos(angle);
    const py = y + size * Math.sin(angle);
    if (i === 0) ctx.moveTo(px, py);
    else ctx.lineTo(px, py);
  }
  ctx.closePath();
}

// Draw diamond shape
function drawDiamond(ctx: CanvasRenderingContext2D, x: number, y: number, size: number) {
  ctx.beginPath();
  ctx.moveTo(x, y - size);
  ctx.lineTo(x + size, y);
  ctx.lineTo(x, y + size);
  ctx.lineTo(x - size, y);
  ctx.closePath();
}

// Custom node renderer
function renderNode(node: any, ctx: CanvasRenderingContext2D, globalScale: number) {
  const size = Math.sqrt(node.val) * 2;
  const color = getNodeColor(node.pulse_score);
  const { shape, glow } = getVelocityStyle(node.velocity);
  const hasHighCentrality = node.centrality > 0.5;

  // Glow effect for high-velocity nodes
  if (glow) {
    ctx.save();
    ctx.shadowColor = colors.glow;
    ctx.shadowBlur = 15;
    ctx.beginPath();
    ctx.arc(node.x, node.y, size + 3, 0, 2 * Math.PI);
    ctx.fillStyle = 'rgba(34, 211, 238, 0.15)';
    ctx.fill();
    ctx.restore();
  }

  // Centrality ring (dashed outer ring for well-connected nodes)
  if (hasHighCentrality) {
    ctx.save();
    ctx.strokeStyle = colors.ring;
    ctx.lineWidth = 2;
    ctx.setLineDash([3, 3]);
    ctx.beginPath();
    ctx.arc(node.x, node.y, size + 6, 0, 2 * Math.PI);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.restore();
  }

  // Main node shape
  ctx.fillStyle = color;
  ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
  ctx.lineWidth = 1.5;

  if (shape === 'hexagon') {
    drawHexagon(ctx, node.x, node.y, size);
  } else if (shape === 'diamond') {
    drawDiamond(ctx, node.x, node.y, size);
  } else {
    ctx.beginPath();
    ctx.arc(node.x, node.y, size, 0, 2 * Math.PI);
  }

  ctx.fill();
  ctx.stroke();

  // Inner highlight for depth
  ctx.fillStyle = 'rgba(255, 255, 255, 0.15)';
  ctx.beginPath();
  ctx.arc(node.x - size * 0.3, node.y - size * 0.3, size * 0.4, 0, 2 * Math.PI);
  ctx.fill();

  // Velocity arrow indicator (small upward arrow for growing topics)
  if (node.velocity > 1.1) {
    const arrowSize = Math.min(size * 0.4, 6);
    ctx.fillStyle = colors.text;
    ctx.beginPath();
    ctx.moveTo(node.x, node.y - arrowSize);
    ctx.lineTo(node.x - arrowSize * 0.6, node.y + arrowSize * 0.3);
    ctx.lineTo(node.x + arrowSize * 0.6, node.y + arrowSize * 0.3);
    ctx.closePath();
    ctx.fill();
  }

  // Label (only at sufficient zoom)
  if (globalScale > 0.7) {
    const fontSize = Math.max(10, 12 / globalScale);
    ctx.font = `600 ${fontSize}px -apple-system, BlinkMacSystemFont, sans-serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';
    ctx.fillStyle = colors.text;
    ctx.fillText(node.label, node.x, node.y + size + 4);
  }
}

export function FlowGraph({ nodes, edges, onNodeClick }: FlowGraphProps) {
  const graphRef = useRef<any>();
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const [ForceGraph2D, setForceGraph2D] = useState<any>(null);
  const [legendExpanded, setLegendExpanded] = useState(false);

  // Dynamically import ForceGraph2D only in browser environment
  useEffect(() => {
    if (typeof window !== 'undefined') {
      import('react-force-graph-2d').then((module) => {
        setForceGraph2D(() => module.default);
      });
    }
  }, []);

  // Configure force simulation for better node separation (but not too spread out)
  useEffect(() => {
    if (graphRef.current && typeof window !== 'undefined') {
      // Moderate repulsion - enough to see nodes but keeps graph cohesive
      graphRef.current.d3Force('charge').strength(-150);
      // Moderate link distance
      graphRef.current.d3Force('link').distance(80);
      // Add collision detection to prevent node overlap
      import('d3-force').then((d3) => {
        if (graphRef.current) {
          graphRef.current.d3Force('collision', d3.forceCollide().radius(30));
          // Add centering force to keep disconnected nodes closer
          graphRef.current.d3Force('center', d3.forceCenter(dimensions.width / 2, dimensions.height / 2));
        }
      });
    }
  }, [ForceGraph2D, nodes, dimensions]);

  // Recenter the graph view
  const handleRecenter = useCallback(() => {
    if (graphRef.current) {
      graphRef.current.zoomToFit(400, 60);
    }
  }, []);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const updateDimensions = () => {
        setDimensions({
          width: window.innerWidth,
          height: window.innerHeight - 100,
        });
      };
      updateDimensions();
      window.addEventListener('resize', updateDimensions);
      return () => window.removeEventListener('resize', updateDimensions);
    }
  }, []);

  const graphData = {
    nodes: nodes.map((n) => ({
      ...n,
      val: 4 + n.pulse_score * 16, // Node size
    })),
    links: edges.map((e) => ({
      source: e.source,
      target: e.target,
      value: e.weight,
    })),
  };

  const handleNodeClick = useCallback(
    (node: any) => {
      if (onNodeClick) {
        onNodeClick(node);
      }
    },
    [onNodeClick]
  );

  if (Platform.OS !== 'web') {
    return (
      <View style={styles.fallback}>
        <Text style={styles.fallbackText}>
          Graph visualization available on web only
        </Text>
      </View>
    );
  }

  if (!ForceGraph2D) {
    return (
      <View style={styles.fallback}>
        <Text style={styles.fallbackText}>Loading graph...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <ForceGraph2D
        ref={graphRef}
        graphData={graphData}
        nodeCanvasObject={renderNode}
        nodePointerAreaPaint={(node: any, color: string, ctx: CanvasRenderingContext2D) => {
          // Expand clickable area slightly
          const size = Math.sqrt(node.val) * 2.5;
          ctx.fillStyle = color;
          ctx.beginPath();
          ctx.arc(node.x, node.y, size, 0, 2 * Math.PI);
          ctx.fill();
        }}
        linkColor={() => colors.edge}
        linkWidth={(link: any) => 0.5 + link.value * 0.5}
        linkDirectionalParticles={2}
        linkDirectionalParticleWidth={2}
        linkDirectionalParticleColor={() => colors.glow}
        backgroundColor="#0f1419"
        onNodeClick={handleNodeClick}
        width={dimensions.width}
        height={dimensions.height}
        cooldownTicks={200}
        d3VelocityDecay={0.2}
        d3AlphaDecay={0.01}
        warmupTicks={50}
      />
      {/* Controls overlay */}
      <View style={styles.controlsContainer}>
        <Pressable style={styles.recenterBtn} onPress={handleRecenter}>
          <Text style={styles.recenterText}>Recenter</Text>
        </Pressable>
        <GraphLegend
          expanded={legendExpanded}
          onToggle={() => setLegendExpanded(!legendExpanded)}
        />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  fallback: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#0f1419',
  },
  fallbackText: {
    color: '#94a3b8',
  },
  controlsContainer: {
    position: 'absolute',
    bottom: 16,
    right: 16,
    zIndex: 100,
    alignItems: 'flex-end',
  },
  recenterBtn: {
    backgroundColor: 'rgba(26, 31, 38, 0.9)',
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#2d3748',
  },
  recenterText: {
    color: '#94a3b8',
    fontSize: 12,
    fontWeight: '600',
  },
});
