import React, { useState, useEffect } from 'react';
import {
  StyleSheet,
  Text,
  View,
  TextInput,
  TouchableOpacity,
  ScrollView,
  Alert,
  SafeAreaView,
  KeyboardAvoidingView,
  Platform
} from 'react-native';

import { getConfig, storeMemory, queryMemory } from './api';

export default function App() {
  const [memoryText, setMemoryText] = useState('');
  const [queryText, setQueryText] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [config, setConfig] = useState(null);
  const [configError, setConfigError] = useState(null);

  // Load configuration on app start
  useEffect(() => {
    try {
      const appConfig = getConfig();
      setConfig(appConfig);
      setConfigError(null);
    } catch (error) {
      setConfigError(error.message);
      setConfig(null);
    }
  }, []);

  const handleStore = async () => {
    if (!memoryText.trim()) {
      Alert.alert('Error', 'Please enter some memory text');
      return;
    }

    setLoading(true);
    setResult(null);

    try {
      const response = await storeMemory(memoryText);
      setResult({
        action: 'Store',
        status: response.status,
        ok: response.ok,
        data: response.json
      });
      
      if (response.ok) {
        setMemoryText(''); // Clear input on success
      }
    } catch (error) {
      setResult({
        action: 'Store',
        status: 0,
        ok: false,
        data: { error: error.message }
      });
    } finally {
      setLoading(false);
    }
  };

  const handleQuery = async () => {
    if (!queryText.trim()) {
      Alert.alert('Error', 'Please enter a search query');
      return;
    }

    setLoading(true);
    setResult(null);

    try {
      const response = await queryMemory(queryText);
      setResult({
        action: 'Query',
        status: response.status,
        ok: response.ok,
        data: response.json
      });
    } catch (error) {
      setResult({
        action: 'Query',
        status: 0,
        ok: false,
        data: { error: error.message }
      });
    } finally {
      setLoading(false);
    }
  };

  const formatJson = (obj) => {
    try {
      return JSON.stringify(obj, null, 2);
    } catch {
      return String(obj);
    }
  };

  const getStatusColor = (status, ok) => {
    if (status === 0) return '#ff6b6b'; // Network error
    if (ok) return '#51cf66'; // Success
    return '#ff6b6b'; // HTTP error
  };

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView 
        style={styles.container} 
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      >
        <ScrollView style={styles.scrollView} contentContainerStyle={styles.scrollContent}>
          {/* Header */}
          <View style={styles.header}>
            <Text style={styles.title}>Marvin Memory Assistant</Text>
            
            {/* Configuration Status */}
            <View style={styles.configStatus}>
              {configError ? (
                <Text style={styles.configError}>⚠️ {configError}</Text>
              ) : (
                <View>
                  <Text style={styles.configText}>
                    📡 Server: {config?.baseUrl || 'Not set'}
                  </Text>
                  <Text style={styles.configText}>
                    🔑 API Key: {config?.apiKey ? `Set (${config.apiKey.length} chars)` : 'Not set'}
                  </Text>
                </View>
              )}
            </View>
          </View>

          {/* Store Section */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>💾 Store Memory</Text>
            <TextInput
              style={styles.textInput}
              placeholder="Enter memory text..."
              value={memoryText}
              onChangeText={setMemoryText}
              multiline
              numberOfLines={3}
              editable={!loading && !configError}
            />
            <TouchableOpacity
              style={[styles.button, (loading || configError) && styles.buttonDisabled]}
              onPress={handleStore}
              disabled={loading || configError}
            >
              <Text style={styles.buttonText}>
                {loading ? 'Storing...' : 'Store'}
              </Text>
            </TouchableOpacity>
          </View>

          {/* Query Section */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>🔍 Query Memories</Text>
            <TextInput
              style={styles.textInput}
              placeholder="Enter search query..."
              value={queryText}
              onChangeText={setQueryText}
              editable={!loading && !configError}
            />
            <TouchableOpacity
              style={[styles.button, (loading || configError) && styles.buttonDisabled]}
              onPress={handleQuery}
              disabled={loading || configError}
            >
              <Text style={styles.buttonText}>
                {loading ? 'Searching...' : 'Query'}
              </Text>
            </TouchableOpacity>
          </View>

          {/* Results Section */}
          {result && (
            <View style={styles.section}>
              <Text style={styles.sectionTitle}>📋 Last Result</Text>
              <View style={styles.resultHeader}>
                <Text style={styles.resultAction}>{result.action}</Text>
                <Text style={[styles.resultStatus, { color: getStatusColor(result.status, result.ok) }]}>
                  {result.status} {result.ok ? '✅' : '❌'}
                </Text>
              </View>
              <ScrollView style={styles.resultContainer} horizontal>
                <Text style={styles.resultText}>
                  {formatJson(result.data)}
                </Text>
              </ScrollView>
            </View>
          )}
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    padding: 20,
  },
  header: {
    marginBottom: 30,
    alignItems: 'center',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 15,
  },
  configStatus: {
    backgroundColor: '#fff',
    padding: 10,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#ddd',
    width: '100%',
  },
  configText: {
    fontSize: 12,
    color: '#666',
    marginBottom: 3,
  },
  configError: {
    fontSize: 12,
    color: '#ff6b6b',
    textAlign: 'center',
  },
  section: {
    backgroundColor: '#fff',
    borderRadius: 10,
    padding: 15,
    marginBottom: 20,
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.1,
    shadowRadius: 3.84,
    elevation: 5,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
    marginBottom: 15,
  },
  textInput: {
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 8,
    padding: 12,
    fontSize: 16,
    backgroundColor: '#fff',
    marginBottom: 15,
    minHeight: 44,
  },
  button: {
    backgroundColor: '#007AFF',
    borderRadius: 8,
    padding: 15,
    alignItems: 'center',
  },
  buttonDisabled: {
    backgroundColor: '#ccc',
  },
  buttonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  resultHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10,
  },
  resultAction: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
  },
  resultStatus: {
    fontSize: 14,
    fontWeight: '600',
  },
  resultContainer: {
    backgroundColor: '#f8f8f8',
    borderRadius: 8,
    padding: 12,
    maxHeight: 300,
  },
  resultText: {
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    fontSize: 12,
    color: '#333',
    lineHeight: 16,
  },
});