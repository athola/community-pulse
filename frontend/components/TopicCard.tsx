import {
  View,
  Text,
  StyleSheet,
  Pressable,
  Linking,
  Platform,
} from 'react-native';

// Web-only tooltip wrapper using native title attribute
function Tooltip({ text, children }: { text: string; children: React.ReactNode }) {
  if (Platform.OS === 'web') {
    // Use native DOM span with title attribute for browser tooltips
    return (
      <span title={text} style={{ cursor: 'help' }}>
        {children}
      </span>
    );
  }
  return <>{children}</>;
}

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
  velocity: number;  // Relative popularity (vs other topics)
  temporal_velocity?: number | null;  // True velocity (vs historical baseline)
  mention_count: number;
  unique_authors: number;
  sample_posts: SamplePost[];
}

interface TopicCardProps {
  topic: TopicNode;
}

export function TopicCard({ topic }: TopicCardProps) {
  const openPost = (url: string) => {
    if (Platform.OS === 'web') {
      window.open(url, '_blank');
    } else {
      Linking.openURL(url);
    }
  };

  // Relative popularity: compares this topic's mentions to average across all topics
  // >1 = above average, <1 = below average (NOT temporal growth/decline)
  const relativePopularity = (topic.velocity - 1) * 100;
  const isAboveAverage = relativePopularity > 0;
  const popularityIndicator = topic.velocity > 1.2
    ? '🔥 Hot topic'
    : `${isAboveAverage ? '▲' : '▼'} ${Math.abs(relativePopularity).toFixed(0)}%`;

  // True temporal velocity: compares to this topic's historical mentions
  // Only available after first snapshot is recorded
  const hasTemporalData = topic.temporal_velocity != null;
  const temporalChange = hasTemporalData ? (topic.temporal_velocity! - 1) * 100 : 0;
  const isGrowing = temporalChange > 0;
  const isStable = Math.abs(temporalChange) < 5; // Less than 5% change = stable
  const temporalIndicator = hasTemporalData
    ? topic.temporal_velocity! > 1.5
      ? '📈 Surging'
      : isStable
        ? '— Stable'
        : `${isGrowing ? '▲' : '▼'} ${Math.abs(temporalChange).toFixed(0)}%`
    : '⏳ Tracking';

  return (
    <View style={styles.card}>
      <View style={styles.header}>
        <Text style={styles.label}>{topic.label}</Text>
        <Text style={styles.authorCount}>
          {topic.unique_authors} people discussing
        </Text>
      </View>

      <View style={styles.metrics}>
        <Tooltip text="Pulse Score: Combines velocity, network centrality, and author diversity to measure emerging trend strength (0-100)">
          <View>
            <Text style={styles.score}>
              {Math.round(topic.pulse_score * 100)}
            </Text>
            <Text style={styles.scoreLabel}>pulse</Text>
          </View>
        </Tooltip>
        <View style={styles.indicators}>
          <Tooltip text={hasTemporalData
            ? isStable
              ? 'Velocity: Stable - no significant change since last hourly snapshot.'
              : `Velocity: ${isGrowing ? 'Growing' : 'Declining'} ${Math.abs(temporalChange).toFixed(0)}% vs previous hourly snapshot. Snapshots are taken every hour for 24-hour trend tracking.`
            : 'Velocity: Tracking started. Snapshots are taken hourly - check back in an hour for growth trends.'
          }>
            <Text style={[
              styles.temporal,
              hasTemporalData && !isGrowing && !isStable && styles.temporalDown,
              hasTemporalData && isStable && styles.temporalStable,
              !hasTemporalData && styles.temporalPending,
            ]}>
              {temporalIndicator}
            </Text>
          </Tooltip>
          <Tooltip text={`Popularity: ${isAboveAverage ? 'Above' : 'Below'} the average mentions per topic by ${Math.abs(relativePopularity).toFixed(0)}%.`}>
            <Text style={[styles.popularity, !isAboveAverage && styles.popularityBelow]}>
              {popularityIndicator}
            </Text>
          </Tooltip>
        </View>
      </View>

      {topic.sample_posts?.length > 0 && (
        <View style={styles.postsSection}>
          <Text style={styles.postsHeader}>Join the conversation:</Text>
          {topic.sample_posts.slice(0, 2).map((post) => (
            <Pressable
              key={post.id}
              style={styles.postLink}
              onPress={() => openPost(post.url)}
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
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#1a1f26',
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: '#2d3748',
  },
  header: {
    marginBottom: 12,
  },
  label: {
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
  indicators: {
    alignItems: 'flex-end',
    gap: 4,
  },
  temporal: {
    fontSize: 14,
    color: '#22d3ee',
    fontWeight: '600',
  },
  temporalDown: {
    color: '#f87171',
  },
  temporalStable: {
    color: '#94a3b8',
  },
  temporalPending: {
    color: '#64748b',
  },
  popularity: {
    fontSize: 12,
    color: '#4ade80',
    fontWeight: '500',
  },
  popularityBelow: {
    color: '#f97316',
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
