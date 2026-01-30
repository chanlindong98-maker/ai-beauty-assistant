/**
 * 兑换码兑换 API
 * POST /.netlify/functions/user-redeem
 */

const { getSupabaseClient, jsonResponse, handleOptions, getAuthToken, getUserFromToken, parseBody } = require('./utils');

exports.handler = async (event, context) => {
    // 处理 CORS 预检请求
    if (event.httpMethod === 'OPTIONS') {
        return handleOptions();
    }

    if (event.httpMethod !== 'POST') {
        return jsonResponse({ success: false, message: '不支持的请求方法' }, 405);
    }

    const token = getAuthToken(event);
    const user = await getUserFromToken(token);

    if (!user) {
        return jsonResponse({ success: false, message: '请先登录哦 🍭' }, 401);
    }

    try {
        const data = parseBody(event);
        const code = (data.code || '').trim();

        // 正则验证兑换码
        const pattern = /^(\d{2})(\d+)([A-Z]{4})(\d{2})([a-z]{2})$/;
        const match = code.match(pattern);

        if (!match) {
            return jsonResponse({ success: false, message: '兑换码格式不对哦，请检查一下~' }, 400);
        }

        const [, todayDd, creditsStr, , laterDd] = match;

        // 验证日期
        const today = new Date();
        const later = new Date(today);
        later.setDate(later.getDate() + 13);

        const todayDD = String(today.getDate()).padStart(2, '0');
        const laterDD = String(later.getDate()).padStart(2, '0');

        if (todayDd !== todayDD || laterDd !== laterDD) {
            return jsonResponse({ success: false, message: '哎呀，这个兑换码不是今天的，或者已经过期了。' }, 400);
        }

        const creditsToAdd = parseInt(creditsStr, 10);
        const supabase = getSupabaseClient();

        // 检查重复
        const { data: checkData } = await supabase
            .from('used_redeem_codes')
            .select('code')
            .eq('code', code);

        if (checkData && checkData.length > 0) {
            return jsonResponse({ success: false, message: '这个兑换码已经用过啦，不能重复使用哦。' }, 400);
        }

        // 记录并更新
        await supabase.from('used_redeem_codes').insert({
            code,
            user_id: user.id,
            credits_added: creditsToAdd,
        });

        const newCredits = user.credits + creditsToAdd;
        await supabase
            .from('user_profiles')
            .update({ credits: newCredits })
            .eq('id', user.id);

        return jsonResponse({
            success: true,
            message: `兑换成功！获得了 ${creditsToAdd} 次魔法能量 ✨`,
            data: { credits: newCredits },
        });

    } catch (e) {
        return jsonResponse({ success: false, message: `兑换过程中出错了: ${e.message}` }, 500);
    }
};
