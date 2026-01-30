/**
 * 获取用户资料 API
 * GET /.netlify/functions/user-profile
 */

const { getSupabaseClient, jsonResponse, handleOptions, getAuthToken } = require('./utils');

exports.handler = async (event, context) => {
    // 处理 CORS 预检请求
    if (event.httpMethod === 'OPTIONS') {
        return handleOptions();
    }

    if (event.httpMethod !== 'GET') {
        return jsonResponse({ success: false, message: '不支持的请求方法' }, 405);
    }

    try {
        // 获取 token
        const token = getAuthToken(event);
        if (!token) {
            return jsonResponse({ success: false, message: '未授权' }, 401);
        }

        const supabase = getSupabaseClient();

        // 验证 token
        const { data: { user }, error: userError } = await supabase.auth.getUser(token);
        if (userError || !user) {
            return jsonResponse({ success: false, message: '无效的令牌' }, 401);
        }

        const userId = user.id;

        // 获取用户资料
        const { data: profile, error: profileError } = await supabase
            .from('user_profiles')
            .select('*')
            .eq('id', userId)
            .single();

        if (profileError || !profile) {
            return jsonResponse({ success: false, message: '用户资料不存在' }, 404);
        }

        return jsonResponse({
            success: true,
            message: '获取成功',
            data: {
                id: userId,
                nickname: profile.nickname,
                device_id: profile.device_id,
                credits: profile.credits,
                referrals_today: profile.referrals_today,
                last_referral_date: profile.last_referral_date,
                is_admin: profile.is_admin || false,
            },
        });

    } catch (e) {
        return jsonResponse({ success: false, message: `获取失败: ${e.message}` }, 500);
    }
};
