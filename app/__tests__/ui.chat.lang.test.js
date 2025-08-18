import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import ChatScreen from '../screens/ChatScreen';

jest.mock('../api', () => {
  const actual = jest.requireActual('../api');
  return {
    ...actual,
    getConfig: () => ({ baseUrl: 'https://x.example', apiKey: '' }),
    auto: jest.fn(),
  };
});

const { auto } = require('../api');

describe('Language alignment', () => {
  beforeEach(() => jest.clearAllMocks());

  it('Hebrew input → Hebrew answer (mocked)', async () => {
    auto.mockResolvedValueOnce({ ok: true, status: 200, json: { action: 'retrieve', language: 'he', result: { candidates: [{ id: '1', text: 'החולצה בוודאות על המדף העליון' }] } } });
    const utils = render(<ChatScreen />);
    fireEvent.changeText(utils.getByLabelText('chat-input'), 'איפה החולצה?');
    fireEvent.press(utils.getByLabelText('chat-send'));
    await waitFor(() => utils.getByText('החולצה בוודאות על המדף העליון'));
  });
});


