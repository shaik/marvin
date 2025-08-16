import React, { useEffect, useMemo, useRef, useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, Platform } from 'react-native';
import { auto as autoDecide } from '../api';

export default function AutoScreen() {
  const [mainText, setMainText] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [followUp, setFollowUp] = useState('');
  const [followUpLoading, setFollowUpLoading] = useState(false);
  const [errorText, setErrorText] = useState('');

  const clarifyInputRef = useRef(null);

  const handleMainSubmit = async () => {
    if (!mainText.trim() || loading) return;
    setLoading(true);
    setErrorText('');
    try {
      const response = await autoDecide(mainText);
      setResult(response?.json || null);
      setFollowUp('');
      setMainText('');
    } finally {
      setLoading(false);
    }
  };

  const showClarify = result?.action === 'clarify';

  const clarifyQuestion = useMemo(() => {
    if (!showClarify) return '';
    return (
      result?.question ||
      result?.message ||
      result?.clarification ||
      ''
    );
  }, [result, showClarify]);

  useEffect(() => {
    if (showClarify && clarifyInputRef.current && typeof clarifyInputRef.current.focus === 'function') {
      try {
        clarifyInputRef.current.focus();
      } catch {}
    }
  }, [showClarify]);

  const followUpDisabled = !followUp.trim() || followUpLoading;

  const handleClarifySubmit = async () => {
    if (followUpDisabled) return;
    setFollowUpLoading(true);
    setErrorText('');
    try {
      const response = await autoDecide(followUp);
      if (response?.ok) {
        setResult(response.json || null);
        setFollowUp('');
      } else {
        if (response?.status === 401) {
          setErrorText('Missing/invalid API key');
        } else if (response?.status === 429) {
          setErrorText('Rate limit');
        } else {
          setErrorText('Server error');
        }
      }
    } catch (e) {
      setErrorText('Server error');
    } finally {
      setFollowUpLoading(false);
    }
  };

  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>Auto</Text>
      {!!errorText && (
        <Text style={styles.errorText}>{errorText}</Text>
      )}

      <TextInput
        value={mainText}
        onChangeText={setMainText}
        placeholder="מה תרצה לשמור או לשאול?"
        accessibilityLabel="main-input"
        style={styles.textInput}
        editable={!loading}
        onSubmitEditing={handleMainSubmit}
        returnKeyType="send"
      />
      <TouchableOpacity
        onPress={handleMainSubmit}
        disabled={loading || !mainText.trim()}
        accessibilityLabel="main-send"
        style={[styles.button, (loading || !mainText.trim()) && styles.buttonDisabled]}
      >
        <Text style={styles.buttonText}>{loading ? '…' : 'Send'}</Text>
      </TouchableOpacity>

      {showClarify && (
        <View style={styles.clarifyCard}>
          <Text style={styles.clarifyTitle}>שאלת הבהרה</Text>
          {!!clarifyQuestion && (
            <Text style={styles.clarifyQuestion}>{clarifyQuestion}</Text>
          )}
          <View style={styles.clarifyRow}>
            <TextInput
              ref={clarifyInputRef}
              value={followUp}
              onChangeText={setFollowUp}
              placeholder="ענה לשאלת הבהרה…"
              accessibilityLabel="clarify-input"
              style={[styles.textInput, styles.clarifyInput]}
              autoFocus
              returnKeyType="send"
              editable={!followUpLoading}
              onSubmitEditing={handleClarifySubmit}
            />
            <TouchableOpacity
              onPress={handleClarifySubmit}
              disabled={followUpDisabled}
              accessibilityLabel="clarify-send"
              style={[styles.smallButton, followUpDisabled && styles.buttonDisabled]}
            >
              <Text style={styles.buttonText}>{followUpLoading ? '…' : 'Send'}</Text>
            </TouchableOpacity>
          </View>
        </View>
      )}

      {result?.action === 'retrieve' && Array.isArray(result?.candidates) && (
        <View style={{ marginTop: 16 }}>
          {result.candidates.map((c, idx) => (
            <Text key={c.id || idx}>{c.text || String(c)}</Text>
          ))}
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  section: {
    backgroundColor: '#fff',
    borderRadius: 10,
    padding: 15,
    marginBottom: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
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
    paddingVertical: 12,
    paddingHorizontal: 16,
    alignItems: 'center',
    alignSelf: 'flex-start',
  },
  smallButton: {
    backgroundColor: '#007AFF',
    borderRadius: 8,
    paddingVertical: 10,
    paddingHorizontal: 12,
    alignItems: 'center',
    alignSelf: 'center',
    marginLeft: 8,
  },
  buttonDisabled: {
    backgroundColor: '#ccc',
  },
  buttonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  errorText: {
    color: '#b00020',
    marginBottom: 8,
  },
  clarifyCard: {
    marginTop: 20,
    backgroundColor: '#F7F9FC',
    borderRadius: 10,
    padding: 12,
    borderWidth: 1,
    borderColor: '#E6ECF5',
  },
  clarifyTitle: {
    fontSize: 14,
    fontWeight: '700',
    color: '#2E3A59',
    marginBottom: 8,
  },
  clarifyQuestion: {
    fontSize: 16,
    color: '#1F2937',
    marginBottom: 10,
  },
  clarifyRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  clarifyInput: {
    flex: 1,
    marginBottom: 0,
    fontFamily: Platform.OS === 'ios' ? 'System' : 'sans-serif',
  },
});


