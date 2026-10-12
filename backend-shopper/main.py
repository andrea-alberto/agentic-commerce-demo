# Copyright 2026 UCP Authors / GDG DevFest Milano 2026
"""
Backend Shopper Agent Server (Port 10998)
Exposes Traveler Context management and SSE live streaming for:
- Demo 3: Two-Agent A2A Federation (Shopper Agent <-> Merchant Agent)
- Demo 4: UCP Standard REST Binding with RFC 9421 Signatures
"""
import asyncio
import json
import logging
import sys
import os
import click
import uvicorn
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse
from starlette.routing import Route

# Add backend/src to path for shared package
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_src_dir = os.path.join(os.path.dirname(current_dir), "backend", "src")
if backend_src_dir not in sys.path:
    sys.path.insert(0, backend_src_dir)

from shopper_service import (
    get_current_context,
    update_current_context,
    set_scenario_preset,
    stream_shopper_mission,
    complete_shopper_authorization,
)
from shopper_user_store import shopper_user_store

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("backend_shopper.main")


async def health_check(request: Request):
    return JSONResponse({"status": "ok", "service": "backend-shopper", "port": 10998})


async def verify_shopper_user(request: Request):
    """Verifica se l'utente è censito nella collezione shopper_users (Nessun auto-provisioning)."""
    email = request.query_params.get("email") or request.headers.get("x-user-email")
    if not email:
        return JSONResponse({"authenticated": False, "authorized": False, "error": "Parametro 'email' obbligatorio"}, status_code=400)

    email = email.strip().lower()
    user = shopper_user_store.get_user(email)
    if not user:
        return JSONResponse({
            "authenticated": True,
            "authorized": False,
            "registered": False,
            "error": f"L'utente '{email}' non è censito nel Personal Shopper Agent. Registrazione manuale richiesta."
        }, status_code=403)

    return JSONResponse({
        "authenticated": True,
        "authorized": True,
        "registered": True,
        "user": user
    })


async def get_context_endpoint(request: Request):
    """Retrieve active traveler context."""
    email = request.query_params.get("email") or request.headers.get("x-user-email")
    if email and shopper_user_store.get_user(email):
        ctx = shopper_user_store.get_traveler_context(email)
        return JSONResponse(ctx.model_dump())
    ctx = get_current_context()
    return JSONResponse(ctx.model_dump())


async def update_context_endpoint(request: Request):
    """Update active traveler context."""
    try:
        body = await request.json()
        updated = update_current_context(body)
        return JSONResponse(updated.model_dump())
    except Exception as e:
        logger.exception("Errore aggiornamento contesto viaggiatore")
        return JSONResponse({"error": str(e)}, status_code=400)


async def set_preset_endpoint(request: Request):
    """Switch active scenario preset."""
    preset_id = request.path_params.get("preset_id", "scenario_departing_soon")
    updated = set_scenario_preset(preset_id)
    return JSONResponse(updated.model_dump())


async def stream_mission_endpoint(request: Request):
    """
    Run the Shopper Agent mission and stream progressive steps over Server-Sent Events (SSE).
    Request body: { "prompt": "...", "protocol": "a2a" | "ucp_rest", "context": {...} }
    """
    try:
        body = await request.json()
    except Exception:
        body = {}

    prompt = body.get("prompt", "Vorrei pranzare a bordo del treno")
    protocol = body.get("protocol", "a2a")
    context_override = body.get("context")

    logger.info("Avvio missione Shopper Agent (%s): '%s'", protocol, prompt)

    generator = stream_shopper_mission(
        prompt=prompt,
        protocol=protocol,
        context_override=context_override,
    )

    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def authorize_mission_endpoint(request: Request):
    """
    Finalize transaction with client-signed AP2 Cart Mandate.
    Request body: { "protocol": "a2a" | "ucp_rest", "challenge": {...}, "ap2_mandate": {...} }
    """
    try:
        body = await request.json()
        result = await complete_shopper_authorization(body)
        return JSONResponse(result)
    except Exception as e:
        logger.exception("Errore completamento autorizzazione missione: %s", e)
        return JSONResponse({"error": str(e)}, status_code=500)


routes = [
    Route("/health", health_check, methods=["GET"]),
    Route("/shopper/users/verify", verify_shopper_user, methods=["GET"]),
    Route("/shopper/context", get_context_endpoint, methods=["GET"]),
    Route("/shopper/context", update_context_endpoint, methods=["PUT", "POST"]),
    Route("/shopper/context/preset/{preset_id}", set_preset_endpoint, methods=["POST"]),
    Route("/shopper/mission/stream", stream_mission_endpoint, methods=["POST"]),
    Route("/shopper/mission/authorize", authorize_mission_endpoint, methods=["POST"]),
]

middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
]

app = Starlette(routes=routes, middleware=middleware)


@click.command()
@click.option("--host", default="0.0.0.0")
@click.option("--port", default=10998)
def main(host: str, port: int):
    """Start the Personal Shopper Agent server on port 10998."""
    logger.info("Avvio Personal Shopper Agent Server su http://%s:%s", host, port)
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
