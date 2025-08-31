from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

@router.websocket('/stream')
async def realtime_stream(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            msg = await ws.receive_text()
            # Echo for placeholder
            await ws.send_json({"echo": msg})
    except WebSocketDisconnect:
        pass
