from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse

app = FastAPI()

@app.middleware("http")
async def redirect_http_to_https(request: Request, call_next):
    host = request.headers.get("host", "")
    secure_url = request.url.replace(scheme="https", netloc=host)
    return RedirectResponse(url=str(secure_url))
