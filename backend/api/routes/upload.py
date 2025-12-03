from fastapi import HTTPException, APIRouter, Depends
from agents_shared.kafka_client import KafkaClient

from api.deps import get_upload_service
from api.schemas import UploadReq, NotifyReq


router = APIRouter()

@router.post("/upload-url")
def get_upload_url(req: UploadReq, upload_service=Depends(get_upload_service)):
    try:
        return upload_service.create_presigned_url(req.filename, req.content_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/notify-upload")
def notify_upload(msg: NotifyReq, upload_service=Depends(get_upload_service)):
    try:
        return upload_service.notify_upload(
            msg.object_id, msg.bucket, msg.user_id, msg.file_id, msg.content_type
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
