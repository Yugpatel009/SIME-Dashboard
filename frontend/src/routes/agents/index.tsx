// ===================
// ©AngelaMos | 2026
// index.tsx
//
// Agent management page with live fleet metrics, agent table, and registration
// ===================

import { useState } from 'react'
import {
  LuBan,
  LuCheck,
  LuChevronLeft,
  LuChevronRight,
  LuCopy,
  LuEye,
  LuKeyRound,
  LuPlus,
  LuSearch,
  LuTrash2,
  LuX,
} from 'react-icons/lu'
import { toast } from 'sonner'
import {
  useAgentStats,
  useAgents,
  useDeleteAgent,
  useRegisterAgent,
  useRevokeAgent,
  useRotateAgentToken,
} from '@/api/hooks'
import type { AgentResponse } from '@/api/types'
import { AGENT_STATUS_LABELS, PAGINATION } from '@/config'
import { useAuthStore } from '@/core/stores'
import styles from './agents.module.scss'

export function Component(): React.ReactElement {
  const [page, setPage] = useState<number>(PAGINATION.DEFAULT_PAGE)
  const [search, setSearch] = useState<string>('')
  const [statusFilter, setStatusFilter] = useState<string>('all')

  const [registerModalOpen, setRegisterModalOpen] = useState<boolean>(false)
  const [inspectAgent, setInspectAgent] = useState<AgentResponse | null>(null)
  const [newCredentials, setNewCredentials] = useState<{
    agentId: string
    token: string
  } | null>(null)

  const user = useAuthStore((s) => s.user)
  const isAdmin = user?.role === 'admin'

  const { data: stats, isLoading: statsLoading } = useAgentStats()
  const { data: agentsData, isLoading: agentsLoading } = useAgents({
    page,
    per_page: PAGINATION.DEFAULT_SIZE,
    status: statusFilter !== 'all' ? statusFilter : undefined,
    search: search.length > 0 ? search : undefined,
  })

  const registerMutation = useRegisterAgent()
  const revokeMutation = useRevokeAgent()
  const rotateMutation = useRotateAgentToken()
  const deleteMutation = useDeleteAgent()

  const [regForm, setRegForm] = useState({
    name: '',
    hostname: '',
    os_type: 'linux',
    agent_version: '1.0.0',
  })

  const handleRegister = (e: React.FormEvent) => {
    e.preventDefault()
    if (!regForm.name || !regForm.hostname) return

    registerMutation.mutate(regForm, {
      onSuccess: (data) => {
        setNewCredentials({
          agentId: data.agent.agent_id,
          token: data.token,
        })
        setRegForm({
          name: '',
          hostname: '',
          os_type: 'linux',
          agent_version: '1.0.0',
        })
      },
    })
  }

  const handleRotate = (agentId: string) => {
    if (!window.confirm(`Rotate credentials for agent '${agentId}'? The previous token will immediately stop working.`)) {
      return
    }
    rotateMutation.mutate(agentId, {
      onSuccess: (data) => {
        setNewCredentials({
          agentId: data.agent.agent_id,
          token: data.token,
        })
      },
    })
  }

  const handleRevoke = (agentId: string) => {
    if (!window.confirm(`Revoke credentials for agent '${agentId}'? It will no longer be permitted to send events.`)) {
      return
    }
    revokeMutation.mutate(agentId)
  }

  const handleDelete = (agentId: string) => {
    if (!window.confirm(`Permanently delete agent '${agentId}'?`)) {
      return
    }
    deleteMutation.mutate(agentId, {
      onSuccess: () => {
        if (inspectAgent?.agent_id === agentId) {
          setInspectAgent(null)
        }
      },
    })
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    toast.success('Copied to clipboard!')
  }

  return (
    <div className={styles.page}>
      {/* Fleet Overview Stat Cards */}
      <div className={styles.statsGrid}>
        <div className={styles.statCard}>
          <span className={styles.statLabel}>Total Registered</span>
          <span className={styles.statValue}>
            {statsLoading ? '...' : stats?.total ?? 0}
          </span>
        </div>
        <div className={styles.statCard}>
          <span className={styles.statLabel}>Active Online</span>
          <span className={styles.statValue} style={{ color: '#4ade80' }}>
            {statsLoading ? '...' : stats?.online ?? 0}
          </span>
        </div>
        <div className={styles.statCard}>
          <span className={styles.statLabel}>Stale / Offline</span>
          <span className={styles.statValue} style={{ color: '#facc15' }}>
            {statsLoading
              ? '...'
              : (stats?.stale ?? 0) + (stats?.offline ?? 0)}
          </span>
        </div>
        <div className={styles.statCard}>
          <span className={styles.statLabel}>Events Ingested</span>
          <span className={styles.statValue}>
            {statsLoading ? '...' : (stats?.total_events ?? 0).toLocaleString()}
          </span>
        </div>
      </div>

      {/* Toolbar with Search, Status Filter, and Register Button */}
      <div className={styles.toolbar}>
        <div className={styles.filterGroup}>
          <div className={styles.searchInputWrapper}>
            <LuSearch className={styles.searchIcon} />
            <input
              type="text"
              placeholder="Search by hostname or agent ID..."
              value={search}
              onChange={(e) => {
                setSearch(e.target.value)
                setPage(1)
              }}
              className={styles.searchInput}
            />
          </div>
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value)
              setPage(1)
            }}
            className={styles.statusSelect}
          >
            <option value="all">All Statuses</option>
            <option value="online">Online</option>
            <option value="stale">Stale</option>
            <option value="offline">Offline</option>
            <option value="revoked">Revoked</option>
          </select>
        </div>

        {isAdmin && (
          <button
            type="button"
            className={styles.primaryBtn}
            onClick={() => setRegisterModalOpen(true)}
          >
            <LuPlus />
            Register Agent
          </button>
        )}
      </div>

      {/* Agents Table */}
      <div className={styles.tableWrapper}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th className={styles.th}>Agent</th>
              <th className={styles.th}>Platform</th>
              <th className={styles.th}>Status</th>
              <th className={styles.th}>Last Heartbeat</th>
              <th className={styles.th}>Last Event</th>
              <th className={styles.th}>Total Events</th>
              <th className={styles.th}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {agentsLoading ? (
              Array.from({ length: 4 }, (_, i) => (
                <tr key={`skel-${i}`}>
                  <td className={styles.skeleton} colSpan={7} />
                </tr>
              ))
            ) : agentsData?.items.length === 0 ? (
              <tr>
                <td className={styles.empty} colSpan={7}>
                  No agents found. Click "Register Agent" to onboard your Kali Linux server.
                </td>
              </tr>
            ) : (
              agentsData?.items.map((agent) => (
                <tr key={agent.agent_id}>
                  <td className={styles.td}>
                    <div className={styles.agentNameCell}>
                      <span className={styles.agentTitle}>{agent.name}</span>
                      <span className={styles.agentId}>{agent.agent_id}</span>
                    </div>
                  </td>
                  <td className={styles.td}>
                    {agent.hostname} ({agent.os_type}) v{agent.agent_version}
                  </td>
                  <td className={styles.td}>
                    <span
                      className={`${styles.statusBadge} ${
                        styles[agent.status] || ''
                      }`}
                    >
                      <span className={styles.dot} />
                      {AGENT_STATUS_LABELS[agent.status] || agent.status}
                    </span>
                  </td>
                  <td className={styles.td}>
                    {agent.last_heartbeat_at
                      ? new Date(agent.last_heartbeat_at).toLocaleTimeString()
                      : 'Never'}
                  </td>
                  <td className={styles.td}>
                    {agent.last_event_at
                      ? new Date(agent.last_event_at).toLocaleTimeString()
                      : 'None'}
                  </td>
                  <td className={styles.td}>
                    {agent.total_events_received.toLocaleString()}
                  </td>
                  <td className={styles.td}>
                    <div className={styles.actions}>
                      <button
                        type="button"
                        className={styles.actionBtn}
                        title="View Details"
                        onClick={() => setInspectAgent(agent)}
                      >
                        <LuEye />
                      </button>
                      {isAdmin && !agent.is_revoked && (
                        <>
                          <button
                            type="button"
                            className={styles.actionBtn}
                            title="Rotate Token"
                            onClick={() => handleRotate(agent.agent_id)}
                          >
                            <LuKeyRound />
                          </button>
                          <button
                            type="button"
                            className={`${styles.actionBtn} ${styles.danger}`}
                            title="Revoke Credentials"
                            onClick={() => handleRevoke(agent.agent_id)}
                          >
                            <LuBan />
                          </button>
                        </>
                      )}
                      {isAdmin && (
                        <button
                          type="button"
                          className={`${styles.actionBtn} ${styles.danger}`}
                          title="Delete Agent"
                          onClick={() => handleDelete(agent.agent_id)}
                        >
                          <LuTrash2 />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {agentsData && agentsData.pages > 1 && (
        <div className={styles.pagination}>
          <button
            type="button"
            className={styles.pageBtn}
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
          >
            <LuChevronLeft />
          </button>
          <span className={styles.pageInfo}>
            {page} / {agentsData.pages}
          </span>
          <button
            type="button"
            className={styles.pageBtn}
            disabled={page >= agentsData.pages}
            onClick={() => setPage((p) => p + 1)}
          >
            <LuChevronRight />
          </button>
        </div>
      )}

      {/* Modal: Register Agent */}
      {registerModalOpen && (
        <div className={styles.modalOverlay}>
          <div className={styles.modal}>
            <div className={styles.modalHeader}>
              <h3>Register New Agent</h3>
              <button
                type="button"
                className={styles.closeBtn}
                onClick={() => setRegisterModalOpen(false)}
              >
                <LuX />
              </button>
            </div>

            <form onSubmit={handleRegister} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div className={styles.formGroup}>
                <label>Agent Name / Label</label>
                <input
                  type="text"
                  placeholder="e.g. Kali Linux Production Agent"
                  value={regForm.name}
                  onChange={(e) => setRegForm({ ...regForm, name: e.target.value })}
                  required
                />
              </div>

              <div className={styles.formGroup}>
                <label>Hostname</label>
                <input
                  type="text"
                  placeholder="e.g. kali-target-01"
                  value={regForm.hostname}
                  onChange={(e) => setRegForm({ ...regForm, hostname: e.target.value })}
                  required
                />
              </div>

              <div className={styles.formGroup}>
                <label>Operating System</label>
                <select
                  value={regForm.os_type}
                  onChange={(e) => setRegForm({ ...regForm, os_type: e.target.value })}
                >
                  <option value="linux">Linux (Kali, Ubuntu, Debian)</option>
                  <option value="windows">Windows</option>
                  <option value="macos">macOS</option>
                </select>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '8px' }}>
                <button
                  type="button"
                  className={styles.actionBtn}
                  style={{ width: 'auto', padding: '6px 12px' }}
                  onClick={() => setRegisterModalOpen(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className={styles.primaryBtn}
                  disabled={registerMutation.isPending}
                >
                  {registerMutation.isPending ? 'Provisioning...' : 'Provision Agent'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: New Credentials / One-Time Token Display */}
      {newCredentials && (
        <div className={styles.modalOverlay}>
          <div className={styles.modal}>
            <div className={styles.modalHeader}>
              <h3>Agent Credentials Generated</h3>
              <button
                type="button"
                className={styles.closeBtn}
                onClick={() => {
                  setNewCredentials(null)
                  setRegisterModalOpen(false)
                }}
              >
                <LuX />
              </button>
            </div>

            <div className={styles.tokenAlert}>
              <strong>Notice:</strong> This secret authentication token is displayed <strong>ONLY ONCE</strong>.
              Store it securely in your Kali Linux agent configuration. If lost, it must be rotated.
            </div>

            <div className={styles.formGroup}>
              <label>Agent Identifier</label>
              <div className={styles.tokenBox}>
                <code>{newCredentials.agentId}</code>
                <button
                  type="button"
                  className={styles.copyBtn}
                  onClick={() => copyToClipboard(newCredentials.agentId)}
                >
                  <LuCopy /> Copy
                </button>
              </div>
            </div>

            <div className={styles.formGroup}>
              <label>Authentication Token (Bearer)</label>
              <div className={styles.tokenBox}>
                <code>{newCredentials.token}</code>
                <button
                  type="button"
                  className={styles.copyBtn}
                  onClick={() => copyToClipboard(newCredentials.token)}
                >
                  <LuCopy /> Copy
                </button>
              </div>
            </div>

            <div className={styles.formGroup}>
              <label>Quick Kali Linux Config Snippet</label>
              <div className={styles.codeSnippet}>
{`# /etc/siem-agent/config.yaml
siem_url: "http://${window.location.hostname}:8431/api/v1"
agent_id: "${newCredentials.agentId}"
agent_token: "${newCredentials.token}"
auth_log_path: "/var/log/auth.log"
heartbeat_interval: 30`}
              </div>
            </div>

            <button
              type="button"
              className={styles.primaryBtn}
              style={{ width: '100%', justifyContent: 'center' }}
              onClick={() => {
                setNewCredentials(null)
                setRegisterModalOpen(false)
              }}
            >
              <LuCheck /> I Have Saved My Token
            </button>
          </div>
        </div>
      )}

      {/* Modal: Inspect Agent Details */}
      {inspectAgent && (
        <div className={styles.modalOverlay}>
          <div className={styles.modal}>
            <div className={styles.modalHeader}>
              <h3>Agent Details: {inspectAgent.name}</h3>
              <button
                type="button"
                className={styles.closeBtn}
                onClick={() => setInspectAgent(null)}
              >
                <LuX />
              </button>
            </div>

            <div className={styles.detailRow}>
              <span className={styles.detailLabel}>Agent ID</span>
              <span className={styles.detailVal}>{inspectAgent.agent_id}</span>
            </div>
            <div className={styles.detailRow}>
              <span className={styles.detailLabel}>Hostname</span>
              <span className={styles.detailVal}>{inspectAgent.hostname}</span>
            </div>
            <div className={styles.detailRow}>
              <span className={styles.detailLabel}>Platform</span>
              <span className={styles.detailVal}>{inspectAgent.os_type} v{inspectAgent.agent_version}</span>
            </div>
            <div className={styles.detailRow}>
              <span className={styles.detailLabel}>IP Address</span>
              <span className={styles.detailVal}>{inspectAgent.ip_address || 'Not reported'}</span>
            </div>
            <div className={styles.detailRow}>
              <span className={styles.detailLabel}>Status</span>
              <span
                className={`${styles.statusBadge} ${
                  styles[inspectAgent.status] || ''
                }`}
              >
                <span className={styles.dot} />
                {AGENT_STATUS_LABELS[inspectAgent.status] || inspectAgent.status}
              </span>
            </div>
            <div className={styles.detailRow}>
              <span className={styles.detailLabel}>Registered By</span>
              <span className={styles.detailVal}>{inspectAgent.registered_by || 'system'}</span>
            </div>
            <div className={styles.detailRow}>
              <span className={styles.detailLabel}>Registered At</span>
              <span className={styles.detailVal}>
                {inspectAgent.created_at ? new Date(inspectAgent.created_at).toLocaleString() : 'N/A'}
              </span>
            </div>
            <div className={styles.detailRow}>
              <span className={styles.detailLabel}>Last Heartbeat</span>
              <span className={styles.detailVal}>
                {inspectAgent.last_heartbeat_at ? new Date(inspectAgent.last_heartbeat_at).toLocaleString() : 'Never'}
              </span>
            </div>
            <div className={styles.detailRow}>
              <span className={styles.detailLabel}>Last Event Received</span>
              <span className={styles.detailVal}>
                {inspectAgent.last_event_at ? new Date(inspectAgent.last_event_at).toLocaleString() : 'None'}
              </span>
            </div>
            <div className={styles.detailRow}>
              <span className={styles.detailLabel}>Total Events Forwarded</span>
              <span className={styles.detailVal}>{inspectAgent.total_events_received.toLocaleString()}</span>
            </div>

            {inspectAgent.metrics && Object.keys(inspectAgent.metrics).length > 0 && (
              <div style={{ marginTop: '8px' }}>
                <span className={styles.detailLabel} style={{ fontSize: '11px', textTransform: 'uppercase' }}>
                  System Telemetry:
                </span>
                <div className={styles.codeSnippet}>
                  {JSON.stringify(inspectAgent.metrics, null, 2)}
                </div>
              </div>
            )}

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '12px' }}>
              <button
                type="button"
                className={styles.actionBtn}
                style={{ width: 'auto', padding: '6px 12px' }}
                onClick={() => setInspectAgent(null)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

Component.displayName = 'Agents'
