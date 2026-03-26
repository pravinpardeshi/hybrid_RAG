
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import ollama

from database import init_db, seed_data, add_policy
from rag_engine import retrieve_policies
from ollama import AsyncClient
import time

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.on_event("startup")
def startup():
    init_db()
    seed_data()

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/ask_old")
async def ask_question_old(question: str = Form(...), amount: float = Form(None)):

    print("➡ Request received")
    start = time.time()

    policies = retrieve_policies(question, amount)
    print("✅ Retrieval done:", time.time() - start)

    context_parts = []
    policy_debug = []

    for title, content, matched, score in policies:

        context_parts.append(content)

        policy_debug.append({
            "title": title,
            "matched": matched,
            "score": round(score, 2)
        })

    context = "\n".join(context_parts)

    prompt = f"""
    You are a policy assistant.
    Answer the user question using ONLY the policy context.

    Policy Context:
    {context}

    Question: {question}
    Answer clearly:
    """

    print('Making LLM Call')

    llm_start = time.time()

    response = ollama.chat( model="llama3.1", messages=[{"role": "user", "content": prompt}],)

    # Async call
    # await get_llm_answer( prompt )

    print("🔥 LLM done:", time.time() - llm_start)
    print("🏁 Total:", time.time() - start)

    return { "answer": response['message']['content'], "policies": policy_debug }


@app.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})

@app.post("/admin/add")
async def admin_add(
    title: str = Form(...),
    category: str = Form(...),
    min_amount: float = Form(...),
    max_amount: float = Form(...),
    content: str = Form(...),
):
    add_policy(title, category, min_amount, max_amount, content)
    return {"status": "ok"}


@app.post("/ask")
async def ask_question( question: str = Form(...), amount: float = Form(None), weight: float = Form(0.6)):

    policies = retrieve_policies(question, amount, weight=weight)

    context = "\n".join([p["content"] for p in policies])

    prompt = f"""
            Answer briefly using only the policy context.

            {context}

            Question: {question}
            """

    response = ollama.chat(
        model="llama3.1",
        messages=[{"role": "user", "content": prompt}]
    )

    return {
        "answer": response['message']['content'],
        "policies": policies
    }


