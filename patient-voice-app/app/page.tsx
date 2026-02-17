"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { RetellWebClient } from "retell-client-js-sdk";

type CallStatus = "idle" | "connecting" | "active" | "ended";

interface TranscriptEntry {
  role: "agent" | "user";
  content: string;
}

export default function Home() {
  const [patientName, setPatientName] = useState("");
  const [dob, setDob] = useState("");
  const [insuranceId, setInsuranceId] = useState("");

  const [micEnabled, setMicEnabled] = useState(false);
  const [isMuted, setIsMuted] = useState(false);

  const [callStatus, setCallStatus] = useState<CallStatus>("idle");
  const [isAgentTalking, setIsAgentTalking] = useState(false);
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([]);
  const [error, setError] = useState("");

  const retellClientRef = useRef<RetellWebClient | null>(null);
  const transcriptEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [transcript]);

  const setupEventListeners = useCallback((client: RetellWebClient) => {
    client.on("call_started", () => {
      setCallStatus("active");
      setError("");
    });

    client.on("call_ended", () => {
      setCallStatus("ended");
      setIsAgentTalking(false);
    });

    client.on("agent_start_talking", () => {
      setIsAgentTalking(true);
    });

    client.on("agent_stop_talking", () => {
      setIsAgentTalking(false);
    });

    client.on("update", (update) => {
      if (update.transcript) {
        const entries: TranscriptEntry[] = update.transcript.map(
          (t: { role: string; content: string }) => ({
            role: t.role === "agent" ? "agent" : "user",
            content: t.content,
          })
        );
        setTranscript(entries);
      }
    });

    client.on("error", (err) => {
      console.error("Retell error:", err);
      setError("Call error occurred. Please try again.");
      setCallStatus("ended");
    });
  }, []);

  const handleStartCall = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setTranscript([]);
    setCallStatus("connecting");

    try {
      const response = await fetch("/api/create-call", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ patientName, dob, insuranceId }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || "Failed to create call");
      }

      const { accessToken } = await response.json();

      const client = new RetellWebClient();
      retellClientRef.current = client;
      setupEventListeners(client);

      await client.startCall({ accessToken });

      if (!micEnabled) {
        client.mute();
        setIsMuted(true);
      } else {
        setIsMuted(false);
      }
    } catch (err) {
      console.error("Failed to start call:", err);
      setError(err instanceof Error ? err.message : "Failed to start call");
      setCallStatus("idle");
    }
  };

  const handleEndCall = () => {
    retellClientRef.current?.stopCall();
    setCallStatus("ended");
    setIsAgentTalking(false);
  };

  const handleToggleMute = () => {
    const client = retellClientRef.current;
    if (!client) return;
    if (isMuted) {
      client.unmute();
      setIsMuted(false);
    } else {
      client.mute();
      setIsMuted(true);
    }
  };

  const handleReset = () => {
    setCallStatus("idle");
    setTranscript([]);
    setError("");
    retellClientRef.current = null;
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-50 p-4 font-sans dark:bg-zinc-950">
      <div className="w-full max-w-lg">
        <h1 className="mb-8 text-center text-2xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-100">
          Patient Voice Call
        </h1>

        {/* Patient Info Form */}
        <form onSubmit={handleStartCall} className="rounded-xl border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
          <h2 className="mb-4 text-lg font-medium text-zinc-800 dark:text-zinc-200">
            Patient Information
          </h2>

          <div className="space-y-4">
            <div>
              <label htmlFor="patientName" className="mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300">
                Patient Name
              </label>
              <input
                id="patientName"
                type="text"
                required
                value={patientName}
                onChange={(e) => setPatientName(e.target.value)}
                disabled={callStatus !== "idle"}
                placeholder="John Doe"
                className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm text-zinc-900 placeholder-zinc-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:cursor-not-allowed disabled:bg-zinc-100 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100 dark:placeholder-zinc-500 dark:disabled:bg-zinc-800/50"
              />
            </div>

            <div>
              <label htmlFor="dob" className="mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300">
                Date of Birth
              </label>
              <input
                id="dob"
                type="date"
                required
                value={dob}
                onChange={(e) => setDob(e.target.value)}
                disabled={callStatus !== "idle"}
                className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm text-zinc-900 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:cursor-not-allowed disabled:bg-zinc-100 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100 dark:disabled:bg-zinc-800/50"
              />
            </div>

            <div>
              <label htmlFor="insuranceId" className="mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300">
                Insurance ID
              </label>
              <input
                id="insuranceId"
                type="text"
                required
                value={insuranceId}
                onChange={(e) => setInsuranceId(e.target.value)}
                disabled={callStatus !== "idle"}
                placeholder="INS-123456789"
                className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm text-zinc-900 placeholder-zinc-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:cursor-not-allowed disabled:bg-zinc-100 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100 dark:placeholder-zinc-500 dark:disabled:bg-zinc-800/50"
              />
            </div>
            <div className="flex items-center justify-between">
              <div>
                <label htmlFor="micToggle" className="block text-sm font-medium text-zinc-700 dark:text-zinc-300">
                  Enable Microphone
                </label>
                <p className="text-xs text-zinc-500 dark:text-zinc-400">
                  Turn on to enable two-way audio
                </p>
              </div>
              <button
                id="micToggle"
                type="button"
                role="switch"
                aria-checked={micEnabled}
                onClick={() => setMicEnabled(!micEnabled)}
                disabled={callStatus !== "idle"}
                className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 ${
                  micEnabled ? "bg-blue-600" : "bg-zinc-300 dark:bg-zinc-600"
                }`}
              >
                <span
                  className={`pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow-sm transition-transform ${
                    micEnabled ? "translate-x-5" : "translate-x-0"
                  }`}
                />
              </button>
            </div>
          </div>

          {error && (
            <p className="mt-4 text-sm text-red-600 dark:text-red-400">{error}</p>
          )}

          <div className="mt-6 flex gap-3">
            {callStatus === "idle" && (
              <button
                type="submit"
                className="w-full rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
              >
                Start Call
              </button>
            )}

            {callStatus === "connecting" && (
              <button
                type="button"
                disabled
                className="w-full rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white opacity-75"
              >
                Connecting...
              </button>
            )}

            {callStatus === "active" && (
              <>
                <button
                  type="button"
                  onClick={handleToggleMute}
                  className={`rounded-lg px-4 py-2.5 text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 ${
                    isMuted
                      ? "bg-zinc-200 text-zinc-700 hover:bg-zinc-300 focus:ring-zinc-400 dark:bg-zinc-700 dark:text-zinc-200 dark:hover:bg-zinc-600"
                      : "bg-green-600 text-white hover:bg-green-700 focus:ring-green-500"
                  }`}
                >
                  {isMuted ? "🎤 Unmute" : "🔇 Mute"}
                </button>
                <button
                  type="button"
                  onClick={handleEndCall}
                  className="flex-1 rounded-lg bg-red-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
                >
                  End Call
                </button>
              </>
            )}

            {callStatus === "ended" && (
              <button
                type="button"
                onClick={handleReset}
                className="w-full rounded-lg bg-zinc-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-zinc-700 focus:outline-none focus:ring-2 focus:ring-zinc-500 focus:ring-offset-2"
              >
                New Call
              </button>
            )}
          </div>
        </form>

        {/* Call Status & Transcript */}
        {callStatus !== "idle" && (
          <div className="mt-4 rounded-xl border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
            {/* Status indicator */}
            <div className="mb-4 flex items-center gap-2">
              <span
                className={`inline-block h-2.5 w-2.5 rounded-full ${
                  callStatus === "active"
                    ? isAgentTalking
                      ? "animate-pulse bg-green-500"
                      : "bg-green-500"
                    : callStatus === "connecting"
                    ? "animate-pulse bg-yellow-500"
                    : "bg-zinc-400"
                }`}
              />
              <span className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
                {callStatus === "connecting" && "Connecting..."}
                {callStatus === "active" &&
                  (isAgentTalking ? "Agent speaking" : "Listening")}
                {callStatus === "ended" && "Call ended"}
              </span>
            </div>

            {/* Transcript */}
            {transcript.length > 0 && (
              <div>
                <h3 className="mb-2 text-sm font-medium text-zinc-600 dark:text-zinc-400">
                  Transcript
                </h3>
                <div className="max-h-64 space-y-2 overflow-y-auto rounded-lg bg-zinc-50 p-3 dark:bg-zinc-800/50">
                  {transcript.map((entry, i) => (
                    <div key={i} className="text-sm">
                      <span
                        className={`font-medium ${
                          entry.role === "agent"
                            ? "text-blue-600 dark:text-blue-400"
                            : "text-zinc-700 dark:text-zinc-300"
                        }`}
                      >
                        {entry.role === "agent" ? "Agent" : "You"}:
                      </span>{" "}
                      <span className="text-zinc-600 dark:text-zinc-400">
                        {entry.content}
                      </span>
                    </div>
                  ))}
                  <div ref={transcriptEndRef} />
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
