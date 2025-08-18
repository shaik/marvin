import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

export default function MessageBubble({ role, text, rtl = false, timestamp }) {
  const isUser = role === 'user';
  const containerAlign = isUser ? 'flex-end' : 'flex-start';
  const bubbleStyle = isUser ? styles.userBubble : styles.assistantBubble;
  const resolvedDirection = rtl ? 'rtl' : 'ltr';

  return (
    <View style={[styles.row, { justifyContent: containerAlign }]}>
      <View style={[styles.bubble, bubbleStyle, styles.shadow]}>
        <Text
          testID={`bubble-text-${rtl ? 'rtl' : 'ltr'}`}
          style={[styles.text, { writingDirection: resolvedDirection, textAlign: rtl ? 'right' : 'left' }]}
        >
          {text}
        </Text>
        {timestamp ? (
          <Text style={[styles.time, { textAlign: isUser ? 'right' : 'left' }]}>{timestamp}</Text>
        ) : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    width: '100%',
    marginVertical: 6,
  },
  bubble: {
    maxWidth: '85%',
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 14,
  },
  userBubble: {
    backgroundColor: '#DCFCE7',
    borderTopRightRadius: 4,
  },
  assistantBubble: {
    backgroundColor: '#FFFFFF',
    borderTopLeftRadius: 4,
    borderWidth: 1,
    borderColor: '#E5E7EB',
  },
  text: {
    fontSize: 16,
    color: '#111827',
  },
  rtl: {
    writingDirection: 'rtl',
    textAlign: 'right',
  },
  time: {
    marginTop: 4,
    fontSize: 10,
    color: '#6B7280',
  },
  shadow: {
    shadowColor: '#000',
    shadowOpacity: 0.05,
    shadowRadius: 3,
    shadowOffset: { width: 0, height: 1 },
    elevation: 2,
  },
});


