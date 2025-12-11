import { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ActivityIndicator,
  Pressable,
  ScrollView,
  useWindowDimensions,
  Linking,
  Platform,
} from 'react-native';
import { useQuery } from '@tanstack/react-query';
import { FlowGraph } from '../components/FlowGraph';
import { usePulseGraph } from '../hooks/usePulseGraph';

const API_URL = process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8000';

interface SamplePost {
  id: string;
  title: string;
  url: string;
  score: number;
  comment_count: number;
}

interface TopicNode {
  id: string;
  slug: string;
  label: string;
  pulse_score: number;
  velocity: number;
  mention_count: number;
  unique_authors: number;
  sample_posts: SamplePost[];
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

  // Only block on pulse data - graph can load independently
  if (pulseQuery.isLoading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#22d3ee" />
        <Text style={styles.loadingText}>Loading pulse...</Text>
      </View>
    );
  }

  if (pulseQuery.error) {
    return (
      <View style={styles.center}>
        <Text style={styles.errorText}>Failed to load pulse data</Text>
        <Text style={styles.errorDetail}>{String(pulseQuery.error)}</Text>
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
                <View style={styles.cardHeader}>
                  <Text style={styles.topicLabel}>{topic.label}</Text>
                  <Text style={styles.authorCount}>
                    {topic.unique_authors} people discussing
                  </Text>
                </View>
                <View style={styles.metrics}>
                  <View>
                    <Text style={styles.score}>
                      {Math.round(topic.pulse_score * 100)}
                    </Text>
                    <Text style={styles.scoreLabel}>pulse</Text>
                  </View>
                  <Text style={styles.velocity}>
                    {topic.velocity > 1.2 ? '🔥' : topic.velocity > 1 ? '↑' : '→'}
                    {topic.velocity > 1.2 ? ' Growing fast' : ` ${((topic.velocity - 1) * 100).toFixed(0)}%`}
                  </Text>
                </View>
                {/* Sample posts - join the conversation */}
                {topic.sample_posts && topic.sample_posts.length > 0 && (
                  <View style={styles.postsSection}>
                    <Text style={styles.postsHeader}>Join the conversation:</Text>
                    {topic.sample_posts.slice(0, 2).map((post) => (
                      <Pressable
                        key={post.id}
                        style={styles.postLink}
                        onPress={() => {
                          if (Platform.OS === 'web') {
                            window.open(post.url, '_blank');
                          } else {
                            Linking.openURL(post.url);
                          }
                        }}
                      >
                        <Text style={styles.postTitle} numberOfLines={1}>
                          {post.title}
                        </Text>
                        <Text style={styles.postMeta}>
                          ▲ {post.score} · {post.comment_count} comments
                        </Text>
                      </Pressable>
                    ))}
                  </View>
                )}
              </View>
            ))}
          </View>
        </ScrollView>
      ) : graphQuery.isLoading ? (
        <View style={styles.center}>
          <ActivityIndicator size="large" color="#22d3ee" />
          <Text style={styles.loadingText}>Loading graph...</Text>
        </View>
      ) : graphQuery.data ? (
        <FlowGraph
          nodes={graphQuery.data.nodes}
          edges={graphQuery.data.edges}
          onNodeClick={(node) => console.log('Clicked:', node.label)}
        />
      ) : (
        <View style={styles.center}>
          <Text style={styles.errorText}>No graph data available</Text>
        </View>
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
  cardHeader: {
    marginBottom: 12,
  },
  topicLabel: {
    fontSize: 18,
    fontWeight: '700',
    color: '#e2e8f0',
    marginBottom: 4,
  },
  authorCount: {
    fontSize: 12,
    color: '#64748b',
  },
  metrics: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  score: {
    fontSize: 32,
    fontWeight: '700',
    color: '#22d3ee',
  },
  scoreLabel: {
    fontSize: 10,
    color: '#64748b',
    textTransform: 'uppercase',
    letterSpacing: 1,
  },
  velocity: {
    fontSize: 14,
    color: '#4ade80',
    fontWeight: '600',
  },
  postsSection: {
    borderTopWidth: 1,
    borderTopColor: '#2d3748',
    paddingTop: 12,
  },
  postsHeader: {
    fontSize: 11,
    color: '#64748b',
    textTransform: 'uppercase',
    letterSpacing: 1,
    marginBottom: 8,
  },
  postLink: {
    backgroundColor: '#0f1419',
    borderRadius: 8,
    padding: 10,
    marginBottom: 6,
  },
  postTitle: {
    fontSize: 13,
    color: '#22d3ee',
    marginBottom: 4,
  },
  postMeta: {
    fontSize: 11,
    color: '#64748b',
  },
});
