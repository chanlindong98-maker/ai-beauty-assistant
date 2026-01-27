/**
 * 后端 API 服务
 * 
 * 封装所有与后端的 HTTP 通信
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * 获取本地存储的访问令牌
 */
function getStoredToken(): string | null {
    const tokenData = localStorage.getItem('happy_beauty_token');
    return tokenData;
}

/**
 * 存储访问令牌
 */
function storeToken(token: string): void {
    localStorage.setItem('happy_beauty_token', token);
}

/**
 * 清除存储的令牌
 */
function clearToken(): void {
    localStorage.removeItem('happy_beauty_token');
}

/**
 * 通用请求方法
 */
async function request<T>(
    endpoint: string,
    options: RequestInit = {}
): Promise<T> {
    const token = getStoredToken();

    const headers: HeadersInit = {
        'Content-Type': 'application/json',
        ...options.headers,
    };

    if (token) {
        (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        ...options,
        headers,
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: '请求失败' }));
        throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
}

// ==================== 认证相关 API ====================

export interface AuthResponse {
    success: boolean;
    message: string;
    user: UserProfile | null;
    access_token: string | null;
}

export interface UserProfile {
    id: string;
    username?: string;
    nickname: string;
    device_id: string;
    credits: number;
    referrals_today: number;
    last_referral_date: string;
}

/**
 * 用户注册
 */
export async function register(
    username: string,
    password: string,
    nickname: string,
    referrerId?: string
): Promise<AuthResponse> {
    const result = await request<AuthResponse>('/api/auth/register', {
        method: 'POST',
        body: JSON.stringify({
            username,
            password,
            nickname,
            referrer_id: referrerId,
        }),
    });

    if (result.success && result.access_token) {
        storeToken(result.access_token);
    }

    return result;
}

/**
 * 用户登录
 */
export async function login(
    username: string,
    password: string
): Promise<AuthResponse> {
    const result = await request<AuthResponse>('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify({ username, password }),
    });

    if (result.success && result.access_token) {
        storeToken(result.access_token);
    }

    return result;
}

/**
 * 用户登出
 */
export async function logout(): Promise<void> {
    try {
        await request('/api/auth/logout', { method: 'POST' });
    } finally {
        clearToken();
    }
}

/**
 * 获取当前用户资料
 */
export async function getProfile(): Promise<UserProfile | null> {
    try {
        const result = await request<{ success: boolean; data: UserProfile }>('/api/user/profile');
        return result.success ? result.data : null;
    } catch {
        return null;
    }
}

/**
 * 检查是否已登录
 */
export function isAuthenticated(): boolean {
    return !!getStoredToken();
}

// ==================== AI 服务相关 API ====================

export interface TryOnResult {
    success: boolean;
    message: string;
    image: string | null;
}

export interface AnalyzeResult {
    success: boolean;
    message: string;
    text: string | null;
}

export interface HairstyleResult {
    success: boolean;
    message: string;
    analysis: string | null;
    recommended_image: string | null;
    catalog_image: string | null;
}

/**
 * 云试衣 / 耳饰试戴
 */
export async function tryOn(
    faceImage: string,
    itemImage: string,
    type: 'clothing' | 'accessory',
    height?: number,
    bodyType?: string
): Promise<TryOnResult> {
    return request<TryOnResult>('/api/ai/try-on', {
        method: 'POST',
        body: JSON.stringify({
            face_image: faceImage,
            item_image: itemImage,
            try_on_type: type,
            height,
            body_type: bodyType,
        }),
    });
}

/**
 * 中医 / 面相分析
 */
export async function analyze(
    image: string,
    type: 'tongue' | 'face-analysis' | 'face-reading'
): Promise<AnalyzeResult> {
    return request<AnalyzeResult>('/api/ai/analyze', {
        method: 'POST',
        body: JSON.stringify({
            image,
            analysis_type: type,
        }),
    });
}

/**
 * 发型推荐
 */
export async function generateHairstyleRecommendation(
    image: string,
    gender: '男' | '女',
    age: number
): Promise<HairstyleResult> {
    return request<HairstyleResult>('/api/ai/hairstyle', {
        method: 'POST',
        body: JSON.stringify({ image, gender, age }),
    });
}

// ==================== 导出令牌管理方法（供组件使用） ====================

export { storeToken, clearToken, getStoredToken };
