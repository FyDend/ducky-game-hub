from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

active_ws = set()

@router.websocket("/ws_events")
async def websocket_events(websocket: WebSocket):
    await websocket.accept()
    active_ws.add(websocket)
    print(f"[WebSocket] Cliente conectado. Total activos: {len(active_ws)}", flush=True)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        print("[WebSocket] Cliente desconectado.", flush=True)
    except Exception as e:
        print(f"[WebSocket] Error en conexión: {e}", flush=True)
    finally:
        active_ws.discard(websocket)

@router.post("/gamepad_event")
async def recibir_gamepad_event(event: dict):
    closed_ws = []
    for ws in list(active_ws):
        try:
            await ws.send_json(event)
        except Exception:
            closed_ws.append(ws)
    for ws in closed_ws:
        active_ws.discard(ws)
    return {"estado": "OK"}
