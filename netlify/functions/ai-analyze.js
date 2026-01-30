/**
 * 中医分析 / 面相分析 API
 * POST /.netlify/functions/ai-analyze
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
        const analysisType = data.analysis_type || 'tongue';

        const imageData = image.includes(',') ? image.split(',')[1] : image;

        // 配置 Gemini
        const apiKey = await getConfig('gemini_api_key');
        if (!apiKey) {
            return jsonResponse({ success: false, message: '未配置 Gemini API 密钥，请在管理后台设置' }, 500);
        }

        const genAI = new GoogleGenerativeAI(apiKey);
        const model = genAI.getGenerativeModel({ model: 'gemini-2.0-flash' });

        // 构建提示词
        let systemInstruction = '你是一位拥有深厚底蕴的中医及传统文化学者。';
        let prompt;

        if (analysisType === 'tongue') {
            systemInstruction += '你拥有30年中医临床经验，擅长舌诊。';
            prompt = `请根据这张舌头照片进行中医分析：
            1. 观察舌质：包括颜色（淡红、红、绛、青紫等）、形态（胖大、瘦小、有无齿痕、裂纹）。
            2. 观察舌苔：包括颜色（白、黄、灰、黑）、厚薄、润燥。
            3. 综合判断：结合舌象推断可能的脏腑状况、气血阴阳平衡情况。
            4. 调理建议：给出饮食、作息、情志及简单穴位按摩的建议。
            请用中文分段回复。`;
        } else if (analysisType === 'face-analysis') {
            systemInstruction += '你拥有30年中医临床经验，擅长面诊。';
            prompt = `请根据这张人脸照片进行中医面诊分析：
            1. 面色分析：观察面色及其分布，对应五脏健康状况。
            2. 气色神态：分析眼神、皮肤光泽度所体现的精气神。
            3. 身体状况推断：基于中医理论推断身体状况。
            4. 调理建议：给出针对性的健康调理方案。
            请用中文分段回复。`;
        } else {
            // face-reading
            systemInstruction += '你是一位精通中国传统相术的大师。';
            prompt = `请根据这张正面人脸照片进行面相分析：
            1. 性格分析：通过眼神、眉形等分析性格特征。
            2. 健康运势：分析健康素质。
            3. 财运事业：分析职业发展潜力。
            4. 命运总括：给出富有智慧的总结和建议。
            请用中文分段回复，需说明仅供参考。`;
        }

        const imagePart = {
            inlineData: {
                data: imageData,
                mimeType: 'image/jpeg',
            },
        };

        const fullPrompt = `${systemInstruction}\n\n${prompt}`;

        console.log('[Analyze] Calling Gemini API...');

        const response = await model.generateContent([imagePart, fullPrompt]);
        const result = response.response;

        let resultText = '';
        if (result.candidates && result.candidates[0]?.content?.parts) {
            for (const part of result.candidates[0].content.parts) {
                if (part.text) {
                    resultText = part.text;
                    break;
                }
            }
        }

        resultText = resultText || 'AI 暂时无法给出分析结果';

        return jsonResponse({
            success: true,
            message: '分析完成',
            text: resultText,
        });

    } catch (e) {
        const msg = e.message || String(e);
        return jsonResponse({ success: false, message: `分析失败: ${msg}` }, 500);
    }
};
