# Proactive Engagement System for Shopify

This project implements a **JavaScript-based engagement system** that tracks user behavior in a Shopify store and uses an LLM to decide whether and when to show a personalized popup message.

## 🚀 Setup Instructions

### Backend

1. Clone this repository and navigate into the `backend` folder:

```bash
git clone <your-repo-url>
cd backend
```

2. Create a virtual environment and install dependencies:

```
python -m venv .venv
source .venv/bin/activate # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

3. Create a .env file in the backend directory:

```
OPENAI_API_KEY=your-openai-key
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
LLM_MODEL=gpt-4o-mini
LLM_TEMPERATURE=0.2
LLM_MAX_TOKENS=150
```

4. Run the backend:

```
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

5. (Optional) Expose your backend to the internet (needed for Shopify) using ngrok or [Cloudflare Tunnel]:

```
ngrok http 8000
```

Copy the HTTPS URL it provides.

---

### Shopify Integration Steps

1. Log into your Shopify Admin and go to:
   Online Store → Themes → Edit code
2. Upload your local `proactive-snippet.js` file (from this repo in folder tracker). Under Assets, upload the file `proactive-snippet.js`.
3. **Or** create new file in assets folder and copy/paste the code and save.
4. Open layout/theme.liquid and before </body> add:

```
<script>
  window.PROACTIVE_API_BASE = "https://<your-ngrok-url>";
</script>
<script src="{{ 'proactive-snippet.js' | asset_url }}" defer></script>
```

4. Save and preview your store.

- The tracker will automatically log page views, clicks (add to cart, quantity changes), and time on site.
- It will periodically send snapshots to your backend at /decide.
- If the LLM decides should_show=true, a popup modal will appear.

### How Prompting Works

- Each snapshot of the session includes:

```
{
"events": [...],
"current_page": "product",
"cart_items": 1,
"time_on_site": 190
}
```

- The backend sends this data to the LLM with a structured prompt:
- Goal: Decide whether a popup should be shown.
- If yes: Generate a short, relevant message for the user.
- The LLM response is expected in JSON:

```
{
"should_show": true,
"message": "Still thinking? Add it to your cart before it's gone!",
"ttl_seconds": 60
}
```

- The frontend receives this response and, if should_show=true, displays a modal with the message.

## ⚙️ Environment Variables

Create a `.env` file in the `backend` directory with the following variables:

| Variable          | Description                                    | Example       |
| ----------------- | ---------------------------------------------- | ------------- |
| `OPENAI_API_KEY`  | API key for OpenAI (or set up Ollama fallback) | `sk-xxxx...`  |
| `BACKEND_HOST`    | Host for the FastAPI server                    | `0.0.0.0`     |
| `BACKEND_PORT`    | Port for the FastAPI server                    | `8000`        |
| `LLM_MODEL`       | Model name to use (OpenAI or Ollama)           | `gpt-4o-mini` |
| `LLM_TEMPERATURE` | Creativity of responses                        | `0.2`         |
| `LLM_MAX_TOKENS`  | Maximum tokens for LLM response                | `150`         |

## Deliverables

- JavaScript tracker (proactive-snippet.js)
- Backend service with FastAPI and LLM integration
- Final Shopify snippet integration
- README with setup, integration, prompting, and environment variables
