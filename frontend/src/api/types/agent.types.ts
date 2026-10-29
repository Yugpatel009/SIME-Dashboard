// ===================
// ©AngelaMos | 2026
// agent.types.ts
//
// Types, schemas, and toast message constants for the Agent Management API
// ===================

import { z } from 'zod'

export const AgentStatus = {
  ONLINE: 'online',
  STALE: 'stale',
  OFFLINE: 'offline',
  REVOKED: 'revoked',
} as const

export type AgentStatus = (typeof AgentStatus)[keyof typeof AgentStatus]

export const agentResponseSchema = z.object({
  id: z.string(),
  agent_id: z.string(),
  name: z.string(),
  hostname: z.string(),
  os_type: z.string(),
  agent_version: z.string(),
  ip_address: z.string().nullable().optional(),
  status: z.enum(['online', 'stale', 'offline', 'revoked']),
  is_revoked: z.boolean(),
  revoked_at: z.string().nullable().optional(),
  last_heartbeat_at: z.string().nullable().optional(),
  last_event_at: z.string().nullable().optional(),
  total_events_received: z.number(),
  last_error: z.string().nullable().optional(),
  registered_by: z.string().nullable().optional(),
  metrics: z.record(z.string(), z.unknown()).optional(),
  created_at: z.string().nullable().optional(),
  updated_at: z.string().nullable().optional(),
})

export const agentRegisterRequestSchema = z.object({
  name: z.string().min(1, 'Name is required').max(64),
  hostname: z.string().min(1, 'Hostname is required').max(128),
  os_type: z.string().default('linux'),
  agent_version: z.string().default('1.0.0'),
})

export const agentRegisterResponseSchema = z.object({
  agent: agentResponseSchema,
  token: z.string(),
  instructions: z.object({
    agent_id: z.string(),
    auth_header: z.string(),
  }),
})

export const agentStatsResponseSchema = z.object({
  total: z.number(),
  online: z.number(),
  stale: z.number(),
  offline: z.number(),
  revoked: z.number(),
  total_events: z.number(),
})

export const agentListResponseSchema = z.object({
  items: z.array(agentResponseSchema),
  total: z.number(),
  page: z.number(),
  per_page: z.number(),
  pages: z.number(),
})

export type AgentResponse = z.infer<typeof agentResponseSchema>
export type AgentRegisterRequest = z.infer<typeof agentRegisterRequestSchema>
export type AgentRegisterResponse = z.infer<typeof agentRegisterResponseSchema>
export type AgentStatsResponse = z.infer<typeof agentStatsResponseSchema>
export type AgentListResponse = z.infer<typeof agentListResponseSchema>

export interface AgentListParams {
  page?: number
  per_page?: number
  status?: string
  search?: string
}

export const AGENT_SUCCESS_MESSAGES = {
  REGISTERED: (name: string) => `Agent '${name}' successfully registered`,
  REVOKED: (id: string) => `Agent '${id}' credentials revoked`,
  ROTATED: (id: string) => `Token rotated for agent '${id}'`,
  DELETED: (id: string) => `Agent '${id}' deleted`,
} as const

export const AGENT_ERROR_MESSAGES = {
  LIST_FAILED: 'Failed to fetch agent list',
  REGISTER_FAILED: 'Failed to register agent',
  REVOKE_FAILED: 'Failed to revoke agent credentials',
  ROTATE_FAILED: 'Failed to rotate agent credentials',
  DELETE_FAILED: 'Failed to delete agent',
} as const
