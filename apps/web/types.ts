
export enum IVCUStatus {
  Draft = 'Draft',
  Generating = 'Generating',
  Verifying = 'Verifying',
  Verified = 'Verified',
  Deployed = 'Deployed',
  Failed = 'Failed'
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
