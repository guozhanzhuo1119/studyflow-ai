"""图片上传：接收单张图片 → 存到 uploads/ → 返回可访问的 URL"""
import uuid
from pathlib import Path

from fastapi import APIRouter, File, UploadFile, HTTPException

router = APIRouter(prefix='/api', tags=['文件上传'])

ALLOWED_EXTS = {'png', 'jpg', 'jpeg', 'webp', 'gif', 'bmp'}
MAX_SIZE = 5 * 1024 * 1024  # 5 MB
UPLOADS_DIR = Path(__file__).resolve().parent.parent.parent / 'uploads'
UPLOADS_DIR.mkdir(exist_ok=True)


@router.post('/upload')
async def upload_image(file: UploadFile = File(...)):
    """上传一张图片，返回前端可直接引用的相对路径。
    校验：扩展名只允许 png/jpg/jpeg/webp/gif/bmp，大小 ≤ 5MB。
    """
    if not file.filename:
        raise HTTPException(400, '文件名为空')

    ext = file.filename.rsplit('.', 1)[-1].lower()
    if ext not in ALLOWED_EXTS:
        raise HTTPException(400, f'不支持的扩展名：{ext}，仅允许 {sorted(ALLOWED_EXTS)}')

    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(413, f'文件过大（{len(content)} 字节），最大 5MB')

    # 随机文件名，避免覆盖；保留原扩展名方便前端浏览器识别
    safe_name = f'{uuid.uuid4().hex[:12]}.{ext}'
    target = UPLOADS_DIR / safe_name
    target.write_bytes(content)

    return {'url': f'/uploads/{safe_name}', 'name': safe_name, 'size': len(content)}
