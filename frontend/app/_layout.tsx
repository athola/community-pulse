import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { Platform, View, StyleSheet } from 'react-native';
import { ClientOnly } from '../components/ClientOnly';

const queryClient = new QueryClient();

function NavigationStack() {
  return (
    <Stack
      screenOptions={{
        headerStyle: { backgroundColor: '#0f1419' },
        headerTintColor: '#e2e8f0',
        headerTitleStyle: { fontWeight: '600' },
        contentStyle: { backgroundColor: '#0f1419' },
      }}
    />
  );
}

export default function RootLayout() {
  const content = (
    <View style={styles.container}>
      <StatusBar style="light" />
      <NavigationStack />
    </View>
  );

  return (
    <QueryClientProvider client={queryClient}>
      {Platform.OS === 'web' ? (
        <ClientOnly fallback={<View style={styles.container} />}>
          {content}
        </ClientOnly>
      ) : (
        content
      )}
    </QueryClientProvider>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0f1419',
  },
});
