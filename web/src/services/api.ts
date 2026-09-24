import type { Track, PlaylistResponse, SubmitTrackInput } from "../types";

const LOCAL_STORAGE_KEY = "playlister_tracks_v2";

function getStoredTracks(): Track[] {
  try {
    const raw = localStorage.getItem(LOCAL_STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) return parsed;
    }
  } catch { /* ignore */ }
  return [];
}

function saveStoredTracks(tracks: Track[]) {
  try {
    localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(tracks));
  } catch { /* ignore */ }
}

async function apiCall(body: unknown): Promise<Response> {
  return fetch("/api/playlist", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export const PlaylistAPI = {
  async getPlaylist(): Promise<PlaylistResponse> {
    try {
      const res = await fetch("/api/playlist");
      if (res.ok) {
        const data = await res.json();
        if (data.success) {
          saveStoredTracks(data.tracks);
          return data;
        }
      }
    } catch { /* offline fallback */ }

    const local = getStoredTracks();
    const nowPlaying = local.find((t) => t.status === "playing") || null;
    return {
      success: true,
      tracks: local,
      nowPlaying,
      counts: {
        total: local.length,
        queued: local.filter((t) => t.status === "queued").length,
        played: local.filter((t) => t.status === "played").length,
      },
      timestamp: Date.now(),
    };
  },

  async submitTrack(input: SubmitTrackInput): Promise<{ success: boolean; message?: string; error?: string; track?: Track }> {
    try {
      const res = await apiCall({ action: "submit", ...input });
      const data = await res.json();
      if (data.success && data.tracks) {
        saveStoredTracks(data.tracks);
      }
      return data;
    } catch {
      return { success: false, error: "Unable to reach the server. Please try again." };
    }
  },

  async removeTrack(id: string): Promise<{ success: boolean }> {
    try {
      const res = await apiCall({ action: "remove", id });
      const data = await res.json();
      if (data.tracks) saveStoredTracks(data.tracks);
      return data;
    } catch {
      const tracks = getStoredTracks().filter((t) => t.id !== id);
      saveStoredTracks(tracks);
      return { success: true };
    }
  },

  async setNowPlaying(id: string): Promise<{ success: boolean }> {
    try {
      const res = await apiCall({ action: "set-playing", id });
      const data = await res.json();
      if (data.tracks) saveStoredTracks(data.tracks);
      return data;
    } catch {
      const tracks = getStoredTracks().map((t) => ({
        ...t,
        status: (t.id === id ? "playing" : t.status === "playing" ? "played" : t.status) as Track["status"],
      }));
      saveStoredTracks(tracks);
      return { success: true };
    }
  },

  async markPlayed(id: string): Promise<{ success: boolean }> {
    try {
      const res = await apiCall({ action: "mark-played", id });
      const data = await res.json();
      if (data.tracks) saveStoredTracks(data.tracks);
      return data;
    } catch {
      const tracks = getStoredTracks().map((t) =>
        t.id === id ? { ...t, status: "played" as const } : t
      );
      saveStoredTracks(tracks);
      return { success: true };
    }
  },

  async reorderTrack(id: string, direction: "up" | "down"): Promise<{ success: boolean }> {
    try {
      const res = await apiCall({ action: "reorder", id, direction });
      const data = await res.json();
      if (data.tracks) saveStoredTracks(data.tracks);
      return data;
    } catch {
      const tracks = getStoredTracks();
      const idx = tracks.findIndex((t) => t.id === id);
      if (idx !== -1) {
        if (direction === "up" && idx > 0) [tracks[idx - 1], tracks[idx]] = [tracks[idx], tracks[idx - 1]];
        if (direction === "down" && idx < tracks.length - 1) [tracks[idx + 1], tracks[idx]] = [tracks[idx], tracks[idx + 1]];
        saveStoredTracks(tracks);
      }
      return { success: true };
    }
  },

  async upvoteTrack(id: string): Promise<{ success: boolean }> {
    try {
      const res = await apiCall({ action: "upvote", id });
      const data = await res.json();
      if (data.tracks) saveStoredTracks(data.tracks);
      return data;
    } catch {
      const tracks = getStoredTracks().map((t) =>
        t.id === id ? { ...t, upvotes: t.upvotes + 1 } : t
      );
      saveStoredTracks(tracks);
      return { success: true };
    }
  },

  async clearAllTracks(): Promise<{ success: boolean }> {
    try {
      const res = await apiCall({ action: "clear" });
      const data = await res.json();
      saveStoredTracks([]);
      return data;
    } catch {
      saveStoredTracks([]);
      return { success: true };
    }
  },
};
