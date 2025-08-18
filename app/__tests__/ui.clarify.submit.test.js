import React from 'react';
import { render, fireEvent, waitFor, act } from '@testing-library/react-native';
import AutoScreen from '../screens/AutoScreen';

jest.mock('../api', () => {
  const actual = jest.requireActual('../api');
  return {
    ...actual,
    getConfig: () => ({ baseUrl: 'https://x.example', apiKey: '' }),
    auto: jest.fn(),
  };
});

const { auto } = require('../api');

describe('Clarify follow-up submission', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  async function reachClarifyQuestion({ question = 'על איזו דליה מדובר?' } = {}) {
    auto.mockResolvedValueOnce({ ok: true, status: 200, json: { action: 'clarify', question } });
    const utils = render(<AutoScreen />);
    fireEvent.changeText(utils.getByLabelText('main-input'), 'דליה');
    await act(async () => {
      fireEvent.press(utils.getByLabelText('main-send'));
    });
    await waitFor(() => utils.getByLabelText('clarify-input'));
    return utils;
  }

  it('follow-up submission triggers second call and shows retrieve; clarify disappears', async () => {
    const utils = await reachClarifyQuestion();

    auto.mockResolvedValueOnce({ ok: true, status: 200, json: { action: 'retrieve', candidates: [{ id: 'a', text: 'Result A' }] } });

    fireEvent.changeText(utils.getByLabelText('clarify-input'), 'דליה מהעבודה');
    await act(async () => {
      fireEvent.press(utils.getByLabelText('clarify-send'));
    });

    await waitFor(() => expect(auto).toHaveBeenCalledTimes(2));

    await waitFor(() => {
      // Expect clarify UI gone
      expect(() => utils.getByLabelText('clarify-input')).toThrow();
    });

    // Expect retrieve UI appears (placeholder: candidate text visible)
    await waitFor(() => utils.getByText('Result A'));
  });

  it('clarify loop supported: second response clarify updates question and resets input', async () => {
    const utils = await reachClarifyQuestion({ question: 'שאלה 1' });

    auto.mockResolvedValueOnce({ ok: true, status: 200, json: { action: 'clarify', question: 'שאלה 2' } });

    const input = utils.getByLabelText('clarify-input');
    fireEvent.changeText(input, 'תשובה 1');
    await act(async () => {
      fireEvent.press(utils.getByLabelText('clarify-send'));
    });

    await waitFor(() => expect(utils.getByText('שאלה 2')).toBeTruthy());

    // Expect input reset to empty
    const inputAfter = utils.getByLabelText('clarify-input');
    expect(inputAfter.props.value).toBe('');
  });

  it('disabled send on empty/whitespace and Enter submits when valid', async () => {
    const utils = await reachClarifyQuestion();

    const input = utils.getByLabelText('clarify-input');
    const btn = utils.getByLabelText('clarify-send');
    fireEvent.changeText(input, '   ');
    expect(btn.props.disabled || btn.props.accessibilityState?.disabled).toBe(true);

    // When valid, Enter should submit
    auto.mockResolvedValueOnce({ ok: true, status: 200, json: { action: 'retrieve', candidates: [] } });
    fireEvent.changeText(input, 'תשובה');
    expect(btn.props.disabled || btn.props.accessibilityState?.disabled).toBe(false);
    await act(async () => {
      fireEvent(input, 'submitEditing');
    });
    await waitFor(() => expect(auto).toHaveBeenCalledTimes(2));
  });

  it('loading state: while awaiting 2nd call, input and Send disabled or spinner visible', async () => {
    const utils = await reachClarifyQuestion();

    let resolveSecond;
    auto.mockImplementationOnce(() => new Promise((res) => { resolveSecond = res; }));

    const input = utils.getByLabelText('clarify-input');
    const btn = utils.getByLabelText('clarify-send');
    fireEvent.changeText(input, 'תשובה');
    await act(async () => {
      fireEvent.press(btn);
    });

    // Expect disabled during in-flight
    expect(utils.getByLabelText('clarify-send').props.disabled || utils.getByLabelText('clarify-send').props.accessibilityState?.disabled).toBe(true);
    expect(utils.getByLabelText('clarify-input').props.editable === false).toBe(true);

    // Finish the promise
    resolveSecond({ ok: true, status: 200, json: { action: 'retrieve', candidates: [] } });
  });

  it('error handling: 401 shows API key banner and clarify remains', async () => {
    const utils = await reachClarifyQuestion();
    auto.mockResolvedValueOnce({ ok: false, status: 401, json: { error: 'Unauthorized' } });
    fireEvent.changeText(utils.getByLabelText('clarify-input'), 'תשובה');
    await act(async () => {
      fireEvent.press(utils.getByLabelText('clarify-send'));
    });

    await waitFor(() => utils.getByText('Missing/invalid API key'));
    // Clarify still present
    expect(utils.getByLabelText('clarify-input')).toBeTruthy();
  });

  it('error handling: 429 shows rate limit banner and clarify remains', async () => {
    const utils = await reachClarifyQuestion();
    auto.mockResolvedValueOnce({ ok: false, status: 429, json: { error: 'Too Many Requests' } });
    fireEvent.changeText(utils.getByLabelText('clarify-input'), 'תשובה');
    await act(async () => {
      fireEvent.press(utils.getByLabelText('clarify-send'));
    });

    await waitFor(() => utils.getByText(/Rate limit/i));
    expect(utils.getByLabelText('clarify-input')).toBeTruthy();
  });

  it('error handling: network/server error shows server error banner and clarify remains', async () => {
    const utils = await reachClarifyQuestion();
    auto.mockResolvedValueOnce({ ok: false, status: 0, json: { error: 'Network error' } });
    fireEvent.changeText(utils.getByLabelText('clarify-input'), 'תשובה');
    await act(async () => {
      fireEvent.press(utils.getByLabelText('clarify-send'));
      await Promise.resolve();
    });

    await waitFor(() => utils.getByText(/Server error/i));
    expect(utils.getByLabelText('clarify-input')).toBeTruthy();
  });

  it('main input replaces clarify state when new main submission is made', async () => {
    const utils = await reachClarifyQuestion();
    auto.mockResolvedValueOnce({ ok: true, status: 200, json: { action: 'retrieve', candidates: [{ id: 'b', text: 'B' }] } });

    // Submit from main input
    fireEvent.changeText(utils.getByLabelText('main-input'), 'טקסט חדש');
    await act(async () => {
      fireEvent.press(utils.getByLabelText('main-send'));
    });

    await waitFor(() => expect(auto).toHaveBeenCalledTimes(2));
    // Clarify cleared
    await waitFor(() => expect(() => utils.getByLabelText('clarify-input')).toThrow());
    // Optionally input cleared as part of UX polish (enforce to fail until implemented)
    expect(utils.getByLabelText('main-input').props.value).toBe('');
  });
});


