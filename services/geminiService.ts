
import { GoogleGenAI } from "@google/genai";
import { TryOnRequest, TCMRequest, HairstyleRequest } from "../types";

const API_KEY = process.env.API_KEY || '';

export const generateTryOnImage = async (params: TryOnRequest): Promise<string> => {
  const ai = new GoogleGenAI({ apiKey: API_KEY });
  
  const facePart = {
    inlineData: {
      mimeType: "image/jpeg",
      data: params.faceImage.split(',')[1]
    }
  };

  const itemPart = {
    inlineData: {
      mimeType: "image/jpeg",
      data: params.itemImage.split(',')[1]
    }
  };

  let prompt = "";
  if (params.type === 'clothing') {
    prompt = `生成一张高度写实的全身或半身照片。
    参考第一张图中的人脸 and 肤色，参考第二张图中的服装款式、颜色 and 纹理。
    要求：这个人身高约为 ${params.height}cm，体型为 ${params.bodyType}。
    将这件衣服完美地穿在图中的人身上。保持背景简洁自然，光影和谐。
    输出必须是穿着该衣服的效果图。`;
  } else {
    prompt = `生成一张高度写实的人脸近照。
    参考第一张图中的人脸，参考第二张图中的耳饰。
    要求：将这款耳饰自然地戴在图中人的耳朵上。
    耳饰的细节（材质、反光、吊坠）应清晰可见。保持五官特征 and 肤色真实。
    输出必须是戴上耳饰后的效果图。`;
  }

  try {
    const response = await ai.models.generateContent({
      model: 'gemini-2.5-flash-image',
      contents: {
        parts: [facePart, itemPart, { text: prompt }]
      },
      config: {
        imageConfig: {
          aspectRatio: "3:4"
        }
      }
    });

    let imageUrl = '';
    const candidates = response.candidates;
    if (candidates && candidates.length > 0) {
      for (const part of candidates[0].content.parts) {
        if (part.inlineData) {
          imageUrl = `data:image/png;base64,${part.inlineData.data}`;
          break;
        }
      }
    }

    if (!imageUrl) {
      throw new Error("AI 未能生成有效的图像部分。");
    }

    return imageUrl;
  } catch (error) {
    console.error("Gemini Try-On Error:", error);
    throw error;
  }
};

export const analyzeTCM = async (params: TCMRequest): Promise<string> => {
  const ai = new GoogleGenAI({ apiKey: API_KEY });
  
  const imagePart = {
    inlineData: {
      mimeType: "image/jpeg",
      data: params.image.split(',')[1]
    }
  };

  let systemInstruction = "你是一位拥有深厚底蕴的中医及传统文化学者。";
  let prompt = "";

  if (params.type === 'tongue') {
    systemInstruction += "你拥有30年中医临床经验，擅长舌诊。";
    prompt = `请根据这张舌头照片进行中医分析：
    1. 观察舌质：包括颜色（淡红、红、绛、青紫等）、形态（胖大、瘦小、有无齿痕、裂纹）。
    2. 观察舌苔：包括颜色（白、黄、灰、黑）、厚薄、润燥。
    3. 综合判断：结合舌象推断可能的脏腑状况、气血阴阳平衡情况（如气虚、湿热、阴虚等）。
    4. 调理建议：给出饮食、作息、情志及简单穴位按摩的建议。
    请用中文分段回复，语言通俗易懂但不失专业性。`;
  } else if (params.type === 'face-analysis') {
    systemInstruction += "你拥有30年中医临床经验，擅长面诊。";
    prompt = `请根据这张人脸照片进行中医面诊分析：
    1. 面色分析：观察面色（如红润、萎黄、苍白、晦暗、青紫等）及其分布，对应五脏健康状况。
    2. 气色神态：分析眼神、皮肤光泽度所体现的精气神。
    3. 身体状况推断：基于中医“五色入五脏”理论，推断身体可能的虚实状况。
    4. 调理建议：给出针对性的健康调理方案，包括饮食调整和生活习惯建议。
    请用中文分段回复，语言温暖贴心。`;
  } else if (params.type === 'face-reading') {
    systemInstruction += "你是一位精通中国传统相术（面相学）的大师。你的分析应结合五官（眼、耳、鼻、口、眉）及面部轮廓。";
    prompt = `请根据这张正面人脸照片，运用中国传统面相学理论进行详细分析：
    1. 性格分析：通过眼神、眉形、面部轮廓等分析其内在性格特征（如果敢、温婉、聪慧等）。
    2. 健康运势：通过人中、地阁、面色润泽度等分析其基本健康素质。
    3. 财运事业：通过准头（鼻翼）、天庭（额头）等分析其职业发展潜力及财富聚集能力。
    4. 命运总括：结合整体面部比例，对其人生大势给出一个富有哲学智慧的总结，并给出一些正向的人生指导建议。
    请用中文分段回复，语气庄重、富有智慧，且需明确说明分析仅供参考。`;
  }

  try {
    const response = await ai.models.generateContent({
      model: 'gemini-3-flash-preview',
      contents: {
        parts: [imagePart, { text: prompt }]
      },
      config: {
        systemInstruction: systemInstruction,
        temperature: 0.7
      }
    });

    return response.text || "AI 暂时无法给出分析结果，请稍后再试。";
  } catch (error) {
    console.error("Gemini Analysis Error:", error);
    throw error;
  }
};

export const generateHairstyle = async (params: HairstyleRequest): Promise<{ analysis: string, recommendedImage: string, catalogImage: string }> => {
  const ai = new GoogleGenAI({ apiKey: API_KEY });
  
  const imagePart = {
    inlineData: {
      mimeType: "image/jpeg",
      data: params.image.split(',')[1]
    }
  };

  const isMale = params.gender === '男';
  const genderSpecificTerm = isMale ? "男士" : "女士";
  const userAge = params.age;
  
  // Define gender-specific style filters
  const maleStyles = "如：寸头、背头、纹理烫、侧分Undercut、渣男锡纸烫、狼尾发型、中分碎发、美式渐变等";
  const femaleStyles = "如：法式慵懒卷、波波头、初恋头、羊羔毛卷、大波浪长发、八字刘海中长发、锁骨发、公主切、齐耳短发等";
  const styleGuide = isMale ? maleStyles : femaleStyles;

  // 1. Analyze face shape and suggest styles
  const analysisResponse = await ai.models.generateContent({
    model: 'gemini-3-flash-preview',
    contents: {
      parts: [imagePart, { text: `你是一位顶级发型设计师。请根据这张照片分析其脸型，并为这位【${userAge}岁】的【${genderSpecificTerm}】推荐10种款式截然不同的发型。
      
      **严格质量要求**：
      1. **年龄与性别匹配**：推荐的发型必须高度契合【${userAge}岁】的年龄气质与【${genderSpecificTerm}】的性别特征。
      2. **款式差异**：这10款发型必须涵盖显著差异，${styleGuide}。
      3. **严禁重复**：10款发型在视觉和结构上必须完全不同。
      
      请按以下格式回复：
      1. 脸型分析：[分析结果]
      2. 10种针对${userAge}岁${genderSpecificTerm}的独一无二推荐发型列表：[列表]
      3. 最优发型推荐：[发型名称] 及针对该年龄段的推荐理由。
      语言要专业且富有亲和力。` }]
    }
  });
  const analysis = analysisResponse.text || "未能生成分析。";

  // 2. Generate the optimal recommendation image
  const recPrompt = `生成一张高度写实的【正面视角】照片。
  **核心要求**：
  - 必须使用原图中的人物面部，确保五官特征与原图【完全一致】。
  - 为图中这位【${userAge}岁】的人物换上一款完美的【${genderSpecificTerm}发型】（最优推荐款）。
  - 发型必须符合该年龄段的审美，如果是男士，严禁出现长发。
  - 背景简洁专业。`;
  
  const recResponse = await ai.models.generateContent({
    model: 'gemini-2.5-flash-image',
    contents: { parts: [imagePart, { text: recPrompt }] },
    config: { imageConfig: { aspectRatio: "3:4" } }
  });

  // 3. Generate a catalog (montage) image
  const catPrompt = `生成一张专业的【${userAge}岁】【${genderSpecificTerm}】正面发型参考画报。
  **关键核心要求**：
  1. **视角统一**：全部为【正面照】。
  2. **人脸一致性**：人脸与原图【完全一致】。
  3. **年龄段契合度**：发型风格应适合【${userAge}岁】的人群。
  4. **多样性**：10种风格迥异的${genderSpecificTerm}发型，绝不重复。
  5. **排版**：整齐网格排版。`;

  const catResponse = await ai.models.generateContent({
    model: 'gemini-2.5-flash-image',
    contents: { parts: [imagePart, { text: catPrompt }] },
    config: { imageConfig: { aspectRatio: "3:4" } }
  });

  const extractImage = (response: any) => {
    const candidates = response.candidates;
    if (candidates && candidates.length > 0) {
      for (const part of candidates[0].content.parts) {
        if (part.inlineData) return `data:image/png;base64,${part.inlineData.data}`;
      }
    }
    return '';
  };

  return {
    analysis,
    recommendedImage: extractImage(recResponse),
    catalogImage: extractImage(catResponse)
  };
};
