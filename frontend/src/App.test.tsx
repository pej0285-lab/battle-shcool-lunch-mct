import '@testing-library/jest-dom/vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { PropsWithChildren, ReactNode } from 'react';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import App from './App';
import type { School } from './types';

vi.mock('@fluentui/react-components', async () => {
  const React = await import('react');
  const passthrough = ({ children, ...props }: PropsWithChildren<Record<string, unknown>>) => React.createElement('div', props, children);
  const text = ({ children, ...props }: PropsWithChildren<Record<string, unknown>>) => React.createElement('span', props, children);
  return {
    FluentProvider: passthrough,
    Badge: text,
    Button: ({ children, ...props }: PropsWithChildren<Record<string, unknown>>) => React.createElement('button', props, children),
    Card: passthrough,
    CardHeader: ({ header, description }: { header: ReactNode; description?: ReactNode }) =>
      React.createElement('div', null, header, description && React.createElement('span', null, description)),
    Divider: () => React.createElement('hr'),
    Input: ({ onChange, ...props }: Record<string, unknown>) =>
      React.createElement('input', {
        ...props,
        onChange: (event: React.ChangeEvent<HTMLInputElement>) =>
          typeof onChange === 'function' && onChange(event, { value: event.target.value }),
      }),
    Spinner: text,
    Tab: ({ children, value }: PropsWithChildren<{ value: string }>) => React.createElement('button', { value }, children),
    TabList: ({ children }: PropsWithChildren) => React.createElement('div', null, children),
    Text: text,
    Textarea: ({ onChange, ...props }: Record<string, unknown>) =>
      React.createElement('textarea', {
        ...props,
        onChange: (event: React.ChangeEvent<HTMLTextAreaElement>) =>
          typeof onChange === 'function' && onChange(event, { value: event.target.value }),
      }),
    Title1: ({ children }: PropsWithChildren) => React.createElement('h1', null, children),
    Title2: ({ children }: PropsWithChildren) => React.createElement('h2', null, children),
    makeStyles: () => () => ({}),
    webLightTheme: {},
  };
});

const schools: School[] = Array.from({ length: 10 }, (_, index) => ({
  office_code: 'B10',
  office_name: '서울특별시교육청',
  school_code: `school-${index}`,
  school_name: `테스트고${index}`,
  region: '서울',
  kind: '고등학교',
}));

beforeEach(() => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes('/api/schools/random')) {
        return new Response(JSON.stringify(schools), { status: 200 });
      }
      if (url.includes('/api/analysis/default-prompt')) {
        return new Response(JSON.stringify({ prompt: '기본 프롬프트' }), { status: 200 });
      }
      return new Response('', { status: 404 });
    }),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
});

test('selects exactly two schools and creates editable prompt', async () => {
  const user = userEvent.setup();
  render(<App />);

  await screen.findByText('테스트고0');
  await user.click(screen.getByText('테스트고0'));
  await user.click(screen.getByText('테스트고1'));
  await user.click(screen.getByText('테스트고2'));

  expect(screen.getByText(/선택된 학교: 테스트고0, 테스트고1 \(2\/2\)/)).toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: '기본 프롬프트 생성' }));

  await waitFor(() => expect(screen.getByLabelText('분석 프롬프트')).toHaveValue('기본 프롬프트'));
  await user.type(screen.getByLabelText('분석 프롬프트'), ' 수정');
  expect(screen.getByLabelText('분석 프롬프트')).toHaveValue('기본 프롬프트 수정');
});
