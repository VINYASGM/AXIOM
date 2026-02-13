
export enum IVCUStatus {
  Draft = 'draft',
  Generating = 'generating',
  Verifying = 'verifying',
  Verified = 'verified',
  Deployed = 'deployed',
  Failed = 'failed'
}

export enum ModelTier {
  Local = 'Local (Qwen3)',
  Fast = 'Balanced (DeepSeek-V3)',
  Capable = 'Capable (Gemini 3 Pro)',
  Frontier = 'Frontier (Claude 4)'
}

export interface VerificationTier {
  name: string;
  status: 'pending' | 'running' | 'passed' | 'failed';
  details?: string;
}

export interface IVCU {
  id: string;
  intent: string;
  code?: string;
  status: IVCUStatus;
  confidence: number;
  cost: number;
  verificationTiers: VerificationTier[];
  timestamp: number;
  error?: string;
}

export interface MemoryNode {
  id: string;
  label: string;
  type: 'Intent' | 'Code' | 'Fact' | 'Dependency';
  x?: number;
  y?: number;
}

export interface MemoryEdge {
  source: string;
  target: string;
}

export interface TeamMember {
  id: string;
  email: string;
  role: 'owner' | 'admin' | 'editor' | 'viewer';
  avatar_url?: string;
}

export interface SpeculationPath {
  id: string;
  label: string;
  probability: number;
  impact_score: number;
  description: string;
}

export interface SpeculationResult {
  intent: string;
  paths: SpeculationPath[];
  recommended_path_id: string;
}

export interface ProjectEconomics {
  budget_limit: number;
  current_usage: number;
  remaining_budget: number;
  project_id: string;
}

export interface Project {
  id: string;
  name: string;
  owner_id: string;
  created_at: string;
}
