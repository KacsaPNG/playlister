import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import App from "../App";
import { PlaylistAPI } from "../services/api";

describe("Playlister Web Application (Hungarian, No Voting, Standard Guest Default)", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("does not open in dev view by default and renders Hungarian empty state without placeholder songs", async () => {
    // Even if localStorage previously had true, it should start in guest view
    localStorage.setItem("playlister_dev_mode", "true");

    render(<App />);

    expect(screen.getByText("ducky's dj app")).toBeDefined();
    expect(screen.getByText("Zene beküldése")).toBeDefined();
    expect(screen.getByText("A lejátszási lista jelenleg üres")).toBeDefined();

    // Dev View controls must NOT be visible by default
    expect(screen.queryByText(/Fejlesztői nézet:/i)).toBeNull();
    expect(screen.queryByText(/Jelszó módosítása/i)).toBeNull();
    expect(screen.queryByText(/Összes törlése/i)).toBeNull();

    // No placeholder songs
    expect(screen.queryByText("Midnight City")).toBeNull();
    expect(screen.queryByText("One More Time")).toBeNull();

    // No voting buttons or upvote elements
    expect(screen.queryByRole("button", { name: /upvote/i })).toBeNull();
    expect(screen.queryByTitle(/vote/i)).toBeNull();
  });

  it("submits a new song using artist and song title in Hungarian", async () => {
    const submitSpy = vi.spyOn(PlaylistAPI, "submitTrack").mockResolvedValueOnce({
      success: true,
      track: {
        id: "test-track-1",
        title: "Gyöngyhajú lány",
        artist: "Omega",
        url: "https://www.youtube.com/watch?v=CGt-rTDkMcM",
        upvotes: 0,
        status: "queued",
        createdAt: Date.now(),
      },
    });

    vi.spyOn(PlaylistAPI, "getPlaylist").mockResolvedValue({
      success: true,
      tracks: [
        {
          id: "test-track-1",
          title: "Gyöngyhajú lány",
          artist: "Omega",
          url: "https://www.youtube.com/watch?v=CGt-rTDkMcM",
          upvotes: 0,
          status: "queued",
          createdAt: Date.now(),
        },
      ],
      nowPlaying: null,
      counts: { total: 1, queued: 1, played: 0 },
      timestamp: Date.now(),
    });

    render(<App />);

    const artistInput = screen.getByLabelText(/Előadó/i);
    const titleInput = screen.getByLabelText(/Szám címe/i);
    const submitBtn = screen.getByRole("button", { name: /Hozzáadás a lejátszási listához/i });

    fireEvent.change(artistInput, { target: { value: "Omega" } });
    fireEvent.change(titleInput, { target: { value: "Gyöngyhajú lány" } });

    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(submitSpy).toHaveBeenCalledWith({
        artist: "Omega",
        title: "Gyöngyhajú lány",
      });
      expect(screen.getByText("Gyöngyhajú lány")).toBeDefined();
      expect(screen.getByText("Omega")).toBeDefined();
    });

    // Verify there is NO vote button on the track
    expect(screen.queryByRole("button", { name: /upvote/i })).toBeNull();
  });

  it("requires password to enter Dev View, allows removing songs, and allows changing password", async () => {
    vi.spyOn(PlaylistAPI, "getPlaylist").mockResolvedValue({
      success: true,
      tracks: [
        {
          id: "test-track-1",
          title: "Nem szólnak a húrok",
          artist: "Edda Művek",
          url: "https://www.youtube.com/watch?v=xyz",
          upvotes: 0,
          status: "queued",
          createdAt: Date.now(),
        },
      ],
      nowPlaying: null,
      counts: { total: 1, queued: 1, played: 0 },
      timestamp: Date.now(),
    });

    const removeSpy = vi.spyOn(PlaylistAPI, "removeTrack").mockResolvedValueOnce({
      success: true,
    });

    render(<App />);

    // Click Dev View button
    const devBtn = screen.getByRole("button", { name: /Fejlesztői nézet/i });
    fireEvent.click(devBtn);

    // Modal opens in Hungarian without hints
    expect(screen.getByText("Fejlesztői belépés")).toBeDefined();
    expect(screen.queryByText(/alapértelmezett/i)).toBeNull();
    expect(screen.queryByText(/quick unlock/i)).toBeNull();

    // Type wrong password
    const passwordInput = screen.getByPlaceholderText(/Add meg a jelszót/i);
    fireEvent.change(passwordInput, { target: { value: "rosszjelszo" } });
    fireEvent.click(screen.getByRole("button", { name: /Belépés/i }));

    await waitFor(() => {
      expect(screen.getByText("Helytelen jelszó.")).toBeDefined();
    });

    // Type correct password
    fireEvent.change(passwordInput, { target: { value: "dj2026" } });
    fireEvent.click(screen.getByRole("button", { name: /Belépés/i }));

    // Dev View banner & remove button should now be available
    await waitFor(() => {
      expect(screen.getByText(/Fejlesztői nézet: Törlés és átrendezés/i)).toBeDefined();
      expect(screen.getByRole("button", { name: /Nem szólnak a húrok törlése/i })).toBeDefined();
    });

    // Remove song
    const removeBtn = screen.getByRole("button", { name: /Nem szólnak a húrok törlése/i });
    fireEvent.click(removeBtn);

    await waitFor(() => {
      expect(removeSpy).toHaveBeenCalledWith("test-track-1");
    });

    // Change Password
    const changePassBtn = screen.getByRole("button", { name: /Jelszó módosítása/i });
    fireEvent.click(changePassBtn);

    expect(screen.getByRole("heading", { name: /Jelszó módosítása/i })).toBeDefined();
    const currentInput = screen.getByLabelText(/Jelenlegi jelszó/i);
    const newInput = screen.getByLabelText(/^Új jelszó$/i);
    const confirmInput = screen.getByLabelText(/Új jelszó megerősítése/i);

    fireEvent.change(currentInput, { target: { value: "dj2026" } });
    fireEvent.change(newInput, { target: { value: "ujtitok456" } });
    fireEvent.change(confirmInput, { target: { value: "ujtitok456" } });

    fireEvent.click(screen.getByRole("button", { name: /Új jelszó mentése/i }));

    await waitFor(() => {
      expect(screen.getByText("A jelszó sikeresen frissítve!")).toBeDefined();
    });

    expect(localStorage.getItem("playlister_dev_password")).toBe("ujtitok456");
  });
});
