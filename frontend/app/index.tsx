import { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ActivityIndicator,
  Pressable,
  ScrollView,
  useWindowDimensions,
} from 'react-native';
import { useQuery } from '@tanstack/react-query';
import { FlowGraph } from '../components/FlowGraph';
import { usePulseGraph } from '../hooks/usePulseGraph';

const API_URL = process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8000';

interface TopicNode {
  id: string;
  slug: string;
  label: string;
  pulse_score: number;
  velocity: number;
}

interface PulseResponse {
  topics: TopicNode[];
  snapshot_id: string;
  captured_at: string;
}

async function fetchPulse(): Promise<PulseResponse> {
  const response = await fetch(`${API_URL}/pulse/current`);
  if (!response.ok) {
    throw new Error('Failed to fetch pulse data');
  }
  return response.json();
}

type ViewType = 'cards' | 'graph';

export default function PulseScreen() {
  const { width } = useWindowDimensions();
  const isMobile = width < 768;

  const [view, setView] = useState<ViewType>(isMobile ? 'cards' : 'graph');

  const pulseQuery = useQuery({
    queryKey: ['pulse'],
    queryFn: fetchPulse,
    refetchInterval: 30000,
  });

  const graphQuery = usePulseGraph();

  const isLoading = pulseQuery.isLoading || graphQuery.isLoading;
  const error = pulseQuery.error || graphQuery.error;

  if (isLoading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#22d3ee" />
        <Text style={styles.loadingText}>Loading pulse...</Text>
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.center}>
        <Text style={styles.errorText}>Failed to load pulse data</Text>
        <Text style={styles.errorDetail}>{String(error)}</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* View Toggle */}
      <View style={styles.toggleContainer}>
        <Pressable
          style={[styles.toggleBtn, view === 'cards' && styles.toggleActive]}
          onPress={() => setView('cards')}
        >
          <Text
            style={[
              styles.toggleText,
              view === 'cards' && styles.toggleTextActive,
            ]}
          >
            Cards
          </Text>
        </Pressable>
        <Pressable
          style={[styles.toggleBtn, view === 'graph' && styles.toggleActive]}
          onPress={() => setView('graph')}
        >
          <Text
            style={[
              styles.toggleText,
              view === 'graph' && styles.toggleTextActive,
            ]}
          >
            Graph
          </Text>
        </Pressable>
      </View>

      {/* Content */}
      {view === 'cards' ? (
        <ScrollView style={styles.scrollView}>
          <View style={styles.topicList}>
            {pulseQuery.data?.topics.map((topic) => (
              <View key={topic.id} style={styles.topicCard}>
                <Text style={styles.topicLabel}>{topic.label}</Text>
                <View style={styles.metrics}>
                  <Text style={styles.score}>
                    {Math.round(topic.pulse_score * 100)}
                  </Text>
                  <Text style={styles.velocity}>
                    {topic.velocity > 1 ? '↑' : '→'}
                    {((topic.velocity - 1) * 100).toFixed(0)}%
                  </Text>
                </View>
              </View>
            ))}
          </View>
        </ScrollView>
      ) : (
        graphQuery.data && (
          <FlowGraph
            nodes={graphQuery.data.nodes}
            edges={graphQuery.data.edges}
            onNodeClick={(node) => console.log('Clicked:', node.label)}
          />
        )
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0f1419',
  },
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#0f1419',
  },
  loadingText: {
    color: '#94a3b8',
    marginTop: 12,
  },
  errorText: {
    color: '#f87171',
    fontSize: 16,
  },
  errorDetail: {
    color: '#94a3b8',
    fontSize: 12,
    marginTop: 8,
  },
  toggleContainer: {
    flexDirection: 'row',
    padding: 12,
    gap: 8,
  },
  toggleBtn: {
    paddingVertical: 8,
    paddingHorizontal: 16,
    borderRadius: 8,
    backgroundColor: '#1a1f26',
  },
  toggleActive: {
    backgroundColor: '#22d3ee',
  },
  toggleText: {
    color: '#94a3b8',
    fontWeight: '600',
  },
  toggleTextActive: {
    color: '#0f1419',
  },
  scrollView: {
    flex: 1,
  },
  topicList: {
    padding: 16,
    gap: 12,
  },
  topicCard: {
    backgroundColor: '#1a1f26',
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: '#2d3748',
  },
  topicLabel: {
    fontSize: 16,
    fontWeight: '600',
    color: '#e2e8f0',
    marginBottom: 8,
  },
  metrics: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  score: {
    fontSize: 28,
    fontWeight: '700',
    color: '#22d3ee',
  },
  velocity: {
    fontSize: 14,
    color: '#4ade80',
  },
});
