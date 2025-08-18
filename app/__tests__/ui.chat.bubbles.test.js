import React from 'react';
import { render } from '@testing-library/react-native';
import MessageBubble from '../components/MessageBubble';

describe('MessageBubble styling and RTL', () => {
  it('renders user and assistant bubbles (snapshot)', () => {
    const { toJSON } = render(
      <>
        <MessageBubble role="user" text="Hello" />
        <MessageBubble role="assistant" text="Hi there" />
      </>
    );
    expect(toJSON()).toMatchSnapshot();
  });

  it('renders RTL via testID when rtl=true', () => {
    const { getByTestId } = render(<MessageBubble role="assistant" text={"שלום"} rtl={true} />);
    expect(getByTestId('bubble-text-rtl')).toBeTruthy();
  });
});


