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

describe('Clarify UI rendering', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders clarify card with question and disabled send', async () => {
    auto.mockResolvedValueOnce({ ok: true, status: 200, json: { action: 'clarify', question: 'על איזו דליה מדובר?' } });

    const { getByLabelText, getByText } = render(<AutoScreen />);

    const mainInput = getByLabelText('main-input');
    fireEvent.changeText(mainInput, 'דליה');
    await act(async () => { await Promise.resolve(); });
    const mainSend = getByLabelText('main-send');
    await act(async () => {
      fireEvent.press(mainSend);
      await Promise.resolve();
    });

    await waitFor(() => expect(getByText('על איזו דליה מדובר?')).toBeTruthy());

    const clarifyInput = getByLabelText('clarify-input');
    expect(clarifyInput).toBeTruthy();
    expect(clarifyInput.props.placeholder).toBe('ענה לשאלת הבהרה…');

    const clarifySend = getByLabelText('clarify-send');
    expect(clarifySend).toBeTruthy();
    expect(clarifySend.props.accessibilityState?.disabled || clarifySend.props.disabled).toBe(true);
  });

  it('disables send when whitespace only', async () => {
    auto.mockResolvedValueOnce({ ok: true, status: 200, json: { action: 'clarify', question: 'על איזו דליה מדובר?' } });

    const { getByLabelText } = render(<AutoScreen />);
    fireEvent.changeText(getByLabelText('main-input'), 'דליה');
    await act(async () => {
      fireEvent.press(getByLabelText('main-send'));
    });

    const clarifyInput = await waitFor(() => getByLabelText('clarify-input'));
    fireEvent.changeText(clarifyInput, '   ');
    const clarifySend = getByLabelText('clarify-send');
    expect(clarifySend.props.accessibilityState?.disabled || clarifySend.props.disabled).toBe(true);
  });

  it('falls back when question field name differs (message)', async () => {
    auto.mockResolvedValueOnce({ ok: true, status: 200, json: { action: 'clarify', message: 'שאלה שונה' } });
    const { getByLabelText, getByText } = render(<AutoScreen />);
    fireEvent.changeText(getByLabelText('main-input'), 'דליה');
    await act(async () => {
      fireEvent.press(getByLabelText('main-send'));
    });
    await waitFor(() => expect(getByText('שאלה שונה')).toBeTruthy());
  });

  it('falls back when question field name differs (clarification)', async () => {
    auto.mockResolvedValueOnce({ ok: true, status: 200, json: { action: 'clarify', clarification: 'עוד שאלה' } });
    const { getByLabelText, getByText } = render(<AutoScreen />);
    fireEvent.changeText(getByLabelText('main-input'), 'דליה');
    await act(async () => {
      fireEvent.press(getByLabelText('main-send'));
    });
    await waitFor(() => expect(getByText('עוד שאלה')).toBeTruthy());
  });
});


