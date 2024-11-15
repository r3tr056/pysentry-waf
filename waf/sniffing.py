

import logging

import asyncio
from request import Request, DBController
from classifier import ThreatClassifier

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse

from waf.utils import check_disk_space, check_memory_usage

from .schema import WAFRequest, parse_request

db = DBController()

app = FastAPI()

# load the threat classifier
# TODO : Developer a more managable and faster model
# loading method
threat_clf = ThreatClassifier()

# setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('WAFLogger')


@app.middleware("http")
async def classify_threats(request: Request, call_next):
    """ Parse and clean request data for analysis """
    req_data = await request.json()
    req_obj = parse_request(req_data)
    
    # async
    threat_detected = await asyncio.to_thread(threat_clf.classify_request, req_obj)
    
    if "valid" not in req_obj.threats or len(req_obj.threats) > 1:
        logger.warning(f"Threats detected: {req_obj.threats}")
        return JSONResponse(status_code=403, content={
            "message": "Request blocked due to threats",
            "threats": req_obj.threats,
            "status": "blocked"
        })
    
    response = await call_next(request)
    logger.info("Safe request processed successfully.")
    return response

def check_models():
    try:
        # Attempt a dummy prediction to ensure model readiness
        test_input = ["test"]
        threat_clf.clf.predict(test_input)
        threat_clf.pt_clf.predict([[len(x)] for x in test_input])
        return {"status": "ok", "message": "Models are loaded and operational"}
    except Exception as e:
        return {"status": "error", "message": f"Model loading or prediction failed: {str(e)}"}

def check_app_status():
    return {"status": "ok", "message": "Application is running"}


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    health_status = {
        "app": check_app_status(),
        # "database": check_database_connection(),
        "memory": check_memory_usage(),
        "disk": check_disk_space(),
        "models": check_models()
    }

    overall_status = all(component["status"] == "ok" for component in health_status.values())
    if not overall_status:
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=health_status)
    
    return health_status

