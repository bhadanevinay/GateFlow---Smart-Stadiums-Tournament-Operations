# Google Cloud Run Deployment Guide — GateFlow
**GCP Project ID:** `gateflow-smart-stadiums`
**Target Service Name:** `gateflow-service`
**Region:** `us-central1` (recommended)

This guide provides step-by-step instructions to build, package, and deploy the GateFlow API application onto Google Cloud Run.

---

## Prerequisites

1. **Google Cloud SDK (`gcloud`)** installed and initialized:
   - Run `gcloud --version` to check.
   - Run `gcloud auth login` to authenticate with your Google account.
2. **Billing Enabled**:
   - Ensure billing is enabled for your Google Cloud project `gateflow-smart-stadiums`.

---

## Deployment Steps

### 1. Set the active GCP Project
Set your CLI context to target the correct project ID:
```bash
gcloud config set project gateflow-smart-stadiums
```

### 2. Enable Required APIs
Enable the APIs for Cloud Run, Artifact Registry, and Cloud Build in your project:
```bash
gcloud services enable \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com
```

### 3. Deploy the Service from Source
Deploy directly from your local project directory. Google Cloud Build will automatically pick up the multi-stage `Dockerfile`, build the optimized container, publish it to Artifact Registry, and deploy it to Cloud Run:
```bash
gcloud run deploy gateflow-service \
    --source . \
    --region us-central1 \
    --allow-unauthenticated
```

During this command:
- It will prompt you to create an Artifact Registry repository if one doesn't exist. Answer `Y`.
- It will build the container on remote Cloud Build runners.
- Once finished, it will output a **Service URL** (e.g., `https://gateflow-service-xxxxxx-uc.a.run.app`).

### 4. Configure Environment Variables (Optional)
If you want to enable the live Google Gemini Phrasing layer, you can configure your API key securely:
```bash
gcloud run services update gateflow-service \
    --region us-central1 \
    --set-env-vars GEMINI_API_KEY="your-gemini-api-key"
```

*Note: If no `GEMINI_API_KEY` is provided, the application will automatically fallback to the offline template-based phrasing layer (so it never crashes or fails startup).*

---

## Verification

To verify that your deployment is live and working:

1. **Test the health endpoint**:
   ```bash
   curl https://<your-service-url>/health
   ```
   *Expected response:* `{"status":"ok"}`

2. **Access the web interface**:
   Open the `<your-service-url>` in your browser to view the interactive dashboard.

3. **Explore interactive API docs**:
   Navigate to `https://<your-service-url>/docs` to test endpoints via the OpenAPI Swagger UI.
