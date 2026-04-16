import { useState, useRef } from 'react';
import axios from 'axios';
import { Mic, Square, Loader2 } from 'lucide-react';

interface VoiceRecorderProps {
  onResponseFetched: (reply: string, data: any[], transcribedText?: string) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

export default function VoiceRecorder({ onResponseFetched, setLoading, setError }: VoiceRecorderProps) {
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const startRecording = async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      // Try to use webm with opus if supported, fallback to default
      const options = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? { mimeType: 'audio/webm;codecs=opus' }
        : undefined;

      const mediaRecorder = new MediaRecorder(stream, options);
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(chunksRef.current, { type: 'audio/webm' });
        // Stop all tracks
        stream.getTracks().forEach(track => track.stop());
        await uploadAudio(audioBlob);
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch (err) {
      console.error(err);
      setError("Microphone access denied or not available.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const uploadAudio = async (blob: Blob) => {
    setIsProcessing(true);
    setLoading(true);
    setError(null);

    const file = new File([blob], "voice_entry.webm", { type: "audio/webm" });
    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await axios.post("http://localhost:8000/api/v1/voice-entry", formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });
      onResponseFetched(response.data.reply || "", response.data.recommendations || [], response.data.transcribed_text);
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || "Failed to process voice entry. Ensure the backend is running.");
    } finally {
      setIsProcessing(false);
      setLoading(false);
    }
  };

  return (
    <button
      onClick={isRecording ? stopRecording : startRecording}
      disabled={isProcessing}
      className={`flex items-center justify-center w-12 h-12 rounded-full transition-all focus:outline-none shrink-0 ${isRecording
        ? 'bg-red-500 hover:bg-red-600 animate-pulse ring-4 ring-red-100 shadow-lg text-white'
        : 'bg-slate-100 hover:bg-slate-200 text-slate-700 shadow-sm'
        } ${isProcessing ? 'opacity-50 cursor-not-allowed bg-slate-200 shadow-none' : ''}`}
      title={isProcessing ? "Processing audio..." : isRecording ? "Stop recording" : "Record your preference"}
    >
      {isProcessing ? (
        <Loader2 className="animate-spin text-slate-500" size={20} />
      ) : isRecording ? (
        <Square className="text-white" fill="currentColor" size={18} />
      ) : (
        <Mic size={20} />
      )}
    </button>
  );
}
