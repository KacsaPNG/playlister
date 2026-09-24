# 🚀 Deploying Playlister Web to Netlify

A clean, modern, professional web playlist where guests can submit music via **Artist** and **Song Title**. The app automatically finds the pure audio version on YouTube Music (skipping video clips) and adds it to the playlist. Includes an admin **Dev View** with password security, password change capabilities, and live song removal.

---

## 🌟 Key Features

1. **Clean Submission (Artist & Song Title Only)**:
   - Guests simply enter the **Artist** and **Song Title**.
   - No unnecessary name, note, or manual URL fields.
   - The server searches YouTube Music / YouTube with audio-priority heuristics (prefers "Official Audio", album tracks, and Topic releases; strictly filters out music video clips, acting skits, short films, and teasers).

2. **No Placeholder Songs**:
   - The playlist starts completely clean and empty.
   - Live updates automatically refresh the list for all connected visitors.

3. **Dev View (Password-Protected & Changeable)**:
   - To enter Dev View, click **"Dev View"** in the top navigation.
   - You must know the password to log in — no hints or bypass buttons.
   - **Default initial password**: `dj2026`.
   - Once logged in, click **"Change Password"** to set your own custom password.
   - In Dev View, you can **remove any song** from the playlist with one click or reorder tracks.

4. **Seamless Local & Desktop App Sync**:
   - Running `npm run dev` in `web/` powers both the frontend and the local API on `http://localhost:5173/api/playlist`.
   - In the PlaylisterAG desktop app, click **`🌐 NETLIFY SYNC`** to import songs into Deck A / Deck B or remove songs from the web playlist.

---

## ⚡ Deployment Instructions

### Method 1: Git-Connected Netlify Deployment (Recommended)

1. Push this repository to your GitHub, GitLab, or Bitbucket account.
2. Go to [Netlify](https://app.netlify.com/) and click **"Add new site"** ➔ **"Import an existing project"**.
3. Select this repository.
4. Netlify will automatically detect [`netlify.toml`](file:///netlify.toml):
   - **Base directory**: `web`
   - **Build command**: `npm run build`
   - **Publish directory**: `dist`
   - **Functions directory**: `netlify/functions`
5. Click **"Deploy site"**!

Your site will be live at `https://<your-site-name>.netlify.app`.

---

### Method 2: Netlify CLI Direct Deploy

```bash
# Navigate to web directory
cd web

# Build for production
npm run build

# Deploy to Netlify
npx netlify deploy --prod --dir=dist --functions=netlify/functions
```

---

## 🧪 Local Testing

```bash
# Run web app locally (port 5173 with built-in API)
cd web
npm run dev

# Run Vitest test suite
npm test

# Run Oxlint
npm run lint
```
