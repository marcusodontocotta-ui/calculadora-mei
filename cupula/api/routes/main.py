from fastapi import APIRouter, HTTPException, Request
from cupula.api.schemas import (
    DecisionRequestDTO,
    LegalAnalysisRequestDTO,
    CodeGenerateDTO,
    CodeReviewDTO,
    CodeDebugDTO,
    ImageGenerateDTO,
    CopyDTO,
    BrainstormDTO,
    VisionScreenshotDTO,
    VisionOCRequestDTO,
    VisionCompareDTO,
    WebhookRequestDTO,
)
from cupula.core.logger import get_logger
from cupula.worker.main import get_worker

logger = get_logger("api.routes")
router = APIRouter()


@router.post("/decide")
async def decide(request: DecisionRequestDTO, req: Request):
    cupula = req.app.state.cupula
    try:
        result = await cupula.process_decision(
            title=request.title,
            description=request.description,
            context=request.context,
            constraints=request.constraints,
            priority=request.priority,
            auto_legal=request.auto_legal,
        )
        return result
    except Exception as e:
        logger.error(f"Erro no /decide: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/legal/analyze")
async def legal_analyze(request: LegalAnalysisRequestDTO, req: Request):
    cupula = req.app.state.cupula
    try:
        result = await cupula.legal_analysis(
            titulo=request.titulo,
            descricao=request.descricao,
            dominios=request.dominios,
            acao_proposta=request.acao_proposta,
            dados_envolvidos=request.dados_envolvidos,
        )
        return result
    except Exception as e:
        logger.error(f"Erro no /legal/analyze: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health(req: Request):
    cupula = req.app.state.cupula
    status = await cupula.get_health()
    return status


@router.get("/status")
async def status(req: Request):
    cupula = req.app.state.cupula
    system_status = await cupula.orchestrator.get_system_status()
    legal_stats = await cupula.legal_gateway.get_stats()
    return {
        "system": system_status,
        "legal": legal_stats,
    }


@router.get("/report")
async def report(req: Request):
    cupula = req.app.state.cupula
    r = await cupula.generate_report()
    return r


@router.get("/meta/analyze")
async def meta_analyze(req: Request):
    cupula = req.app.state.cupula
    result = await cupula.run_meta_analysis()
    return result


@router.get("/leaderboard")
async def leaderboard(req: Request, limit: int = 20):
    cupula = req.app.state.cupula
    lb = await cupula.orchestrator.reputation.get_leaderboard(limit)
    return {"leaderboard": lb}


@router.get("/legal/stats")
async def legal_stats(req: Request):
    cupula = req.app.state.cupula
    stats = await cupula.legal_gateway.get_stats()
    alerts = await cupula.legal_gateway.get_alerts(10)
    return {"stats": stats, "alerts": alerts}


# ── AI Capability Endpoints ──────────────────────────────────────────────────


@router.get("/ai/capabilities")
async def ai_capabilities(req: Request):
    cupula = req.app.state.cupula
    return await cupula.ai_capabilities_list()


@router.post("/ai/code/generate")
async def ai_code_generate(request: CodeGenerateDTO, req: Request):
    cupula = req.app.state.cupula
    try:
        return await cupula.ai_code_generate(
            description=request.description,
            language=request.language,
            framework=request.framework,
            style=request.style,
            constraints=request.constraints,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Erro no /ai/code/generate: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ai/code/review")
async def ai_code_review(request: CodeReviewDTO, req: Request):
    cupula = req.app.state.cupula
    try:
        return await cupula.ai_code_review(code=request.code, language=request.language)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Erro no /ai/code/review: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ai/code/debug")
async def ai_code_debug(request: CodeDebugDTO, req: Request):
    cupula = req.app.state.cupula
    try:
        return await cupula.ai_code_debug(
            code=request.code, error=request.error, language=request.language,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Erro no /ai/code/debug: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ai/image/generate")
async def ai_image_generate(request: ImageGenerateDTO, req: Request):
    cupula = req.app.state.cupula
    try:
        return await cupula.ai_generate_image(
            prompt=request.prompt,
            style=request.style,
            size=request.size,
            quality=request.quality,
            variations=request.variations,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Erro no /ai/image/generate: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ai/copy/create")
async def ai_copy_create(request: CopyDTO, req: Request):
    cupula = req.app.state.cupula
    try:
        return await cupula.ai_create_copy(
            brief=request.brief, product=request.product, audience=request.audience,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Erro no /ai/copy/create: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ai/brainstorm")
async def ai_brainstorm(request: BrainstormDTO, req: Request):
    cupula = req.app.state.cupula
    try:
        return await cupula.ai_brainstorm(
            topic=request.topic, context=request.context, count=request.count,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Erro no /ai/brainstorm: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ai/vision/screenshot")
async def ai_vision_screenshot(request: VisionScreenshotDTO, req: Request):
    cupula = req.app.state.cupula
    try:
        return await cupula.ai_vision_screenshot(
            image_url=request.image_url, context=request.context,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Erro no /ai/vision/screenshot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ai/vision/ocr")
async def ai_vision_ocr(request: VisionOCRequestDTO, req: Request):
    cupula = req.app.state.cupula
    try:
        return await cupula.ai_vision_ocr(image_url=request.image_url)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Erro no /ai/vision/ocr: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ai/vision/compare")
async def ai_vision_compare(request: VisionCompareDTO, req: Request):
    cupula = req.app.state.cupula
    try:
        return await cupula.ai_vision_compare(
            image_url_a=request.image_url_a, image_url_b=request.image_url_b,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Erro no /ai/vision/compare: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Webhook Endpoints ──────────────────────────────────────────────────────


@router.post("/webhook")
async def webhook_generic(request: WebhookRequestDTO, req: Request):
    worker = get_worker()
    if not worker:
        raise HTTPException(status_code=503, detail="Worker não está rodando")
    try:
        return await worker.process_webhook(request.__dict__)
    except Exception as e:
        logger.error(f"Erro no /webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhook/decision")
async def webhook_decision(request: WebhookRequestDTO, req: Request):
    worker = get_worker()
    if not worker:
        raise HTTPException(status_code=503, detail="Worker não está rodando")
    try:
        payload = {**request.__dict__, "trigger": "decision"}
        return await worker.process_webhook(payload)
    except Exception as e:
        logger.error(f"Erro no /webhook/decision: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhook/legal")
async def webhook_legal(request: WebhookRequestDTO, req: Request):
    worker = get_worker()
    if not worker:
        raise HTTPException(status_code=503, detail="Worker não está rodando")
    try:
        payload = {**request.__dict__, "trigger": "legal"}
        return await worker.process_webhook(payload)
    except Exception as e:
        logger.error(f"Erro no /webhook/legal: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhook/n8n")
async def webhook_n8n(request: WebhookRequestDTO, req: Request):
    worker = get_worker()
    if not worker:
        raise HTTPException(status_code=503, detail="Worker não está rodando")
    try:
        payload = {**request.__dict__, "trigger": "n8n"}
        return await worker.process_webhook(payload)
    except Exception as e:
        logger.error(f"Erro no /webhook/n8n: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhook/status")
async def webhook_status(request: WebhookRequestDTO, req: Request):
    worker = get_worker()
    if not worker:
        raise HTTPException(status_code=503, detail="Worker não está rodando")
    try:
        return await worker.process_webhook({"trigger": "status"})
    except Exception as e:
        logger.error(f"Erro no /webhook/status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/worker/stats")
async def worker_stats():
    worker = get_worker()
    if not worker:
        return {"worker": "not_running"}
    import json as _json
    import redis.asyncio as aioredis
    from cupula.config.settings import get_settings
    redis = aioredis.from_url(get_settings().REDIS_URL, decode_responses=True)
    try:
        raw = await redis.get("cupula:worker:stats")
        return {"worker": _json.loads(raw) if raw else {}}
    finally:
        await redis.close()
