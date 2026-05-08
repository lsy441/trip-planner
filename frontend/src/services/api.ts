import axios from 'axios'
import type { TripFormData, TripPlanResponse, FeedbackRequest } from '@/types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000, // 5分钟超时
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    console.log('发送请求:', config.method?.toUpperCase(), config.url)
    return config
  },
  (error) => {
    console.error('请求错误:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => {
    console.log('收到响应:', response.status, response.config.url)
    return response
  },
  (error) => {
    console.error('响应错误:', error.response?.status, error.message)
    return Promise.reject(error)
  }
)

/**
 * 生成旅行计划
 */
export async function generateTripPlan(formData: TripFormData): Promise<TripPlanResponse> {
  try {
    const response = await apiClient.post<TripPlanResponse>('/api/trip/plan', formData)
    return response.data
  } catch (error: any) {
    console.error('生成旅行计划失败:', error)
    throw new Error(error.response?.data?.detail || error.message || '生成旅行计划失败')
  }
}

/**
 * 健康检查
 */
export async function healthCheck(): Promise<any> {
  try {
    const response = await apiClient.get('/api/trip/health')
    return response.data
  } catch (error: any) {
    console.error('健康检查失败:', error)
    throw new Error(error.message || '健康检查失败')
  }
}

/**
 * 基于反馈调整旅行计划 (LangGraph v2.0 反馈机制)
 */
export async function updatePlanWithFeedback(feedbackReq: FeedbackRequest): Promise<TripPlanResponse> {
  try {
    const response = await apiClient.post<TripPlanResponse>('/api/trip/feedback', feedbackReq)
    return response.data
  } catch (error: any) {
    console.error('反馈调整失败:', error)
    throw new Error(error.response?.data?.detail || error.message || '反馈调整失败')
  }
}

/**
 * SSE流式生成旅行计划 - 实时进度
 */
export async function generateTripPlanStream(
  formData: TripFormData,
  onProgress?: (message: string) => void
): Promise<TripPlanResponse> {
  const url = `${API_BASE_URL}/api/trip/plan-stream`

  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(formData)
  })

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`)
  }

  const reader = response.body?.getReader()
  if (!reader) {
    throw new Error('不支持流式响应')
  }

  return new Promise((resolve, reject) => {
    const decoder = new TextDecoder()
    let buffer = ''

    function readStream() {
      reader?.read().then(({ done, value }) => {
        if (done) {
          reject(new Error('流结束无结果'))
          return
        }

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              if (data.type === 'progress' && onProgress) {
                onProgress(data.message)
              } else if (data.type === 'result') {
                resolve(data as unknown as TripPlanResponse)
              } else if (data.type === 'error') {
                reject(new Error(data.message))
              }
            } catch (e) { }
          }
        }

        readStream()
      }).catch(reject)
    }

    readStream()
  })
}

export interface SessionInfo {
  session_id: string
  title: string
  message_count: number
  updated_at: string | null
}

export interface SessionDetail {
  session_id: string
  messages: { role: string; content: string }[]
}

export async function getChatSessions(): Promise<SessionInfo[]> {
  try {
    const response = await apiClient.get<{ sessions: SessionInfo[] }>('/api/chat/sessions')
    return response.data.sessions
  } catch (error: any) {
    console.error('获取会话列表失败:', error)
    return []
  }
}

export async function getChatSession(sessionId: string): Promise<SessionDetail | null> {
  try {
    const response = await apiClient.get<SessionDetail>(`/api/chat/sessions/${sessionId}`)
    return response.data
  } catch (error: any) {
    console.error('获取会话详情失败:', error)
    return null
  }
}

export async function deleteChatSession(sessionId: string): Promise<boolean> {
  try {
    await apiClient.delete(`/api/chat/sessions/${sessionId}`)
    return true
  } catch (error: any) {
    console.error('删除会话失败:', error)
    return false
  }
}

export default apiClient

