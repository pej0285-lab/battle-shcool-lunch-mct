import type { AgUiEvent, AnalysisResult, School } from './types';

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '';

export async function fetchRandomSchools(): Promise<School[]> {
  const response = await fetch(`${API_BASE}/api/schools/random?count=10`);
  if (!response.ok) {
    throw new Error('무작위 학교 목록을 가져오지 못했습니다.');
  }
  return response.json() as Promise<School[]>;
}

export async function fetchDefaultPrompt(schools: School[], mealDate: string): Promise<string> {
  const response = await fetch(`${API_BASE}/api/analysis/default-prompt`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ schools, meal_date: mealDate }),
  });
  if (!response.ok) {
    throw new Error('기본 분석 프롬프트를 생성하지 못했습니다.');
  }
  const payload = (await response.json()) as { prompt: string };
  return payload.prompt;
}

export async function runAnalysis(
  schools: School[],
  mealDate: string,
  prompt: string,
  onEvent: (event: AgUiEvent) => void,
): Promise<AnalysisResult> {
  const response = await fetch(`${API_BASE}/api/analysis/ag-ui`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ schools, meal_date: mealDate, prompt }),
  });
  if (!response.ok || !response.body) {
    throw new Error('분석 요청에 실패했습니다.');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let result: AnalysisResult | null = null;

  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split('\n\n');
    buffer = events.pop() ?? '';
    for (const chunk of events) {
      const line = chunk.split('\n').find((entry) => entry.startsWith('data: '));
      if (!line) {
        continue;
      }
      const event = JSON.parse(line.slice(6)) as AgUiEvent;
      onEvent(event);
      if (event.type === 'RUN_ERROR') {
        throw new Error(event.message ?? '분석 중 오류가 발생했습니다.');
      }
      if (event.type === 'RUN_FINISHED' && event.data) {
        result = event.data;
      }
    }
  }

  if (!result) {
    throw new Error('분석 결과를 받지 못했습니다.');
  }
  return result;
}
