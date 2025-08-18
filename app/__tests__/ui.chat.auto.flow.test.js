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

describe('ChatScreen /auto flow', () => {
  beforeEach(() => jest.clearAllMocks());

  async function typeAndSend(utils, text) {
    fireEvent.changeText(utils.getByLabelText('chat-input'), text);
    fireEvent.press(utils.getByLabelText('chat-send'));
    await waitFor(() => expect(auto).toHaveBeenCalled());
  }

  it('retrieve with 1 candidate → one assistant bubble with that text', async () => {
    auto.mockResolvedValueOnce({ ok: true, status: 200, json: { action: 'retrieve', result: { candidates: [{ id: '1', text: 'pink shirt on the top shelf' }] } } });
    const utils = render(<ChatScreen />);
    await typeAndSend(utils, 'where is my shirt?');
    await waitFor(() => utils.getByText('pink shirt on the top shelf'));
  });

  it('retrieve with 3 candidates → likely answer + also found 2 more line', async () => {
    auto.mockResolvedValueOnce({ ok: true, status: 200, json: { action: 'retrieve', result: { candidates: [
      { id: '1', text: 'top shelf' }, { id: '2', text: 'drawer' }, { id: '3', text: 'laundry' }
    ] } } });
    const utils = render(<ChatScreen />);
    await typeAndSend(utils, 'where?');
    await waitFor(() => utils.getByText('top shelf'));
    await waitFor(() => utils.getByText('Also found 2 more'));
  });

  it('store → Saved: …', async () => {
    auto.mockResolvedValueOnce({ ok: true, status: 201, json: { action: 'store', decision: { normalized_text: 'I lent the pink shirt to Hadar' } } });
    const utils = render(<ChatScreen />);
    await typeAndSend(utils, 'I lent the pink shirt to Hadar');
    await waitFor(() => utils.getByText(/Saved: I lent the pink shirt/));
  });

  it('clarify → shows question bubble', async () => {
    auto.mockResolvedValueOnce({ ok: true, status: 200, json: { action: 'clarify', decision: { clarify_prompt: 'על איזו דליה מדובר?' } } });
    const utils = render(<ChatScreen />);
    await typeAndSend(utils, 'דליה');
    await waitFor(() => utils.getByText('על איזו דליה מדובר?'));
  });
});


