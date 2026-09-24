import react from '@vitejs/plugin-react'
import { defineConfig, type Plugin } from 'vite'
// @ts-expect-error yt-search untyped
import ytSearch from 'yt-search'
import type { IncomingMessage, ServerResponse } from 'http'

interface TrackItem {
  id: string;
  title: string;
  artist: string;
  url: string;
  thumbnailUrl?: string;
  youtubeId?: string;
  upvotes: number;
  status: 'playing' | 'queued' | 'played';
  createdAt: number;
}

// In-memory store for local Vite development
let devTracks: TrackItem[] = [];

// Helper to find the audio version (not video clip)
async function searchAudioOnlyTrack(title: string, artist: string) {
  const queries = [
    `${artist} - ${title} Audio`,
    `${artist} ${title} Official Audio`,
    `${artist} ${title} Topic`,
    `${artist} ${title}`,
  ];

  const videoKeywords = /\b(music\s*video|official\s*video|official\s*music\s*video|\bmv\b|video\s*clip|short\s*film|visualizer)\b/i;
  const audioKeywords = /\b(official\s*audio|audio\s*only|album\s*version|original\s*mix|full\s*audio|\baudio\b)\b/i;

  for (const q of queries) {
    try {
      const searchResult = await ytSearch(q);
      const videos = searchResult.videos?.slice(0, 10) || [];
      if (!videos.length) continue;

      const scored = videos.map((v: any) => {
        const titleLower = (v.title || '').toLowerCase();
        const authorLower = (v.author?.name || '').toLowerCase();
        let score = 0;

        if (audioKeywords.test(titleLower)) score += 50;
        if (authorLower.includes('topic')) score += 40;
        if (authorLower.includes('vevo')) score += 10;
        if (videoKeywords.test(titleLower)) score -= 60;

        // Prefer normal song duration (2 to 7 minutes)
        const dur = v.duration?.seconds || 0;
        if (dur >= 120 && dur <= 420) score += 15;
        if (dur > 600) score -= 30; // penalize 10+ min extended films/clips

        return { v, score };
      });

      scored.sort((a: any, b: any) => b.score - a.score);
      const best = scored[0]?.v;
      if (best) {
        return {
          url: `https://www.youtube.com/watch?v=${best.videoId}`,
          youtubeId: best.videoId,
          thumbnailUrl: best.thumbnail || `https://img.youtube.com/vi/${best.videoId}/hqdefault.jpg`,
          foundTitle: best.title,
          foundArtist: best.author?.name || artist,
        };
      }
    } catch (err) {
      console.warn('ytSearch error for query:', q, err);
    }
  }
  return null;
}

function parseJsonBody(req: IncomingMessage): Promise<any> {
  return new Promise((resolve) => {
    let body = '';
    req.on('data', (chunk) => {
      body += chunk;
    });
    req.on('end', () => {
      try {
        resolve(JSON.parse(body || '{}'));
      } catch {
        resolve({});
      }
    });
  });
}

function playlistApiDevPlugin(): Plugin {
  return {
    name: 'playlist-api-dev-server',
    configureServer(server) {
      server.middlewares.use(async (req: IncomingMessage, res: ServerResponse, next: () => void) => {
        const url = req.url || '';
        if (url === '/api/playlist' || url.startsWith('/api/playlist?')) {
          res.setHeader('Content-Type', 'application/json');
          res.setHeader('Access-Control-Allow-Origin', '*');
          res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
          res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

          if (req.method === 'OPTIONS') {
            res.statusCode = 204;
            res.end();
            return;
          }

          if (req.method === 'GET') {
            res.statusCode = 200;
            res.end(
              JSON.stringify({
                success: true,
                tracks: devTracks,
                nowPlaying: null,
                counts: {
                  total: devTracks.length,
                  queued: devTracks.length,
                  played: 0,
                },
                timestamp: Date.now(),
              })
            );
            return;
          }

          if (req.method === 'POST') {
            const body = await parseJsonBody(req);
            const action = body.action || 'submit';

            if (action === 'submit') {
              const title = (body.title || '').trim();
              const artist = (body.artist || '').trim();

              if (!title || !artist) {
                res.statusCode = 400;
                res.end(JSON.stringify({ success: false, error: 'Artist and Song Title are required.' }));
                return;
              }

              const found = await searchAudioOnlyTrack(title, artist);
              if (!found) {
                res.statusCode = 404;
                res.end(
                  JSON.stringify({
                    success: false,
                    error: `Could not find an audio version for "${title}" by ${artist} on YouTube Music.`,
                  })
                );
                return;
              }

              // Check duplicates
              if (devTracks.some((t) => t.youtubeId === found.youtubeId)) {
                res.statusCode = 409;
                res.end(JSON.stringify({ success: false, error: 'This song is already in the playlist.' }));
                return;
              }

              const newTrack: TrackItem = {
                id: 'track-' + Date.now() + '-' + Math.random().toString(36).slice(2, 7),
                title: title,
                artist: artist,
                url: found.url,
                thumbnailUrl: found.thumbnailUrl,
                youtubeId: found.youtubeId,
                upvotes: 0,
                status: 'queued',
                createdAt: Date.now(),
              };

              devTracks.push(newTrack);
              res.statusCode = 201;
              res.end(
                JSON.stringify({
                  success: true,
                  message: 'Track added to playlist!',
                  track: newTrack,
                  tracks: devTracks,
                })
              );
              return;
            }

            if (action === 'remove') {
              const id = body.id;
              devTracks = devTracks.filter((t) => t.id !== id);
              res.statusCode = 200;
              res.end(JSON.stringify({ success: true, tracks: devTracks }));
              return;
            }

            if (action === 'reorder') {
              const id = body.id;
              const dir = body.direction;
              const idx = devTracks.findIndex((t) => t.id === id);
              if (idx !== -1) {
                if (dir === 'up' && idx > 0) {
                  [devTracks[idx - 1], devTracks[idx]] = [devTracks[idx], devTracks[idx - 1]];
                } else if (dir === 'down' && idx < devTracks.length - 1) {
                  [devTracks[idx + 1], devTracks[idx]] = [devTracks[idx], devTracks[idx + 1]];
                }
              }
              res.statusCode = 200;
              res.end(JSON.stringify({ success: true, tracks: devTracks }));
              return;
            }

            if (action === 'upvote') {
              const id = body.id;
              devTracks = devTracks.map((t) => (t.id === id ? { ...t, upvotes: t.upvotes + 1 } : t));
              res.statusCode = 200;
              res.end(JSON.stringify({ success: true, tracks: devTracks }));
              return;
            }

            if (action === 'clear') {
              devTracks = [];
              res.statusCode = 200;
              res.end(JSON.stringify({ success: true, tracks: [] }));
              return;
            }

            res.statusCode = 400;
            res.end(JSON.stringify({ success: false, error: 'Unknown action.' }));
            return;
          }
        }
        next();
      });
    },
  };
}

export default defineConfig({
  plugins: [react(), playlistApiDevPlugin()],
  // @ts-expect-error vitest config
  test: {
    environment: 'jsdom',
    globals: true,
  },
})
