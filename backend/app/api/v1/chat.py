import json
import uuid
import asyncio
import os
import re
import httpx
import pdfplumber
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, BackgroundTasks, Path as FastAPIPath, Query, File, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.database import execute_query, execute_insert
from app.core.config import settings
from app.api.deps import SuperAdminUser

router = APIRouter()

# OpenRouter Config
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

def extract_text_from_file(file_path: str, file_type: str) -> Dict[str, Any]:
    """Resilient text extraction."""
    try:
        if not os.path.exists(file_path):
            return {"text": "File not found.", "metadata": {}}
            
        if file_type == 'pdf':
            text = ""
            with pdfplumber.open(file_path) as pdf:
                # Limit to 30 pages
                for page in pdf.pages[:30]:
                    content = page.extract_text()
                    if content: text += content + "\n"
            
            # Collapse whitespace
            text = re.sub(r'[ \t]+', ' ', text)
            text = re.sub(r'\n+', '\n', text)
            
            return {
                "text": text.strip(),
                "metadata": {
                    "pages": len(pdf.pages),
                    "balance": re.findall(r"(?:Balance|Closing).{1,15}?([\d,]+\.\d{2})", text, re.I)[:1]
                }
            }
        elif file_type == 'excel':
            excel_file = pd.ExcelFile(file_path)
            df = pd.read_excel(file_path, sheet_name=excel_file.sheet_names[0])
            df_trunc = df.iloc[:500, :40]
            return {"text": df_trunc.to_csv(index=False), "metadata": {"sheets": excel_file.sheet_names, "rows": len(df)}}
    except Exception as e:
        return {"text": f"Error: {str(e)}", "metadata": {}}
    return {"text": "", "metadata": {}}

def get_system_prompt(org_name: str, context: str) -> str:
    return f"""You are FinCore Intelligence AI.
Organisation: {org_name}

{context}

Guidelines:
1. Derrive answers ONLY from the provided document context.
2. Use bold text for key figures and ₹ for currency.
3. Be professional and concise.
"""

class ChatStart(BaseModel):
    firstMessage: str

class ChatMessagePayload(BaseModel):
    content: str

@router.post("/conversations")
async def create_conversation(req: ChatStart, user: SuperAdminUser):
    conv_id = str(uuid.uuid4())
    execute_insert('INSERT INTO "Conversation" (id, "orgId", "userId", title, "createdAt", "updatedAt") VALUES (%s, %s, %s, %s, %s, %s)', (conv_id, user["org_id"], user["id"], None, datetime.utcnow(), datetime.utcnow()))
    execute_insert('INSERT INTO "Message" (id, "conversationId", role, content, "createdAt") VALUES (%s, %s, %s, %s, %s)', (str(uuid.uuid4()), conv_id, "user", req.firstMessage, datetime.utcnow()))
    execute_insert('INSERT INTO "AIUsageLog" (id, "userId", "userEmail", "orgId", model, "tokensIn", "tokensOut", "costUsd", action, "sessionId", "createdAt") VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)', (str(uuid.uuid4()), user["id"], user.get("email", ""), user["org_id"], "INIT", 0, 0, 0, "CHAT_START", conv_id, datetime.utcnow()))
    return {"conversationId": conv_id}

@router.get("/conversations")
async def list_conversations(user: SuperAdminUser, offset: int = 0, limit: int = 20):
    rows = execute_query('SELECT c.id, c.title, c."createdAt", (SELECT content FROM "Message" m WHERE m."conversationId" = c.id ORDER BY m."createdAt" DESC LIMIT 1) as "lastMessage" FROM "Conversation" c WHERE c."orgId" = %s AND c."userId" = %s ORDER BY c."createdAt" DESC LIMIT %s OFFSET %s', (user["org_id"], user["id"], limit, offset))
    return [{"id": r["id"], "title": r["title"] or "New Conversation", "createdAt": r["createdAt"].isoformat(), "lastMessage": r["lastMessage"]} for r in rows]

@router.get("/conversations/{id}")
async def get_conversation(user: SuperAdminUser, id: str = FastAPIPath(...)):
    conv = execute_query('SELECT id, title, "createdAt" FROM "Conversation" WHERE id = %s AND "orgId" = %s', (id, user["org_id"]))
    if not conv: raise HTTPException(404, "Not found")
    messages = execute_query('SELECT id, role, content, "createdAt" FROM "Message" WHERE "conversationId" = %s ORDER BY "createdAt" ASC', (id,))
    files = execute_query('SELECT id, filename, "fileType", "createdAt" FROM "ConversationFile" WHERE "conversationId" = %s', (id,))
    return {"id": conv[0]["id"], "title": conv[0].get("title"), "messages": [{"id": m["id"], "role": m["role"], "content": m["content"], "createdAt": m["createdAt"].isoformat()} for m in messages], "files": files}

@router.post("/conversations/{id}/upload")
async def upload_chat_file(user: SuperAdminUser, id: str = FastAPIPath(...), file: UploadFile = File(...)):
    ext = file.filename.split('.')[-1].lower()
    if ext not in ['pdf', 'xlsx', 'xls']: raise HTTPException(400, "Unsupported")
    file_id = str(uuid.uuid4())
    local_path = Path(settings.LOCAL_STORAGE_PATH) / "chats" / id / f"{file_id}_{file.filename}"
    local_path.parent.mkdir(parents=True, exist_ok=True)
    with open(local_path, "wb") as f: f.write(await file.read())
    execute_insert('INSERT INTO "ConversationFile" (id, "conversationId", "userId", "orgId", filename, "s3Key", "fileType") VALUES (%s, %s, %s, %s, %s, %s, %s)', (file_id, id, user["id"], user["org_id"], file.filename, str(local_path), 'pdf' if ext == 'pdf' else 'excel'))
    execute_insert('INSERT INTO "AIUsageLog" (id, "userId", "userEmail", "orgId", model, "tokensIn", "tokensOut", "costUsd", action, "sessionId", "createdAt") VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)', (str(uuid.uuid4()), user["id"], user.get("email", ""), user["org_id"], 'FILE', 0, 0, 0, "FILE_UPLOAD", id, datetime.utcnow()))
    return {"id": file_id}

@router.post("/conversations/{id}/messages")
async def chat_message(req: ChatMessagePayload, user: SuperAdminUser, background_tasks: BackgroundTasks, id: str = FastAPIPath(...)):
    last_msg = execute_query('SELECT content FROM "Message" WHERE "conversationId" = %s ORDER BY "createdAt" DESC LIMIT 1', (id,))
    if not last_msg or last_msg[0]["content"] != req.content:
        execute_insert('INSERT INTO "Message" (id, "conversationId", role, content, "createdAt") VALUES (%s, %s, %s, %s, %s)', (str(uuid.uuid4()), id, "user", req.content, datetime.utcnow()))
        execute_insert('UPDATE "Conversation" SET "updatedAt" = %s WHERE id = %s', (datetime.utcnow(), id))
    
    async def chat_stream_generator():
        yield "data: " + json.dumps({"type": "status", "content": "Scanning documents..."}) + "\n\n"
        files = execute_query('SELECT "s3Key", "fileType", "filename" FROM "ConversationFile" WHERE "conversationId" = %s', (id,))
        context = ""
        for f in files:
            yield "data: " + json.dumps({"type": "status", "content": f"AI Scout reading {f['filename']}..."}) + "\n\n"
            try:
                res = await asyncio.wait_for(asyncio.to_thread(extract_text_from_file, f["s3Key"], f["fileType"]), timeout=15)
                context += f"\n[FILE: {f['filename']}]\nCONTENT:\n{res['text']}\n\n"
            except: 
                yield "data: " + json.dumps({"type": "status", "content": f"Skipped {f['filename']} (too large/complex)"}) + "\n\n"

        api_key = settings.OPENROUTER_API_KEY
        if not api_key:
            yield "data: " + json.dumps({"type": "content_block_delta", "delta": {"text": "API Key Missing."}}) + "\n\n"
            return

        hist = execute_query('SELECT role, content FROM "Message" WHERE "conversationId" = %s ORDER BY "createdAt" ASC', (id,))
        messages = [{"role": m["role"], "content": m["content"]} for m in hist]
        sys_prompt = get_system_prompt("Vyrenzo", context)
        
        yield "data: " + json.dumps({"type": "status", "content": "Formulating answer..."}) + "\n\n"
        
        full_content, tokens_in, tokens_out = "", 0, 0
        try:
            async with httpx.AsyncClient() as client:
                async with client.stream("POST", OPENROUTER_URL, headers={"Authorization": f"Bearer {api_key}"}, json={"model": settings.OPENROUTER_MODEL, "messages": [{"role": "system", "content": sys_prompt}] + messages, "stream": True}, timeout=60.0) as resp:
                    if resp.status_code != 200:
                        error_body = await resp.aread()
                        yield "data: " + json.dumps({"type": "content_block_delta", "delta": {"text": f"AI Error ({resp.status_code}): {error_body.decode()}"}}) + "\n\n"
                        return
                        
                    async for line in resp.aiter_lines():
                        if not line.startswith("data: "): continue
                        data_str = line[6:].strip()
                        if data_str == "[DONE]": break
                        try:
                            data = json.loads(data_str)
                            if 'choices' in data and data['choices']:
                                delta = data['choices'][0].get('delta', {})
                                if 'content' in delta:
                                    txt = delta['content']
                                    full_content += txt
                                    yield "data: " + json.dumps({"type": "content_block_delta", "delta": {"text": txt}}) + "\n\n"
                            if 'usage' in data:
                                tokens_in, tokens_out = data['usage'].get('prompt_tokens', 0), data['usage'].get('completion_tokens', 0)
                        except: continue

            if full_content.strip():
                execute_insert('INSERT INTO "Message" (id, "conversationId", role, content, "createdAt") VALUES (%s, %s, %s, %s, %s)', (str(uuid.uuid4()), id, "assistant", full_content, datetime.utcnow()))
                if tokens_in == 0: tokens_in = len(sys_prompt + "".join([m["content"] for m in messages])) // 4
                if tokens_out == 0: tokens_out = len(full_content) // 4
                cost_usd = (tokens_in * 1.0 + tokens_out * 2.0) / 1_000_000.0
                execute_insert('INSERT INTO "AIUsageLog" (id, "userId", "userEmail", "orgId", model, "tokensIn", "tokensOut", "costUsd", action, "sessionId", "createdAt") VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)', (str(uuid.uuid4()), user["id"], user.get("email", ""), user["org_id"], settings.OPENROUTER_MODEL, tokens_in, tokens_out, cost_usd, "DOC_CHAT", id, datetime.utcnow()))
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield "data: " + json.dumps({"type": "content_block_delta", "delta": {"text": f"System Error: {str(e)}"}}) + "\n\n"
            
    return StreamingResponse(chat_stream_generator(), media_type="text/event-stream")
