import React, { useRef, useState } from 'react';
import { View, TextInput, TouchableOpacity, Text, FlatList, KeyboardAvoidingView, Platform, StyleSheet } from 'react-native';
import MessageBubble from '../components/MessageBubble';
import { detectRtl } from '../utils/text';
import { auto as autoDecide } from '../api';
import ClarifyInline from '../components/ClarifyInline';

export default function ChatScreen() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const listRef = useRef(null);
  const [expandedMore, setExpandedMore] = useState(new Set());
  const [debugVisible, setDebugVisible] = useState(false);
  const [lastJson, setLastJson] = useState(null);

  const handleSend = async () => {
    const trimmed = input.trim();
    if (!trimmed || loading) return;

    const now = Date.now();
    const userMsg = { id: `u_${now}`, role: 'user', text: trimmed };
    const placeholderId = `a_${now}`;
    const assistantPending = { id: placeholderId, role: 'assistant', text: '…', meta: { pending: true } };
    setMessages(prev => [...prev, userMsg, assistantPending]);
    setInput('');
    setLoading(true);
    // Scroll to bottom shortly after state update
    setTimeout(() => {
      if (listRef.current && listRef.current.scrollToEnd) {
        listRef.current.scrollToEnd({ animated: true });
      }
    }, 0);

    try {
      const preferredLanguage = detectRtl(trimmed) ? 'he' : 'en';
      const response = await autoDecide(trimmed, { preferredLanguage });
      const json = response?.json || {};
      setLastJson(json);
      if (!response?.ok) {
        let errText = 'Server error';
        if (response?.status === 401) errText = 'Missing/invalid API key';
        else if (response?.status === 429) errText = 'Rate limit';
        setMessages(prev => prev.map(m => (m.meta?.pending ? { ...m, role: 'assistant', text: errText, meta: {} } : m)));
        return;
      }
      const action = json?.action;

      let assistantText = '';
      let moreCount = 0;

      if (action === 'retrieve') {
        const candidates = (json?.result?.candidates || json?.candidates || []);
        if (Array.isArray(candidates) && candidates.length > 0) {
          assistantText = candidates[0]?.text || String(candidates[0]);
          moreCount = Math.max(0, candidates.length - 1);
        } else {
          assistantText = 'No results';
        }
      } else if (action === 'store') {
        const savedText = json?.decision?.normalized_text || json?.result?.text || trimmed;
        assistantText = `Saved: ${savedText}`;
      } else if (action === 'clarify') {
        assistantText = json?.decision?.clarify_prompt || json?.question || json?.message || json?.clarification || 'Need clarification';
      } else {
        assistantText = 'Server error';
      }

      setMessages(prev => {
        const next = [...prev];
        const idx = next.findIndex(m => m.id === placeholderId || m.meta?.pending);
        const meta = { moreCount };
        if (action === 'clarify') meta.type = 'clarify';
        if (Array.isArray(json?.result?.candidates) && json.result.candidates.length > 1) {
          meta.moreItems = json.result.candidates.slice(1);
        }
        if (json?.language && ((preferredLanguage === 'he' && json.language !== 'he') || (preferredLanguage === 'en' && json.language !== 'en'))) {
          meta.langTag = 'translated';
        }
        const finalAssistant = { id: placeholderId, role: 'assistant', text: assistantText, meta };
        if (idx !== -1) {
          next[idx] = finalAssistant;
        } else {
          next.push(finalAssistant);
        }
        return next;
      });
    } catch (e) {
      setMessages(prev => {
        const next = [...prev];
        const idx = next.findIndex(m => m.meta?.pending);
        const finalAssistant = { id: `a_err_${Date.now()}`, role: 'assistant', text: 'Server error' };
        if (idx !== -1) next[idx] = finalAssistant; else next.push(finalAssistant);
        return next;
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={styles.container}>
      <View style={styles.topBar}>
        <TouchableOpacity accessibilityLabel="debug-toggle" onPress={() => setDebugVisible(v => !v)}>
          <Text style={styles.debugText}>{debugVisible ? 'Hide debug' : 'Show debug'}</Text>
        </TouchableOpacity>
      </View>
      <FlatList
        ref={listRef}
        data={messages}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.listContent}
        renderItem={({ item }) => (
          <View>
            <MessageBubble role={item.role} text={item.text} rtl={detectRtl(item.text)} />
            {item.role === 'assistant' && item?.meta?.moreCount > 0 ? (
              <TouchableOpacity
                accessibilityLabel={`more-toggle-${item.id}`}
                onPress={() => {
                  setExpandedMore(prev => {
                    const copy = new Set(prev);
                    if (copy.has(item.id)) copy.delete(item.id); else copy.add(item.id);
                    return copy;
                  });
                }}
              >
                <Text style={styles.moreText}>Also found {item.meta.moreCount} more</Text>
              </TouchableOpacity>
            ) : null}
            {item.role === 'assistant' && item?.meta?.moreItems && expandedMore.has(item.id) ? (
              <View style={styles.moreList}>
                {item.meta.moreItems.map((c, idx) => (
                  <Text key={c.id || idx} style={styles.moreItemText}>{c.text || String(c)}</Text>
                ))}
              </View>
            ) : null}
            {item.role === 'assistant' && item?.meta?.langTag === 'translated' ? (
              <Text style={styles.translatedTag}>(other language)</Text>
            ) : null}
            {item.role === 'assistant' && item?.meta?.type === 'clarify' ? (
              <ClarifyInline
                onSubmit={async (followUp) => {
                  // append a new pending assistant below
                  const pendId = `a_inline_${Date.now()}`;
                  setMessages(prev => [...prev, { id: pendId, role: 'assistant', text: '…', meta: { pending: true } }]);
                  try {
                    const resp = await autoDecide(followUp);
                    const j = resp?.json || {};
                    let text = '';
                    let more = 0;
                    if (j.action === 'retrieve') {
                      const c = j?.result?.candidates || [];
                      text = c[0]?.text || 'No results';
                      more = Math.max(0, c.length - 1);
                    } else if (j.action === 'store') {
                      const savedText = j?.decision?.normalized_text || followUp;
                      text = `Saved: ${savedText}`;
                    } else if (j.action === 'clarify') {
                      text = j?.decision?.clarify_prompt || 'Need clarification';
                    } else {
                      text = 'Server error';
                    }
                    setMessages(prev => prev.map(m => m.id === pendId ? { id: pendId, role: 'assistant', text, meta: { moreCount: more, type: j.action === 'clarify' ? 'clarify' : undefined } } : m));
                  } catch (e) {
                    setMessages(prev => prev.map(m => m.id === pendId ? { ...m, text: 'Server error', meta: {} } : m));
                  }
                }}
              />
            ) : null}
          </View>
        )}
        ListEmptyComponent={<View style={styles.empty}><Text style={styles.emptyText}>No messages yet</Text></View>}
      />
      <View style={styles.inputRow}>
        <TextInput
          value={input}
          onChangeText={setInput}
          placeholder="כתוב הודעה…"
          style={styles.input}
          accessibilityLabel="chat-input"
          returnKeyType="send"
          onSubmitEditing={handleSend}
        />
        <TouchableOpacity
          onPress={handleSend}
          accessibilityLabel="chat-send"
          style={[styles.sendBtn, (!input.trim()) && styles.sendDisabled]}
          disabled={!input.trim()}
        >
          <Text style={styles.sendText}>Send</Text>
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F3F4F6' },
  listContent: { padding: 16, paddingBottom: 80 },
  topBar: { paddingHorizontal: 12, paddingTop: 8 },
  debugText: { color: '#6B7280', fontSize: 12 },
  empty: { alignItems: 'center', marginTop: 32 },
  emptyText: { color: '#6B7280' },
  inputRow: {
    flexDirection: 'row',
    padding: 10,
    backgroundColor: '#fff',
    borderTopWidth: 1,
    borderTopColor: '#E5E7EB',
  },
  input: {
    flex: 1,
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#E5E7EB',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
    marginRight: 8,
  },
  sendBtn: {
    backgroundColor: '#007AFF',
    borderRadius: 8,
    paddingHorizontal: 16,
    justifyContent: 'center',
  },
  sendDisabled: {
    backgroundColor: '#9CA3AF',
  },
  sendText: { color: '#fff', fontWeight: '600' },
  moreText: { color: '#6B7280', fontSize: 12, marginTop: 4, marginLeft: 8 },
  translatedTag: { color: '#9CA3AF', fontSize: 11, marginTop: 2, marginLeft: 8, fontStyle: 'italic' },
  moreList: { marginTop: 6, marginLeft: 12 },
  moreItemText: { color: '#374151', fontSize: 14, marginTop: 2 },
});


