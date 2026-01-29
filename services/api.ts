/// <reference types="vite/client" />
/**
 * 后端 API 服务
 * 
 * 封装所有与后端的 HTTP 通信
 */

// 在 Vercel 部署时使用相对路径，本地开发时可指定后端地址
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || (import.meta.env.DEV ? 'http://127.0.0.1:8000' : '');

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
 * 获取或生成持久化的设备 ID (一机一码)
 */
function getPersistentDeviceId(): string {
    let deviceId = localStorage.getItem('happy_beauty_device_id');
    if (!deviceId) {
        // 生成 12 位 16 进制随机字符串
        deviceId = Math.random().toString(16).substring(2, 14);
        localStorage.setItem('happy_beauty_device_id', deviceId);
    }
    return deviceId;
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

        let message = '';
        if (Array.isArray(error.detail)) {
            // FastAPI 验证错误通常返回一个包含 loc, msg, type 的对象列表
            message = error.detail.map((d: any) => d.msg || JSON.stringify(d)).join('; ');
        } else {
            message = error.detail || `HTTP ${response.status}`;
        }

        throw new Error(message);
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

export interface GenericResponse<T = any> {
    success: boolean;
    message: string;
    data?: T;
}

export interface UserProfile {
    id: string;
    username?: string;
    nickname: string;
    device_id: string;
    credits: number;
    referrals_today: number;
    last_referral_date: string;
    is_admin: boolean;
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
            device_id: getPersistentDeviceId(),
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
    } catch (error: any) {
        // 如果是 401 认证错误，说明 token 已失效，清除本地缓存
        if (error.message && error.message.includes('401')) {
            clearToken();
        }
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

/**
 * 兑换码兑换
 */
export async function redeemCode(code: string): Promise<GenericResponse<{ credits: number }>> {
    return request<GenericResponse>('/api/user/redeem', {
        method: 'POST',
        body: JSON.stringify({ code }),
    });
}

// ==================== 支付相关 API ====================

export interface CreateOrderResponse {
    success: boolean;
    message: string;
    pay_url: string | null;
    order_id: string | null;
}

/**
 * 创建支付宝订单
 */
export async function createAlipayOrder(amount: number, credits: number): Promise<CreateOrderResponse> {
    return request<CreateOrderResponse>('/api/payment/alipay/create', {
        method: 'POST',
        body: JSON.stringify({ amount, credits }),
    });
}

// ==================== 管理后台 API ====================

export interface DashboardStats {
    total_users: number;
    total_recharge_amount: number;
    today_recharge_amount: number;
    total_orders: number;
    active_users_24h: number;
}

export interface AdminUserDetail {
    id: string;
    nickname: string;
    email: string | null;
    credits: number;
    is_admin: boolean;
}

export interface SystemConfigItem {
    key: string;
    value: string;
    description: string | null;
}

/**
 * 获取仪表盘统计
 */
export async function getAdminStats(): Promise<DashboardStats> {
    return request<DashboardStats>('/api/admin/dashboard/stats');
}

/**
 * 获取会员列表
 */
export async function getAdminUsers(query?: string): Promise<AdminUserDetail[]> {
    const url = query ? `/api/admin/users?query=${encodeURIComponent(query)}` : '/api/admin/users';
    return request<AdminUserDetail[]>(url);
}

/**
 * 修改用户魔法值
 */
export async function updateAdminUserCredits(userId: string, credits: number, mode: 'set' | 'add'): Promise<any> {
    return request('/api/admin/users/credits', {
        method: 'POST',
        body: JSON.stringify({ user_id: userId, credits, mode }),
    });
}

/**
 * 获取系统配置
 */
export async function getAdminConfig(): Promise<SystemConfigItem[]> {
    return request<SystemConfigItem[]>('/api/admin/config');
}

/**
 * 更新系统配置
 */
export async function updateAdminConfig(items: SystemConfigItem[]): Promise<any> {
    return request('/api/admin/config/update', {
        method: 'POST',
        body: JSON.stringify(items),
    });
}

/**
 * 修改管理员密码
 */
export async function resetAdminPassword(newPassword: string): Promise<any> {
    return request('/api/admin/reset-password', {
        method: 'POST',
        body: JSON.stringify({ new_password: newPassword }),
    });
}

// ==================== 导出令牌管理方法（供组件使用） ====================

export { storeToken, clearToken, getStoredToken };
