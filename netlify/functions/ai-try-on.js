/**
 * 云试衣 / 耳饰试戴 API
 * POST /.netlify/functions/ai-try-on
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
        const faceImage = data.face_image || '';
        const itemImage = data.item_image || '';
        const tryOnType = data.try_on_type || 'clothing';
        const height = data.height || 165;
        const bodyType = data.body_type || '标准';

        // 提取 base64 数据
        const faceData = faceImage.includes(',') ? faceImage.split(',')[1] : faceImage;
        const itemData = itemImage.includes(',') ? itemImage.split(',')[1] : itemImage;

        // 配置 Gemini
        const apiKey = await getConfig('gemini_api_key');
        if (!apiKey) {
            return jsonResponse({ success: false, message: '未配置 Gemini API 密钥，请在管理后台设置' }, 500);
        }

        const genAI = new GoogleGenerativeAI(apiKey);
        const model = genAI.getGenerativeModel({
            model: 'gemini-2.0-flash-exp',
            generationConfig: {
                responseModalities: ['image', 'text'],
            }
        });

        // 构建提示词
        let prompt;
        if (tryOnType === 'clothing') {
            prompt = `生成一张高度写实的全身或半身照片。
            参考第一张图中的人脸和肤色，参考第二张图中的服装款式、颜色和纹理。
            要求：这个人身高约为 ${height}cm，体型为 ${bodyType}。
            将这件衣服完美地穿在图中的人身上。保持背景简洁自然，光影和谐。
            输出必须是穿着该衣服的效果图。`;
        } else {
            prompt = `生成一张高度写实的人脸近照。
            参考第一张图中的人脸，参考第二张图中的耳饰。
            要求：将这款耳饰自然地戴在图中人的耳朵上。
            耳饰的细节（材质、反光、吊坠）应清晰可见。保持五官特征和肤色真实。
            输出必须是戴上耳饰后的效果图。`;
        }

        // 构建图片内容
        const facePart = {
            inlineData: {
                data: faceData,
                mimeType: 'image/jpeg',
            },
        };
        const itemPart = {
            inlineData: {
                data: itemData,
                mimeType: 'image/jpeg',
            },
        };

        console.log('[Try-On] Calling Gemini API...');

        const response = await model.generateContent([facePart, itemPart, prompt]);
        const result = response.response;

        // 提取图片
        let resultImage = null;
        let modelText = '';
        const debugLog = [];
        const vTime = '20260130-Netlify';

        if (result.candidates && result.candidates[0]?.content?.parts) {
            for (let i = 0; i < result.candidates[0].content.parts.length; i++) {
                const part = result.candidates[0].content.parts[i];
                if (part.text) {
                    modelText = part.text;
                    debugLog.push(`T${i}`);
                }
                if (part.inlineData) {
                    const imgData = part.inlineData.data;
                    resultImage = `data:image/jpeg;base64,${imgData}`;
                    debugLog.push(`I${i}`);
                    break;
                }
            }
        } else {
            debugLog.push('EmptyParts');
        }

        if (!resultImage) {
            let fReason = 'Unknown';
            try {
                fReason = String(result.candidates?.[0]?.finishReason || 'Unknown');
            } catch (e) { }

            const safetyInfo = [];
            try {
                const ratings = result.candidates?.[0]?.safetyRatings || [];
                for (const rating of ratings) {
                    if (rating.probability !== 'NEGLIGIBLE') {
                        safetyInfo.push(`${rating.category}:${rating.probability}`);
                    }
                }
            } catch (e) { }

            let errMsg = `[${vTime}] AI 未能生成图像 | 原因: ${fReason} | 风险: ${safetyInfo.join(',') || 'None'}`;
            if (modelText) {
                errMsg += ` | AI解释: ${modelText.substring(0, 50)}`;
            }

            return jsonResponse({
                success: false,
                message: errMsg,
                debug: debugLog.join('/'),
            }, 500);
        }

        return jsonResponse({
            success: true,
            message: '生成成功',
            image: resultImage,
        });

    } catch (e) {
        const msg = e.message || String(e);
        return jsonResponse({ success: false, message: `生成失败: ${msg}` }, 500);
    }
};
