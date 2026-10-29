// ===================
// ©AngelaMos | 2026
// useAgents.ts
//
// React Query hooks for Agent fleet management: listing, registration, token rotation, and revocation
// ===================

import {
  type UseMutationResult,
  type UseQueryResult,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query'
import { toast } from 'sonner'
import type {
  AgentListParams,
  AgentListResponse,
  AgentRegisterRequest,
  AgentRegisterResponse,
  AgentResponse,
  AgentStatsResponse,
  DeleteResponse,
} from '@/api/types'
import {
  AGENT_ERROR_MESSAGES,
  AGENT_SUCCESS_MESSAGES,
} from '@/api/types/agent.types'
import { API_ENDPOINTS, PAGINATION, QUERY_KEYS } from '@/config'
import { apiClient } from '@/core/lib'

export const agentQueries = {
  all: () => QUERY_KEYS.AGENTS.ALL,
  list: (params: AgentListParams) =>
    QUERY_KEYS.AGENTS.LIST(
      params.page ?? PAGINATION.DEFAULT_PAGE,
      params.per_page ?? PAGINATION.DEFAULT_SIZE,
      params.status,
      params.search
    ),
  stats: () => QUERY_KEYS.AGENTS.STATS(),
  byId: (id: string) => QUERY_KEYS.AGENTS.BY_ID(id),
} as const

export const useAgents = (
  params: AgentListParams = {}
): UseQueryResult<AgentListResponse, Error> => {
  return useQuery({
    queryKey: agentQueries.list(params),
    queryFn: async () => {
      const response = await apiClient.get<AgentListResponse>(
        API_ENDPOINTS.AGENTS.LIST,
        { params }
      )
      return response.data
    },
    refetchInterval: 10000, // Poll every 10s for live heartbeat status
  })
}

export const useAgentStats = (): UseQueryResult<AgentStatsResponse, Error> => {
  return useQuery({
    queryKey: agentQueries.stats(),
    queryFn: async () => {
      const response = await apiClient.get<AgentStatsResponse>(
        API_ENDPOINTS.AGENTS.STATS
      )
      return response.data
    },
    refetchInterval: 10000,
  })
}

export const useAgent = (
  agentId: string
): UseQueryResult<AgentResponse, Error> => {
  return useQuery({
    queryKey: agentQueries.byId(agentId),
    queryFn: async () => {
      const response = await apiClient.get<AgentResponse>(
        API_ENDPOINTS.AGENTS.BY_ID(agentId)
      )
      return response.data
    },
    enabled: agentId.length > 0,
  })
}

export const useRegisterAgent = (): UseMutationResult<
  AgentRegisterResponse,
  Error,
  AgentRegisterRequest
> => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (payload: AgentRegisterRequest) => {
      const response = await apiClient.post<AgentRegisterResponse>(
        API_ENDPOINTS.AGENTS.REGISTER,
        payload
      )
      return response.data
    },
    onSuccess: (data) => {
      toast.success(AGENT_SUCCESS_MESSAGES.REGISTERED(data.agent.name))
      queryClient.invalidateQueries({ queryKey: agentQueries.all() })
    },
    onError: () => {
      toast.error(AGENT_ERROR_MESSAGES.REGISTER_FAILED)
    },
  })
}

export const useRevokeAgent = (): UseMutationResult<
  AgentResponse,
  Error,
  string
> => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (agentId: string) => {
      const response = await apiClient.post<AgentResponse>(
        API_ENDPOINTS.AGENTS.REVOKE(agentId)
      )
      return response.data
    },
    onSuccess: (data) => {
      toast.success(AGENT_SUCCESS_MESSAGES.REVOKED(data.agent_id))
      queryClient.invalidateQueries({ queryKey: agentQueries.all() })
    },
    onError: () => {
      toast.error(AGENT_ERROR_MESSAGES.REVOKE_FAILED)
    },
  })
}

export const useRotateAgentToken = (): UseMutationResult<
  { agent: AgentResponse; token: string },
  Error,
  string
> => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (agentId: string) => {
      const response = await apiClient.post<{ agent: AgentResponse; token: string }>(
        API_ENDPOINTS.AGENTS.ROTATE_TOKEN(agentId)
      )
      return response.data
    },
    onSuccess: (data) => {
      toast.success(AGENT_SUCCESS_MESSAGES.ROTATED(data.agent.agent_id))
      queryClient.invalidateQueries({ queryKey: agentQueries.all() })
    },
    onError: () => {
      toast.error(AGENT_ERROR_MESSAGES.ROTATE_FAILED)
    },
  })
}

export const useDeleteAgent = (): UseMutationResult<
  DeleteResponse,
  Error,
  string
> => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (agentId: string) => {
      const response = await apiClient.delete<DeleteResponse>(
        API_ENDPOINTS.AGENTS.DELETE(agentId)
      )
      return response.data
    },
    onSuccess: (_, agentId) => {
      toast.success(AGENT_SUCCESS_MESSAGES.DELETED(agentId))
      queryClient.invalidateQueries({ queryKey: agentQueries.all() })
    },
    onError: () => {
      toast.error(AGENT_ERROR_MESSAGES.DELETE_FAILED)
    },
  })
}
