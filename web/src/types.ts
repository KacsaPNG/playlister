export interface Track {
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

export interface PlaylistResponse {
  success: boolean;
  tracks: Track[];
  nowPlaying: Track | null;
  counts: {
    total: number;
    queued: number;
    played: number;
  };
  timestamp: number;
  message?: string;
  error?: string;
}

export interface SubmitTrackInput {
  title: string;
  artist: string;
}
