import { useEffect, useMemo, useState } from 'react';
import {
  Badge,
  Button,
  Card,
  CardHeader,
  Divider,
  Input,
  Spinner,
  Tab,
  TabList,
  Text,
  Textarea,
  Title1,
  Title2,
  makeStyles,
} from '@fluentui/react-components';
import { fetchDefaultPrompt, fetchRandomSchools, runAnalysis } from './api';
import { defaultMealDate, isCurrentOrPreviousMonth } from './date';
import type { AgUiEvent, AnalysisResult, School } from './types';

const useStyles = makeStyles({
  shell: { maxWidth: '1120px', margin: '0 auto', padding: '24px' },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '16px' },
  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '12px', marginTop: '16px' },
  section: { marginTop: '24px' },
  selected: { border: '2px solid #0f6cbd' },
  actions: { display: 'flex', gap: '12px', alignItems: 'center', marginTop: '16px', flexWrap: 'wrap' },
  resultGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '16px' },
  evidence: { margin: '4px 0' },
});

export default function App() {
  const styles = useStyles();
  const [tab, setTab] = useState<'lookup' | 'analysis'>('analysis');
  const [schools, setSchools] = useState<School[]>([]);
  const [selectedCodes, setSelectedCodes] = useState<string[]>([]);
  const [mealDate, setMealDate] = useState(defaultMealDate());
  const [prompt, setPrompt] = useState('');
  const [events, setEvents] = useState<AgUiEvent[]>([]);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchRandomSchools().then(setSchools).catch((err: Error) => setError(err.message));
  }, []);

  const selectedSchools = useMemo(
    () => selectedCodes.map((code) => schools.find((school) => school.school_code === code)).filter((school): school is School => Boolean(school)),
    [schools, selectedCodes],
  );
  const dateValid = isCurrentOrPreviousMonth(mealDate);
  const canBuildPrompt = selectedSchools.length === 2 && dateValid;

  async function toggleSchool(school: School) {
    setSelectedCodes((current) => {
      if (current.includes(school.school_code)) {
        return current.filter((code) => code !== school.school_code);
      }
      if (current.length >= 2) {
        return current;
      }
      return [...current, school.school_code];
    });
  }

  async function createPrompt() {
    if (!canBuildPrompt) {
      return;
    }
    setError(null);
    setPrompt(await fetchDefaultPrompt(selectedSchools, mealDate));
  }

  async function submitAnalysis() {
    setLoading(true);
    setError(null);
    setEvents([]);
    setResult(null);
    try {
      const analysis = await runAnalysis(selectedSchools, mealDate, prompt, (event) => setEvents((current) => [...current, event]));
      setResult(analysis);
    } catch (err) {
      setError(err instanceof Error ? err.message : '분석 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className={styles.shell}>
      <div className={styles.header}>
        <div>
          <Title1>급식 배틀</Title1>
          <Text block>NEIS 중식 데이터와 멀티에이전트 루브릭으로 두 학교 급식을 비교합니다.</Text>
        </div>
        <TabList selectedValue={tab} onTabSelect={(_, data) => setTab(data.value as 'lookup' | 'analysis')}>
          <Tab value="lookup">급식 조회</Tab>
          <Tab value="analysis">급식 분석</Tab>
        </TabList>
      </div>

      {tab === 'lookup' ? (
        <Card className={styles.section}>
          <CardHeader header={<Title2>급식 조회</Title2>} />
          <Text>학교 검색, 선택, 날짜 범위 조회는 백엔드 NEIS API 경계를 통해 확장되는 기본 페이지입니다. 분석은 상단의 급식 분석 탭에서 실행하세요.</Text>
        </Card>
      ) : (
        <>
          <section className={styles.section}>
            <Title2>1. 무작위 학교 10개 중 2개 선택</Title2>
            <div className={styles.grid}>
              {schools.map((school) => (
                <Card
                  key={school.school_code}
                  className={selectedCodes.includes(school.school_code) ? styles.selected : undefined}
                  onClick={() => void toggleSchool(school)}
                >
                  <CardHeader
                    header={<Text weight="semibold">{school.school_name}</Text>}
                    description={`${school.region ?? school.office_name} · ${school.kind ?? '학교'}`}
                  />
                </Card>
              ))}
            </div>
            <Text block>선택된 학교: {selectedSchools.map((school) => school.school_name).join(', ') || '없음'} ({selectedSchools.length}/2)</Text>
          </section>

          <section className={styles.section}>
            <Title2>2. 분석 날짜 선택</Title2>
            <Input aria-label="분석 날짜" type="date" value={mealDate} onChange={(_, data) => setMealDate(data.value)} />
            {!dateValid && <Text block role="alert">이번 달 또는 직전 달의 날짜만 선택할 수 있습니다.</Text>}
          </section>

          <section className={styles.section}>
            <Title2>3. 분석 프롬프트 생성 및 수정</Title2>
            <div className={styles.actions}>
              <Button appearance="primary" disabled={!canBuildPrompt} onClick={() => void createPrompt()}>
                기본 프롬프트 생성
              </Button>
              <Button disabled={!canBuildPrompt || !prompt || loading} onClick={() => void submitAnalysis()}>
                분석 전송
              </Button>
              {loading && <Spinner size="tiny" label="AG-UI 이벤트 수신 중" />}
            </div>
            <Textarea
              aria-label="분석 프롬프트"
              value={prompt}
              onChange={(_, data) => setPrompt(data.value)}
              resize="vertical"
              placeholder="분석 프롬프트를 생성하거나 직접 입력하세요."
              rows={5}
            />
          </section>

          {error && <Text role="alert">{error}</Text>}
          {events.length > 0 && (
            <section className={styles.section}>
              <Title2>진행 상태</Title2>
              {events.map((event, index) => (
                <Badge key={`${event.type}-${index}`} appearance="filled">
                  {event.message ?? event.type}
                </Badge>
              ))}
            </section>
          )}
          {result && <AnalysisResultView result={result} />}
        </>
      )}
    </main>
  );
}

function AnalysisResultView({ result }: { result: AnalysisResult }) {
  const styles = useStyles();
  return (
    <section className={styles.section}>
      <Title2>분석 결과</Title2>
      <Text block>{result.overall_commentary}</Text>
      <Text block>패턴: {result.pattern}</Text>
      <Text block>{result.is_tie ? '동점' : `승자: ${result.winner}`}</Text>
      <div className={styles.resultGrid}>
        {result.schools.map((evaluation) => (
          <Card key={evaluation.school.school_code}>
            <CardHeader header={<Title2>{evaluation.school.school_name}</Title2>} description={`총점 ${evaluation.total_score.toFixed(1)}점`} />
            <Divider />
            {evaluation.criteria.map((criterion) => (
              <div key={criterion.key}>
                <Text weight="semibold">
                  {criterion.title}: {criterion.rating}/5 · {criterion.weighted_score.toFixed(1)}점
                </Text>
                <Text block>{criterion.rationale}</Text>
                {criterion.evidence.map((evidence) => (
                  <Text block size={200} className={styles.evidence} key={evidence}>
                    근거: {evidence}
                  </Text>
                ))}
              </div>
            ))}
            <Divider />
            {(result.improvements[evaluation.school.school_name] ?? []).map((item) => (
              <Text block key={item}>
                개선안: {item}
              </Text>
            ))}
          </Card>
        ))}
      </div>
      <Card className={styles.section}>
        <CardHeader header="최종 평가자 품질 게이트" description={result.quality_gate.passed ? '통과' : '확인 필요'} />
        {result.quality_gate.findings.map((finding) => (
          <Text block key={finding}>
            {finding}
          </Text>
        ))}
      </Card>
    </section>
  );
}
