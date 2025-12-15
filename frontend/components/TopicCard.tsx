import {
  View,
  Text,
  StyleSheet,
  Pressable,
  Linking,
  Platform,
} from 'react-native';

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

  const velocityIndicator = topic.velocity > 1.2
    ? '🔥 Growing fast'
    : `↑ ${((topic.velocity - 1) * 100).toFixed(0)}%`;

  return (
    <View style={styles.card}>
      <View style={styles.header}>
        <Text style={styles.label}>{topic.label}</Text>
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
        <Text style={styles.velocity}>{velocityIndicator}</Text>
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
