import threading
import logging
from contextlib import asynccontextmanager
from typing import List
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import JSONResponse

from pymongo import MongoClient, ReturnDocument
from pymongo.server_api import ServerApi
from bson import ObjectId
from config import MONGODB_URL
from .schema import IPAddress, Threat, ThreatUpdate


app = FastAPI()

# mongodb client
client = MongoClient(MONGODB_URL, server_api=ServerApi('1'))
db = client['waf_db']
threats_collection = db['threats']
blocked_ips_collection = db['blocked_ips']

# Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan():
    print("Application has started!")
    yield  # Code after yield is run on shutdown
    logger.info("Shutting down application...")

app.router.lifespan_context = lifespan

@app.get('/api/threats', response_model=List[Threat])
async def fetch_threats():
    """ Fetch all threats from the database """
    threats = list(threats_collection.find({}, {'_id': 0}))
    return threats


@app.get('/api/threats/{threat_id}', response_model=Threat)
async def retrieve_threat(threat_id):
    """ Retreive a specific threat by ID """
    try:
        threat = threats_collection.find_one({'_id': ObjectId(threat_id)}, {'_id': 0})
        if threat:
            return threat
    except Exception as e:
        logger.error(f"Error retreiving threat: {str(e)}")
    raise HTTPException(status_code=404, detail="Threat not found.")

# Add Threat Intelligence
@app.post('/api/threats', response_model=dict, status_code=201)
async def add_threat(threat: Threat):
    """ Add a new thread to the database """
    new_threat = threat.model_dump()
    inserted_id = threats_collection.insert_one(new_threat).inserted_id
    if inserted_id is not None:
        return {'message': 'Threat added successfully', 'inserted_id': str(inserted_id)}

# Update Threat Intelligence
@app.put('/api/threats/{threat_id}', response_model=dict)
async def update_threat(threat_id, threat_update: ThreatUpdate):
    """ Update an existing threat by ID """
    updated_threat = {k: v for k, v in threat_update.model_dump().items() if v is not None}
    try:
        updated = threats_collection.find_one_and_update(
            {'_id': ObjectId(threat_id)},
            {'$set': updated_threat},
            return_document=ReturnDocument.AFTER
        )
        if updated:
            return {"message": "Threat updated successfully"}
    except Exception as e:
        logger.error(f"Error updating threat: {str(e)}")

    raise HTTPException(status_code=404, detail="Threat not found")

# Delete Threat Intelligence
@app.delete('/api/threats/{threat_id}', response_model=List[Threat])
async def delete_threat(threat_id: str):
    """Delete threat by id"""
    result = threats_collection.delete_one({'_id': ObjectId(threat_id)})
    if result.deleted_count:
        return {'message': 'Threat deleted successfully'}
    raise HTTPException(status_code=404, detail="Threat not found")

# Search Threats
@app.get('/api/threats/search', response_model=List[Threat])
async def search_threats(query: str):
    """ Search threats based on text query """
    threats = list(threats_collection.find({'$text': {'$search': query}}, {'_id': 0}))
    return threats

# Fetch Blocked IP Addresses
@app.get('/api/blocked-ips', response_model=List[IPAddress])
async def fetch_blocked_ips():
    """Fetch all blocked ip addresses"""
    blocked_ips = list(blocked_ips_collection.find({}, {'_id': 0}))
    return blocked_ips

# Block IP Address
@app.post('/api/blocked-ips', response_model=dict, status_code=201)
async def block_ip(ip_address: IPAddress):
    """Block an IP address"""
    if blocked_ips_collection.find_one({"ip_address": ip_address.ip_address}):
        raise HTTPException(status_code=409, detail="IP address is already blocked")
    
    blocked_ips_collection.insert_one(ip_address.model_dump())
    return {'message': 'IP address blocked successfully'}

# Unblock IP Address
@app.delete('/api/blocked-ips/{ip_address}', response_model=dict)
async def unblock_ip(ip_address):
    result = blocked_ips_collection.delete_one({'ip_address': ip_address})
    if result.deleted_count > 0:
        return {'message': 'IP address unblocked successfully'}
    else:
        return {'message': 'IP address not found'}

@app.get('/')
def index():
    return {'message': 'Hello World'}

if __name__ == '__main__':
    app.run(debug=True)