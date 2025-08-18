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

describe('Chat clarify inline flow', () => {
  beforeEach(() => jest.clearAllMocks());

  it('clarify then follow-up → retrieve likely answer', async () => {
    auto.mockResolvedValueOnce({ ok: true, status: 200, json: { action: 'clarify', decision: { clarify_prompt: 'על איזו דליה מדובר?' } } });
    const utils = render(<ChatScreen />);
    fireEvent.changeText(utils.getByLabelText('chat-input'), 'דליה');
    fireEvent.press(utils.getByLabelText('chat-send'));
    await waitFor(() => utils.getByText('על איזו דליה מדובר?'));

    auto.mockResolvedValueOnce({ ok: true, status: 200, json: { action: 'retrieve', result: { candidates: [{ id: '1', text: 'דליה מהעבודה' }, { id: '2', text: 'דליה מהמשפחה' }] } } });
    fireEvent.changeText(utils.getByLabelText('clarify-inline-input'), 'דליה מהעבודה');
    fireEvent.press(utils.getByLabelText('clarify-inline-send'));

    await waitFor(() => utils.getByText('דליה מהעבודה'));
    await waitFor(() => utils.getByText('Also found 1 more'));
  });
});


