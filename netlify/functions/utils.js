/**
 * Netlify Functions 共享工具模块
 */

const { createClient } = require('@supabase/supabase-js');

/**
 * 获取 Supabase 客户端
 */
function getSupabaseClient() {
    const url = process.env.SUPABASE_URL || '';
    const key = process.env.SUPABASE_SERVICE_ROLE_KEY || '';

    if (!url || !key) {
        throw new Error('缺少 Supabase 环境变量 (SUPABASE_URL 或 SUPABASE_SERVICE_ROLE_KEY)');
    }

    if (!key.startsWith('eyJ')) {
        throw new Error('SUPABASE_SERVICE_ROLE_KEY 格式不正确。请确保使用的是 Service Role (Secret) Key。');
    }

    return createClient(url, key);
}

/**
 * CORS 响应头
 */
function corsHeaders() {
    return {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    };
}

/**
 * 创建 JSON 响应
 */
function jsonResponse(data, statusCode = 200) {
    return {
        statusCode,
        headers: {
            'Content-Type': 'application/json',
            ...corsHeaders(),
        },
        body: JSON.stringify(data),
    };
}

/**
 * 处理 OPTIONS 预检请求
 */
function handleOptions() {
    return {
        statusCode: 200,
        headers: corsHeaders(),
        body: '',
    };
}

/**
 * 从请求中获取认证令牌
 */
function getAuthToken(event) {
    const auth = event.headers.authorization || event.headers.Authorization || '';
    if (auth.startsWith('Bearer ')) {
        return auth.substring(7);
    }
    return null;
}

/**
 * 从 token 获取用户信息
 */
async function getUserFromToken(token) {
    if (!token) return null;

    try {
        const supabase = getSupabaseClient();
        const { data: { user }, error } = await supabase.auth.getUser(token);

        if (error || !user) return null;

        // 获取用户资料
        const { data: profile } = await supabase
            .from('user_profiles')
            .select('*')
            .eq('id', user.id)
            .single();

        if (profile) {
            return {
                id: user.id,
                email: user.email,
                ...profile,
            };
        }
    } catch (e) {
        console.error('getUserFromToken error:', e);
    }

    return null;
}

/**
 * 获取并验证管理员用户
 */
async function getAdminUser(token) {
    const user = await getUserFromToken(token);
    if (user && user.is_admin) {
        return user;
    }
    return null;
}

/**
 * 解析请求体
 */
function parseBody(event) {
    try {
        if (!event.body) return {};
        return JSON.parse(event.body);
    } catch (e) {
        return {};
    }
}

/**
 * 获取动态配置项
 * 优先从数据库 system_config 表读取，如果不存在则回退到环境变量
 */
async function getConfig(key, defaultValue = '') {
    // 1. 尝试从数据库读取
    try {
        const supabase = getSupabaseClient();
        const { data } = await supabase
            .from('system_config')
            .select('value')
            .eq('key', key)
            .single();

        if (data && data.value) {
            return data.value;
        }
    } catch (e) {
        // 数据库读取失败，继续尝试环境变量
    }

    // 2. 回退到环境变量
    const envKey = key.toUpperCase();
    const envValue = process.env[envKey] || '';
    if (envValue) {
        return envValue;
    }

    return defaultValue;
}

/**
 * 扣减魔法值
 */
async function consumeCredit(userId, currentCredits) {
    if (currentCredits <= 0) {
        return false;
    }

    const supabase = getSupabaseClient();
    await supabase
        .from('user_profiles')
        .update({ credits: currentCredits - 1 })
        .eq('id', userId);

    return true;
}

module.exports = {
    getSupabaseClient,
    corsHeaders,
    jsonResponse,
    handleOptions,
    getAuthToken,
    getUserFromToken,
    getAdminUser,
    parseBody,
    getConfig,
    consumeCredit,
};
