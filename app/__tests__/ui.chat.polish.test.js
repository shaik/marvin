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

describe('Chat polish: errors and more results', () => {
  beforeEach(() => jest.clearAllMocks());

  it('shows friendly error banners for 401/429/network', async () => {
    // 401
    auto.mockResolvedValueOnce({ ok: false, status: 401, json: { error: 'Unauthorized' } });
    let utils = render(<ChatScreen />);
    fireEvent.changeText(utils.getByLabelText('chat-input'), 'hi');
    fireEvent.press(utils.getByLabelText('chat-send'));
    await waitFor(() => utils.getByText('Missing/invalid API key'));

    // 429
    utils.unmount();
    auto.mockResolvedValueOnce({ ok: false, status: 429, json: { error: 'Too Many Requests' } });
    utils = render(<ChatScreen />);
    fireEvent.changeText(utils.getByLabelText('chat-input'), 'hi');
    fireEvent.press(utils.getByLabelText('chat-send'));
    await waitFor(() => utils.getByText('Rate limit'));

    // network
    utils.unmount();
    auto.mockResolvedValueOnce({ ok: false, status: 0, json: { error: 'Network error' } });
    utils = render(<ChatScreen />);
    fireEvent.changeText(utils.getByLabelText('chat-input'), 'hi');
    fireEvent.press(utils.getByLabelText('chat-send'));
    await waitFor(() => utils.getByText('Server error'));
  });

  it('expands more results when tapping the more line', async () => {
    auto.mockResolvedValueOnce({ ok: true, status: 200, json: { action: 'retrieve', result: { candidates: [
      { id: '1', text: 'A' }, { id: '2', text: 'B' }, { id: '3', text: 'C' }
    ] } } });
    const utils = render(<ChatScreen />);
    fireEvent.changeText(utils.getByLabelText('chat-input'), 'q');
    fireEvent.press(utils.getByLabelText('chat-send'));
    await waitFor(() => utils.getByText('A'));
    await waitFor(() => utils.getByText('Also found 2 more'));
    fireEvent.press(utils.getByLabelText(/more-toggle/));
    await waitFor(() => utils.getByText('B'));
    await waitFor(() => utils.getByText('C'));
  });
});


