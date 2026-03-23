import asyncio
import sys
import time
import random
import os
import requests as http_requests
import re
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv(override=True)

def _get_api_key():
    return os.getenv("OPENROUTER_API_KEY", "").strip()

FALLBACK_MODELS = [
    "openai/gpt-4o-mini",
    "google/gemini-2.0-flash-001",
    "anthropic/claude-3.5-haiku",
    "mistralai/mistral-7b-instruct:free",
    "microsoft/phi-3-mini-128k-instruct:free",
    "meta-llama/llama-3.1-8b-instruct:free",
]

def _get_models():
    """Return list of models to try: user's preferred model first, then fallbacks"""
    primary = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini").strip()
    models = [primary]
    for m in FALLBACK_MODELS:
        if m != primary:
            models.append(m)
    return models

def _call_ai_pollinations(prompt, log_callback=None):
    """Fallback to Keyless AI Provider (Pollinations.ai)"""
    def log(msg):
        if log_callback: log_callback("info", msg)
        else: print(msg)
    log("[AI] 🌐 Falling back to FREE Keyless AI (Pollinations.ai)...")
    try:
        resp = http_requests.post(
            "https://text.pollinations.ai/openai",
            headers={"Content-Type": "application/json"},
            json={
                "model": "openai",
                "messages": [
                    {"role": "system", "content": "You are a precise data extraction and form-filling assistant. You must strictly follow the output format requested. Never refuse to answer. If asked for a rating, opinion, or personal detail, provide a realistic simulated response. Do not include conversational filler."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.5
            },
            timeout=30
        )
        if resp.status_code == 200:
            data = resp.json()
            text = data["choices"][0]["message"]["content"]
            ans = text.strip() if text else None
            log(f"[AI] ✅ Response from Pollinations: {ans}")
            return ans
    except Exception as e:
        log(f"[AI] ❌ Pollinations error: {e}")
    return None

def _call_groq(prompt, log_callback=None, user_keys=None):
    """Call Groq API (High-speed Llama 3)"""
    def log(msg):
        if log_callback: log_callback("info", msg)
        else: print(msg)
    
    # Use user-provided key if available, or .env
    api_key = (user_keys or {}).get("groq", "").strip() or os.getenv("GROQ_API_KEY", "").strip()
    if not api_key: return None
    
    log("[AI] 🔄 Trying Groq API (Llama 3.3)...")
    try:
        resp = http_requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.5,
                "max_tokens": 500,
            },
            timeout=20
        )
        if resp.status_code == 200:
            data = resp.json()
            text = data["choices"][0]["message"]["content"]
            ans = text.strip() if text else None
            log(f"[AI] ✅ Response from Groq: {ans}")
            return ans
        else:
            log(f"[AI] ⚠️ Groq error {resp.status_code}")
    except Exception as e:
        log(f"[AI] ❌ Groq request error: {e}")
    return None

def _call_gemini_direct(prompt, log_callback=None, user_keys=None):
    """Call Google Gemini API directly"""
    def log(msg):
        if log_callback: log_callback("info", msg)
        else: print(msg)
        
    # Use user-provided key if available, or .env
    api_key = (user_keys or {}).get("gemini", "").strip() or os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key: return None
    
    log("[AI] 🔄 Trying Direct Gemini API (1.5 Flash)...")
    try:
        # Use v1 for more stability if v1beta 404s
        url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={api_key}"
        resp = http_requests.post(
            url,
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{
                    "parts": [{"text": prompt}]
                }],
                "generationConfig": {
                    "temperature": 0.4,
                    "maxOutputTokens": 500,
                }
            },
            timeout=25
        )
        if resp.status_code == 200:
            data = resp.json()
            # Extract text from Gemini response structure
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            ans = text.strip() if text else None
            log(f"[AI] ✅ Response from Direct Gemini: {ans}")
            return ans
        else:
            log(f"[AI] ⚠️ Gemini direct error {resp.status_code}")
    except Exception as e:
        log(f"[AI] ❌ Gemini direct error: {e}")
    return None

def _call_ai(prompt, max_retries=1, log_callback=None, user_keys=None):
    """Call OpenRouter API with model fallback, then completely free AI if exhausted"""
    def log(msg):
        if log_callback: log_callback("info", msg)
        else: print(msg)

    api_key = _get_api_key()
    
    # 1. Try Primary OpenRouter (Preferred model)
    if api_key:
        models = _get_models()
        for model in models:
            log(f"[AI] 🔄 Trying model={model}...")
            for attempt in range(max_retries):
                try:
                    resp = http_requests.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": model,
                            "messages": [{"role": "user", "content": prompt}],
                            "max_tokens": 500,
                        },
                        timeout=30,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        text = data["choices"][0]["message"]["content"]
                        ans = text.strip() if text else None
                        log(f"[AI] ✅ Response from {model}: {ans}")
                        return ans
                    elif resp.status_code in [429, 402]:
                        log(f"[AI] ⚠️ Rate limit or Quota exhausted on {model} (Status {resp.status_code})")
                        break # Try next model or provider
                    else:
                        log(f"[AI] ❌ {model} error {resp.status_code}")
                        break
                except Exception as e:
                    log(f"[AI] ❌ {model} request error: {e}")
                    break
            log(f"[AI] 🔄 Switching to next option...")
    
    # 2. Try Groq (if key available)
    ans = _call_groq(prompt, log_callback=log_callback, user_keys=user_keys)
    if ans: return ans
    
    # 3. Try Gemini Direct (if key available)
    ans = _call_gemini_direct(prompt, log_callback=log_callback, user_keys=user_keys)
    if ans: return ans
    
    # Final Fallback
    return _call_ai_pollinations(prompt, log_callback=log_callback)

# Fix for Windows console 'charmap' encoding error with Thai characters
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

PERSONAL_KEYWORDS = [
    "ชื่อ", "นามสกุล", "name", "สถาบัน", "มหาวิทยาลัย", "โรงเรียน", "school", "university",
    "รหัส", "student id", "เลขที่", "ห้อง", "class", "section", "ชั้น", "room",
    "สาขา", "คณะ", "faculty", "major", "department", "แผนก",
    "เบอร์", "โทรศัพท์", "phone", "tel", "อีเมล", "email", "e-mail",
    "ที่อยู่", "address", "บ้านเลขที่",
    "เพศ", "gender", "วันเกิด", "birthdate", "อายุ", "age",
    "ตำแหน่ง", "position", "หน่วยงาน", "organization", "บริษัท", "company",
]

def classify_questions_batch(questions: list, user_keys: dict = None, log_callback=None):
    """Classify multiple questions between 'personal' and 'exam' in ONE AI call to save quota"""
    if not questions: return {}
    
    # 1. Pre-filter very obvious cases with regex to save AI quota
    results = {}
    to_ask_ai = []
    
    personal_regex = re.compile(r'ชื่อ|นามสกุล|name|อีเมล|email|เบอร์|phone|รหัส|id|เลขที่|ห้อง|class|เพศ|gender|อายุ|age|ที่อยู่|address', re.I)
    
    for q_title in questions:
        if not q_title: continue
        # If it's a very clear personal question and short, skip AI
        if personal_regex.search(q_title) and len(q_title) < 15:
            results[q_title] = "personal"
        else:
            to_ask_ai.append(q_title)
            
    if not to_ask_ai: return results
    
    # 2. Ask AI for ambiguous cases
    batch_prompt = "Classify each question title as 'p' (personal info: Name, ID, Phone, Email, etc) or 'e' (exam/other: Knowledge, Opinions, Surveys).\n"
    batch_prompt += "Format: 1:p, 2:e, ...\nItems:\n"
    for i, title in enumerate(to_ask_ai):
        batch_prompt += f"{i+1}:{title}\n"
        
    ai_resp = _call_ai(batch_prompt, log_callback=log_callback, user_keys=user_keys)
    if ai_resp:
        # Parse format like "1:p, 2:e" or "1:p\n2:e"
        matches = re.findall(r'(\d+)\s*[:\.\-]\s*([pe])', ai_resp.lower())
        for idx_str, cat in matches:
            idx = int(idx_str) - 1
            if 0 <= idx < len(to_ask_ai):
                results[to_ask_ai[idx]] = "personal" if cat == "p" else "exam"
                
    # Fill remaining with default 'exam'
    for title in to_ask_ai:
        if title not in results:
            results[title] = "exam"
            
    return results

def _is_personal_question(title: str) -> bool:
    """Legacy helper, now mostly used as first-pass filter"""
    title_lower = title.lower().strip()
    for kw in PERSONAL_KEYWORDS:
        if kw in title_lower:
            return True
    return False

async def parse_google_form(url: str, user_keys: dict = None):
    result = {"success": False, "message": "", "data": {"title": "", "description": "", "questions": []}}
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
        )
        page = await context.new_page()
        try:
            await page.goto(url, wait_until='domcontentloaded', timeout=60000)
            
            # Check if it requires login
            if "accounts.google.com" in page.url:
                result["message"] = "ฟอร์มนี้ถูกจำกัดสิทธิ์ ตรวจพบการบังคับล็อกอินด้วยอีเมลองค์กรหรือมหาวิทยาลัย (ระบบอัตโนมัติไม่สามารถเจาะผ่านหน้าล็อกอิน Google ได้)"
                await browser.close()
                return result
                
            # Wait for first question to appear
            try:
                await page.locator('div[role="listitem"]').first.wait_for(state='visible', timeout=10000)
            except:
                pass # Form might be empty or slow
            
            # Extract title and description
            title_el = await page.locator('div[role="heading"][aria-level="1"]').first.all()
            if title_el:
                result["data"]["title"] = await title_el[0].inner_text()
            
            desc_el = await page.locator('div[dir="auto"]').all()
            if len(desc_el) > 1:
                result["data"]["description"] = await desc_el[1].inner_text()

            # Find ALL questions on all pages
            page_num = 1
            processed_titles = set() # Avoid duplicates on weird redirects
            
            while page_num < 20: # Safety cap
                # Wait for questions to be stable
                await page.wait_for_timeout(500)
                question_items = await page.locator('div[role="listitem"]').all()
                
                for index, item in enumerate(question_items):
                    q_title_el = await item.locator('div[role="heading"]').all()
                    q_title = await q_title_el[0].inner_text() if q_title_el else ""
                    q_title = q_title.replace('*', '').strip()
                    
                    if not q_title: continue
                    
                    # Unique ID for UI
                    q_id = f"p{page_num}_{index}"
                    
                    q_info = {
                        "index": q_id,
                        "title": q_title,
                        "type": None,
                        "options": [],
                        "category": "exam",
                    }
                    
                    # Detect question type (prioritize MCQ for speed scan)
                    radios = await item.locator('div[role="radio"]').all()
                    checkboxes = await item.locator('div[role="checkbox"]').all()
                    
                    if radios:
                        q_info["type"] = "radio"
                        for r in radios:
                            val = await r.get_attribute("data-value") or await r.get_attribute("aria-label")
                            if val: q_info["options"].append(val.strip())
                    elif checkboxes:
                        q_info["type"] = "checkbox"
                        for c in checkboxes:
                            val = await c.get_attribute("data-value") or await c.get_attribute("aria-label")
                            if val: q_info["options"].append(val.strip())
                    else:
                        listboxes = await item.locator('div[role="listbox"]').all()
                        if listboxes:
                            q_info["type"] = "dropdown"
                            for box in listboxes:
                                if await box.is_visible():
                                    await box.click(force=True)
                                    await page.wait_for_timeout(150) # Reduced from 250
                                    opts = await page.locator('div[role="option"]').all()
                                    for opt in opts:
                                        if await opt.is_visible():
                                            opt_text = await opt.get_attribute("data-value") or await opt.inner_text()
                                            if opt_text and opt_text.strip() not in ["Choose", "เลือก", ""]:
                                                q_info["options"].append(opt_text.strip())
                                    await page.keyboard.press("Escape")
                                    await page.wait_for_timeout(50)
                        else:
                            text_inputs = await item.locator('input[type="text"]').all()
                            textareas = await item.locator('textarea').all()
                            if textareas: q_info["type"] = "textarea"
                            elif text_inputs: q_info["type"] = "text"
                            else: continue
                    
                    result["data"]["questions"].append(q_info)
                
                # --- AI Question Classification (Batch for the current page) ---
                titles_to_classify = [q["title"] for q in result["data"]["questions"] if q["index"].startswith(f"p{page_num}_")]
                if titles_to_classify:
                    classification = classify_questions_batch(titles_to_classify, user_keys=user_keys)
                    for q in result["data"]["questions"]:
                        if q["index"].startswith(f"p{page_num}_") and q["title"] in classification:
                            q["category"] = classification[q["title"]]
                            
                # Fast search for Next button
                next_btn = await page.locator('div[role="button"]:has-text("ถัดไป"), div[role="button"]:has-text("Next"), button:has-text("ถัดไป"), button:has-text("Next")').first.all()
                if next_btn and await next_btn[0].is_visible():
                    await next_btn[0].click(force=True)
                    page_num += 1
                    # Wait for next set of questions
                    try:
                        await page.wait_for_timeout(600)
                    except: break
                else:
                    break
            
            result["success"] = True
        except Exception as e:
            result["message"] = str(e)
        finally:
            await browser.close()
    return result

def generate_ai_answer(question_title: str, context: dict = None, log_callback=None, user_keys=None):
    """Smart AI to generate answers based on context, falls back to simple heuristic"""
    ctx_str = ""
    if context and context.get("title"):
        ctx_str = f"หัวข้อแบบสอบถาม: '{context['title']}'\nคำอธิบายแบบสอบถาม: '{context.get('description', '')}'\n"
        
    prompt = (f"คุณคือผู้ช่วยทำแบบสอบถามออนไลน์และตอบข้อสอบ หน้าที่ของคุณคือตอบคำถามตามบริบทให้สมจริง เป็นธรรมชาติ ถูกต้อง และตรงคำถามที่สุด\n"
              f"{ctx_str}"
              f"คำถามที่ต้องตอบตอนนี้คือ: '{question_title}'\n"
              f"กติกา: กรุณาให้เฉพาะคำตอบที่ตรงประเด็นที่สุดเพียงอย่างเดียว สั้นๆ ไม่ต้องมีคำอารัมภบท ไม่ต้องมีเครื่องหมายคำพูดครอบ ไม่ต้องอธิบายเหตุผลเพิ่มเด็ดขาด ห้ามปฏิเสธการตอบ หากเป็นความคิดเห็นให้ตอบแง่บวก")
              
    result = _call_ai(prompt, log_callback=log_callback, user_keys=user_keys)
    if result:
        return result

    title_lower = question_title.lower()
    if "ชื่อ" in title_lower or "name" in title_lower:
        return "สมชาย ใจดี"
    elif "อายุ" in title_lower or "age" in title_lower:
        return str(random.randint(20, 40))
    elif "เบอร์" in title_lower or "phone" in title_lower:
        return "0812345678"
    elif "เหตุผล" in title_lower or "reason" in title_lower:
        return "ทดสอบระบบอัตโนมัติ (AI Generated)"
    elif "ที่อยู่" in title_lower or "address" in title_lower:
        return "123 กรุงเทพมหานคร ประเทศไทย"
    else:
        return "คำตอบจาก AI อัตโนมัติ"

def generate_ai_mcq_answer(question_title: str, options: list, context: dict = None, log_callback=None, user_keys=None):
    """Smart AI to pick the best option from a list for multiple choice questions"""
    if options:
        ctx_str = ""
        if context and context.get("title"):
            ctx_str = f"หัวข้อแบบสอบถาม: '{context['title']}'\n"
            
        opts_str = "\n".join([f"- {opt}" for opt in options if opt])
        prompt = (f"คุณคือผู้ช่วยทำแบบทดสอบ/ข้อสอบ หน้าที่ของคุณคือเลือกคำตอบที่ 'ถูกต้องที่สุด' เพียง 1 ข้อ\n"
                  f"{ctx_str}"
                  f"คำถาม: '{question_title}'\n"
                  f"ตัวเลือกที่มี (ห้ามตอบนอกเหนือจากนี้):\n{opts_str}\n\n"
                  f"กติกาสำคัญ: ให้พิมพ์เฉพาะ 'ข้อความของตัวเลือก' ที่ถูกต้องเป๊ะๆ กลับมาเพียง 1 ข้อ ห้ามพิมพ์อะไรเพิ่ม ห้ามมีคำอารัมภบทเด็ดขาด ห้ามปฏิเสธการตอบ หากเป็นความคิดเห็นให้สุ่มเลือกให้สมเหตุสมผล")
                  
        result = _call_ai(prompt, log_callback=log_callback, user_keys=user_keys)
        if result:
            ans = result
            for opt in options:
                if opt and (ans.lower() == opt.lower() or ans.lower() in opt.lower() or opt.lower() in ans.lower()):
                    return opt
            return ans
    return None

def batch_ai_mcq_answers(questions_batch: list, context: dict = None, log_callback=None, user_keys=None):
    """Answer multiple MCQ questions in ONE API call for speed"""
    if not questions_batch:
        return {}
    
    ctx_str = ""
    if context and context.get("title"):
        ctx_str = f"หัวข้อแบบสอบถาม: '{context['title']}'\n"
    
    batch_prompt = f"""คุณคือผู้ช่วยทำข้อสอบ หน้าที่ของคุณคือเลือกคำตอบที่ถูกต้องที่สุดให้ทุกข้อ
{ctx_str}
ตอบทุกข้อต่อไปนี้ ตอบในรูปแบบ:
Q1: [คำตอบ]
Q2: [คำตอบ]
...

"""
    for i, q in enumerate(questions_batch):
        opts_str = ", ".join([f'"{o}"' for o in q["options"] if o])
        batch_prompt += f"Q{i+1}: คำถาม: '{q['title']}' | ตัวเลือก: [{opts_str}]\n"
    
    batch_prompt += f"""\nกติกาสำคัญมาก:
- ต้องตอบทุกข้อในรูปแบบ Q[หมายเลข]: [คำตอบ] เท่านั้น ห้ามพิมพ์ข้อความอื่น
- คำตอบต้องตรงกับตัวเลือกที่มีให้เป๊ะๆ
- ห้ามปฏิเสธการตอบเด็ดขาด หากเป็นความคิดเห็น คะแนน หรือข้อมูลส่วนตัว ให้ทำการสุ่มเลือกตัวเลือกมา 1 ข้อแบบเนียนๆ"""
    
    result_text = _call_ai(batch_prompt, log_callback=log_callback, user_keys=user_keys)
    if not result_text:
        return {}
    
    # Parse responses using regex like "Q1: answer" or "1. answer"
    answers = {}
    
    # Try to find all patterns like (Q1|1|ข้อ 1) : [answer]
    # This pattern looks for: Optional (Q/ข้อ/Item/Question) + digit + separator (:|.|-) + everything until next marker or end
    pattern = re.compile(r'(?:Q|ข้อ|Item|Question)?\s*(\d+)\s*[:\.\-]\s*(.*?)(?=\n(?:Q|ข้อ|Item|Question)?\s*\d+\s*[:\.\-]|$)', re.IGNORECASE | re.DOTALL)
    matches = pattern.findall(result_text)
    
    # [Robust Fallback] If no numbered matches, handle conversational text + line-by-line list
    if not matches:
        lines = [l.strip() for l in result_text.split('\n') if l.strip()]
        # If we find a block of lines that exactly matches the batch size, assume those are the answers
        for start_idx in range(len(lines) - len(questions_batch) + 1):
            potential_batch = lines[start_idx : start_idx + len(questions_batch)]
            # Check if these lines look like answers (not too long, no "Question:" header, etc)
            if all(len(l) < 200 for l in potential_batch):
                for i, line in enumerate(potential_batch):
                    # Strip common prefixes
                    clean_line = re.sub(r'^(?:Q|Ans|A|ตอบ)?\s*\d*\s*[:\.\-]\s*', '', line, flags=re.IGNORECASE)
                    matches.append((str(i+1), clean_line))
                break

    for m_idx_str, ans in matches:
        try:
            i = int(m_idx_str) - 1 # Convert to 0-based index
            if 0 <= i < len(questions_batch):
                ans = ans.strip().lower()
                q = questions_batch[i]
                
                # --- Fuzzy Matching Logic ---
                best_match = None
                
                # 1. Exact match (case-insensitive)
                for opt in q["options"]:
                    if opt and opt.lower() == ans:
                        best_match = opt
                        break
                
                # 2. Contains match
                if not best_match:
                    for opt in q["options"]:
                        opt_lower = opt.lower()
                        if opt and (ans in opt_lower or opt_lower in ans):
                            best_match = opt
                            break
                
                # 3. AI might return "A. Option Text" - strip the "A. "
                if not best_match:
                    ans_clean = re.sub(r'^[a-z]\s*[:\.\-]\s*', '', ans)
                    for opt in q["options"]:
                        if opt and opt.lower() == ans_clean:
                            best_match = opt
                            break
                
                if best_match:
                    answers[i] = best_match
                else:
                    # Fallback to raw AI response if it's not a closed choice
                    answers[i] = ans
        except:
            continue
            
    return answers

async def fill_google_form(url: str, email: str = "", manual_answers: dict = None, log_callback=None, user_keys: dict = None):
    if manual_answers is None: manual_answers = {}
    if user_keys is None: user_keys = {}
    result = {"success": False, "message": ""}
    
    def log_info(msg, content=None):
        if content is not None:
            # Called as log_info(msg_type, content)
            msg_type, msg_content = msg, content
        else:
            # Called as log_info(message)
            msg_type, msg_content = "info", msg
            
        if log_callback:
            log_callback(msg_type, msg_content)
        print(msg_content)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
        )
        page = await context.new_page()
        
        try:
            print(f"Navigating to {url}")
            await page.goto(url, wait_until='networkidle')
            
            # Check if it requires login (redirects to accounts.google.com)
            if "accounts.google.com" in page.url:
                result["message"] = "ฟอร์มนี้ถูกจำกัดสิทธิ์ ต้องล็อกอินด้วยอีเมลองค์กรหรือมหาวิทยาลัยเท่านั้น ระบบอัตโนมัติไม่สามารถล็อกอินและข้ามผ่านหน้าระบบรักษาความปลอดภัยของ Google แทนคุณได้"
                await browser.close()
                return result

            # Get title for AI context
            form_context = {"title": "", "description": ""}
            try:
                title_el = await page.locator('div[role="heading"][aria-level="1"]').first.all()
                if title_el:
                    form_context["title"] = await title_el[0].inner_text()
                desc_el = await page.locator('div[dir="auto"]').all()
                if len(desc_el) > 1:
                    form_context["description"] = await desc_el[1].inner_text()
            except:
                pass

            # Loop to handle multi-page forms
            max_pages = 10
            pages_processed = 0
            
            while pages_processed < max_pages:
                pages_processed += 1
                
                # Wait for form to render
                await page.wait_for_timeout(1000)

                # Look for email input field (often top of the form)
                email_inputs = await page.locator('input[type="email"]').all()
                if email_inputs:
                    print(f"Found {len(email_inputs)} email inputs.")
                    if not email:
                        result["message"] = "The form requires an email address, but none was provided."
                        await browser.close()
                        return result
                    
                    # Fill the email field(s)
                    for email_input in email_inputs:
                        if await email_input.is_visible() and await email_input.is_enabled():
                            await email_input.fill(email)
                            print(f"Filled email: {email}")
                
                # Collect MCQ questions for batch AI processing
                mcq_batch = []
                
                # Go through questions, fill text inline, collect MCQs
                question_items = await page.locator('div[role="listitem"]').all()
                log_info(f"📄 พบ {len(question_items)} คำถามในหน้า {pages_processed}")
                
                for index, item in enumerate(question_items):
                    q_title_el = await item.locator('div[role="heading"]').all()
                    q_title = await q_title_el[0].inner_text() if q_title_el else f"ข้อ {index+1}"
                    q_title = q_title.replace('*', '').strip()
                    
                    # Check for manual answers with multiple index formats
                    page_idx = f"p{pages_processed}_{index}"
                    str_idx = str(index)
                    manual_val = manual_answers.get(page_idx, manual_answers.get(str_idx, "")).strip()

                    # Text inputs
                    text_inputs = await item.locator('input[type="text"]').all()
                    textareas = await item.locator('textarea').all()
                    
                    if text_inputs or textareas:
                        if manual_val:
                            answer_text = manual_val
                            log_info(f"⌨️ พิมพ์เอง: '{q_title}' -> '{answer_text}'")
                        else:
                            answer_text = generate_ai_answer(q_title, form_context, log_callback=log_info, user_keys=user_keys)
                            log_info(f"✨ AI: '{q_title}' -> '{answer_text}'")
                        
                        for text_in in text_inputs:
                            if await text_in.is_visible() and await text_in.is_editable():
                                val = await text_in.input_value()
                                if not val:
                                    await text_in.fill(answer_text)
                        for t in textareas:
                            if await t.is_visible() and await t.is_editable():
                                val = await t.input_value()
                                if not val:
                                    await t.fill(answer_text)
                        continue

                    # Radio buttons
                    radios = await item.locator('div[role="radio"]').all()
                    if radios:
                        is_selected = any([await r.get_attribute('aria-checked') == 'true' for r in radios])
                        if not is_selected:
                            visible_radios = [r for r in radios if await r.is_visible()]
                            if visible_radios:
                                options_texts = []
                                for r in visible_radios:
                                    val = await r.get_attribute("data-value")
                                    if not val:
                                        val = await r.get_attribute("aria-label")
                                    options_texts.append(val.strip() if val else "")
                                
                                # Use manual or collect for batch
                                if manual_val and manual_val in options_texts:
                                    ai_choice = manual_val
                                else:
                                    mcq_batch.append({"idx": index, "page_idx": pages_processed, "title": q_title, "options": options_texts,
                                                      "type": "radio", "elements": visible_radios, "element_texts": options_texts})
                                    continue
                                
                                for r, text in zip(visible_radios, options_texts):
                                    if text and ai_choice == text:
                                        await r.click(force=True)
                                        log_info(f"🔘 เลือก (⌨️): '{q_title}' -> {ai_choice}")
                                        break
                                await page.wait_for_timeout(100)
                        continue

                    # Checkboxes
                    checkboxes = await item.locator('div[role="checkbox"]').all()
                    if checkboxes:
                        is_selected = any([await c.get_attribute('aria-checked') == 'true' for c in checkboxes])
                        if not is_selected:
                            visible_cbs = [c for c in checkboxes if await c.is_visible()]
                            if visible_cbs:
                                options_texts = []
                                for c in visible_cbs:
                                    val = await c.get_attribute("data-value")
                                    if not val:
                                        val = await c.get_attribute("aria-label")
                                    options_texts.append(val.strip() if val else "")
                                
                                if manual_val and manual_val in options_texts:
                                    ai_choice = manual_val
                                else:
                                    mcq_batch.append({"idx": index, "page_idx": pages_processed, "title": q_title, "options": options_texts,
                                                      "type": "checkbox", "elements": visible_cbs, "element_texts": options_texts})
                                    continue
                                
                                for c, text in zip(visible_cbs, options_texts):
                                    if text and ai_choice == text:
                                        await c.click(force=True)
                                        log_info(f"☑️ ติ๊ก (⌨️): '{q_title}' -> {ai_choice}")
                                        break
                                await page.wait_for_timeout(100)
                        continue
                            
                    # Dropdowns (listboxes)
                    listboxes = await item.locator('div[role="listbox"]').all()
                    for box in listboxes:
                        if await box.is_visible():
                            # check if it already has a value beside default
                            text_content = await box.inner_text()
                            if text_content and text_content.strip() not in ["Choose", "เลือก"]:
                                continue # Already chosen
                                
                            # To get options, we must click
                            await box.click(force=True)
                            await page.wait_for_timeout(300)
                            options_els = await page.locator('div[role="option"]').all()
                            options_texts = []
                            visible_options = []
                            for opt in options_els:
                                if await opt.is_visible():
                                    opt_text = await opt.get_attribute("data-value") or await opt.inner_text()
                                    if opt_text and opt_text.strip() not in ["Choose", "เลือก", ""]:
                                        visible_options.append(opt)
                                        options_texts.append(opt_text.strip())
                            
                            if visible_options:
                                # Add to batch instead of calling AI here
                                if manual_val and manual_val in options_texts:
                                    # Fill immediately if manual
                                    for o, text in zip(visible_options, options_texts):
                                        if text == manual_val:
                                            await o.click(force=True)
                                            log_info(f"🔽 เลือก Dropdown (⌨️): '{q_title}' -> {manual_val}")
                                            break
                                else:
                                    mcq_batch.append({
                                        "title": q_title, "options": options_texts, "type": "dropdown",
                                        "box_element": box, "option_texts": options_texts, "category": "exam"
                                    })
                            
                            # Close dropdown if we didn't fill it yet or just finished reading
                            await page.keyboard.press("Escape")
                            await page.wait_for_timeout(100)

                # --- End of question_items loop ---

                # Now process the batch of AI questions
                if mcq_batch:
                    chunk_size = 10
                    for i in range(0, len(mcq_batch), chunk_size):
                        chunk = mcq_batch[i:i+chunk_size]
                        log_info(f"🧠 AI คิดคำตอบแบบกลุ่ม ({i+1}-{min(i+chunk_size, len(mcq_batch))}/{len(mcq_batch)})...")
                        results = batch_ai_mcq_answers(chunk, form_context, log_callback=log_info, user_keys=user_keys)
                        
                        for idx_in_chunk, q_data in enumerate(chunk):
                            ans = results.get(idx_in_chunk)
                            if not ans:
                                log_info(f"⚠️ AI ไม่ตอบแบบกลุ่มสำหรับข้อ '{q_data['title']}' - กำลังลองถามรายข้อ...")
                                if q_data["type"] == "dropdown":
                                    ans = generate_ai_mcq_answer(q_data['title'], q_data['options'], form_context, log_callback=log_info, user_keys=user_keys)
                                else:
                                    ans = generate_ai_mcq_answer(q_data['title'], q_data['element_texts'], form_context, log_callback=log_info, user_keys=user_keys)
                                
                            if not ans:
                                log_info(f"❌ สุ่มคำตอบข้อ '{q_data['title']}' (AI ไม่ตอบทุกช่องทาง)")
                                # Continue to random selection at bottom
                            
                            if q_data["type"] == "dropdown":
                                # Re-open dropdown to click
                                await q_data["box_element"].click(force=True)
                                await page.wait_for_timeout(200)
                                opt_to_click = await page.locator(f'div[role="option"]:has-text("{ans}")').first.all()
                                if opt_to_click:
                                    await opt_to_click[0].click(force=True)
                                    log_info(f"🔽 เลือก Dropdown (✨ AI): '{q_data['title']}' -> {ans}")
                                else:
                                    all_opts = await page.locator('div[role="option"]').all()
                                    visible_opts = []
                                    for o in all_opts:
                                         if await o.is_visible():
                                             txt = await o.get_attribute("data-value") or await o.inner_text()
                                             if txt and txt.strip() not in ["Choose", "เลือก", ""]:
                                                 visible_opts.append((o, txt.strip()))
                                    
                                    if visible_opts:
                                        matched_opt = None
                                        for o, txt in visible_opts:
                                            if ans.lower() in txt.lower() or txt.lower() in ans.lower():
                                                matched_opt = o
                                                break
                                        if matched_opt:
                                            await matched_opt.click(force=True)
                                            log_info(f"🔽 เลือก Dropdown (✨ AI แบบอ้างอิงข้อความใกล้เคียง): '{q_data['title']}' -> {ans}")
                                        else:
                                            random_o, random_txt = random.choice(visible_opts)
                                            await random_o.click(force=True)
                                            log_info(f"🔽 เลือก Dropdown (สุ่มเพราะ AI ตอบไม่ตรงตัวเลือก): '{q_data['title']}' -> {random_txt}")
                                    else:
                                        await page.keyboard.press("Escape")
                            else:
                                # Radio or Checkbox
                                matched = False
                                for el, text in zip(q_data["elements"], q_data["element_texts"]):
                                    if text == ans:
                                        await el.click(force=True)
                                        log_info(f"{'🔘' if q_data['type'] == 'radio' else '☑️'} เลือก (✨ AI): '{q_data['title']}' -> {ans}")
                                        matched = True
                                        break
                                if not matched and q_data["elements"]:
                                    await random.choice(q_data["elements"]).click(force=True)
                                    log_info(f"🔘 เลือก (สุ่ม): '{q_data['title']}'")
                            
                            await page.wait_for_timeout(50)
                
                log_info("✅ กรอกข้อมูลหน้าหน้าปัจจุบันเรียบร้อย")


                print("Attempting to find Next or Submit button...")
                submit_clicked = False
                is_final_submit = False
                
                # We prioritize the submit button over the next button
                # Check Submit first
                submit_texts = ["Submit", "ส่ง"]
                for btn_text in submit_texts:
                    btns = await page.locator(f'div[role="button"]:has-text("{btn_text}")').all()
                    for btn in btns:
                        if await btn.is_visible():
                            await btn.click(force=True)
                            print(f"Clicked '{btn_text}' (Submit) button.")
                            submit_clicked = True
                            is_final_submit = True
                            break
                    if submit_clicked: break
                    
                # If no Submit, look for Next
                if not submit_clicked:
                    next_texts = ["Next", "ถัดไป"]
                    for btn_text in next_texts:
                        btns = await page.locator(f'div[role="button"]:has-text("{btn_text}")').all()
                        for btn in btns:
                            if await btn.is_visible():
                                await btn.click(force=True)
                                print(f"Clicked '{btn_text}' (Next) button.")
                                submit_clicked = True
                                break
                        if submit_clicked: break
                
                # If neither Next nor Submit found by exact text, guess based on position
                if not submit_clicked:
                    all_buttons = await page.locator('div[role="button"]').all()
                    visible_buttons = [b for b in all_buttons if await b.is_visible()]
                    if visible_buttons:
                        # Usually the last button is Submit or Next and second to last is Back/Clear
                        last_btn = visible_buttons[-1]
                        last_text = await last_btn.inner_text()
                        if "ล้าง" in last_text or "Clear" in last_text:
                            if len(visible_buttons) >= 2:
                                await visible_buttons[-2].click(force=True)
                                log_info("กดปุ่มรองสุดท้าย (Fallback)")
                                submit_clicked = True
                        else:
                            await last_btn.click(force=True)
                            log_info(f"กดปุ่มสุดท้าย '{last_text}' (Fallback)")
                            submit_clicked = True
                            if "Submit" in last_text or "ส่ง" in last_text:
                                is_final_submit = True

                if not submit_clicked:
                    result["message"] = "Could not find Next or Submit button to progress."
                    log_info("❌ ไม่พบปุ่มทำรายการต่อ (Next/Submit)")
                    break

                # Wait for navigation or validation error
                await page.wait_for_timeout(1000)
                
                # Check for validation errors quickly
                err_msg_els = await page.locator('div[role="alert"]').all()
                if err_msg_els:
                    errors = []
                    required_questions = []
                    
                    found_required_error = False
                    for e_node in err_msg_els:
                        if await e_node.is_visible():
                            txt = await e_node.inner_text()
                            if txt:
                                clean_txt = txt.strip()
                                errors.append(clean_txt)
                                if "จำเป็นต้องตอบคำถามนี้" in clean_txt or "This is a required question" in clean_txt:
                                    found_required_error = True
                    
                    if found_required_error:
                        # Identify WHICH questions have the error
                        # In Google Forms, the error div is usually inside the listitem next to the heading
                        q_items = await page.locator('div[role="listitem"]').all()
                        for q_idx, q_item in enumerate(q_items):
                            alerts = await q_item.locator('div[role="alert"]').all()
                            has_err = False
                            for a in alerts:
                                if await a.is_visible():
                                    t = await a.inner_text()
                                    if t and ("จำเป็น" in t or "required" in t.lower()):
                                        has_err = True
                                        break
                            
                            if has_err:
                                h_el = await q_item.locator('div[role="heading"]').all()
                                title = await h_el[0].inner_text() if h_el else f"ข้อ {q_idx+1}"
                                
                                # Extract options for MCQ types
                                options = []
                                radios = await q_item.locator('div[role="radio"]').all()
                                checkboxes = await q_item.locator('div[role="checkbox"]').all()
                                listboxes = await q_item.locator('div[role="listbox"]').all()
                                
                                if radios:
                                    for r in radios:
                                        val = await r.get_attribute("data-value") or await r.get_attribute("aria-label")
                                        if val: options.append(val.strip())
                                elif checkboxes:
                                    for c in checkboxes:
                                        val = await c.get_attribute("data-value") or await c.get_attribute("aria-label")
                                        if val: options.append(val.strip())
                                elif listboxes:
                                    # For dropdowns, options might not be visible, but we can try to guess from the box inner text or just fallback to text
                                    pass

                                required_questions.append({
                                    "index": f"p{pages_processed}_{q_idx}",
                                    "title": title.replace('*', '').strip(),
                                    "options": options,
                                    "error": "Required field missed"
                                })
                        
                        if required_questions:
                            result["required_missing"] = required_questions
                            result["message"] = f"พบคำถามที่ยังไม่ได้ตอบ {len(required_questions)} ข้อ (ข้อบังคับ)"
                            log_info(f"⚠️ {result['message']}")
                            break

                    if errors:
                        err_str = ", ".join(set(errors))
                        result["message"] = f"พบข้อผิดพลาดที่ฟอร์ม: {err_str}"
                        log_info(f"⚠️ {result['message']}")
                        break
                
                # Check if we moved to formResponse (Success!)
                # A true success page usually has no more form questions left.
                question_items_left = await page.locator('div[role="listitem"]').count()
                
                curr_url = page.url
                if "formResponse" in curr_url and question_items_left == 0:
                    page_text = await page.content()
                    if "Your response has been recorded" in page_text or "บันทึกคำตอบของคุณแล้ว" in page_text:
                        result["success"] = True
                        result["message"] = "Form submitted successfully."
                        log_info("✅ ส่งแบบสอบถามสำเร็จแล้ว!")
                        break
                    else:
                        result["success"] = True
                        result["message"] = "Form submitted successfully. (Custom confirmation page)"
                        log_info("✅ ส่งแบบสอบถามสำเร็จแล้ว!")
                        break
                        
                # If we clicked submit and we are still on the form view without formResponse, try checking success text just in case
                if is_final_submit:
                    page_text = await page.content()
                    if "Your response has been recorded" in page_text or "บันทึกคำตอบของคุณแล้ว" in page_text:
                        result["success"] = True
                        result["message"] = "Form submitted successfully."
                        log_info("✅ ส่งแบบสอบถามสำเร็จแล้ว!")
                        break
                    # Wait a bit longer then check again
                    try:
                        await page.wait_for_url("**/formResponse*", timeout=8000)
                        result["success"] = True
                        result["message"] = "Form submitted successfully."
                        log_info("✅ ส่งแบบสอบถามสำเร็จแล้ว!")
                    except:
                        result["message"] = "Submit button was clicked, but the confirmation page did not load. The form might have unsupported required fields."
                        log_info("⚠️ กดปุ่มส่งแต่หน้าจอไม่เปลี่ยนเป็นหน้ายืนยันความสำเร็จ")
                    break
                
                # If we get here, it means we clicked Next and we are now moving to the next iteration of the loop
                log_info(f"หน้าที่ {pages_processed} ทำงานเสร็จสิ้น กำลังไปหน้าถัดไป...")
            
            # Take a screenshot of the final state
            try:
                os.makedirs("static", exist_ok=True)
                shot_name = f"result_{int(time.time())}.png"
                shot_path = os.path.join("static", shot_name)
                await page.screenshot(path=shot_path, full_page=True)
                result["screenshot"] = "/" + shot_path.replace("\\", "/")
                log_info("📸 บันทึกภาพหน้าจอผลลัพธ์สุดท้ายแล้ว")
            except Exception as e:
                log_info(f"⚠️ ไม่สามารถบันทึกภาพหน้าจอได้: {e}")
            
        except Exception as e:
            msg = f"An error occurred: {str(e)}"
            result["message"] = msg
            log_info(f"❌ {msg}")
        
        finally:
            await browser.close()
            
    return result

# For local testing if run directly
if __name__ == "__main__":
    test_url = input("Enter Google Form URL: ")
    test_email = input("Enter Email (optional): ")
    res = asyncio.run(fill_google_form(test_url, test_email))
    print(res)
