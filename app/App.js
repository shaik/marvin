/**
 * Marvin Memory Assistant - Mobile App
 * Chat-style interface with voice recording and memory management
 */

import React, { useState, useEffect, useRef } from 'react';
import {
  StyleSheet,
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ScrollView,
  Alert,
  Dimensions,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider, SafeAreaView } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import * as Location from 'expo-location';
import Voice from '@react-native-voice/voice';
import { Audio } from 'expo-av';

// Import API services
import { storeMemory, queryMemory, testConnection } from './api';

const { width: screenWidth } = Dimensions.get('window');

// Message types
const MESSAGE_TYPES = {
  USER: 'user',
  MARVIN: 'marvin',
  SYSTEM: 'system',
};

export default function App() {
  // State management
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [currentLocation, setCurrentLocation] = useState(null);
  
  // Refs
  const scrollViewRef = useRef(null);
  const soundRef = useRef(null);

  // Initialize app
  useEffect(() => {
    initializeApp();
    return () => {
      cleanup();
    };
  }, []);

  // Initialize voice recognition and permissions
  const initializeApp = async () => {
    try {
      // Test API connection
      const connected = await testConnection();
      setIsConnected(connected);
      
      if (connected) {
        addSystemMessage('Connected to Marvin Memory Service ✓');
      } else {
        addSystemMessage('⚠️ Could not connect to memory service. Check your HEROKU_URL configuration.');
      }

      // Initialize voice recognition
      await initializeVoice();
      
      // Request location permission
      await requestLocationPermission();
      
      // Initialize audio
      await initializeAudio();
      
      // Welcome message
      addMarvinMessage('שלום! אני מרווין, עוזר הזיכרון שלך. אתה יכול לספר לי דברים או לשאול אותי שאלות.');
      
    } catch (error) {
      console.error('App initialization error:', error);
      addSystemMessage('❌ Initialization error: ' + error.message);
    }
  };

  // Initialize voice recognition
  const initializeVoice = async () => {
    try {
      Voice.onSpeechStart = onSpeechStart;
      Voice.onSpeechRecognized = onSpeechRecognized;
      Voice.onSpeechEnd = onSpeechEnd;
      Voice.onSpeechError = onSpeechError;
      Voice.onSpeechResults = onSpeechResults;
      Voice.onSpeechPartialResults = onSpeechPartialResults;
    } catch (error) {
      console.error('Voice initialization error:', error);
    }
  };

  // Initialize audio for TTS
  const initializeAudio = async () => {
    try {
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
      });
    } catch (error) {
      console.error('Audio initialization error:', error);
    }
  };

  // Request location permission
  const requestLocationPermission = async () => {
    try {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status === 'granted') {
        const location = await Location.getCurrentPositionAsync({});
        setCurrentLocation({
          latitude: location.coords.latitude,
          longitude: location.coords.longitude,
        });
      }
    } catch (error) {
      console.error('Location permission error:', error);
    }
  };

  // Cleanup
  const cleanup = () => {
    Voice.destroy().then(Voice.removeAllListeners);
    if (soundRef.current) {
      soundRef.current.unloadAsync();
    }
  };

  // Voice recognition handlers
  const onSpeechStart = () => {
    console.log('Speech recognition started');
  };

  const onSpeechRecognized = () => {
    console.log('Speech recognized');
  };

  const onSpeechEnd = () => {
    console.log('Speech recognition ended');
    setIsRecording(false);
  };

  const onSpeechError = (error) => {
    console.error('Speech recognition error:', error);
    setIsRecording(false);
    addSystemMessage('❌ Speech recognition error: ' + error.error?.message || 'Unknown error');
  };

  const onSpeechResults = (event) => {
    const result = event.value?.[0];
    if (result) {
      setInputText(result);
    }
  };

  const onSpeechPartialResults = (event) => {
    const partial = event.value?.[0];
    if (partial) {
      setInputText(partial);
    }
  };

  // Message helpers
  const addMessage = (text, type, metadata = {}) => {
    const message = {
      id: Date.now() + Math.random(),
      text,
      type,
      timestamp: new Date().toISOString(),
      ...metadata,
    };
    setMessages(prev => [...prev, message]);
    
    // Auto-scroll to bottom
    setTimeout(() => {
      scrollViewRef.current?.scrollToEnd({ animated: true });
    }, 100);
  };

  const addUserMessage = (text) => addMessage(text, MESSAGE_TYPES.USER);
  const addMarvinMessage = (text, metadata = {}) => addMessage(text, MESSAGE_TYPES.MARVIN, metadata);
  const addSystemMessage = (text) => addMessage(text, MESSAGE_TYPES.SYSTEM);

  // Text-to-speech
  const speakText = async (text) => {
    try {
      // Stop any current playback
      if (soundRef.current) {
        await soundRef.current.unloadAsync();
      }

      // For demo purposes, we'll use a simple beep
      // In production, you'd integrate with a TTS service
      const { sound } = await Audio.Sound.createAsync(
        { uri: 'https://www.soundjay.com/buttons/sounds/button-09.wav' },
        { shouldPlay: true }
      );
      soundRef.current = sound;
    } catch (error) {
      console.error('TTS error:', error);
    }
  };

  // Handle voice recording
  const toggleRecording = async () => {
    try {
      if (isRecording) {
        await Voice.stop();
        setIsRecording(false);
      } else {
        setInputText('');
        await Voice.start('he-IL'); // Hebrew locale
        setIsRecording(true);
      }
    } catch (error) {
      console.error('Voice recording error:', error);
      setIsRecording(false);
      addSystemMessage('❌ Voice recording error: ' + error.message);
    }
  };

  // Process user input (text or voice)
  const processUserInput = async (text) => {
    if (!text?.trim()) return;

    const userText = text.trim();
    addUserMessage(userText);
    setInputText('');
    setIsProcessing(true);

    try {
      // Determine if this is a query or a statement to store
      const isQuestion = userText.includes('?') || 
                        userText.startsWith('מה') || 
                        userText.startsWith('איפה') || 
                        userText.startsWith('מתי') ||
                        userText.startsWith('איך') ||
                        userText.startsWith('למה');

      if (isQuestion) {
        // Query existing memories
        const response = await queryMemory(userText);
        
        if (response.candidates && response.candidates.length > 0) {
          const bestMatch = response.candidates[0];
          if (bestMatch.similarity_score > 0.7) {
            addMarvinMessage(bestMatch.text, {
              similarity_score: bestMatch.similarity_score,
              memory_id: bestMatch.memory_id,
            });
          } else {
            addMarvinMessage('מצטער, לא מצאתי תשובה מתאימה. אולי תוכל לנסח את השאלה אחרת?');
          }
        } else {
          addMarvinMessage('לא מצאתי מידע רלוונטי. תוכל לספר לי יותר על זה?');
        }
      } else {
        // Store new memory
        const locationString = currentLocation 
          ? `${currentLocation.latitude},${currentLocation.longitude}`
          : null;

        const response = await storeMemory(userText, 'he', locationString);
        
        if (response.duplicate_detected) {
          addMarvinMessage(
            `יש לי זיכרון דומה: "${response.existing_memory_preview}". האם תרצה לעדכן אותו?`,
            {
              duplicate_memory_id: response.memory_id,
              similarity_score: response.similarity_score,
            }
          );
        } else {
          addMarvinMessage('שמרתי את הזיכרון שלך ✓');
        }
      }
    } catch (error) {
      console.error('Processing error:', error);
      addMarvinMessage('מצטער, הייתה שגיאה בעיבוד הבקשה שלך. נסה שוב.');
    } finally {
      setIsProcessing(false);
    }
  };

  // Handle send button press
  const handleSend = () => {
    processUserInput(inputText);
  };

  // Render message bubble
  const renderMessage = (message) => {
    const isUser = message.type === MESSAGE_TYPES.USER;
    const isSystem = message.type === MESSAGE_TYPES.SYSTEM;
    
    return (
      <View 
        key={message.id} 
        style={[
          styles.messageContainer,
          isUser ? styles.userMessageContainer : styles.marvinMessageContainer,
          isSystem && styles.systemMessageContainer,
        ]}
      >
        <View style={[
          styles.messageBubble,
          isUser ? styles.userBubble : styles.marvinBubble,
          isSystem && styles.systemBubble,
        ]}>
          <Text style={[
            styles.messageText,
            isUser ? styles.userText : styles.marvinText,
            isSystem && styles.systemText,
          ]}>
            {message.text}
          </Text>
          
          {message.similarity_score && (
            <Text style={styles.metadataText}>
              דיוק: {Math.round(message.similarity_score * 100)}%
            </Text>
          )}
        </View>
        
        <Text style={styles.timestampText}>
          {new Date(message.timestamp).toLocaleTimeString('he-IL', {
            hour: '2-digit',
            minute: '2-digit',
          })}
        </Text>
      </View>
    );
  };

  return (
    <SafeAreaProvider>
      <SafeAreaView style={styles.container}>
        <StatusBar style="light" />
        
        {/* Header */}
        <LinearGradient
          colors={['#4C566A', '#5E81AC']}
          style={styles.header}
        >
          <Text style={styles.headerTitle}>מרווין</Text>
          <Text style={styles.headerSubtitle}>עוזר הזיכרון האישי שלך</Text>
          <View style={[
            styles.connectionStatus,
            { backgroundColor: isConnected ? '#A3BE8C' : '#BF616A' }
          ]}>
            <Text style={styles.connectionText}>
              {isConnected ? 'מחובר' : 'לא מחובר'}
            </Text>
          </View>
        </LinearGradient>

        {/* Messages */}
        <ScrollView 
          ref={scrollViewRef}
          style={styles.messagesContainer}
          contentContainerStyle={styles.messagesContent}
          showsVerticalScrollIndicator={false}
        >
          {messages.map(renderMessage)}
          
          {isProcessing && (
            <View style={styles.typingIndicator}>
              <Text style={styles.typingText}>מרווין כותב...</Text>
            </View>
          )}
        </ScrollView>

        {/* Input Area */}
        <KeyboardAvoidingView 
          behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
          style={styles.inputContainer}
        >
          <LinearGradient
            colors={['#3B4252', '#434C5E']}
            style={styles.inputBackground}
          >
            <View style={styles.inputRow}>
              <TextInput
                style={styles.textInput}
                value={inputText}
                onChangeText={setInputText}
                placeholder="הקלד הודעה או לחץ על המיקרופון..."
                placeholderTextColor="#81A1C1"
                multiline
                textAlign="right"
                onSubmitEditing={handleSend}
                blurOnSubmit={false}
              />
              
              <TouchableOpacity 
                style={[
                  styles.micButton,
                  isRecording && styles.micButtonActive
                ]}
                onPress={toggleRecording}
                disabled={isProcessing}
              >
                <Ionicons 
                  name={isRecording ? "stop" : "mic"} 
                  size={24} 
                  color={isRecording ? "#BF616A" : "#ECEFF4"} 
                />
              </TouchableOpacity>
              
              <TouchableOpacity 
                style={styles.sendButton}
                onPress={handleSend}
                disabled={!inputText.trim() || isProcessing}
              >
                <Ionicons 
                  name="send" 
                  size={20} 
                  color={inputText.trim() ? "#88C0D0" : "#4C566A"} 
                />
              </TouchableOpacity>
            </View>
          </LinearGradient>
        </KeyboardAvoidingView>
      </SafeAreaView>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#2E3440',
  },
  header: {
    paddingHorizontal: 20,
    paddingVertical: 15,
    alignItems: 'center',
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#ECEFF4',
    textAlign: 'center',
  },
  headerSubtitle: {
    fontSize: 14,
    color: '#D8DEE9',
    textAlign: 'center',
    marginTop: 4,
  },
  connectionStatus: {
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 12,
    marginTop: 8,
  },
  connectionText: {
    fontSize: 12,
    color: '#ECEFF4',
    fontWeight: '600',
  },
  messagesContainer: {
    flex: 1,
    backgroundColor: '#3B4252',
  },
  messagesContent: {
    padding: 16,
  },
  messageContainer: {
    marginVertical: 4,
  },
  userMessageContainer: {
    alignItems: 'flex-end',
  },
  marvinMessageContainer: {
    alignItems: 'flex-start',
  },
  systemMessageContainer: {
    alignItems: 'center',
  },
  messageBubble: {
    maxWidth: screenWidth * 0.8,
    padding: 12,
    borderRadius: 16,
    marginBottom: 4,
  },
  userBubble: {
    backgroundColor: '#5E81AC',
    borderBottomRightRadius: 4,
  },
  marvinBubble: {
    backgroundColor: '#434C5E',
    borderBottomLeftRadius: 4,
  },
  systemBubble: {
    backgroundColor: '#4C566A',
    borderRadius: 8,
  },
  messageText: {
    fontSize: 16,
    lineHeight: 22,
  },
  userText: {
    color: '#ECEFF4',
    textAlign: 'right',
  },
  marvinText: {
    color: '#E5E9F0',
    textAlign: 'left',
  },
  systemText: {
    color: '#81A1C1',
    textAlign: 'center',
    fontSize: 14,
    fontStyle: 'italic',
  },
  metadataText: {
    fontSize: 12,
    color: '#81A1C1',
    marginTop: 4,
    textAlign: 'right',
  },
  timestampText: {
    fontSize: 11,
    color: '#4C566A',
    textAlign: 'center',
  },
  typingIndicator: {
    alignItems: 'flex-start',
    marginVertical: 8,
  },
  typingText: {
    fontSize: 14,
    color: '#81A1C1',
    fontStyle: 'italic',
  },
  inputContainer: {
    backgroundColor: '#3B4252',
  },
  inputBackground: {
    paddingHorizontal: 16,
    paddingVertical: 12,
  },
  inputRow: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    backgroundColor: '#434C5E',
    borderRadius: 24,
    paddingHorizontal: 16,
    paddingVertical: 8,
  },
  textInput: {
    flex: 1,
    fontSize: 16,
    color: '#ECEFF4',
    maxHeight: 100,
    marginRight: 12,
    textAlign: 'right',
  },
  micButton: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: '#4C566A',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 8,
  },
  micButtonActive: {
    backgroundColor: '#BF616A',
  },
  sendButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: '#4C566A',
    justifyContent: 'center',
    alignItems: 'center',
  },
});
