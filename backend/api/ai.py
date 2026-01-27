"""
AI 服务 API 端点

代理所有 AI 调用，确保 API Key 不暴露在前端
"""
from fastapi import APIRouter, Depends, HTTPException
from schemas.ai import (
    TryOnRequest, AnalyzeRequest, HairstyleRequest,
    ImageResponse, TextResponse, HairstyleResponse
)
from middleware.auth import get_current_user
from services.supabase_client import get_supabase_client
from services import gemini_service

router = APIRouter(prefix="/ai", tags=["AI 服务"])


async def consume_credit(user_id: str, current_credits: int) -> int:
    """
    扣减用户魔法值
    
    Returns:
        扣减后的魔法值
    """
    if current_credits <= 0:
        raise HTTPException(
            status_code=402,
            detail="魔法值不足！快去个人中心分享给小伙伴获取次数吧~"
        )
    
    supabase = get_supabase_client()
    new_credits = current_credits - 1
    
    supabase.table("user_profiles")\
        .update({"credits": new_credits})\
        .eq("id", user_id)\
        .execute()
    
    return new_credits


@router.post("/try-on", response_model=ImageResponse)
async def try_on(
    request: TryOnRequest,
    current_user: dict = Depends(get_current_user)
) -> ImageResponse:
    """
    云试衣 / 耳饰试戴
    
    根据上传的人物照片和服装/配饰照片生成效果图
    """
    try:
        # 扣减魔法值
        await consume_credit(current_user["id"], current_user["credits"])
        
        # 提取 base64 数据（移除 data:image/xxx;base64, 前缀）
        face_data = request.face_image.split(",")[1] if "," in request.face_image else request.face_image
        item_data = request.item_image.split(",")[1] if "," in request.item_image else request.item_image
        
        # 调用 Gemini 服务
        result_image = await gemini_service.generate_try_on_image(
            face_image_base64=face_data,
            item_image_base64=item_data,
            height=request.height,
            body_type=request.body_type.value if request.body_type else None,
            try_on_type=request.try_on_type.value
        )
        
        return ImageResponse(
            success=True,
            message="生成成功",
            image=f"data:image/png;base64,{result_image}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成失败: {str(e)}")


@router.post("/analyze", response_model=TextResponse)
async def analyze(
    request: AnalyzeRequest,
    current_user: dict = Depends(get_current_user)
) -> TextResponse:
    """
    中医分析 / 面相分析
    
    支持舌象、面色、面相三种分析类型
    """
    try:
        # 扣减魔法值
        await consume_credit(current_user["id"], current_user["credits"])
        
        # 提取 base64 数据
        image_data = request.image.split(",")[1] if "," in request.image else request.image
        
        # 调用 Gemini 服务
        result_text = await gemini_service.analyze_tcm(
            image_base64=image_data,
            analysis_type=request.analysis_type.value
        )
        
        return TextResponse(
            success=True,
            message="分析完成",
            text=result_text
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@router.post("/hairstyle", response_model=HairstyleResponse)
async def hairstyle(
    request: HairstyleRequest,
    current_user: dict = Depends(get_current_user)
) -> HairstyleResponse:
    """
    发型推荐
    
    分析用户脸型并推荐合适的发型，同时生成效果图
    """
    try:
        # 扣减魔法值
        await consume_credit(current_user["id"], current_user["credits"])
        
        # 提取 base64 数据
        image_data = request.image.split(",")[1] if "," in request.image else request.image
        
        # 调用 Gemini 服务
        result = await gemini_service.generate_hairstyle(
            image_base64=image_data,
            gender=request.gender.value,
            age=request.age
        )
        
        return HairstyleResponse(
            success=True,
            message="推荐完成",
            analysis=result["analysis"],
            recommended_image=f"data:image/png;base64,{result['recommendedImage']}" if result["recommendedImage"] else None,
            catalog_image=f"data:image/png;base64,{result['catalogImage']}" if result["catalogImage"] else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"推荐失败: {str(e)}")
