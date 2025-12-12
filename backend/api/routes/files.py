from fastapi import HTTPException, APIRouter, Depends
import logging

from api.deps import minio_client, MINIO_BUCKET, kafka_client, KAFKA_PRODUCE_TOPIC, get_redis_client
from api.schemas import UploadReq, NotifyReq
from api.services.files_service import FilesService

logger = logging.getLogger(__name__)

router = APIRouter()
files_service = FilesService(minio_client, MINIO_BUCKET, kafka_client, KAFKA_PRODUCE_TOPIC)

@router.post("/upload-url")
def get_upload_url(req: UploadReq):
    try:
        return files_service.create_presigned_url(req.filename)
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/notify-upload")
def notify_upload(msg: NotifyReq, redis_client=Depends(get_redis_client)):
    try:
        return files_service.notify_upload(
            msg.object_id, msg.bucket, msg.user_id, msg.file_id, msg.content_type, msg.session_id, redis_client
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/files-for-session/{session_id}")
def get_files_for_session(session_id: str):
    return files_service.get_files_for_session(session_id)
