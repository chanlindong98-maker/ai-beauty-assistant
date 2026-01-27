"""
AI 服务相关的请求/响应模型
"""
from pydantic import BaseModel, Field
from enum import Enum


class BodyType(str, Enum):
    """体型枚举"""
    SLIM = "苗条"
    STANDARD = "标准"
    ATHLETIC = "健壮"
    PLUMP = "丰满"


class TryOnType(str, Enum):
    """试穿类型枚举"""
    CLOTHING = "clothing"
    ACCESSORY = "accessory"


class AnalysisType(str, Enum):
    """分析类型枚举"""
    TONGUE = "tongue"
    FACE_ANALYSIS = "face-analysis"
    FACE_READING = "face-reading"


class Gender(str, Enum):
    """性别枚举"""
    MALE = "男"
    FEMALE = "女"


class TryOnRequest(BaseModel):
    """试穿/试戴请求"""
    face_image: str = Field(..., description="人物照片 base64")
    item_image: str = Field(..., description="服装/配饰照片 base64")
    height: int | None = Field(None, ge=100, le=250, description="身高（cm）")
    body_type: BodyType | None = Field(None, description="体型")
    try_on_type: TryOnType = Field(..., description="试穿类型")


class AnalyzeRequest(BaseModel):
    """分析请求"""
    image: str = Field(..., description="图片 base64")
    analysis_type: AnalysisType = Field(..., description="分析类型")


class HairstyleRequest(BaseModel):
    """发型推荐请求"""
    image: str = Field(..., description="人物照片 base64")
    gender: Gender = Field(..., description="性别")
    age: int = Field(..., ge=5, le=100, description="年龄")


class ImageResponse(BaseModel):
    """图片生成响应"""
    success: bool
    message: str
    image: str | None = None


class TextResponse(BaseModel):
    """文本分析响应"""
    success: bool
    message: str
    text: str | None = None


class HairstyleResponse(BaseModel):
    """发型推荐响应"""
    success: bool
    message: str
    analysis: str | None = None
    recommended_image: str | None = None
    catalog_image: str | None = None
