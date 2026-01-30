/**
 * API 连通性测试
 * GET /.netlify/functions/ping
 */

const { jsonResponse, handleOptions } = require('./utils');

exports.handler = async (event, context) => {
    // 处理 CORS 预检请求
    if (event.httpMethod === 'OPTIONS') {
        return handleOptions();
    }

    // 获取环境变量（脱敏处理）
    const supabaseUrl = process.env.SUPABASE_URL || '未设置';
    const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY || '未设置';

    function maskKey(k) {
        if (k === '未设置') return k;
        if (k.length < 8) return `太短(${k.length}位)`;
        return `${k.substring(0, 4)}...${k.substring(k.length - 4)} (长度: ${k.length})`;
    }

    // 简单判断 Key 格式
    const isJwt = serviceKey.startsWith('eyJ');

    return jsonResponse({
        success: true,
        message: 'API 连通性测试成功！✨',
        diagnostics: {
            SUPABASE_URL: supabaseUrl,
            SUPABASE_SERVICE_ROLE_KEY: maskKey(serviceKey),
            KEY_FORMAT_IS_JWT: isJwt,
            NODE_VERSION: process.version,
            PLATFORM: 'Netlify Functions',
        },
    });
};
