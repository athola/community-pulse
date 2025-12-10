import { useCallback, useRef, useEffect, useState } from 'react';
import { View, StyleSheet, Platform, Text } from 'react-native';

// Only import on web
let ForceGraph2D: any = null;
if (Platform.OS === 'web') {
  ForceGraph2D = require('react-force-graph-2d').default;
}

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
  low: '#3b5068',
  mid: '#0d9488',
  high: '#22d3ee',
  text: '#e2e8f0',
  edge: '#2d3748',
};

function getNodeColor(pulseScore: number): string {
  if (pulseScore < 0.4) return colors.low;
  if (pulseScore < 0.7) return colors.mid;
  return colors.high;
}

export function FlowGraph({ nodes, edges, onNodeClick }: FlowGraphProps) {
  const graphRef = useRef<any>();
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });

  useEffect(() => {
    if (Platform.OS === 'web' && typeof window !== 'undefined') {
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

  if (Platform.OS !== 'web' || !ForceGraph2D) {
    return (
      <View style={styles.fallback}>
        <Text style={styles.fallbackText}>
          Graph visualization available on web only
        </Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <ForceGraph2D
        ref={graphRef}
        graphData={graphData}
        nodeLabel="label"
        nodeColor={(node: any) => getNodeColor(node.pulse_score)}
        nodeVal={(node: any) => node.val}
        linkColor={() => colors.edge}
        linkWidth={(link: any) => 0.5 + link.value}
        backgroundColor="#0f1419"
        onNodeClick={handleNodeClick}
        width={dimensions.width}
        height={dimensions.height}
        cooldownTicks={100}
        d3VelocityDecay={0.3}
      />
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
});
