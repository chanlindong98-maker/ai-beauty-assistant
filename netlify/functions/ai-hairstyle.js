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

const { GoogleGenerativeAI } = require('@google/generative-ai');

/**
 * 从 Gemini 响应中提取图像数据
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
    } catch (e) {
        console.error('[AI] Extract Image Error:', e);
    }
    return '';
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

        const genAI = new GoogleGenerativeAI(apiKey);

        // 文本分析模型
        const textModel = genAI.getGenerativeModel({ model: 'gemini-2.0-flash' });

        // 图像生成模型
        const imageModel = genAI.getGenerativeModel({
            model: 'gemini-2.0-flash-exp',
            generationConfig: {
                responseModalities: ['image', 'text'],
            }
        });

        const isMale = gender === '男';
        const genderTerm = isMale ? '男士' : '女士';
        const maleStyles = '如：寸头、背头、纹理烫等';
        const femaleStyles = '如：法式慵懒卷、波波头、大波浪等';
        const styleGuide = isMale ? maleStyles : femaleStyles;

        const imagePart = {
            inlineData: {
                data: imageData,
                mimeType: 'image/jpeg',
            },
        };

        // 分析脸型
        const analysisPrompt = `你是一位顶级发型设计师。请根据这张照片分析其脸型，并为这位【${age}岁】的【${genderTerm}】推荐10种发型。
        发型款式应涵盖显著差异，${styleGuide}。
        请按以下格式回复：
        1. 脸型分析
        2. 10种推荐发型列表
        3. 最优发型推荐及理由`;

        console.log('[Hairstyle] Analyzing face...');
        const analysisResponse = await textModel.generateContent([imagePart, analysisPrompt]);

        let analysisText = '';
        if (analysisResponse.response.candidates?.[0]?.content?.parts) {
            for (const part of analysisResponse.response.candidates[0].content.parts) {
                if (part.text) {
                    analysisText = part.text;
                    break;
                }
            }
        }
        analysisText = analysisText || '未能生成分析';

        // 生成推荐发型图片
        const recPrompt = `生成一张高度写实的正面照片。
        必须使用原图中的人物面部，为这位${age}岁的人物换上一款完美的${genderTerm}发型。
        背景简洁专业。`;

        console.log('[Hairstyle] Generating recommended hairstyle...');
        const recResponse = await imageModel.generateContent([imagePart, recPrompt]);
        const recImage = extractImage(recResponse.response);

        // 生成发型目录
        const catPrompt = `生成一张${age}岁${genderTerm}的发型参考画报。
        展示10种风格迥异的发型，整齐网格排版。`;

        console.log('[Hairstyle] Generating catalog...');
        const catResponse = await imageModel.generateContent([imagePart, catPrompt]);
        const catImage = extractImage(catResponse.response);

        const vTag = '[20260130-Netlify]';

        if (!recImage || !catImage) {
            let fReason = 'Unknown';
            try {
                fReason = String(recResponse.response.candidates?.[0]?.finishReason || 'Unknown');
            } catch (e) { }

            let safetyMsg = 'None';
            try {
                const risks = (recResponse.response.candidates?.[0]?.safetyRatings || [])
                    .filter(r => r.probability !== 'NEGLIGIBLE')
                    .map(r => `${r.category}:${r.probability}`);
                if (risks.length) safetyMsg = risks.join(',');
            } catch (e) { }

            return jsonResponse({
                success: false,
                message: `${vTag} AI 未能生成发型图像 | 原因: ${fReason} | 风险: ${safetyMsg}`,
                debug: 'Extraction Failed',
            }, 500);
        }

        console.log('[Hairstyle] Success');

        return jsonResponse({
            success: true,
            message: '推荐完成',
            analysis: analysisText,
            recommended_image: `data:image/jpeg;base64,${recImage}`,
            catalog_image: `data:image/jpeg;base64,${catImage}`,
        });

    } catch (e) {
        const msg = e.message || String(e);
        return jsonResponse({ success: false, message: `推荐失败: ${msg}` }, 500);
    }
};
