import express from "express";
import path from "path";
import dotenv from "dotenv";
import { GoogleGenAI, Type } from "@google/genai";

dotenv.config();

const app = express();
const port = process.env.PORT || 3000;

app.use(express.json({ limit: "50mb" }));
app.use(express.urlencoded({ extended: true, limit: "50mb" }));

// Initialize Google GenAI client according to skill requirements
const ai = new GoogleGenAI({
  apiKey: process.env.GEMINI_API_KEY,
  httpOptions: {
    headers: {
      "User-Agent": "aistudio-build",
    },
  },
});

// JARVIS system prompt
const JARVIS_SYSTEM_PROMPT = `You are J.A.R.V.I.S. (Just A Rather Very Intelligent System), the iconic, sophisticated, unflappable AI assistant.
Your demeanor is polite, articulate, calm, razor-sharp, and subtly British.
You address the user as "sir", "boss", or in an impeccably courteous manner.

The user interacts primarily via VOICE.
Your job is to parse the user's intent into executable workspace actions AND provide a natural, concise spoken response (1-2 sentences max for voice clarity).

Possible actions:
1. "CREATE_FOLDER": create a new folder. parameters: { folderName: string, parentPath?: string }
2. "CREATE_FILE": create a new file. parameters: { fileName: string, folderPath?: string, content?: string }
3. "WRITE_FILE": append or overwrite content in a file. parameters: { fileName: string, content: string, mode?: "append" | "overwrite" }
4. "DELETE_FILE": delete a file or folder. parameters: { targetName: string, isFolder?: boolean }
5. "OPEN_FILE": inspect or open a file. parameters: { fileName: string }
6. "TAKE_SCREENSHOT": trigger screen capture. parameters: { analyzeImmediately?: boolean }
7. "CREATE_NOTE": create a quick or detailed note. parameters: { title: string, content: string, tags?: string[], category?: string }
8. "SEARCH_NOTES": search notes. parameters: { query: string }
9. "SUMMARIZE_VIDEO": generate comprehensive notes and breakdown of the current video. parameters: { instructions?: string }
10. "VIDEO_TIMESTAMP_NOTE": capture note at current video playback position. parameters: { note: string }
11. "GENERAL_QUERY": conversation, advice, calculations, code help, or questions. parameters: {}

Always return a valid JSON object matching the requested schema.`;

async function generateContentWithFallback(params: any) {
  const models = ["gemini-3.8-flash", "gemini-flash-latest"];
  let lastError: any = null;

  for (const model of models) {
    try {
      return await ai.models.generateContent({
        ...params,
        model,
      });
    } catch (err: any) {
      lastError = err;
      console.warn(`Model ${model} encounter:`, err.message || err);
      // Brief sleep before attempting fallback model
      await new Promise((r) => setTimeout(r, 400));
    }
  }
  throw lastError;
}

// 1. Voice Command & Intent Parser endpoint
app.post("/api/jarvis/command", async (req, res) => {
  try {
    const { input, context } = req.body;
    if (!input || typeof input !== "string") {
      return res.status(400).json({ error: "Input text is required" });
    }

    const contextStr = context ? `Current Workspace Context: ${JSON.stringify(context)}` : "";

    const response = await generateContentWithFallback({
      contents: `${contextStr}\nUser command: "${input}"`,
      config: {
        systemInstruction: JARVIS_SYSTEM_PROMPT,
        responseMimeType: "application/json",
        responseSchema: {
          type: Type.OBJECT,
          properties: {
            speechResponse: {
              type: Type.STRING,
              description: "Short, elegant spoken reply in JARVIS persona (e.g. 'Right away, sir. Creating folder Project Apex.')",
            },
            action: {
              type: Type.STRING,
              description: "One of CREATE_FOLDER, CREATE_FILE, WRITE_FILE, DELETE_FILE, OPEN_FILE, TAKE_SCREENSHOT, CREATE_NOTE, SEARCH_NOTES, SUMMARIZE_VIDEO, VIDEO_TIMESTAMP_NOTE, GENERAL_QUERY",
            },
            parameters: {
              type: Type.OBJECT,
              properties: {
                folderName: { type: Type.STRING },
                fileName: { type: Type.STRING },
                fileContent: { type: Type.STRING },
                mode: { type: Type.STRING },
                targetName: { type: Type.STRING },
                isFolder: { type: Type.BOOLEAN },
                title: { type: Type.STRING },
                content: { type: Type.STRING },
                category: { type: Type.STRING },
                tags: {
                  type: Type.ARRAY,
                  items: { type: Type.STRING },
                },
                query: { type: Type.STRING },
                note: { type: Type.STRING },
                instructions: { type: Type.STRING },
              },
            },
            fullAnswer: {
              type: Type.STRING,
              description: "Detailed answer if the user asked a technical or general query",
            },
          },
          required: ["speechResponse", "action", "parameters"],
        },
      },
    });

    const parsed = JSON.parse(response.text || "{}");
    return res.json(parsed);
  } catch (error: any) {
    console.error("JARVIS command parsing error:", error);
    return res.status(500).json({
      speechResponse: "I encountered a minor processing anomaly, sir. Let me assist you directly.",
      action: "GENERAL_QUERY",
      parameters: {},
      error: error.message || "Failed to process command",
    });
  }
});

// 2. Multimodal Screenshot Analysis
app.post("/api/jarvis/analyze-screenshot", async (req, res) => {
  try {
    const { imageBase64, prompt } = req.body;
    if (!imageBase64) {
      return res.status(400).json({ error: "Screenshot image is required" });
    }

    const cleanBase64 = imageBase64.replace(/^data:image\/[a-z]+;base64,/, "");

    const response = await generateContentWithFallback({
      contents: {
        parts: [
          {
            inlineData: {
              mimeType: "image/png",
              data: cleanBase64,
            },
          },
          {
            text:
              prompt ||
              "Analyze this screen capture in detail. As JARVIS, summarize what is being displayed, identify code, errors, text, or visual elements, and highlight any notable items or suggestions.",
          },
        ],
      },
      config: {
        systemInstruction:
          "You are JARVIS. Speak clearly, concisely, and with technical competence. Address the user politely as 'sir' or 'boss'. Provide both a comprehensive analysis and a short 1-sentence spoken summary.",
      },
    });

    const analysisText = response.text || "No analysis could be generated.";
    return res.json({
      analysis: analysisText,
      speechSummary: `Visual telemetry analyzed, sir. Here is what I observed on your display.`,
    });
  } catch (error: any) {
    console.error("Screenshot analysis error:", error);
    return res.status(500).json({
      error: error.message || "Failed to analyze screenshot",
    });
  }
});

// 3. Video Note-taking & Summarizer
app.post("/api/jarvis/video-notes", async (req, res) => {
  try {
    const { videoTitle, videoUrl, userPrompt, existingNotes, frameBase64, duration, currentTime } = req.body;

    const parts: any[] = [];
    if (frameBase64) {
      parts.push({
        inlineData: {
          mimeType: "image/png",
          data: frameBase64.replace(/^data:image\/[a-z]+;base64,/, ""),
        },
      });
    }

    const promptText = `
Task: Generate structured, professional video notes for this video.
Video Title: ${videoTitle || "User Video Session"}
Video URL/Source: ${videoUrl || "Active Player/Stream"}
Current Timestamp: ${currentTime || "Live"}
Total Duration: ${duration || "Unknown"}
User Directives: ${userPrompt || "Generate a complete breakdown with key concepts, timeline points, and action items."}
User's Realtime Markers: ${JSON.stringify(existingNotes || [])}

Please output a comprehensive, well-structured markdown note document with:
1. Executive Summary (2-3 sentences)
2. Core Takeaways (bullet points)
3. Timestamped Breakdown / Key Moments
4. Action Items & Knowledge Nuggets
`;

    parts.push({ text: promptText });

    const response = await generateContentWithFallback({
      contents: { parts },
      config: {
        systemInstruction:
          "You are JARVIS generating high-density, lucid executive study notes for Tony Stark. Use pristine markdown formatting.",
      },
    });

    return res.json({
      notes: response.text,
      speechResponse: "I have compiled the comprehensive video telemetry and study notes for you, sir.",
    });
  } catch (error: any) {
    console.error("Video note generation error:", error);
    return res.status(500).json({ error: error.message || "Failed to generate video notes" });
  }
});

// 4. High-Fidelity Voice Synthesis (Gemini TTS)
app.post("/api/jarvis/tts", async (req, res) => {
  try {
    const { text, voice } = req.body;
    if (!text) {
      return res.status(400).json({ error: "Text is required" });
    }

    // Use gemini-3.8-flash-lite-tts for fast, crisp audio
    // Voices: 'Charon', 'Fenrir', 'Puck', 'Kore', 'Zephyr'
    const chosenVoice = voice || "Fenrir"; // Fenrir has an authoritative, deep cadence suitable for JARVIS

    const response = await ai.models.generateContent({
      model: "gemini-3.8-flash-lite-tts",
      contents: [
        {
          role: "user",
          parts: [
            {
              text: text,
              speechMetadata: {
                style: "Polite, refined, articulate British gentleman, composed and intelligent",
              },
            },
          ],
        },
      ],
      config: {
        responseModalities: ["AUDIO"],
        speechConfig: {
          voiceConfig: {
            prebuiltVoiceConfig: { voiceName: chosenVoice },
          },
        },
      },
    });

    const base64Audio = response.candidates?.[0]?.content?.parts?.[0]?.inlineData?.data;
    if (!base64Audio) {
      return res.status(500).json({ error: "No audio generated" });
    }

    return res.json({
      audioBase64: base64Audio,
      mimeType: "audio/wav",
    });
  } catch (error: any) {
    // If TTS fails (e.g. rate limit), return graceful status so client can fallback to Web Speech API
    console.warn("Gemini TTS warning:", error.message);
    return res.status(500).json({ error: error.message || "TTS fallback required" });
  }
});

// Setup Vite middleware in dev or static files in production
async function startServer() {
  if (process.env.NODE_ENV !== "production") {
    const { createServer: createViteServer } = await import("vite");
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.resolve(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (_req, res) => {
      res.sendFile(path.resolve(distPath, "index.html"));
    });
  }

  app.listen(port, () => {
    console.log(`JARVIS AI Assistant active on http://0.0.0.0:${port}`);
  });
}

startServer();
