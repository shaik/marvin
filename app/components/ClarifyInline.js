import React, { useState } from 'react';
import { View, TextInput, TouchableOpacity, Text, StyleSheet } from 'react-native';

export default function ClarifyInline({ onSubmit, disabled }) {
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);

  const handle = async () => {
    const trimmed = text.trim();
    if (!trimmed || loading || disabled) return;
    setLoading(true);
    try {
      await onSubmit(trimmed);
      setText('');
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.row}>
      <TextInput
        value={text}
        onChangeText={setText}
        placeholder="ענה לשאלת הבהרה…"
        style={styles.input}
        accessibilityLabel="clarify-inline-input"
        returnKeyType="send"
        onSubmitEditing={handle}
        editable={!loading && !disabled}
      />
      <TouchableOpacity
        onPress={handle}
        accessibilityLabel="clarify-inline-send"
        style={[styles.btn, (!text.trim() || loading || disabled) && styles.btnDisabled]}
        disabled={!text.trim() || loading || disabled}
      >
        <Text style={styles.btnText}>{loading ? '…' : 'Send'}</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', marginTop: 8 },
  input: {
    flex: 1,
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#E5E7EB',
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 8,
    marginRight: 8,
  },
  btn: { backgroundColor: '#007AFF', borderRadius: 8, paddingHorizontal: 12, paddingVertical: 10 },
  btnDisabled: { backgroundColor: '#9CA3AF' },
  btnText: { color: '#fff', fontWeight: '600' },
});


