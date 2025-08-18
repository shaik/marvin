import React from 'react';
import { render, fireEvent, act } from '@testing-library/react-native';
import ChatScreen from '../screens/ChatScreen';

jest.mock('../api', () => {
  const actual = jest.requireActual('../api');
  return {
    ...actual,
    getConfig: () => ({ baseUrl: 'https://x.example', apiKey: '' }),
    auto: jest.fn(() => new Promise(() => {})),
  };
});

describe('ChatScreen scaffold', () => {
  it('renders input and empty list initially', () => {
    const { getByLabelText, getByText } = render(<ChatScreen />);
    expect(getByLabelText('chat-input')).toBeTruthy();
    expect(getByText('No messages yet')).toBeTruthy();
  });

  it('appends user message and pending assistant on send', async () => {
    const { getByLabelText, getByText, queryByText } = render(<ChatScreen />);
    const input = getByLabelText('chat-input');
    fireEvent.changeText(input, 'hello world');
    await act(async () => {
      fireEvent.press(getByLabelText('chat-send'));
      await Promise.resolve();
    });

    expect(queryByText('No messages yet')).toBeNull();
    expect(getByText('hello world')).toBeTruthy();
    expect(getByText('…')).toBeTruthy();
  });
});


