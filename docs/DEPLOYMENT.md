# Deployment Guide (Free Tier)

This guide explains how to deploy the ADK RAG system using completely free services:
- **Frontend**: Netlify (Free Tier)
- **Backend**: Render (Free Tier)
- **Vector Database**: Pinecone (Free Tier)
- **LLM / Embeddings**: Google Gemini API (Free Tier)

---

## 1. Prepare Your Repository

First, push your local code to a GitHub repository:

1. Create a new repository on [GitHub](https://github.com/new).
2. Push your code:
   ```bash
   git add .
   git commit -m "Prepare for deployment"
   git push origin main
   ```

---

## 2. Deploy Backend to Render

Render will host the FastAPI backend.

1. Go to [Render](https://render.com/) and sign in with GitHub.
2. Click **New +** and select **Web Service**.
3. Choose **Build and deploy from a Git repository** and connect your GitHub repository.
4. Fill in the deployment settings:
   - **Name**: `adk-rag-backend` (or similar)
   - **Region**: Choose the closest region.
   - **Branch**: `main`
   - **Root Directory**: `.` (Leave blank)
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.api:app --host 0.0.0.0 --port $PORT`
5. Select the **Free** instance type.
6. Scroll down to **Environment Variables** and add the following:
   - `GOOGLE_API_KEY`: Your Gemini API key.
   - `PINECONE_API_KEY`: Your Pinecone API key.
   - `PINECONE_INDEX_NAME`: `adk-rag-index`
   - `TOP_K`: `5`
7. Click **Create Web Service**.

Wait for the deployment to finish (it may take 5-10 minutes). Once complete, copy the **Render URL** (e.g., `https://adk-rag-backend.onrender.com`).

> **Note on Free Tier**: Render's free tier sleeps after 15 minutes of inactivity. The first request after a sleep period may take 30-60 seconds to respond as the server spins back up.

---

## 3. Deploy Frontend to Netlify

Netlify will host the React frontend. The frontend needs to know where the backend is hosted.

1. Go to [Netlify](https://www.netlify.com/) and sign in with GitHub.
2. Click **Add new site** > **Import an existing project**.
3. Connect to GitHub and select your repository.
4. Fill in the build settings:
   - **Base directory**: `frontend`
   - **Build command**: `npm run build`
   - **Publish directory**: `frontend/dist`
5. Click **Add environment variables** and add:
   - `VITE_API_URL`: Your Render backend URL (e.g., `https://adk-rag-backend.onrender.com`)
6. Click **Deploy site**.

Netlify will automatically build and publish your React app. The configuration in `frontend/netlify.toml` automatically handles SPA routing for React Router.

---

## 4. Test the Deployed System

1. Open the Netlify URL (e.g., `https://your-site-name.netlify.app`).
2. Log in with a User ID.
3. Upload a document (this will extract, chunk, embed with Gemini, and store in Pinecone).
4. Go to the Chat tab and test asking questions!

### Troubleshooting

- **Frontend says API Offline**: Ensure your `VITE_API_URL` exactly matches the Render URL (without a trailing slash). Also, wait ~60 seconds to ensure the Render free tier instance has woken up.
- **Upload fails**: Check the Render deployment logs. Ensure `GOOGLE_API_KEY` and `PINECONE_API_KEY` are correct.
