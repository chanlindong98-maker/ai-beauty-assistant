/**
 * 用户注册 API
 * POST /.netlify/functions/auth-register
 */

const { getSupabaseClient, jsonResponse, handleOptions, parseBody } = require('./utils');
const { v4: uuidv4 } = require('uuid');

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
        const { username, password, nickname, referrer_id: referrerId } = data;

        if (!username || !password || !nickname) {
            return jsonResponse({ success: false, message: '注册信息不完整哦 🍭' }, 400);
        }

        const supabase = getSupabaseClient();
        const email = `${username}@happy-beauty.local`;

        // 使用 Admin API 直接创建用户，避免邮件验证问题
        const { data: authData, error: authError } = await supabase.auth.admin.createUser({
            email,
            password,
            email_confirm: true, // 直接标记为已验证
            user_metadata: { nickname }
        });

        if (authError || !authData.user) {
            console.error('Supabase Auth registry error:', authError);
            return jsonResponse({
                success: false,
                message: '注册失败了，请看详细错误提示 🍬',
                detail: authError?.message || '未知认证错误'
            }, 400);
        }

        const userId = authData.user.id;
        const deviceId = uuidv4().replace(/-/g, '').substring(0, 12);
        const today = new Date().toISOString().split('T')[0];

        // 创建用户资料
        const profileData = {
            id: userId,
            nickname,
            device_id: deviceId,
            credits: 3,
            referrals_today: 0,
            last_referral_date: today,
            referrer_id: null,
        };

        // 推荐逻辑
        if (referrerId) {
            try {
                const { data: referrerData } = await supabase
                    .from('user_profiles')
                    .select('*')
                    .eq('device_id', referrerId)
                    .single();

                if (referrerData) {
                    const currentReferrals = referrerData.last_referral_date === today
                        ? referrerData.referrals_today
                        : 0;

                    if (currentReferrals < 5) {
                        await supabase
                            .from('user_profiles')
                            .update({
                                credits: referrerData.credits + 1,
                                referrals_today: currentReferrals + 1,
                                last_referral_date: today,
                            })
                            .eq('id', referrerData.id);

                        profileData.referrer_id = referrerData.id;
                    }
                }
            } catch (e) {
                // 推荐失败不影响主流程
                console.error('Referral error:', e);
            }
        }

        await supabase.from('user_profiles').insert(profileData);

        return jsonResponse({
            success: true,
            message: '注册成功！✨',
            user: {
                nickname,
                device_id: deviceId,
                credits: 3,
                referrals_today: 0,
                last_referral_date: today,
                is_admin: false,
            },
            access_token: authData.session?.access_token || null,
        });

    } catch (e) {
        const errorMsg = e.message || String(e);
        let userMsg = `服务器内部错误: ${errorMsg}`;
        let statusCode = 500;

        if (errorMsg.toLowerCase().includes('already registered')) {
            userMsg = '该用户名已经有人用了哦，换一个吧 🍬';
            statusCode = 400;
        } else if (errorMsg.includes('Supabase 环境变量')) {
            userMsg = '配置错误：请在 Netlify 检查 SUPABASE_URL 环境变量';
        }

        return jsonResponse({ success: false, message: userMsg, detail: errorMsg }, statusCode);
    }
};
