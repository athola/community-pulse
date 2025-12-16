import { useQuery } from '@tanstack/react-query';

const API_URL = process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8001';

export interface TopicNode {
  id: string;
  slug: string;
  label: string;
  pulse_score: number;
  velocity: number;
  centrality: number;
}

export interface TopicEdge {
  source: string;
  target: string;
  weight: number;
}

export interface GraphData {
  nodes: TopicNode[];
  edges: TopicEdge[];
}

async function fetchGraph(): Promise<GraphData> {
  const response = await fetch(`${API_URL}/pulse/graph`);
  if (!response.ok) {
    throw new Error('Failed to fetch graph data');
  }
  const data = await response.json();
  return {
    nodes: data.nodes,
    edges: data.edges,
  };
}

export function usePulseGraph() {
  return useQuery({
    queryKey: ['pulse-graph'],
    queryFn: fetchGraph,
    refetchInterval: 60000, // Refresh every minute
  });
}
