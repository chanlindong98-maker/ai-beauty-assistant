/**
 * 管理后台 API
 * GET/POST /.netlify/functions/admin
 */

const {
    getSupabaseClient,
    jsonResponse,
    handleOptions,
    getAuthToken,
    getAdminUser,
    parseBody
} = require('./utils');

exports.handler = async (event, context) => {
    // 处理 CORS 预检请求
    if (event.httpMethod === 'OPTIONS') {
        return handleOptions();
    }

    try {
        const method = event.httpMethod;

        // 解析 action 参数
        const params = event.queryStringParameters || {};
        let action = params.action;

        // 如果没有 action 参数，从路径中推断
        if (!action) {
            const rawPath = event.path.toLowerCase();
            if (rawPath.includes('stats')) action = 'stats';
            else if (rawPath.includes('users')) action = 'users';
            else if (rawPath.includes('credits')) action = 'credits';
            else if (rawPath.includes('config')) action = 'config';
            else if (rawPath.includes('password')) action = 'password';
        }

        console.log(`[Admin API] ${method} ${event.path} -> ${action}`);

        // 权限检查
        const token = getAuthToken(event);
        const admin = await getAdminUser(token);

        if (!admin) {
            return jsonResponse({ success: false, message: '需要管理员权限，请重新登录' }, 403);
        }

        const supabase = getSupabaseClient();

        // [Stats] 营收统计
        if (action === 'stats' && method === 'GET') {
            const { count: totalUsers } = await supabase
                .from('user_profiles')
                .select('id', { count: 'exact', head: true });

            const { data: ordersData } = await supabase
                .from('orders')
                .select('amount')
                .eq('status', 'PAID');

            const amounts = (ordersData || [])
                .filter(i => i.amount)
                .map(i => parseFloat(i.amount));

            const today = new Date().toISOString().split('T')[0];
            const { data: todayOrdersData } = await supabase
                .from('orders')
                .select('amount')
                .eq('status', 'PAID')
                .gte('created_at', `${today}T00:00:00`);

            const todayAmounts = (todayOrdersData || [])
                .filter(i => i.amount)
                .map(i => parseFloat(i.amount));

            return jsonResponse({
                total_users: totalUsers || 0,
                total_recharge_amount: amounts.reduce((a, b) => a + b, 0),
                today_recharge_amount: todayAmounts.reduce((a, b) => a + b, 0),
                total_orders: amounts.length,
                active_users_24h: totalUsers || 0,
            });
        }

        // [Users] 会员列表
        if (action === 'users' && method === 'GET') {
            const query = params.query;
            let builder = supabase.from('user_profiles').select('*');

            if (query) {
                builder = builder.ilike('nickname', `%${query}%`);
            }

            const { data } = await builder.order('id').limit(100);

            const result = (data || []).map(i => ({
                id: i.id,
                nickname: i.nickname,
                credits: i.credits || 0,
                is_admin: i.is_admin || false,
            }));

            return jsonResponse(result);
        }

        // [Credits] 修改魔法值
        if (action === 'credits' && method === 'POST') {
            const body = parseBody(event);
            const userId = body.user_id;
            const creditsVal = body.credits || 0;
            const mode = body.mode || 'set';

            if (!userId) {
                return jsonResponse({ success: false, message: '缺少用户 ID' }, 400);
            }

            let newCredits;
            if (mode === 'add') {
                const { data: curr } = await supabase
                    .from('user_profiles')
                    .select('credits')
                    .eq('id', userId)
                    .single();

                const base = curr?.credits || 0;
                newCredits = base + parseInt(creditsVal, 10);
            } else {
                newCredits = parseInt(creditsVal, 10);
            }

            newCredits = Math.max(0, newCredits);

            await supabase
                .from('user_profiles')
                .update({ credits: newCredits })
                .eq('id', userId);

            return jsonResponse({
                success: true,
                message: `成功更新为 ${newCredits} 次`,
                new_credits: newCredits,
            });
        }

        // [Config] 系统设置
        if (action === 'config') {
            if (method === 'GET') {
                const { data: dbConfig } = await supabase
                    .from('system_config')
                    .select('*');

                const configMap = {};
                (dbConfig || []).forEach(item => {
                    configMap[item.key] = item;
                });

                const essentialKeys = [
                    ['gemini_api_key', 'Gemini API 密钥', process.env.GEMINI_API_KEY || ''],
                    ['alipay_app_id', '支付宝 AppID', process.env.ALIPAY_APP_ID || ''],
                    ['alipay_app_private_key', '支付宝应用私钥', process.env.ALIPAY_APP_PRIVATE_KEY || ''],
                    ['alipay_public_key', '支付宝公钥', process.env.ALIPAY_PUBLIC_KEY || ''],
                    ['alipay_notify_url', '支付宝异步回调地址', process.env.ALIPAY_NOTIFY_URL || ''],
                    ['alipay_return_url', '支付宝同步跳转地址', process.env.ALIPAY_RETURN_URL || ''],
                ];

                const result = [];
                const added = new Set();

                for (const [key, desc, envVal] of essentialKeys) {
                    if (configMap[key]) {
                        result.push(configMap[key]);
                    } else {
                        result.push({ key, value: envVal, description: desc });
                    }
                    added.add(key);
                }

                for (const item of (dbConfig || [])) {
                    if (!added.has(item.key)) {
                        result.push(item);
                    }
                }

                return jsonResponse(result);
            }

            if (method === 'POST') {
                const items = parseBody(event);

                for (const it of items) {
                    if (it.key) {
                        await supabase.from('system_config').upsert({
                            key: it.key,
                            value: it.value,
                            description: it.description || '',
                            updated_at: new Date().toISOString(),
                        });
                    }
                }

                return jsonResponse({ success: true });
            }
        }

        // [Password] 重置密码
        if (action === 'password' && method === 'POST') {
            const body = parseBody(event);
            const pwd = body.new_password;

            if (!pwd || pwd.length < 6) {
                return jsonResponse({ success: false, message: '密码过短' }, 400);
            }

            await supabase.auth.admin.updateUserById(admin.id, { password: pwd });

            return jsonResponse({ success: true });
        }

        return jsonResponse({ success: false, message: `Unsupported action: ${action}` }, 404);

    } catch (e) {
        console.error('[Admin API Error]', e);
        return jsonResponse({ success: false, message: `API Error: ${e.message}` }, 500);
    }
};
