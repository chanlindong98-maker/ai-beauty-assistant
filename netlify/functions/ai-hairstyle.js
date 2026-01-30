/**
 * 发型推荐 API
 * POST /.netlify/functions/ai-hairstyle
 */

const {
    getSupabaseClient,
    jsonResponse,
    handleOptions,
    getAuthToken,
    getUserFromToken,
    parseBody,
    getConfig,
    consumeCredit
} = require('./utils');

/**
 * 从 API 响应中提取图像数据
 */
function extractImage(result) {
    try {
        if (result.candidates && result.candidates[0]?.content?.parts) {
            for (const part of result.candidates[0].content.parts) {
                if (part.inlineData) {
                    return part.inlineData.data;
                }
            }
        }
    } catch (e) { }
    return '';
}

/**
 * 发送请求到 Gemini REST API
 */
async function callGemini(apiKey, payload) {
    const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${apiKey}`;
    const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
    const result = await response.json();
    if (!response.ok) {
        throw new Error(result.error?.message || response.statusText);
    }
    return result;
}

exports.handler = async (event, context) => {
    // 处理 CORS 预检请求
    if (event.httpMethod === 'OPTIONS') {
        return handleOptions();
    }

    if (event.httpMethod !== 'POST') {
        return jsonResponse({ success: false, message: '不支持的请求方法' }, 405);
    }

    try {
        // 验证用户
        const token = getAuthToken(event);
        const user = await getUserFromToken(token);

        if (!user) {
            return jsonResponse({ success: false, message: '未授权' }, 401);
        }

        // 检查并扣减魔法值
        if (!(await consumeCredit(user.id, user.credits))) {
            return jsonResponse({ success: false, message: '魔法值不足' }, 402);
        }

        // 解析请求
        const data = parseBody(event);
        const image = data.image || '';
        const gender = data.gender || '女';
        const age = data.age || 25;

        const imageData = image.includes(',') ? image.split(',')[1] : image;

        // 配置 Gemini
        const apiKey = await getConfig('gemini_api_key');
        if (!apiKey) {
            return jsonResponse({ success: false, message: '未配置 Gemini API 密钥，请在管理后台设置' }, 500);
        }

        const genderTerm = gender === '男' ? '男士' : '女士';
        const styleGuide = gender === '男' ? '如：寸头、背头、纹理烫等' : '如：法式慵懒卷、波波头、大波浪等';

        // 1. 分析脸型 (文本)
        console.log('[Hairstyle] Analyzing face...');
        const analysisResult = await callGemini(apiKey, {
            contents: [{
                parts: [
                    { inline_data: { mime_type: 'image/jpeg', data: imageData } },
                    { text: `你是一位顶级发型设计师。请根据这张照片分析其脸型，并为这位【${age}岁】的【${genderTerm}】推荐10种发型。发型款式应涵盖显著差异，${styleGuide}。请按以下格式回复：1. 脸型分析 2. 10种推荐发型列表 3. 最优发型推荐及理由` }
                ]
            }]
        });

        const analysisText = analysisResult.candidates?.[0]?.content?.parts?.[0]?.text || '未能生成分析';

        // 2. 生成推荐发型图片 (图像)
        console.log('[Hairstyle] Generating recommended hairstyle...');
        const recResult = await callGemini(apiKey, {
            contents: [{
                parts: [
                    { inline_data: { mime_type: 'image/jpeg', data: imageData } },
                    { text: `生成一张高度写实的正面照片。必须使用原图中的人物面部，为这位${age}岁的人物换上一款完美的${genderTerm}发型。背景简洁专业。` }
                ]
            }],
            generationConfig: { responseModalities: ["IMAGE"] }
        });
        const recImage = extractImage(recResult);

        // 3. 生成发型目录 (图像)
        console.log('[Hairstyle] Generating catalog...');
        const catResult = await callGemini(apiKey, {
            contents: [{
                parts: [
                    { inline_data: { mime_type: 'image/jpeg', data: imageData } },
                    { text: `生成一张${age}岁${genderTerm}的发型参考画报。展示10种风格迥异的发型，整齐网格排版。` }
                ]
            }],
            generationConfig: { responseModalities: ["IMAGE"] }
        });
        const catImage = extractImage(catResult);

        if (!recImage || !catImage) {
            return jsonResponse({
                success: false,
                message: `AI 未能完全生成发型图像 (可能是安全过滤或资源受限)`,
                detail: 'Missing image output'
            }, 500);
        }

        return jsonResponse({
            success: true,
            message: '推荐完成',
            analysis: analysisText,
            recommended_image: `data:image/jpeg;base64,${recImage}`,
            catalog_image: `data:image/jpeg;base64,${catImage}`,
        });

    } catch (e) {
        console.error('[Hairstyle] Fatal Error:', e);
        return jsonResponse({ success: false, message: `推荐过程异常: ${e.message || String(e)}` }, 500);
    }
};
