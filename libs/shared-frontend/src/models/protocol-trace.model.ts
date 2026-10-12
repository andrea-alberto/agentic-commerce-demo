// Copyright 2026 UCP Authors / GDG DevFest Milano 2026

export interface ProtocolStep {
  step_number: number;
  protocol: 'a2a' | 'ucp_rest' | 'a2a_direct' | 'web_mcp' | string;
  actor_source: string;
  actor_target: string;
  action: string;
  description: string;
  payload: any;
  headers?: Record<string, string>;
  status: 'success' | 'pending' | 'warning' | 'error';
  timestamp: string;
  latency_ms?: number;
  related_message_id?: string;
}

export interface MissionStreamEvent {
  type: 'step' | 'challenge' | 'proposal' | 'final' | 'error';
  step?: ProtocolStep;
  challenge?: any;
  proposal?: any;
  final_order?: any;
  message?: string;
}
