# -*- coding: utf-8 -*-
"""AI 识别 API（Day 5）：POST /api/v1/recognize 图片上传 → 类别+置信度 → 阈值分流/兜底。"""
import logging

from fastapi import APIRouter, File, HTTPException, UploadFile

from ..services.recognition_pipeline import RecognitionPipeline

logger = logging.getLogger("recognize")

router = APIRouter()

# 允许的图片 MIME 类型（前端 wx.uploadFile 可能丢失 MIME，允许 octet-stream 按扩展名兜底）
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp",
                       "image/gif", "image/bmp", "application/octet-stream"}
ALLOWED_IMAGE_EXT = {"jpg", "jpeg", "png", "webp", "gif", "bmp"}
# 单张图片上限：5MB（微信小程序上传限制内；超出返回 413，前端走手动选择）
MAX_IMAGE_BYTES = 5 * 1024 * 1024


def _default_vision_backend(image_path):
    """默认视觉服务 backend：未配置真实服务时抛异常 -> pipeline 走 fallback 兜底。
    接入真实服务方式：部署时替换为实际视觉识别函数（见成员B交接文档 §3.1）。"""
    raise RuntimeError("未配置 AI 识别服务 backend，默认走失败兜底（可手动选择类别）")


# 模块级 pipeline 实例；测试/演示时可直接替换为注入 Mock backend 的实例
_pipeline = RecognitionPipeline(backend=_default_vision_backend, timeout_seconds=5.0)


def _check_image(image: UploadFile | None):
    """文件存在性 / MIME / 扩展名检查；返回 (是否允许, 错误信息)。"""
    if image is None or image.filename is None or image.filename.strip() == "":
        return False, "缺少图片文件 image"
    ctype = (image.content_type or "").lower()
    if ctype and ctype not in ALLOWED_IMAGE_TYPES:
        return False, f"不支持的图片格式（{image.content_type}），请上传 JPG/PNG/WebP/GIF/BMP"
    ext = (image.filename or "").rsplit(".", 1)[-1].lower() if "." in (image.filename or "") else ""
    if ext and ext not in ALLOWED_IMAGE_EXT:
        return False, f"不支持的图片扩展名（.{ext}），请上传 JPG/PNG/WebP/GIF/BMP"
    return True, ""


@router.post("/recognize")
async def recognize_image(image: UploadFile | None = File(default=None)):
    """
    图片上传 → AI 识别 → 统一推荐结构。

    返回（HTTP 200，业务统一 JSON）：
        {
          "code": 0,
          "message": "ok",
          "data": {
             category_id / category_name / confidence / need_confirm /
             matched_by / fallback / available_categories / status /
             fallback_reason / raw_label
          }
        }

    错误处理（系统级，前端展示 message 并走手动选择类别）：
        400 缺少图片 / 格式不支持 / 读取失败 / 内容为空（code 400xx）
        413 图片超过 5MB（code 41301）

    AI 服务异常/超时/数据非法不会返回 5xx：pipeline 内部兜底为
    data.fallback=true + fallback_reason + available_categories，
    保证「识别失败也能继续发布」的验收标准。
    """
    # 1) 文件存在性与格式检查（系统级错误）
    ok, err = _check_image(image)
    if not ok:
        raise HTTPException(status_code=400,
                            detail={"code": 40001, "message": err})

    # 2) 读取字节 + 大小限制
    try:
        data = await image.read()
    except Exception as exc:  # noqa: BLE001
        logger.warning("读取上传图片失败：%s", exc)
        raise HTTPException(status_code=400,
                            detail={"code": 40003, "message": "读取上传图片失败，请重试"})
    if not data:
        raise HTTPException(status_code=400,
                            detail={"code": 40004, "message": "图片内容为空，请重新上传"})
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413,
                            detail={"code": 41301,
                                    "message": "图片过大（超过 5MB），请压缩后重试"})

    # 3) 识别链路（含失败兜底，业务上不阻断发布）
    try:
        result = _pipeline.recommend(image_bytes=data)
    except Exception as exc:  # noqa: BLE001 - 兜底要求捕获所有异常
        logger.warning("识别链路异常：%s", exc)
        result = _pipeline.recommend()
        result["fallback_reason"] = "识别服务异常，请手动选择类别"

    return {"code": 0, "message": "ok", "data": result}
