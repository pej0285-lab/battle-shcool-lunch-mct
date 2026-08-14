export interface School {
  office_code: string;
  office_name: string;
  school_code: string;
  school_name: string;
  region?: string | null;
  kind?: string | null;
}

export interface CriterionScore {
  key: string;
  title: string;
  weight: number;
  rating: number;
  weighted_score: number;
  evidence: string[];
  rationale: string;
}

export interface SchoolEvaluation {
  school: School;
  criteria: CriterionScore[];
  total_score: number;
  summary: string;
}

export interface AnalysisResult {
  pattern: string;
  schools: SchoolEvaluation[];
  winner: string | null;
  is_tie: boolean;
  overall_commentary: string;
  improvements: Record<string, string[]>;
  quality_gate: {
    passed: boolean;
    findings: string[];
    non_scored_role: string;
  };
}

export interface AgUiEvent {
  type: string;
  message?: string;
  data?: AnalysisResult;
}
