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
import { TopicCard } from '../components/TopicCard';
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

// Sub-components for better modularity
function LoadingState({ message }: { message: string }) {
  return (
    <View style={styles.center}>
      <ActivityIndicator size="large" color="#22d3ee" />
      <Text style={styles.loadingText}>{message}</Text>
    </View>
  );
}

function ErrorState({ message, detail }: { message: string; detail?: string }) {
  return (
    <View style={styles.center}>
      <Text style={styles.errorText}>{message}</Text>
      {detail && <Text style={styles.errorDetail}>{detail}</Text>}
    </View>
  );
}

function ViewToggle({
  view,
  onViewChange,
}: {
  view: ViewType;
  onViewChange: (v: ViewType) => void;
}) {
  return (
    <View style={styles.toggleContainer}>
      <Pressable
        style={[styles.toggleBtn, view === 'cards' && styles.toggleActive]}
        onPress={() => onViewChange('cards')}
      >
        <Text
          style={[styles.toggleText, view === 'cards' && styles.toggleTextActive]}
        >
          Cards
        </Text>
      </Pressable>
      <Pressable
        style={[styles.toggleBtn, view === 'graph' && styles.toggleActive]}
        onPress={() => onViewChange('graph')}
      >
        <Text
          style={[styles.toggleText, view === 'graph' && styles.toggleTextActive]}
        >
          Graph
        </Text>
      </Pressable>
    </View>
  );
}

function CardsView({ topics }: { topics: TopicNode[] }) {
  return (
    <ScrollView style={styles.scrollView}>
      <View style={styles.topicList}>
        {topics.map((topic) => (
          <TopicCard key={topic.id} topic={topic} />
        ))}
      </View>
    </ScrollView>
  );
}

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

  if (pulseQuery.isLoading) {
    return <LoadingState message="Loading pulse..." />;
  }

  if (pulseQuery.error) {
    return (
      <ErrorState
        message="Failed to load pulse data"
        detail={String(pulseQuery.error)}
      />
    );
  }

  const renderContent = () => {
    if (view === 'cards') {
      return <CardsView topics={pulseQuery.data?.topics || []} />;
    }

    if (graphQuery.isLoading) {
      return <LoadingState message="Loading graph..." />;
    }

    if (graphQuery.data) {
      return (
        <FlowGraph
          nodes={graphQuery.data.nodes}
          edges={graphQuery.data.edges}
          onNodeClick={(node) => console.log('Clicked:', node.label)}
        />
      );
    }

    return <ErrorState message="No graph data available" />;
  };

  return (
    <View style={styles.container}>
      <ViewToggle view={view} onViewChange={setView} />
      {renderContent()}
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
});
