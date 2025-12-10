import { View, Text, StyleSheet, ActivityIndicator } from 'react-native';
import { useQuery } from '@tanstack/react-query';

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

export default function PulseScreen() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['pulse'],
    queryFn: fetchPulse,
    refetchInterval: 30000, // Refresh every 30s
  });

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
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Community Pulse</Text>
      <View style={styles.topicList}>
        {data?.topics.map((topic) => (
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
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 16,
    backgroundColor: '#0f1419',
  },
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#0f1419',
  },
  title: {
    fontSize: 24,
    fontWeight: '700',
    color: '#e2e8f0',
    marginBottom: 20,
  },
  loadingText: {
    color: '#94a3b8',
    marginTop: 12,
  },
  errorText: {
    color: '#f87171',
  },
  topicList: {
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
