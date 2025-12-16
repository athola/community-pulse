/**
 * API client for Community Pulse backend
 */

const API_URL = process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8001';

export interface TopicNode {
  id: string;
  slug: string;
  label: string;
  pulse_score: number;
  velocity: number;
  centrality: number;
  mention_count: number;
  unique_authors: number;
}

export interface TopicEdge {
  source: string;
  target: string;
  weight: number;
  shared_posts: number;
}

export interface ClusterInfo {
  id: string;
  topic_ids: string[];
  collective_velocity: number;
  size: number;
}

export interface PulseResponse {
  topics: TopicNode[];
  clusters: ClusterInfo[];
  snapshot_id: string;
  captured_at: string;
}

export interface GraphResponse {
  nodes: TopicNode[];
  edges: TopicEdge[];
  clusters: ClusterInfo[];
  captured_at: string;
}

/**
 * Fetch current pulse state
 */
export async function fetchPulse(
  limit: number = 20,
  minScore: number = 0.0
): Promise<PulseResponse> {
  const params = new URLSearchParams({
    limit: limit.toString(),
    min_score: minScore.toString(),
  });

  const response = await fetch(`${API_URL}/pulse/current?${params}`);
  if (!response.ok) {
    throw new Error('Failed to fetch pulse data');
  }

  return response.json();
}

/**
 * Fetch topic co-occurrence graph
 */
export async function fetchGraph(
  minEdgeWeight: number = 2
): Promise<GraphResponse> {
  const params = new URLSearchParams({
    min_edge_weight: minEdgeWeight.toString(),
  });

  const response = await fetch(`${API_URL}/pulse/graph?${params}`);
  if (!response.ok) {
    throw new Error('Failed to fetch graph data');
  }

  return response.json();
}

/**
 * Health check
 */
export async function healthCheck(): Promise<{ status: string }> {
  const response = await fetch(`${API_URL}/health`);
  if (!response.ok) {
    throw new Error('Health check failed');
  }

  return response.json();
}
