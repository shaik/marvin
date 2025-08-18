import detectRtl from '../utils/text';

test('detects RTL for Hebrew', () => {
  expect(detectRtl('מה נשמע')).toBe(true);
});

test('detects LTR for English', () => {
  expect(detectRtl('hello')).toBe(false);
});


