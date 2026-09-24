import ytSearch from "yt-search";
import { getStore } from "@netlify/blobs";

export interface TrackItem {
  id: string;
  title: string;
  artist: string;
  url: string;
  thumbnailUrl?: string;
  youtubeId?: string;
  upvotes: number;
  status: "playing" | "queued" | "played";
  createdAt: number;
}

// ---------------------------------------------------------------------------
// YouTube Music search – prefer audio-only / official audio results
// ---------------------------------------------------------------------------
async function findYouTubeMusicLink(
  title: string,
  artist: string
): Promise<{ url: string; youtubeId: string; thumbnailUrl: string; foundTitle: string; foundArtist: string } | null> {
  const queries = [
    `${artist} ${title} official audio`,
    `${artist} ${title} audio`,
    `${artist} ${title}`,
  ];

  // Keywords that indicate a music-video clip (lower priority)
  const videoKeywords = /\b(official\s*video|music\s*video|\bmv\b|official\s*mv|lyric\s*video|visualizer|performance|live|concert|version)\b/i;
  // Keywords that indicate pure audio (higher priority)
  const audioKeywords = /\b(official\s*audio|audio\s*only|full\s*song|studio|hq|hd\s*audio|lyrics?)\b/i;

  for (const q of queries) {
    let results;
    try {
      const searchResult = await ytSearch(q);
      results = searchResult.videos?.slice(0, 10) || [];
    } catch {
      continue;
    }

    if (!results.length) continue;

    // Score each result – prefer audio, penalise clips
    const scored = results.map((v) => {
      const combined = `${v.title} ${v.author?.name || ""}`.toLowerCase();
      let score = 0;
      if (audioKeywords.test(v.title)) score += 20;
      if (videoKeywords.test(v.title)) score -= 15;
      // Prefer shorter videos (songs ≤ 10 min)
      const durSec = v.duration?.seconds || 9999;
      if (durSec <= 600) score += 10;
      if (durSec <= 360) score += 5;
      // Penalise very short (< 90 s → probably a promo) or very long (> 15 min)
      if (durSec < 90 || durSec > 900) score -= 10;
      // Prefer results from music-related channels
      if (/vevo|records|music|audio/i.test(combined)) score += 5;
      return { v, score };
    });

    scored.sort((a, b) => b.score - a.score);
    const best = scored[0]?.v;
    if (!best) continue;

    return {
      url: `https://www.youtube.com/watch?v=${best.videoId}`,
      youtubeId: best.videoId,
      thumbnailUrl: best.thumbnail || `https://img.youtube.com/vi/${best.videoId}/hqdefault.jpg`,
      foundTitle: best.title,
      foundArtist: best.author?.name || artist,
    };
  }

  return null;
}

// ---------------------------------------------------------------------------
// Netlify Blobs persistence with in-memory fallback
// ---------------------------------------------------------------------------
let inMemoryTracks: TrackItem[] = [];

async function loadTracks(): Promise<TrackItem[]> {
  try {
    const store = getStore("playlister_queue");
    const data = await store.get("tracks", { type: "json" });
    if (Array.isArray(data)) return data as TrackItem[];
  } catch {
    // fall through to memory
  }
  return inMemoryTracks;
}

async function saveTracks(tracks: TrackItem[]): Promise<void> {
  inMemoryTracks = tracks;
  try {
    const store = getStore("playlister_queue");
    await store.setJSON("tracks", tracks);
  } catch {
    // keep in memory only
  }
}

// ---------------------------------------------------------------------------
// Handler
// ---------------------------------------------------------------------------
export default async function handler(request: Request) {
  const method = request.method.toUpperCase();

  const cors = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
  };

  if (method === "OPTIONS") return new Response(null, { status: 204, headers: cors });

  // GET /api/playlist
  if (method === "GET") {
    const tracks = await loadTracks();
    const nowPlaying = tracks.find((t) => t.status === "playing") || null;
    return new Response(
      JSON.stringify({
        success: true,
        tracks,
        nowPlaying,
        counts: {
          total: tracks.length,
          queued: tracks.filter((t) => t.status === "queued").length,
          played: tracks.filter((t) => t.status === "played").length,
        },
        timestamp: Date.now(),
      }),
      { status: 200, headers: cors }
    );
  }

  // POST /api/playlist
  if (method === "POST") {
    let body: Record<string, unknown>;
    try {
      body = await request.json();
    } catch {
      return new Response(JSON.stringify({ success: false, error: "Invalid JSON body." }), {
        status: 400,
        headers: cors,
      });
    }

    const action = (body.action as string) || "submit";
    let tracks = await loadTracks();

    // ── SUBMIT ──────────────────────────────────────────────────────────────
    if (action === "submit") {
      const title = ((body.title as string) || "").trim();
      const artist = ((body.artist as string) || "").trim();

      if (!title || !artist) {
        return new Response(
          JSON.stringify({ success: false, error: "Both Song Title and Artist are required." }),
          { status: 400, headers: cors }
        );
      }

      // Search YouTube Music for the best audio-only match
      const found = await findYouTubeMusicLink(title, artist);
      if (!found) {
        return new Response(
          JSON.stringify({ success: false, error: `Could not find "${title}" by ${artist} on YouTube Music. Please double-check the spelling.` }),
          { status: 404, headers: cors }
        );
      }

      // Deduplicate by YouTube ID
      if (tracks.some((t) => t.youtubeId === found.youtubeId)) {
        return new Response(
          JSON.stringify({ success: false, error: "This song is already in the playlist." }),
          { status: 409, headers: cors }
        );
      }

      const newTrack: TrackItem = {
        id: "track-" + Date.now() + "-" + Math.random().toString(36).slice(2, 7),
        title: found.foundTitle || title,
        artist: found.foundArtist || artist,
        url: found.url,
        thumbnailUrl: found.thumbnailUrl,
        youtubeId: found.youtubeId,
        upvotes: 0,
        status: "queued",
        createdAt: Date.now(),
      };

      tracks.push(newTrack);
      await saveTracks(tracks);

      return new Response(
        JSON.stringify({ success: true, message: "Track added to playlist!", track: newTrack, tracks }),
        { status: 201, headers: cors }
      );
    }

    // ── REMOVE ──────────────────────────────────────────────────────────────
    if (action === "remove") {
      const id = body.id as string;
      const before = tracks.length;
      tracks = tracks.filter((t) => t.id !== id);
      if (tracks.length === before)
        return new Response(JSON.stringify({ success: false, error: "Track not found." }), { status: 404, headers: cors });
      await saveTracks(tracks);
      return new Response(JSON.stringify({ success: true, tracks }), { status: 200, headers: cors });
    }

    // ── SET-PLAYING ──────────────────────────────────────────────────────────
    if (action === "set-playing") {
      const id = body.id as string;
      tracks = tracks.map((t) => ({
        ...t,
        status: t.id === id ? "playing" : t.status === "playing" ? "played" : t.status,
      }));
      await saveTracks(tracks);
      return new Response(JSON.stringify({ success: true, tracks }), { status: 200, headers: cors });
    }

    // ── MARK-PLAYED ──────────────────────────────────────────────────────────
    if (action === "mark-played") {
      const id = body.id as string;
      tracks = tracks.map((t) => (t.id === id ? { ...t, status: "played" as const } : t));
      await saveTracks(tracks);
      return new Response(JSON.stringify({ success: true, tracks }), { status: 200, headers: cors });
    }

    // ── REORDER ──────────────────────────────────────────────────────────────
    if (action === "reorder") {
      const id = body.id as string;
      const dir = body.direction as "up" | "down";
      const idx = tracks.findIndex((t) => t.id === id);
      if (idx !== -1) {
        if (dir === "up" && idx > 0) [tracks[idx - 1], tracks[idx]] = [tracks[idx], tracks[idx - 1]];
        if (dir === "down" && idx < tracks.length - 1) [tracks[idx + 1], tracks[idx]] = [tracks[idx], tracks[idx + 1]];
        await saveTracks(tracks);
      }
      return new Response(JSON.stringify({ success: true, tracks }), { status: 200, headers: cors });
    }

    // ── UPVOTE ──────────────────────────────────────────────────────────────
    if (action === "upvote") {
      const id = body.id as string;
      tracks = tracks.map((t) => (t.id === id ? { ...t, upvotes: t.upvotes + 1 } : t));
      await saveTracks(tracks);
      return new Response(JSON.stringify({ success: true, tracks }), { status: 200, headers: cors });
    }

    // ── CLEAR ────────────────────────────────────────────────────────────────
    if (action === "clear") {
      await saveTracks([]);
      return new Response(JSON.stringify({ success: true, tracks: [] }), { status: 200, headers: cors });
    }

    return new Response(JSON.stringify({ success: false, error: "Unknown action." }), { status: 400, headers: cors });
  }

  return new Response(JSON.stringify({ error: "Method not allowed." }), { status: 405, headers: cors });
}
