/**
 * 用户登录 API
 * POST /.netlify/functions/auth-login
 */

const { getSupabaseClient, jsonResponse, handleOptions, parseBody } = require('./utils');

exports.handler = async (event, context) => {
    // 处理 CORS 预检请求
    if (event.httpMethod === 'OPTIONS') {
        return handleOptions();
    }

    if (event.httpMethod !== 'POST') {
        return jsonResponse({ success: false, message: '不支持的请求方法' }, 405);
    }

    try {
        const data = parseBody(event);
        const { username, password } = data;

        if (!username || !password) {
            return jsonResponse({ success: false, message: '请输入用户名和密码哦 🍬' }, 400);
        }

        const supabase = getSupabaseClient();
        const email = `${username}@happy-beauty.local`;

        // 登录
        const { data: authData, error: authError } = await supabase.auth.signInWithPassword({
            email,
            password,
        });

        if (authError || !authData.user) {
            return jsonResponse({ success: false, message: '用户名或密码不对哦，再试一次吧' }, 400);
        }

        const userId = authData.user.id;

        // 获取用户资料
        const { data: profile, error: profileError } = await supabase
            .from('user_profiles')
            .select('*')
            .eq('id', userId)
            .single();

        if (profileError || !profile) {
            return jsonResponse({ success: false, message: '找不到您的魔法档案，请重新注册' }, 404);
        }

        return jsonResponse({
            success: true,
            message: '欢迎回来！✨',
            user: {
                nickname: profile.nickname,
                device_id: profile.device_id,
                credits: profile.credits,
                referrals_today: profile.referrals_today || 0,
                last_referral_date: profile.last_referral_date || '',
                is_admin: profile.is_admin || false,
            },
            access_token: authData.session?.access_token || null,
        });

    } catch (e) {
        const errorMsg = e.message || String(e);
        let userMsg = `登录失败: ${errorMsg}`;
        let statusCode = 500;

        if (errorMsg.toLowerCase().includes('credentials') || errorMsg.toLowerCase().includes('invalid')) {
            userMsg = '用户名或密码不对哦 🍭';
            statusCode = 401;
        } else if (errorMsg.includes('Supabase 环境变量')) {
            userMsg = '配置错误：请检查环境变量设置';
        }

        return jsonResponse({ success: false, message: userMsg, detail: errorMsg }, statusCode);
    }
};
